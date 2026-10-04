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
            if line.get("requires") is not None and line.get("requires") == line.get("reveals"):
                _err(issues, "self-requiring-line", f"line requires and reveals the same clue '{line['requires']}'", f"people[{i}].talk[{j}]")
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
