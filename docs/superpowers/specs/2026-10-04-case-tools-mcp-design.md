# case-tools MCP server: design

Python MCP server that validates, solves and lints Cold Trail case files. Goals: (1) give the team (esp. `game-designer`) a fast feedback loop while writing cases; (2) learn how to build MCP servers (tools, resources, prompts, stdio, testing over the protocol).

## Decisions
- Language: Python (>= 3.10), official `mcp` Python SDK 2.x, pinned `mcp>=2.3,<3` (checked 2026-10-04). In 2.x FastMCP was renamed: `from mcp.server.mcpserver import MCPServer`; tool results expose `is_error` / `structured_content` (snake_case).
- Independent of the C++ build: validation and solving are reimplemented in Python. Drift risk is covered by a parity test (see Tests).
- Transport: stdio only. Registered for the team in `.mcp.json` at the repo root.
- Scope: files `data/*.json` only. No subdirectories, no `..`, no absolute paths.
- Approach: package with a pure core and a thin MCP layer. Core functions know nothing about MCP.
- Packaging: `pip` + `venv` (no `uv` required), `pyproject.toml`, tests with pytest.

## Structure
```
tools/case-tools/
  pyproject.toml
  src/case_tools/
    model.py      # dataclasses mirroring docs/case-format.md
    validate.py   # list of Issue objects
    solve.py      # reachability + ordered solution steps
    lint.py       # soft quality warnings
    server.py     # MCPServer: tools, resource, prompt
    __main__.py   # `python -m case_tools`
  tests/
.mcp.json         # repo root, registers the server
```

## Core (pure functions)
All take a parsed `Case`; none import `mcp`.
- `model.py`: `Case`, `Location`, `Person`, `Item`, `Clue`, `TalkLine`, `Solution`. JSON -> `Case` with the stdlib only. Field names follow the contract in `docs/case-format.md`.
- `validate.py`: returns `list[Issue]` (`severity`, `code`, `message`, `path`) instead of raising, so the model sees all problems in one call. Checks: id references resolve (`start`, exits, location items, person `location`, talk `requires`/`reveals`, item `reveals`, `killer`, `required_clues`); ids unique per kind; **new vs. C++:** names unique case-insensitively across locations/people/items, ids lowercase snake_case; required keys present; wrong JSON types reported, not crashed on.
- `solve.py`: same semantics as the C++ engine: exits are one-way, an item is examinable only in its own location, a person is talkable only where they stand, a talk line is shown only if its `requires` clue is found, a line can unlock a later line in the same talk. Returns obtainable clues in discovery order as steps (`go X`, `examine Y`, `talk Z`), and whether all `required_clues` are obtainable.
- `lint.py`: warnings: counts outside 5-6 locations / 4-5 people / 8-10 clues; no red herring (every clue required); talk-unlock chain deeper than 3; unobtainable clue; empty `explanation`; suspect with no talk lines.

## MCP layer (`server.py`)
- Tools (each takes `path`, relative, must match `data/<name>.json`): `validate_case`, `solve_case`, `lint_case`. Results are structured (issues / steps / warnings), never free text only.
- Resource: `case-format://spec` serves `docs/case-format.md`.
- Prompt: `design_case(theme)`: template for `game-designer`: read the format, design the case, run the three tools until clean.
- Path guard: one function resolves and checks the path against the repo's `data/` dir; violations return an error result (not a traceback).
- Errors: unreadable file, invalid JSON or a rejected path become a structured result with an `error` field (a raised exception would reach the client only as a generic "Error executing tool", verified on mcp 2.3.0); the server never crashes on a bad case. Tool results are typed pydantic models so clients get `structured_content`.
- stdio hygiene: nothing is ever printed to stdout except protocol messages.

## Tests (pytest, owned by qa)
- Core: small case dicts built in the tests, one defect per test (dangling ref, duplicate name, non-snake_case id, unreachable clue, unlock cycle). `solve` tests assert step order.
- Parity with C++: `validate` and `solve` on `data/case01.json` and on the mini case from `tests/test_support.h` (same JSON content) must report no errors and all required clues obtainable.
- Protocol: start the server over stdio with the SDK client, call all three tools, read the resource and prompt, assert a path outside `data/` is rejected.

## CI
New job in `.github/workflows/pr-build.yml`: ubuntu-latest, set up Python, `python -m pip install -e "tools/case-tools[dev]"`, `pytest tools/case-tools`. The existing C++ matrix is unchanged.

## Team and lanes
| Who | Owns |
|---|---|
| programmer | `tools/case-tools/src/`, `tools/case-tools/pyproject.toml` |
| qa | `tools/case-tools/tests/` (writes tests first) |
| Lead | `.mcp.json`, CI workflow, agent files, `CLAUDE.md`, `README.md` |
| game-designer | no code; `.claude/agents/game-designer.md` gets `mcp__case-tools__validate_case`, `mcp__case-tools__solve_case`, `mcp__case-tools__lint_case` in `tools:` |

Process as in `CLAUDE.md`: Lead reviews the PR first (comment only), the user reviews and merges; remarks are fixed by the programmer.

## Documentation
`README.md` gets an architecture section (game client, case files, MCP server, MCP clients) and a "Python tooling" section; `CLAUDE.md` gets the Python commands and lanes.

## Out of scope (v1)
Case generation or editing tools, playing the game through MCP, HTTP transport, publishing to PyPI, replacing the C++ loader checks (issue #3 stays for the engine).
