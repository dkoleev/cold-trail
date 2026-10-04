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
