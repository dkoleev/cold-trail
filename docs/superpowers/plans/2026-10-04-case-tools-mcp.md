# case-tools MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Python MCP server `case-tools` that validates, solves and lints Cold Trail case files (`data/*.json`).

**Architecture:** Package `tools/case-tools/` with a pure core (`model`, `validate`, `solve`, `lint`, `paths`) and a thin MCP layer (`server.py`, `MCPServer` from `mcp` 2.x). Core never imports `mcp`. Tools return typed pydantic results (structured output); errors are results with an `error` field, never raised.

**Tech Stack:** Python >= 3.10 (dev machine: 3.13.7), `mcp>=2.3,<3`, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-04-case-tools-mcp-design.md`

## Global Constraints
- Python >= 3.10; dependency `mcp>=2.3,<3`; dev dependency `pytest>=8`; no other runtime deps.
- mcp 2.x API (verified): `from mcp.server.mcpserver import MCPServer`; `mcp.run()` = stdio; client: `mcp.ClientSession`, `mcp.StdioServerParameters`, `mcp.client.stdio.stdio_client`; results use `res.is_error`, `res.structured_content`; resource read `await s.read_resource(uri)` -> `.contents[0].text`; prompt `await s.get_prompt(name, args)` -> `.messages[0].content.text`.
- Tools only accept paths matching `data/<name>.json` (relative, no subdirectories, no `..`, no absolute, no backslashes).
- Nothing printed to stdout in the server (stdio protocol channel).
- Core code has no `mcp` import.
- Contract JSON = `docs/case-format.md` (top keys `title, intro, start, locations, people, items, clues, solution`; talk line key `requires` (python field `requires`), `reveals`).
- Ownership: programmer `tools/case-tools/src/`, `tools/case-tools/pyproject.toml`; qa `tools/case-tools/tests/` (writes tests first); Lead `.mcp.json`, `.github/workflows/pr-build.yml`, `.claude/agents/`, `CLAUDE.md`, `README.md`, `.gitignore`. game-designer: no code.
- Cross-role TDD: qa writes failing tests from the interfaces below, programmer makes them pass without editing tests; qa's red commit stays LOCAL until the programmer is green, the programmer pushes both.
- Every commit message: blank line, then exactly `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Branch `feat/case-tools-mcp` from `main`. PR flow per `CLAUDE.md`: Lead reviews first (PR comment only), user reviews and merges; remarks fixed by the programmer.
- Local Python: `py -3.13 -m venv .venv`, then `.venv\Scripts\python -m pip install -e "tools/case-tools[dev]"`; tests: `.venv\Scripts\python -m pytest tools/case-tools`. `.venv/` is git-ignored.

## Order
1 -> 2T,2I -> 3T,3I -> 4T,4I -> 5T,5I -> 6 -> 7. (`nT` = qa tests, `nI` = programmer implementation; one review per task covering both.)

## Interfaces (shared by all tasks)
```python
# issues.py
@dataclass(frozen=True)
class Issue: severity: str; code: str; message: str; path: str     # severity "error" | "warning"
# model.py (all frozen dataclasses; tuples not lists)
Clue(id, text); Item(id, name, description, reveals: str|None); TalkLine(text, requires: str|None, reveals: str|None)
Person(id, name, description, location, talk: tuple[TalkLine, ...]); Location(id, name, description, exits: tuple[str,...], items: tuple[str,...])
Solution(killer, required_clues: tuple[str,...], explanation); Case(title, intro, start, locations, people, items, clues, solution)
def case_from_dict(raw: dict) -> Case            # assumes validate_raw(raw) == []
# validate.py
def validate_raw(raw: object) -> list[Issue]     # all issues, never raises
# solve.py
@dataclass(frozen=True)
class Step: action: str; target: str; gives: tuple[str, ...]      # action "go" | "examine" | "talk"; target = display name
@dataclass(frozen=True)
class SolveResult: obtainable: tuple[str, ...]; steps: tuple[Step, ...]; missing_required: tuple[str, ...]  # + property solvable -> bool
def solve(case: Case) -> SolveResult
# lint.py
def lint(case: Case) -> list[Issue]              # severity "warning"
# paths.py
class PathError(ValueError)
def repo_root() -> Path                          # env CASE_TOOLS_ROOT or cwd, resolved
def resolve_case_path(path: str, root: Path | None = None) -> Path   # raises PathError
```
Issue codes: validate: `wrong-type`, `missing-field`, `duplicate-id`, `bad-id-format`, `duplicate-name`, `unknown-ref`. lint: `size-locations`, `size-people`, `size-clues`, `few-required-clues`, `no-red-herring`, `deep-unlock-chain`, `unobtainable-clue`, `empty-explanation`, `silent-suspect`, `one-way-exit`.

## Review Focus
1. Not-an-object JSON, wrong types, missing keys -> `validate_raw` returns issues, never raises. (Task 2)
2. Path traversal (`../x.json`, `data/../x.json`, `/abs/data/x.json`, `data\x.json`, `data/sub/x.json`, `data/x.txt`) rejected; symlink escaping `data/` rejected. (Task 5)
3. UTF-8 BOM at the start of a case file is read fine (cf. issue #8 for the C++ side). (Task 5)
4. Empty arrays (no people / no locations' exits) -> issues or warnings, no crash. (Tasks 2, 3)
5. Missing file / invalid JSON through the server -> structured `error`, `is_error` False, server stays alive for the next call. (Task 5)

---

### Task 1: Scaffold + CI job (Lead; dispatch to a general-purpose subagent)

**Files:** Create `tools/case-tools/pyproject.toml`, `tools/case-tools/src/case_tools/__init__.py`, `tools/case-tools/src/case_tools/issues.py`, `tools/case-tools/tests/test_smoke.py`; Modify `.gitignore`, `.github/workflows/pr-build.yml`.

- [ ] **Step 1:** `git switch main && git pull --ff-only && git switch -c feat/case-tools-mcp`.
- [ ] **Step 2:** `tools/case-tools/pyproject.toml`
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "case-tools"
version = "0.1.0"
description = "MCP server that validates, solves and lints Cold Trail case files"
requires-python = ">=3.10"
dependencies = ["mcp>=2.3,<3"]

[project.optional-dependencies]
dev = ["pytest>=8"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```
- [ ] **Step 3:** `src/case_tools/__init__.py` empty. `src/case_tools/issues.py`
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Issue:
    severity: str  # "error" | "warning"
    code: str
    message: str
    path: str
```
`tests/test_smoke.py`
```python
from case_tools.issues import Issue


def test_issue_is_a_value_object():
    assert Issue("error", "x", "m", "$") == Issue("error", "x", "m", "$")
```
- [ ] **Step 4:** append to `.gitignore`: `.venv/`, `__pycache__/`, `*.egg-info/`, `.pytest_cache/`.
- [ ] **Step 5:** append this job to `.github/workflows/pr-build.yml` (same indentation level as `build:`, under `jobs:`)
```yaml
  python:
    name: case-tools (python)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
          cache: pip
          cache-dependency-path: tools/case-tools/pyproject.toml
      - run: python -m pip install -e "tools/case-tools[dev]"
      - run: python -m pytest tools/case-tools
```
- [ ] **Step 6:** Local: create `.venv`, install, run pytest. Expected: 1 passed.
- [ ] **Step 7:** Commit `chore: case-tools scaffold and CI job`; `git push -u origin feat/case-tools-mcp`; `gh pr create --draft --fill --base main`; `gh pr checks --watch`. Expected: C++ matrix green (unchanged) and `case-tools (python)` green.

---

### Task 2: model + validate (qa 2T, programmer 2I)

**Files:** Create `tools/case-tools/tests/conftest.py`, `tools/case-tools/tests/test_validate.py`, `tools/case-tools/src/case_tools/model.py`, `tools/case-tools/src/case_tools/validate.py`

**Consumes:** `Issue`. **Produces:** `model.py` dataclasses + `case_from_dict`; `validate_raw`; fixtures `mini_raw()` (deep copy of MINI), `MINI`.

- [ ] **Step 1 (qa):** `tests/conftest.py`
```python
import copy

import pytest

# Same content as kMiniCase in tests/test_support.h (C++ side).
MINI = {
    "title": "Mini",
    "intro": "A body lies in the hall.",
    "start": "hall",
    "locations": [
        {"id": "hall", "name": "Hall", "description": "A cold marble hall.", "exits": ["study"], "items": []},
        {"id": "study", "name": "Study", "description": "Papers everywhere.", "exits": ["hall"], "items": ["note"]},
    ],
    "people": [
        {
            "id": "butler", "name": "Mr. Grey", "description": "Stiff and pale.", "location": "hall",
            "talk": [
                {"text": "I saw nothing."},
                {"text": "Fine, I lied about my alibi.", "requires": "c_note", "reveals": "c_alibi"},
            ],
        },
        {"id": "maid", "name": "Ann", "description": "Nervous.", "location": "study", "talk": [{"text": "I was asleep."}]},
    ],
    "items": [{"id": "note", "name": "torn note", "description": "A threat, signed G.", "reveals": "c_note"}],
    "clues": [
        {"id": "c_note", "text": "A threatening note signed G."},
        {"id": "c_alibi", "text": "The butler lied about his alibi."},
    ],
    "solution": {
        "killer": "butler",
        "required_clues": ["c_note", "c_alibi"],
        "explanation": "The butler wrote the note and lied.",
    },
}


@pytest.fixture
def mini_raw():
    return copy.deepcopy(MINI)
```
`tests/test_validate.py`
```python
import pytest

from case_tools.model import case_from_dict
from case_tools.validate import validate_raw


def codes(issues):
    return [i.code for i in issues]


def test_mini_case_is_valid(mini_raw):
    assert validate_raw(mini_raw) == []


def test_case_from_dict_builds_model(mini_raw):
    case = case_from_dict(mini_raw)
    assert case.title == "Mini"
    assert case.people[0].talk[1].requires == "c_note"
    assert case.items[0].reveals == "c_note"
    assert case.locations[0].exits == ("study",)
    assert case.solution.required_clues == ("c_note", "c_alibi")


@pytest.mark.parametrize("raw", [[], "text", 5, None])
def test_non_object_is_a_wrong_type_issue(raw):
    assert codes(validate_raw(raw)) == ["wrong-type"]


def test_missing_top_level_key(mini_raw):
    del mini_raw["start"]
    issues = validate_raw(mini_raw)
    assert codes(issues) == ["missing-field"]
    assert issues[0].path == "$"


def test_wrong_type_of_nested_field(mini_raw):
    mini_raw["locations"][0]["exits"] = "study"
    issues = validate_raw(mini_raw)
    assert codes(issues) == ["wrong-type"]
    assert issues[0].path == "locations[0].exits"


def test_wrong_type_of_list_element(mini_raw):
    mini_raw["locations"][0]["exits"] = [5]
    assert codes(validate_raw(mini_raw)) == ["wrong-type"]


def test_entry_that_is_not_an_object(mini_raw):
    mini_raw["clues"][0] = "oops"
    assert codes(validate_raw(mini_raw)) == ["wrong-type"]


def test_null_reveals_is_treated_as_absent(mini_raw):
    mini_raw["items"][0]["reveals"] = None
    assert validate_raw(mini_raw) == []


def test_dangling_start(mini_raw):
    mini_raw["start"] = "nowhere"
    issues = validate_raw(mini_raw)
    assert codes(issues) == ["unknown-ref"]
    assert issues[0].path == "start"


def test_dangling_exit_and_location_item(mini_raw):
    mini_raw["locations"][0]["exits"] = ["attic"]
    mini_raw["locations"][1]["items"] = ["ghost"]
    issues = validate_raw(mini_raw)
    assert sorted(i.path for i in issues) == ["locations[0].exits[0]", "locations[1].items[0]"]


def test_dangling_person_location_and_talk_refs(mini_raw):
    mini_raw["people"][0]["location"] = "attic"
    mini_raw["people"][0]["talk"][1]["requires"] = "c_x"
    mini_raw["people"][0]["talk"][1]["reveals"] = "c_y"
    issues = validate_raw(mini_raw)
    assert sorted(i.path for i in issues) == [
        "people[0].location",
        "people[0].talk[1].requires",
        "people[0].talk[1].reveals",
    ]


def test_dangling_item_reveals_killer_and_required_clue(mini_raw):
    mini_raw["items"][0]["reveals"] = "c_x"
    mini_raw["solution"]["killer"] = "ghost"
    mini_raw["solution"]["required_clues"] = ["c_y"]
    issues = validate_raw(mini_raw)
    assert sorted(i.path for i in issues) == ["items[0].reveals", "solution.killer", "solution.required_clues[0]"]


def test_duplicate_ids_per_kind(mini_raw):
    mini_raw["people"][1]["id"] = "butler"
    mini_raw["clues"][1]["id"] = "c_note"
    issues = validate_raw(mini_raw)
    assert codes(issues).count("duplicate-id") == 2


def test_bad_id_format(mini_raw):
    mini_raw["locations"][0]["id"] = "Great Hall"
    mini_raw["locations"][1]["exits"] = ["Great Hall"]
    mini_raw["start"] = "Great Hall"
    mini_raw["people"][0]["location"] = "Great Hall"
    assert codes(validate_raw(mini_raw)) == ["bad-id-format"]


def test_duplicate_names_are_case_insensitive_across_kinds(mini_raw):
    mini_raw["items"][0]["name"] = "HALL"
    issues = validate_raw(mini_raw)
    assert codes(issues) == ["duplicate-name"]
    assert issues[0].path == "items[0].name"


def test_empty_people_gives_issues_not_a_crash(mini_raw):
    mini_raw["people"] = []
    issues = validate_raw(mini_raw)
    assert codes(issues) == ["unknown-ref"]
    assert issues[0].path == "solution.killer"


def test_all_issues_are_reported_together(mini_raw):
    mini_raw["start"] = "nowhere"
    mini_raw["solution"]["killer"] = "ghost"
    assert len(validate_raw(mini_raw)) == 2
```
- [ ] **Step 2 (qa):** Run pytest. Expected: FAIL (ModuleNotFoundError `case_tools.model`). Commit locally `test: model and validate tests (red)`; do NOT push.
- [ ] **Step 3 (programmer):** `src/case_tools/model.py`
```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Clue:
    id: str
    text: str


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    description: str
    reveals: str | None = None


@dataclass(frozen=True)
class TalkLine:
    text: str
    requires: str | None = None
    reveals: str | None = None


@dataclass(frozen=True)
class Person:
    id: str
    name: str
    description: str
    location: str
    talk: tuple[TalkLine, ...]


@dataclass(frozen=True)
class Location:
    id: str
    name: str
    description: str
    exits: tuple[str, ...]
    items: tuple[str, ...]


@dataclass(frozen=True)
class Solution:
    killer: str
    required_clues: tuple[str, ...]
    explanation: str


@dataclass(frozen=True)
class Case:
    title: str
    intro: str
    start: str
    locations: tuple[Location, ...]
    people: tuple[Person, ...]
    items: tuple[Item, ...]
    clues: tuple[Clue, ...]
    solution: Solution


def case_from_dict(raw: dict) -> Case:
    """Build a Case from a dict that already passed validate_raw."""
    return Case(
        title=raw["title"],
        intro=raw["intro"],
        start=raw["start"],
        locations=tuple(
            Location(l["id"], l["name"], l["description"], tuple(l["exits"]), tuple(l["items"]))
            for l in raw["locations"]
        ),
        people=tuple(
            Person(
                p["id"], p["name"], p["description"], p["location"],
                tuple(TalkLine(t["text"], t.get("requires"), t.get("reveals")) for t in p["talk"]),
            )
            for p in raw["people"]
        ),
        items=tuple(Item(i["id"], i["name"], i["description"], i.get("reveals")) for i in raw["items"]),
        clues=tuple(Clue(c["id"], c["text"]) for c in raw["clues"]),
        solution=Solution(
            raw["solution"]["killer"],
            tuple(raw["solution"]["required_clues"]),
            raw["solution"]["explanation"],
        ),
    )
```
`src/case_tools/validate.py`
```python
from __future__ import annotations

import re

from case_tools.issues import Issue

_SNAKE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
_KIND = {"locations": "location", "people": "person", "items": "item", "clues": "clue"}

_TOP = {"title": str, "intro": str, "start": str, "locations": list, "people": list,
        "items": list, "clues": list, "solution": dict}
_ENTRY = {
    "locations": {"id": str, "name": str, "description": str, "exits": list, "items": list},
    "people": {"id": str, "name": str, "description": str, "location": str, "talk": list},
    "items": {"id": str, "name": str, "description": str},
    "clues": {"id": str, "text": str},
}
_SOLUTION = {"killer": str, "required_clues": list, "explanation": str}


def _err(issues: list[Issue], code: str, message: str, path: str) -> None:
    issues.append(Issue("error", code, message, path))


def _obj(obj: dict, spec: dict, path: str, issues: list[Issue]) -> bool:
    ok = True
    for key, typ in spec.items():
        if key not in obj:
            _err(issues, "missing-field", f"missing field '{key}'", path)
            ok = False
        elif not isinstance(obj[key], typ):
            _err(issues, "wrong-type", f"'{key}' must be {typ.__name__}", f"{path}.{key}" if path != "$" else key)
            ok = False
    return ok


def _optional_str(obj: dict, keys: tuple[str, ...], path: str, issues: list[Issue]) -> bool:
    ok = True
    for key in keys:
        if obj.get(key) is not None and not isinstance(obj[key], str):
            _err(issues, "wrong-type", f"'{key}' must be str", f"{path}.{key}")
            ok = False
    return ok


def _str_list(values: list, path: str, issues: list[Issue]) -> bool:
    ok = True
    for i, v in enumerate(values):
        if not isinstance(v, str):
            _err(issues, "wrong-type", "must be str", f"{path}[{i}]")
            ok = False
    return ok


def _check_shape(raw: dict, issues: list[Issue]) -> bool:
    if not _obj(raw, _TOP, "$", issues):
        return False
    ok = True
    for coll, spec in _ENTRY.items():
        for i, entry in enumerate(raw[coll]):
            path = f"{coll}[{i}]"
            if not isinstance(entry, dict):
                _err(issues, "wrong-type", "must be an object", path)
                ok = False
                continue
            ok &= _obj(entry, spec, path, issues)
            if coll == "items":
                ok &= _optional_str(entry, ("reveals",), path, issues)
            if coll == "locations":
                for key in ("exits", "items"):
                    if isinstance(entry.get(key), list):
                        ok &= _str_list(entry[key], f"{path}.{key}", issues)
            if coll == "people" and isinstance(entry.get("talk"), list):
                for j, line in enumerate(entry["talk"]):
                    lp = f"{path}.talk[{j}]"
                    if not isinstance(line, dict):
                        _err(issues, "wrong-type", "must be an object", lp)
                        ok = False
                        continue
                    ok &= _obj(line, {"text": str}, lp, issues)
                    ok &= _optional_str(line, ("requires", "reveals"), lp, issues)
    sol = raw["solution"]
    ok &= _obj(sol, _SOLUTION, "solution", issues)
    if isinstance(sol.get("required_clues"), list):
        ok &= _str_list(sol["required_clues"], "solution.required_clues", issues)
    return ok


def _check_ids_and_names(raw: dict, issues: list[Issue]) -> None:
    for coll, kind in _KIND.items():
        seen: set[str] = set()
        for i, entry in enumerate(raw[coll]):
            ident = entry["id"]
            if ident in seen:
                _err(issues, "duplicate-id", f"duplicate {kind} id '{ident}'", f"{coll}[{i}].id")
            seen.add(ident)
            if not _SNAKE.match(ident):
                _err(issues, "bad-id-format", f"{kind} id '{ident}' must be lowercase snake_case", f"{coll}[{i}].id")
    names: dict[str, str] = {}
    for coll in ("locations", "people", "items"):
        for i, entry in enumerate(raw[coll]):
            key = entry["name"].strip().lower()
            if key in names:
                _err(issues, "duplicate-name", f"name '{entry['name']}' already used by {names[key]}", f"{coll}[{i}].name")
            else:
                names[key] = f"{coll}[{i}]"


def _check_references(raw: dict, issues: list[Issue]) -> None:
    ids = {coll: {e["id"] for e in raw[coll]} for coll in _KIND}

    def need(coll: str, ref: str, path: str) -> None:
        if ref not in ids[coll]:
            _err(issues, "unknown-ref", f"unknown {_KIND[coll]} '{ref}'", path)

    need("locations", raw["start"], "start")
    for i, loc in enumerate(raw["locations"]):
        for j, ref in enumerate(loc["exits"]):
            need("locations", ref, f"locations[{i}].exits[{j}]")
        for j, ref in enumerate(loc["items"]):
            need("items", ref, f"locations[{i}].items[{j}]")
    for i, person in enumerate(raw["people"]):
        need("locations", person["location"], f"people[{i}].location")
        for j, line in enumerate(person["talk"]):
            for key in ("requires", "reveals"):
                if line.get(key) is not None:
                    need("clues", line[key], f"people[{i}].talk[{j}].{key}")
    for i, item in enumerate(raw["items"]):
        if item.get("reveals") is not None:
            need("clues", item["reveals"], f"items[{i}].reveals")
    need("people", raw["solution"]["killer"], "solution.killer")
    for j, ref in enumerate(raw["solution"]["required_clues"]):
        need("clues", ref, f"solution.required_clues[{j}]")


def validate_raw(raw: object) -> list[Issue]:
    """All problems of a parsed case file, in one list. Never raises."""
    if not isinstance(raw, dict):
        return [Issue("error", "wrong-type", "case must be a JSON object", "$")]
    issues: list[Issue] = []
    if not _check_shape(raw, issues):
        return issues
    _check_ids_and_names(raw, issues)
    _check_references(raw, issues)
    return issues
```
- [ ] **Step 4 (programmer):** Run pytest. Expected: all pass (smoke + validate). Commit `feat: case model and validator`; push; `gh pr checks --watch`.

---

### Task 3: solve (qa 3T, programmer 3I)

**Files:** Create `tools/case-tools/tests/test_solve.py`, `tools/case-tools/src/case_tools/solve.py`

**Consumes:** `Case`, `case_from_dict`, fixtures. **Produces:** `Step`, `SolveResult`, `solve`.
Semantics = C++ engine: exits one-way; item examinable only in its own location; person talkable only where they stand; a talk line is shown only if its `requires` clue is found; a line can unlock a later line within the same talk. The solver simulates a greedy walker (nearest-first, repeated rounds). One-way dead ends are out of scope: `lint` flags them (`one-way-exit`).

- [ ] **Step 1 (qa):** `tests/test_solve.py`
```python
from case_tools.model import case_from_dict
from case_tools.solve import Step, solve


def test_mini_case_steps_in_order(mini_raw):
    result = solve(case_from_dict(mini_raw))
    assert result.obtainable == ("c_note", "c_alibi")
    assert result.steps == (
        Step("go", "Study", ()),
        Step("examine", "torn note", ("c_note",)),
        Step("go", "Hall", ()),
        Step("talk", "Mr. Grey", ("c_alibi",)),
    )
    assert result.missing_required == ()
    assert result.solvable is True


def test_clue_behind_an_unobtainable_gate_is_missing(mini_raw):
    mini_raw["clues"].append({"id": "c_ghost", "text": "never found"})
    mini_raw["people"][0]["talk"][1]["requires"] = "c_ghost"
    result = solve(case_from_dict(mini_raw))
    assert "c_alibi" not in result.obtainable
    assert result.missing_required == ("c_alibi",)
    assert result.solvable is False


def test_unreachable_location_hides_its_clues(mini_raw):
    mini_raw["locations"][0]["exits"] = []
    result = solve(case_from_dict(mini_raw))
    assert result.obtainable == ()
    assert result.solvable is False


def test_a_line_can_unlock_a_later_line_in_the_same_talk(mini_raw):
    mini_raw["clues"].append({"id": "c_extra", "text": "extra"})
    mini_raw["items"][0]["reveals"] = None
    mini_raw["people"][0]["talk"] = [
        {"text": "first", "reveals": "c_note"},
        {"text": "second", "requires": "c_note", "reveals": "c_alibi"},
    ]
    result = solve(case_from_dict(mini_raw))
    assert result.obtainable == ("c_note", "c_alibi")
    assert result.steps == (Step("talk", "Mr. Grey", ("c_note", "c_alibi")),)


def test_case_without_people_does_not_crash(mini_raw):
    mini_raw["people"] = []
    mini_raw["solution"]["killer"] = "butler"  # dangling on purpose: solve works on the model only
    result = solve(case_from_dict(mini_raw))
    assert result.obtainable == ("c_note",)
```
- [ ] **Step 2 (qa):** Run pytest on the file. Expected: FAIL (`case_tools.solve` missing). Commit locally `test: solve tests (red)`; no push.
- [ ] **Step 3 (programmer):** `src/case_tools/solve.py`
```python
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from case_tools.model import Case, Location


@dataclass(frozen=True)
class Step:
    action: str  # "go" | "examine" | "talk"
    target: str  # display name the player types
    gives: tuple[str, ...]  # clue ids learned by this step


@dataclass(frozen=True)
class SolveResult:
    obtainable: tuple[str, ...]  # clue ids in discovery order
    steps: tuple[Step, ...]
    missing_required: tuple[str, ...]

    @property
    def solvable(self) -> bool:
        return not self.missing_required


def _bfs_order(case: Case) -> list[Location]:
    by_id = {l.id: l for l in case.locations}
    seen = {case.start}
    order: list[Location] = []
    queue = deque([case.start])
    while queue:
        loc = by_id[queue.popleft()]
        order.append(loc)
        for nxt in loc.exits:
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return order


def _route(case: Case, src: str, dst: str) -> list[str] | None:
    """Location ids to walk from src to dst (excluding src); None if there is no way."""
    by_id = {l.id: l for l in case.locations}
    parent = {src: src}
    queue = deque([src])
    while queue:
        cur = queue.popleft()
        if cur == dst:
            break
        for nxt in by_id[cur].exits:
            if nxt not in parent:
                parent[nxt] = cur
                queue.append(nxt)
    if dst not in parent:
        return None
    path: list[str] = []
    at = dst
    while at != src:
        path.append(at)
        at = parent[at]
    return path[::-1]


def _collect(case: Case, loc: Location, found: list[str]) -> list[Step]:
    """Actions at `loc` that teach new clues; appends the new clue ids to `found`."""
    steps: list[Step] = []
    items = {i.id: i for i in case.items}
    for item_id in loc.items:
        item = items[item_id]
        if item.reveals and item.reveals not in found:
            found.append(item.reveals)
            steps.append(Step("examine", item.name, (item.reveals,)))
    for person in case.people:
        if person.location != loc.id:
            continue
        gained: list[str] = []
        for line in person.talk:
            if line.requires and line.requires not in found:
                continue
            if line.reveals and line.reveals not in found:
                found.append(line.reveals)
                gained.append(line.reveals)
        if gained:
            steps.append(Step("talk", person.name, tuple(gained)))
    return steps


def solve(case: Case) -> SolveResult:
    by_id = {l.id: l for l in case.locations}
    found: list[str] = []
    steps: list[Step] = []
    at = case.start
    progress = True
    while progress:
        progress = False
        for loc in _bfs_order(case):
            if not _collect(case, loc, list(found)):
                continue
            walk = _route(case, at, loc.id)
            if walk is None:
                continue
            steps.extend(Step("go", by_id[hop].name, ()) for hop in walk)
            at = loc.id
            steps.extend(_collect(case, loc, found))
            progress = True
    missing = tuple(c for c in case.solution.required_clues if c not in found)
    return SolveResult(tuple(found), tuple(steps), missing)
```
- [ ] **Step 4 (programmer):** Run full pytest. Expected: all pass. Commit `feat: solver`; push; `gh pr checks --watch`.

---

### Task 4: lint (qa 4T, programmer 4I)

**Files:** Create `tools/case-tools/tests/test_lint.py`, `tools/case-tools/src/case_tools/lint.py`

**Consumes:** `Case`, `solve`, `Issue`. **Produces:** `lint(case) -> list[Issue]` (all `severity == "warning"`).

- [ ] **Step 1 (qa):** `tests/test_lint.py`
```python
from case_tools.lint import lint
from case_tools.model import case_from_dict


def lint_codes(raw):
    return [w.code for w in lint(case_from_dict(raw))]


def test_mini_case_only_warns_about_sizes(mini_raw):
    codes = lint_codes(mini_raw)
    assert set(codes) == {"size-locations", "size-people", "size-clues", "few-required-clues", "no-red-herring"}
    assert all(w.severity == "warning" for w in lint(case_from_dict(mini_raw)))


def test_red_herring_present_when_a_clue_is_not_required(mini_raw):
    mini_raw["clues"].append({"id": "c_herring", "text": "noise"})
    mini_raw["items"][0]["reveals"] = "c_note"
    assert "no-red-herring" not in lint_codes(mini_raw)


def test_empty_explanation(mini_raw):
    mini_raw["solution"]["explanation"] = "   "
    assert "empty-explanation" in lint_codes(mini_raw)


def test_silent_suspect(mini_raw):
    mini_raw["people"][1]["talk"] = []
    assert "silent-suspect" in lint_codes(mini_raw)


def test_unobtainable_clue(mini_raw):
    mini_raw["clues"].append({"id": "c_ghost", "text": "never found"})
    warnings = lint(case_from_dict(mini_raw))
    assert [(w.code, w.path) for w in warnings if w.code == "unobtainable-clue"] == [("unobtainable-clue", "clues[2]")]


def test_one_way_exit(mini_raw):
    mini_raw["locations"][1]["exits"] = []
    warnings = lint(case_from_dict(mini_raw))
    assert [(w.code, w.path) for w in warnings if w.code == "one-way-exit"] == [("one-way-exit", "locations[0].exits[0]")]


def test_deep_unlock_chain(mini_raw):
    # c1 (item) -> c2 -> c3 -> c4 -> c5 : depth 4 > 3
    mini_raw["clues"] = [{"id": f"c{i}", "text": f"clue {i}"} for i in range(1, 6)]
    mini_raw["items"][0]["reveals"] = "c1"
    mini_raw["people"][0]["talk"] = [
        {"text": "a", "requires": "c1", "reveals": "c2"},
        {"text": "b", "requires": "c2", "reveals": "c3"},
        {"text": "c", "requires": "c3", "reveals": "c4"},
        {"text": "d", "requires": "c4", "reveals": "c5"},
    ]
    mini_raw["solution"]["required_clues"] = ["c1", "c2", "c3"]
    assert "deep-unlock-chain" in lint_codes(mini_raw)


def test_shallow_chain_is_fine(mini_raw):
    assert "deep-unlock-chain" not in lint_codes(mini_raw)
```
- [ ] **Step 2 (qa):** Run the file. Expected: FAIL (`case_tools.lint` missing). Commit locally `test: lint tests (red)`; no push.
- [ ] **Step 3 (programmer):** `src/case_tools/lint.py`
```python
from __future__ import annotations

from case_tools.issues import Issue
from case_tools.model import Case
from case_tools.solve import solve


def _warn(code: str, message: str, path: str) -> Issue:
    return Issue("warning", code, message, path)


def _unlock_depth(case: Case) -> dict[str, int]:
    """Depth 0 = learnable without any gate; a gated line adds 1 to the depth of its requirement."""
    depth: dict[str, int] = {}
    changed = True
    while changed:
        changed = False
        sources: list[tuple[str, int | None]] = []
        for item in case.items:
            if item.reveals:
                sources.append((item.reveals, 0))
        for person in case.people:
            for line in person.talk:
                if not line.reveals:
                    continue
                if line.requires is None:
                    sources.append((line.reveals, 0))
                elif line.requires in depth:
                    sources.append((line.reveals, depth[line.requires] + 1))
        for clue, d in sources:
            if d is not None and (clue not in depth or d < depth[clue]):
                depth[clue] = d
                changed = True
    return depth


def lint(case: Case) -> list[Issue]:
    warnings: list[Issue] = []
    for label, n, lo, hi, code in (
        ("locations", len(case.locations), 5, 6, "size-locations"),
        ("people", len(case.people), 4, 5, "size-people"),
        ("clues", len(case.clues), 8, 10, "size-clues"),
    ):
        if not lo <= n <= hi:
            warnings.append(_warn(code, f"{n} {label}, expected {lo}-{hi}", label))
    if len(case.solution.required_clues) < 3:
        warnings.append(_warn("few-required-clues", "fewer than 3 required clues", "solution.required_clues"))
    if set(case.solution.required_clues) >= {c.id for c in case.clues}:
        warnings.append(_warn("no-red-herring", "every clue is required; add a red herring", "clues"))
    if not case.solution.explanation.strip():
        warnings.append(_warn("empty-explanation", "explanation is empty", "solution.explanation"))
    for i, person in enumerate(case.people):
        if not person.talk:
            warnings.append(_warn("silent-suspect", f"{person.name} has no talk lines", f"people[{i}].talk"))
    obtainable = set(solve(case).obtainable)
    for i, clue in enumerate(case.clues):
        if clue.id not in obtainable:
            warnings.append(_warn("unobtainable-clue", f"clue '{clue.id}' cannot be obtained", f"clues[{i}]"))
    by_id = {l.id: l for l in case.locations}
    for i, loc in enumerate(case.locations):
        for j, dest in enumerate(loc.exits):
            if dest in by_id and loc.id not in by_id[dest].exits:
                warnings.append(_warn("one-way-exit", f"{loc.id} -> {dest} has no way back", f"locations[{i}].exits[{j}]"))
    if max(_unlock_depth(case).values(), default=0) > 3:
        warnings.append(_warn("deep-unlock-chain", "a clue sits behind more than 3 gated talk lines", "people"))
    return warnings
```
- [ ] **Step 4 (programmer):** Run full pytest. Expected: all pass. Commit `feat: linter`; push; `gh pr checks --watch`.

---

### Task 5: paths + MCP server (qa 5T, programmer 5I)

**Files:** Create `tools/case-tools/tests/test_paths.py`, `tools/case-tools/tests/test_parity.py`, `tools/case-tools/tests/test_server.py`, `tools/case-tools/src/case_tools/paths.py`, `tools/case-tools/src/case_tools/server.py`, `tools/case-tools/src/case_tools/__main__.py`

**Consumes:** `validate_raw`, `case_from_dict`, `solve`, `lint`. **Produces:** `resolve_case_path`, `repo_root`, `PathError`; MCP server: tools `validate_case(path)`, `solve_case(path)`, `lint_case(path)`; resource `case-format://spec`; prompt `design_case(theme)`; `python -m case_tools`.
Result models (pydantic, in `server.py`): `ValidateResult(valid: bool=False, issues: list[IssueModel]=[], error: str|None=None)`; `SolveResult(solvable: bool=False, obtainable: list[str]=[], missing_required: list[str]=[], steps: list[StepModel]=[], error: str|None=None)`; `LintResult(warnings: list[IssueModel]=[], error: str|None=None)`; `IssueModel(severity, code, message, path)`; `StepModel(action, target, gives: list[str])`.

- [ ] **Step 1 (qa):** `tests/test_paths.py`
```python
import os

import pytest

from case_tools.paths import PathError, resolve_case_path


@pytest.fixture
def root(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "case01.json").write_text("{}", encoding="utf-8")
    return tmp_path


def test_valid_path_resolves_inside_data(root):
    assert resolve_case_path("data/case01.json", root) == (root / "data" / "case01.json").resolve()


@pytest.mark.parametrize(
    "bad",
    [
        "../x.json",
        "data/../x.json",
        "/abs/data/x.json",
        "C:/data/x.json",
        "data\\x.json",
        "data/sub/x.json",
        "data/x.txt",
        "data/.json",
        "data/",
        "",
        "case01.json",
        "data/x.json\n",
    ],
)
def test_rejected_paths(root, bad):
    with pytest.raises(PathError):
        resolve_case_path(bad, root)


def test_symlink_escaping_data_is_rejected(root, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "secret.json"
    outside.write_text("{}", encoding="utf-8")
    link = root / "data" / "link.json"
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not available")
    with pytest.raises(PathError):
        resolve_case_path("data/link.json", root)
```
`tests/test_parity.py`
```python
import json
from pathlib import Path

from case_tools.lint import lint
from case_tools.model import case_from_dict
from case_tools.solve import solve
from case_tools.validate import validate_raw

REAL_CASE = Path(__file__).resolve().parents[3] / "data" / "case01.json"


def test_real_case01_is_valid_solvable_and_lint_clean():
    raw = json.loads(REAL_CASE.read_text(encoding="utf-8"))
    assert validate_raw(raw) == []
    case = case_from_dict(raw)
    assert solve(case).solvable
    assert lint(case) == []


def test_mini_case_matches_the_cpp_fixture(mini_raw):
    assert validate_raw(mini_raw) == []
    assert solve(case_from_dict(mini_raw)).solvable
```
`tests/test_server.py`
```python
import asyncio
import json
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from conftest import MINI


@pytest.fixture
def root(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "data" / "mini.json").write_text(json.dumps(MINI), encoding="utf-8")
    bom = "\ufeff" + json.dumps(MINI)
    (tmp_path / "data" / "bom.json").write_text(bom, encoding="utf-8")
    (tmp_path / "data" / "broken.json").write_text("{not json", encoding="utf-8")
    bad = dict(MINI, start="nowhere")
    (tmp_path / "data" / "bad.json").write_text(json.dumps(bad), encoding="utf-8")
    (tmp_path / "docs" / "case-format.md").write_text("# spec", encoding="utf-8")
    return tmp_path


def with_session(root: Path, fn):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "case_tools"],
        env={**os.environ, "CASE_TOOLS_ROOT": str(root)},
    )

    async def go():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await fn(session)

    return asyncio.run(go())


def call(root, name, path):
    async def fn(s):
        return await s.call_tool(name, {"path": path})

    return with_session(root, fn)


def test_lists_the_three_tools(root):
    async def fn(s):
        return {t.name for t in (await s.list_tools()).tools}

    assert with_session(root, fn) == {"validate_case", "solve_case", "lint_case"}


def test_validate_valid_case(root):
    res = call(root, "validate_case", "data/mini.json")
    assert res.is_error is False
    assert res.structured_content["valid"] is True
    assert res.structured_content["issues"] == []


def test_validate_reports_issues(root):
    res = call(root, "validate_case", "data/bad.json")
    assert res.structured_content["valid"] is False
    assert res.structured_content["issues"][0]["code"] == "unknown-ref"


def test_solve_returns_ordered_steps(root):
    res = call(root, "solve_case", "data/mini.json")
    data = res.structured_content
    assert data["solvable"] is True
    assert [s["action"] for s in data["steps"]] == ["go", "examine", "go", "talk"]


def test_solve_refuses_an_invalid_case(root):
    data = call(root, "solve_case", "data/bad.json").structured_content
    assert data["solvable"] is False
    assert "validate_case" in data["error"]


def test_lint_returns_warnings(root):
    data = call(root, "lint_case", "data/mini.json").structured_content
    assert "size-locations" in [w["code"] for w in data["warnings"]]


def test_bom_prefixed_file_is_read(root):
    assert call(root, "validate_case", "data/bom.json").structured_content["valid"] is True


@pytest.mark.parametrize("path", ["../etc/passwd", "data/../x.json", "/abs/data/mini.json", "data/sub/x.json"])
def test_path_outside_data_is_rejected_without_crashing(root, path):
    res = call(root, "validate_case", path)
    assert res.is_error is False
    assert res.structured_content["error"]


def test_missing_and_broken_files_give_a_structured_error_and_server_survives(root):
    async def fn(s):
        missing = await s.call_tool("validate_case", {"path": "data/missing.json"})
        broken = await s.call_tool("validate_case", {"path": "data/broken.json"})
        after = await s.call_tool("validate_case", {"path": "data/mini.json"})
        return missing, broken, after

    missing, broken, after = with_session(root, fn)
    assert "not found" in missing.structured_content["error"]
    assert "invalid JSON" in broken.structured_content["error"]
    assert after.structured_content["valid"] is True


def test_resource_serves_the_format_spec(root):
    async def fn(s):
        return await s.read_resource("case-format://spec")

    assert with_session(root, fn).contents[0].text == "# spec"


def test_prompt_mentions_theme_and_tools(root):
    async def fn(s):
        return await s.get_prompt("design_case", {"theme": "lighthouse"})

    text = with_session(root, fn).messages[0].content.text
    assert "lighthouse" in text
    assert "validate_case" in text and "solve_case" in text and "lint_case" in text
```
- [ ] **Step 2 (qa):** Run pytest. Expected: FAIL (`case_tools.paths` / server missing; protocol tests error on `python -m case_tools`). Commit locally `test: paths, parity and protocol tests (red)`; no push.
- [ ] **Step 3 (programmer):** `src/case_tools/paths.py`
```python
from __future__ import annotations

import os
import re
from pathlib import Path

_CASE_PATH = re.compile(r"data/[A-Za-z0-9_-]+\.json")


class PathError(ValueError):
    pass


def repo_root() -> Path:
    return Path(os.environ.get("CASE_TOOLS_ROOT") or Path.cwd()).resolve()


def resolve_case_path(path: str, root: Path | None = None) -> Path:
    """Accept only data/<name>.json inside the repo's data dir (symlinks resolved)."""
    base = (root or repo_root()).resolve()
    if not _CASE_PATH.fullmatch(path):
        raise PathError("path must look like data/<name>.json (relative, no subdirectories)")
    full = (base / path).resolve()
    if full.parent != (base / "data").resolve():
        raise PathError("path escapes the data/ directory")
    return full
```
`src/case_tools/server.py`
```python
from __future__ import annotations

import json
from dataclasses import asdict

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel

from case_tools.lint import lint
from case_tools.model import case_from_dict
from case_tools.paths import PathError, repo_root, resolve_case_path
from case_tools.solve import solve
from case_tools.validate import validate_raw

mcp = MCPServer("case-tools")


class IssueModel(BaseModel):
    severity: str
    code: str
    message: str
    path: str


class StepModel(BaseModel):
    action: str
    target: str
    gives: list[str]


class ValidateResult(BaseModel):
    valid: bool = False
    issues: list[IssueModel] = []
    error: str | None = None


class SolveResult(BaseModel):
    solvable: bool = False
    obtainable: list[str] = []
    missing_required: list[str] = []
    steps: list[StepModel] = []
    error: str | None = None


class LintResult(BaseModel):
    warnings: list[IssueModel] = []
    error: str | None = None


def _load(path: str) -> tuple[object | None, str | None]:
    try:
        full = resolve_case_path(path)
    except PathError as exc:
        return None, str(exc)
    try:
        return json.loads(full.read_text(encoding="utf-8-sig")), None
    except FileNotFoundError:
        return None, f"file not found: {path}"
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON in {path}: {exc}"
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"cannot read {path}: {exc}"


def _issues(items) -> list[IssueModel]:
    return [IssueModel(**asdict(i)) for i in items]


_INVALID = "case is invalid; run validate_case first"


@mcp.tool()
def validate_case(path: str) -> ValidateResult:
    """Validate data/<name>.json against the case format. Returns every issue at once."""
    raw, error = _load(path)
    if error:
        return ValidateResult(error=error)
    issues = validate_raw(raw)
    return ValidateResult(valid=not any(i.severity == "error" for i in issues), issues=_issues(issues))


@mcp.tool()
def solve_case(path: str) -> SolveResult:
    """Simulate a player on data/<name>.json: which clues are obtainable, in which order, and whether the required ones are."""
    raw, error = _load(path)
    if error:
        return SolveResult(error=error)
    if validate_raw(raw):
        return SolveResult(error=_INVALID)
    result = solve(case_from_dict(raw))
    return SolveResult(
        solvable=result.solvable,
        obtainable=list(result.obtainable),
        missing_required=list(result.missing_required),
        steps=[StepModel(action=s.action, target=s.target, gives=list(s.gives)) for s in result.steps],
    )


@mcp.tool()
def lint_case(path: str) -> LintResult:
    """Quality warnings for data/<name>.json (sizes, red herring, unlock depth, dead ends)."""
    raw, error = _load(path)
    if error:
        return LintResult(error=error)
    if validate_raw(raw):
        return LintResult(error=_INVALID)
    return LintResult(warnings=_issues(lint(case_from_dict(raw))))


@mcp.resource("case-format://spec")
def case_format_spec() -> str:
    """The case file format (docs/case-format.md)."""
    return (repo_root() / "docs" / "case-format.md").read_text(encoding="utf-8")


@mcp.prompt()
def design_case(theme: str) -> str:
    """Template for designing a new Cold Trail case."""
    return (
        f"Design a new Cold Trail detective case with the theme: {theme}.\n"
        "1. Read the resource case-format://spec first and follow the format exactly.\n"
        "2. Write the case to data/<name>.json.\n"
        "3. Run validate_case until there are no issues, then solve_case (the required clues must be "
        "obtainable, the killer deducible from clue texts alone), then lint_case until it has no warnings.\n"
        "4. Fair play: at least one red herring, killer deducible from the clue texts."
    )
```
`src/case_tools/__main__.py`
```python
from case_tools.server import mcp

if __name__ == "__main__":
    mcp.run()
```
- [ ] **Step 4 (programmer):** Run full pytest (`python -m pytest tools/case-tools`). Expected: all pass, including the protocol tests (each starts a server process). If `test_parity` fails on `lint(case) == []` for `data/case01.json`, STOP and report the exact warnings (do not edit `data/`; Lead routes it to game-designer).
- [ ] **Step 5 (programmer):** Commit `feat: path guard and MCP server`; push; `gh pr checks --watch`.

---

### Task 6: Integration: `.mcp.json`, agents, docs (Lead; general-purpose subagent)

**Files:** Create `.mcp.json`; Modify `.claude/agents/game-designer.md`, `CLAUDE.md`, `README.md`

- [ ] **Step 1:** `.mcp.json` (repo root)
```json
{
  "mcpServers": {
    "case-tools": {
      "command": "${CASE_TOOLS_PYTHON:-python}",
      "args": ["-m", "case_tools"],
      "env": { "CASE_TOOLS_ROOT": "." }
    }
  }
}
```
- [ ] **Step 2:** `.claude/agents/game-designer.md` frontmatter `tools:` becomes `Read, Write, Edit, Glob, Grep, mcp__case-tools__validate_case, mcp__case-tools__solve_case, mcp__case-tools__lint_case`; add one body line: `After writing a case run validate_case, solve_case and lint_case (MCP server case-tools) until clean.`
- [ ] **Step 3:** `CLAUDE.md`: add lines: Python tooling commands (venv + `pip install -e "tools/case-tools[dev]"`, `python -m pytest tools/case-tools`), lanes (programmer `tools/case-tools/src` + `pyproject.toml`; qa `tools/case-tools/tests`), `.mcp.json` note (set env `CASE_TOOLS_PYTHON` to the venv python, e.g. `.venv\Scripts\python.exe`).
- [ ] **Step 4:** `README.md`: in Architecture replace "planned" markers (diagram label `Python, planned` -> `Python`; bullet "(`case-tools`, Python, planned)" -> "(`case-tools`, Python)"; layout line `tools/case-tools/  MCP server in Python (planned)` -> `tools/case-tools/  MCP server in Python`). Add section "## Python tooling (case-tools MCP server)": venv + install + test commands, the three tools, the resource and the prompt, the `data/<name>.json` path rule, how to register it in Claude Code (`.mcp.json` ships with the repo; set `CASE_TOOLS_PYTHON`; check with `claude mcp list`).
- [ ] **Step 5:** Commit `docs: register case-tools MCP server, update agents and docs`; push; `gh pr checks --watch`. Expected: green.

---

### Task 7: Final check, PR hand-off (Lead)

- [ ] **Step 1:** Fresh venv, install, full pytest; C++ build and ctest unchanged (43 tests). Expected: all pass.
- [ ] **Step 2:** Manual protocol check: `claude mcp list` shows `case-tools` connected (user approves the project server on first use) and `validate_case("data/case01.json")` returns `valid: true`. If Claude Code cannot be driven from the session, report the exact command for the user.
- [ ] **Step 3:** Whole-branch review by Lead, posted as a PR comment (`gh pr review --comment`); Lead never approves, merges or closes.
- [ ] **Step 4:** Tell the user the PR is ready; user reviews and merges. Remarks go to the programmer (tests-only remarks to qa).

---

## Unresolved questions
1. `.mcp.json` uses `${CASE_TOOLS_PYTHON:-python}`; does the user's Claude Code expand it as expected? (Verified manually in Task 7.)
2. Public repo and Python deps in CI: OK to add the `python` job to the PR workflow (extra ~1 min)?
