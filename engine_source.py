import json
import os
import sys
import urllib.error
import urllib.request
from collections import namedtuple
from itertools import count

ENV_URL = os.environ.get("MAKEFUN_ENV_URL") or sys.exit("MAKEFUN_ENV_URL is not set")

# 120-cell board mailbox layout
A1, H1, A8, H8 = 91, 98, 21, 28
N, E, S, W = -10, 1, 10, -1

directions = {
    "P": (N, N + N, N + W, N + E),
    "N": (N + N + E, E + N + E, E + S + E, S + S + E, S + S + W, W + S + W, W + N + W, N + N + W),
    "B": (N + E, S + E, S + W, N + W),
    "R": (N, E, S, W),
    "Q": (N, E, S, W, N + E, S + E, S + W, N + W),
    "K": (N, E, S, W, N + E, S + E, S + W, N + W),
}

piece = {"P": 100, "N": 320, "B": 330, "R": 500, "Q": 900, "K": 20000}

centre = lambda i: min(i, 7 - i)
pawnAdvance = [0, 0, 4, 8, 14, 24, 40, 0]
pawnCentre = [0, 0, 0, 10, 15, 10, 5, 0]

pst = {}
for k in piece:
    t = [0] * 120
    for sq in range(120):
        r = 9 - (sq // 10)
        f = (sq % 10) - 1
        if 0 <= r < 8 and 0 <= f < 8:
            c = centre(f) + centre(r)
            if k == "P":
                v = pawnAdvance[r] + (pawnCentre[r] if f in (3, 4) else 0)
            elif k == "N":
                v = 6 * c - 20
            elif k == "B":
                v = 4 * c - 8
            elif k == "R":
                v = (15 if r == 6 else 0) + (5 if r == 0 and f in (3, 4) else 0)
            elif k == "Q":
                v = 2 * c - 6
            elif k == "K":
                v = [20, 25, 10, 0, 0, 10, 25, 20][f] if r == 0 else max(-50, -15 * r)
            t[sq] = v + piece[k]
    pst[k] = tuple(t)

k_end = [0] * 120
for sq in range(120):
    r = 9 - (sq // 10)
    f = (sq % 10) - 1
    if 0 <= r < 8 and 0 <= f < 8:
        c = centre(f) + centre(r)
        k_end[sq] = 8 * c - 24 + piece["K"]
K_MID, K_END = pst["K"], tuple(k_end)

MATE_LOWER = piece["K"] - 13 * piece["Q"]
MATE_UPPER = piece["K"] + 10 * piece["Q"]
QS = 40
QS_A = 140
EVAL_ROUGHNESS = 15
TABLE_SIZE = 100000

initial = (
    "         \n"
    "         \n"
    " rnbqkbnr\n"
    " pppppppp\n"
    " ........\n"
    " ........\n"
    " ........\n"
    " ........\n"
    " PPPPPPPP\n"
    " RNBQKBNR\n"
    "         \n"
    "         \n"
)

Move = namedtuple("Move", "i j prom")


class Position(namedtuple("Position", "board score wc bc ep kp")):
    def gen_moves(self):
        for i, p in enumerate(self.board):
            if p not in "PNBRQK":
                continue
            for d in directions[p]:
                for j in count(i + d, d):
                    q = self.board[j]
                    if q in " \nPNBRQK":
                        break
                    if p == "P":
                        if d in (N, N + N) and q != ".":
                            break
                        if d == N + N and (i < A1 + N or self.board[i + N] != "."):
                            break
                        if d in (N + W, N + E) and q == "." and j != self.ep and abs(j - self.kp) > 1:
                            break
                        if A8 <= j <= H8:
                            for prom in "NBRQ":
                                yield Move(i, j, prom)
                            break
                    yield Move(i, j, "")
                    if p in "PNK" or q in "pnbrqk":
                        break
                    if i == A1 and self.board[j + E] == "K" and self.wc[0]:
                        yield Move(j + E, j + W, "")
                    if i == H1 and self.board[j + W] == "K" and self.wc[1]:
                        yield Move(j + W, j + E, "")

    def rotate(self, nullmove=False):
        return Position(
            self.board[::-1].swapcase(),
            -self.score,
            self.bc,
            self.wc,
            119 - self.ep if self.ep and not nullmove else 0,
            119 - self.kp if self.kp and not nullmove else 0,
        )

    def move(self, move):
        i, j, prom = move
        p, q = self.board[i], self.board[j]
        put = lambda board, idx, ch: board[:idx] + ch + board[idx + 1 :]
        board = self.board
        wc, bc, ep, kp = self.wc, self.bc, 0, 0
        score = self.score + self.value(move)
        board = put(board, j, board[i])
        board = put(board, i, ".")
        wc = (wc[0] and i != A1, wc[1] and i != H1)
        bc = (bc[0] and j != H8, bc[1] and j != A8)
        if p == "K":
            wc = (False, False)
            if abs(j - i) == 2:
                kp = (i + j) // 2
                r = A1 if j < i else H1
                board = put(board, r, ".")
                board = put(board, kp, "R")
        if p == "P":
            if A8 <= j <= H8:
                board = put(board, j, prom)
            if j - i == 2 * N:
                ep = i + N
            if j == self.ep:
                board = put(board, j + S, ".")
        return Position(board[::-1].swapcase(), -score, bc, wc, 119 - ep if ep else 0, 119 - kp if kp else 0)

    def value(self, move):
        i, j, prom = move
        p, q = self.board[i], self.board[j]
        score = pst[p][j] - pst[p][i]
        if q in "pnbrqk":
            score += pst[q.upper()][119 - j]
        if abs(j - self.kp) < 2:
            score += pst["K"][119 - j]
        if p == "K" and abs(i - j) == 2:
            score += pst["R"][(i + j) // 2] - pst["R"][A1 if j < i else H1]
        if p == "P":
            if A8 <= j <= H8:
                score += pst[prom][j] - pst["P"][j]
            if j == self.ep:
                score += pst["P"][119 - (j + S)]
        # Bishop pair dynamic evaluation adjustment
        if p == "B" and self.board.count("B") >= 2:
            score += 10
        return score

    def king_capture(self):
        return next((m for m in self.gen_moves() if self.board[m.j] == "k" or abs(m.j - self.kp) < 2), None)


class Stop(Exception):
    pass


Entry = namedtuple("Entry", "lower upper")


class Searcher:
    def __init__(self):
        self.tp_score, self.tp_move, self.history = {}, {}, set()
        self.nodes, self.node_cap = 0, 10000

    def bound(self, pos, gamma, depth, root=False):
        self.nodes += 1
        if self.nodes % 2048 == 0 and self.nodes > self.node_cap:
            raise Stop

        depth = max(depth, 0)
        if pos.score <= -MATE_LOWER:
            return -MATE_UPPER

        if not root:
            entry = self.tp_score.get((pos, depth), Entry(-MATE_UPPER, MATE_UPPER))
            if entry.lower >= gamma:
                return entry.lower
            if entry.upper < gamma:
                return entry.upper
            if depth > 0 and pos in self.history:
                return -200 if pos.score > 50 else 0

        killer = self.tp_move.get(pos)

        def moves():
            if not root and depth > 2 and abs(pos.score) < 500 and any(c in pos.board for c in "RBNQ"):
                score = -self.bound(pos.rotate(nullmove=True), 1 - gamma, depth - 3)
                proof = score >= gamma and (self.tp_move.get(pos) or pos.king_capture())
                if proof and pos.value(proof) >= MATE_LOWER:
                    yield proof, MATE_UPPER
                elif score < gamma or self.bound(pos.rotate(nullmove=True), 1 - MATE_LOWER, depth - 3) >= 1 - MATE_LOWER:
                    yield None, score

            if depth == 0:
                yield None, pos.score

            nonlocal killer
            if not killer and depth > 2:
                self.bound(pos, gamma, depth - 3, root=True)
                killer = self.tp_move.get(pos)

            val_lower = QS - depth * QS_A
            if killer and pos.value(killer) >= val_lower:
                yield killer, -self.bound(pos.move(killer), 1 - gamma, depth - 1)

            for cnt, (val, move) in enumerate(
                sorted(((v, m) for m in pos.gen_moves() if (v := pos.value(m)) >= val_lower), reverse=True)
            ):
                if depth <= 1 and pos.score + val < gamma:
                    yield (move, MATE_UPPER) if val >= MATE_LOWER else (None, pos.score + val)
                    break

                red = depth > 2 and cnt > 2 and val < 60
                score = -self.bound(pos.move(move), 1 - gamma, depth - 2 if red else depth - 1)
                if red and score >= gamma:
                    score = -self.bound(pos.move(move), 1 - gamma, depth - 1)
                yield move, score

        best, live = -MATE_UPPER, False
        for move, score in moves():
            best = max(best, score)
            live |= move is not None and score > -MATE_UPPER
            if best >= gamma:
                if move is not None and depth:
                    self.tp_move[pos] = move
                    if len(self.tp_move) > TABLE_SIZE:
                        del self.tp_move[next(k for k in self.tp_move if k != self.root)]
                break

        if depth and not live and all(pos.move(m).king_capture() for m in pos.gen_moves()):
            best = -MATE_LOWER if pos.rotate(nullmove=True).king_capture() else 0

        if not root:
            self.tp_score[pos, depth] = Entry(best, entry.upper) if best >= gamma else Entry(entry.lower, best)
        if len(self.tp_score) > TABLE_SIZE:
            del self.tp_score[next(iter(self.tp_score))]

        return best

    def search(self, history):
        self.nodes, self.history = 0, set(history)
        self.tp_score.clear()
        pos = self.root = history[-1]

        bare = sum(c.isupper() for c in pos.board) <= 3 or sum(c.islower() for c in pos.board) <= 3
        pst["K"] = K_END if bare else K_MID

        gamma = 0
        for depth in range(1, 100):
            lower, upper, probes = 1 - MATE_UPPER, MATE_UPPER, 0
            while lower < upper - EVAL_ROUGHNESS:
                score = self.bound(pos, gamma, depth, root=True)
                if score >= gamma:
                    lower = max(lower, score)
                else:
                    upper = min(upper, score)
                probes += 1
                yield depth, gamma, score, self.tp_move.get(pos)
                if lower > upper or probes > 40:
                    break
                gamma = (lower + upper + 1) // 2


def parse(c):
    return A1 + ord(c[0]) - ord("a") - 10 * (int(c[1]) - 1)


def render(i):
    return chr((i - A1) % 10 + ord("a")) + str(1 - (i - A1) // 10)


def post(path, body):
    req = urllib.request.Request(
        ENV_URL + path,
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        sys.exit(f"{path}: HTTP {e.code} {e.read().decode(errors='replace')}")


def play():
    searcher = Searcher()
    searcher.node_cap = 10000

    while True:
        g = post("/game", {})
        if g["status"] == "done":
            break

        while g["status"] == "your_move":
            hist = [Position(initial, 0, (True, True), (True, True), 0, 0)]
            for ply, m in enumerate(g["moves"]):
                i, j, prom = parse(m[:2]), parse(m[2:4]), m[4:].upper()
                if ply % 2 == 1:
                    i, j = 119 - i, 119 - j
                hist.append(hist[-1].move(Move(i, j, prom)))

            searcher.nodes = 0
            best_committed = None
            cand = None
            d0 = 1
            is_black = len(hist) % 2 == 0

            try:
                for depth, gamma, score, move in searcher.search(hist):
                    if depth > d0:
                        if cand:
                            best_committed = cand
                        d0 = depth
                    if score >= gamma and move:
                        i, j = move.i, move.j
                        if is_black:
                            i, j = 119 - i, 119 - j
                        cand = render(i) + render(j) + move.prom.lower()
            except Stop:
                pass

            chosen_move = best_committed or cand
            if not chosen_move or chosen_move not in g["legal_moves"]:
                chosen_move = g["legal_moves"][0]

            g = post("/move", {"game": g["game"], "move": chosen_move})

        print(f"game {g['game']}: {g['outcome']} by {g['reason']}", file=sys.stderr)
    print(f"done: {g.get('wins')} won, {g.get('draws')} drawn, {g.get('losses')} lost", file=sys.stderr)


if __name__ == "__main__":
    play()
