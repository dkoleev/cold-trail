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


def test_a_line_that_requires_the_clue_it_reveals_is_an_error(mini_raw):
    mini_raw["people"][0]["talk"][1]["requires"] = "c_alibi"
    issues = validate_raw(mini_raw)
    assert codes(issues) == ["self-requiring-line"]
    assert issues[0].path == "people[0].talk[1]"
