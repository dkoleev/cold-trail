# Case file format

A case is one JSON file (see `data/case01.json`). All keys listed are required unless marked optional. Omit optional keys when unused.

## Top level

| Key | Type | Notes |
|---|---|---|
| `title` | string | Case title |
| `intro` | string | Shown at game start |
| `start` | locId | Starting location |
| `locations` | array | See below |
| `people` | array | See below |
| `items` | array | See below |
| `clues` | array | See below |
| `solution` | object | See below |

## Objects

| Object | Key | Type | Notes |
|---|---|---|---|
| location | `id`, `name`, `description` | string | |
| location | `exits` | locId[] | Make exits bidirectional |
| location | `items` | itemId[] | May be empty |
| person | `id`, `name`, `description` | string | |
| person | `location` | locId | |
| person | `talk` | talk line[] | Shown in order |
| talk line | `text` | string | |
| talk line | `requires` | clueId, optional | Line shown only if this clue is already found |
| talk line | `reveals` | clueId, optional | Clue learned when the line is shown |
| item | `id`, `name`, `description` | string | |
| item | `reveals` | clueId, optional | Learned when examined in its location |
| clue | `id`, `text` | string | |
| solution | `killer` | personId | |
| solution | `required_clues` | clueId[] | Evidence needed for a winning accusation |
| solution | `explanation` | string | Non-empty, derivable from clue texts |

## Invariants

- Ids are lowercase snake_case and unique per kind.
- Every id reference resolves: `start`, `exits`, location `items`, person `location`, item `reveals`, talk `requires`/`reveals`, `killer`, `required_clues`.
- Names are unique case-insensitively across locations, people and items (the player types names).
- A clue never requires itself.

## Design rules for cases

- 5-6 locations, 4-5 people, 8-10 clues; all locations reachable from `start`.
- Every clue is obtainable by walking, examining or talking; talk-unlock chains are at most 3 deep.
- At least 3 required clues and at least 1 red herring (a clue not in `required_clues`).
- Fair play: the killer is deducible from clue texts alone, through contradictions between statements and physical evidence.
