# Tiny Chess Engine (4KB)

[![make.fun · tiny-chess-01](https://make.fun/badge/tiny-chess-01.svg)](https://make.fun/bounty/tiny-chess-01?utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01)
[![rank](https://make.fun/badge/tiny-chess-01/MusounoEnma/tiny-chess/rank.svg)](https://make.fun/bounty/tiny-chess-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01)
[![reward](https://make.fun/badge/tiny-chess-01/MusounoEnma/tiny-chess/reward.svg)](https://make.fun/bounty/tiny-chess-01?utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01)

A high-performance compact chess engine written in under 4 KB of Python 3 standard library for the [make.fun tiny-chess-01 bounty](https://make.fun/bounty/tiny-chess-01).

## Features
- Ultra-compact pure Python 3.13 implementation ($\le$ 4,096 bytes)
- MTD-bi search with iterative deepening and transposition table
- Fractional-depth integrated quiescence search and move ordering
- Piece-Square tables, endgame king centralization, and bishop pair heuristics
- Deterministic 10,000-node budget with zero wall-clock search dependency

## Run
```bash
python3 main.py
```
