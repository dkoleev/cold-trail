# Cold Trail: design

CLI text detective game in C++20. Player investigates, finds the maniac. Main goal of the project: learn to work with an agent team.

## Decisions
- Language of game text: English. Commands: English.
- C++20 (`CMAKE_CXX_STANDARD 20`, required), CMake (CLion-native). Deps via FetchContent: nlohmann/json, GoogleTest.
- Avoid `std::format` unless CI proves it builds on all 3 platforms; fall back to streams. No C++23 features.
- Scope v1: one case, data-driven (JSON). Engine reads the case file.
- One chance to accuse: wrong `accuse` = game over.

## Structure
```
CMakeLists.txt          # detective_core (lib) + detective (exe) + tests
src/  main.cpp, game.*, parser.*, case_loader.*, model.h
data/case01.json        # the only case
tests/                  # GoogleTest: parser, loader, solvability
docs/case-format.md     # contract between roles
.claude/agents/         # game-designer.md, programmer.md, qa.md
.github/workflows/      # PR build on Windows, Linux, macOS
```

## Game
- Commands: `look`, `go <place>`, `talk <person>`, `examine <item>`, `clues`, `accuse <person>`, `help`, `quit`.
- Case: 5-6 locations, 4-5 suspects, 8-10 clues.
- JSON describes: locations (exits, items, people), characters (lines tied to clues), clues, solution (killer + set of clues sufficient to accuse).
- Win: `accuse` the killer with enough clues found. Lose: `accuse` the wrong person.

## Team
| Role | Who | Responsibility | Writes only in |
|---|---|---|---|
| Lead | main session | tasks, acceptance, routes bugs, owns contracts | anywhere |
| game-designer | subagent | rules, commands, case, characters, clues, data format | `data/`, `docs/` |
| programmer | subagent | engine, command parser, case loader | `src/`, `CMakeLists.txt` |
| qa | subagent | tests, solvability validator, bug reports | `tests/` |

Workflow:
1. game-designer writes `docs/case-format.md` + `data/case01.json` (the contract).
2. programmer implements the engine against the contract.
3. qa writes tests and a validator: every required clue reachable, killer deducible. 2 and 3 run in parallel once the contract exists.
4. Lead accepts work, returns bugs to the owner.

## CI
GitHub Actions on `pull_request`: configure + build + ctest on ubuntu-latest, windows-latest, macos-latest.

## Out of scope (v1)
Multiple cases, procedural generation, save/load, localization.
