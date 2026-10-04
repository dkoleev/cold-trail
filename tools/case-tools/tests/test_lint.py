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
