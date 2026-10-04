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


def _obtainable(case: Case) -> list[str]:
    """Clues a player who plans well can learn: fixed point over every reachable location (exits are static)."""
    found: list[str] = []
    changed = True
    while changed:
        changed = False
        for loc in _bfs_order(case):
            before = len(found)
            _collect(case, loc, found)
            changed |= len(found) > before
    return found


def solve(case: Case) -> SolveResult:
    """`obtainable`/`solvable` assume the player picks the best order; `steps` is a greedy walkthrough
    (nearest location first) and can be incomplete when one-way exits trap the walker (lint flags them)."""
    by_id = {l.id: l for l in case.locations}
    walked: list[str] = []
    steps: list[Step] = []
    at = case.start
    progress = True
    while progress:
        progress = False
        for loc in _bfs_order(case):
            if not _collect(case, loc, list(walked)):
                continue
            walk = _route(case, at, loc.id)
            if walk is None:
                continue
            steps.extend(Step("go", by_id[hop].name, ()) for hop in walk)
            at = loc.id
            steps.extend(_collect(case, loc, walked))
            progress = True
    found = _obtainable(case)
    missing = tuple(c for c in case.solution.required_clues if c not in found)
    return SolveResult(tuple(found), tuple(steps), missing)
