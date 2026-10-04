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
