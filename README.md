# Cold Trail

A CLI text detective game: investigate a crime scene, gather evidence, interview suspects, and accuse the killer. Choose wisely—you get one accusation.

## How to Play

Navigate locations, talk to suspects and learn their stories, examine evidence for clues. Piece together the facts to identify the culprit. Accusing the real killer before you have enough evidence is refused and the game goes on. Accusing anyone else ends the game: one wrong accusation means game over.

## Commands

| Command | Usage | Notes |
|---------|-------|-------|
| `look` | Show current location, exits, items, people | Default when you arrive |
| `go <place>` | Move to an adjacent location | Case-insensitive |
| `talk <person>` | Interview a suspect or witness | Full name required, e.g., `talk Mrs. Pell` |
| `examine <item>` | Inspect an item for clues | Case-insensitive |
| `clues` | List all clues found so far | Shows your evidence |
| `accuse <person>` | Accuse a suspect (one chance) | Full name required; must have required evidence |
| `help` | Show command reference | |
| `quit` | Exit the game | |

Names (places, people, items) are matched case-insensitively, but the full name is required.

## Build and Test

### Prerequisites

Use the CLion toolchain (Windows only):

```powershell
$b="C:\Program Files\JetBrains\CLion 2026.2.3.1\bin"
$env:PATH="$b\cmake\win\x64\bin;$b\ninja\win\x64;$b\mingw\bin;$env:PATH"
```

(This sets up CMake, Ninja, and MinGW; for CI/other platforms, these are pre-installed.)

### Build and Test

```powershell
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Debug
cmake --build build --parallel
ctest --test-dir build --output-on-failure
```

Expected: all tests pass.

## Run the Game

```bash
build/detective [case.json]
```

- Default case: `data/case01.json` (the absolute path of the data directory is baked in at build time; if you move the binary, pass the case path as `argv[1]`)
- Optional: specify a case file path to load a different case

Example:
```bash
build/detective data/case01.json
```

## CLion Setup

1. Open the repository folder in CLion
2. CMake configuration loads automatically
3. Create or select run configuration `detective`
4. Run via IDE or terminal

## Case File Format

Detective cases are JSON files. See `docs/case-format.md` for the schema. A case defines locations, suspects, items, clues, and the solution (required evidence and killer).

## Project Layout

```
src/               Engine: case loader, command parser, game logic
tests/             GoogleTest suite
data/              Case files (JSON)
docs/              Documentation
  case-format.md   Case JSON schema and design rules
CMakeLists.txt     Build configuration
```

## Team Roles

| Role | Owner | Scope |
|------|-------|-------|
| Lead | main session | Delegates tasks, reviews PRs first (as a PR comment) |
| Programmer | `programmer` agent | `src/`, CMakeLists.txt |
| Game Designer | `game-designer` agent | `data/`, case-format.md |
| QA | `qa` agent | `tests/`, writes tests first |
| User | (you) | Reviews and merges PRs |

## PR Workflow

1. Lead reviews the PR first and posts findings as a PR comment (never approves, merges or closes)
2. User reviews, then merges or closes
3. Remarks are fixed by the programmer, who pushes to the PR branch (test or data remarks go to qa / game-designer)
