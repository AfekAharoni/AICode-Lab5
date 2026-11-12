# CLAUDE.md

Python chess game for AICODE Lab 5 (pair/team work). See `README.md` for the full task.

## Commands

```sh
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest          # all tests, including mypy (tests/test_types.py)
mypy                      # type check only; settings in pyproject.toml
python3 server.py         # http://127.0.0.1:8000
```

Before every commit: `python -m pytest` must pass (it includes the type check).

## Layout

- `game.py`: pure rules. A position is `[board, turn]`; `board` maps squares like `"e2"`
  to pieces like `"wP"` (color `w`/`b` + kind `KQRBNP`); `turn` is `"w"` or `"b"`.
  `move()` mutates the position in place; use `copy_position()` before storing it.
- `session.py`: `Session` holds the game (position, notation, opponent) and handles
  actions in `dispatch()`. `reset()` starts a new game; `after_move()` recomputes sidebar
  data and must be called after anything that changes the position.
- `computer.py`: one-move-lookahead opponent (plays Black).
- `server.py`: HTTP server, one in-memory `Session`. `static/`: browser UI only; all rules
  run in Python.
- `tests/`: pytest; one file per feature (e.g. `tests/test_undo.py`).

## Conventions

- Python 3.10+, standard library only at runtime.
- Every new feature comes with tests. Tests drive the game through
  `Session.dispatch({...})` where possible.
- New code should have type annotations; keep `mypy` clean (no blanket `# type: ignore`).
- Record team decisions (e.g. undo behavior against the computer) in `README.md` under
  "Team decisions", and encode them in tests.

## Git workflow

- `origin` = course repo (read only; supplies `feature/captured-pieces`,
  `feature/promotion`). `team` = our repo, https://github.com/AfekAharoni/AICode-Lab5.
- One branch per feature from `team/main`; push to `team`. Merge order into `main`:
  undo and save/load, then `origin/feature/captured-pieces`, then `origin/feature/promotion`.
- After each merge: run the tests and play the game before asking an agent for fixes.
