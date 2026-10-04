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
