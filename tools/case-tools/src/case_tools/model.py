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
