from case_tools.issues import Issue


def test_issue_is_a_value_object():
    assert Issue("error", "x", "m", "$") == Issue("error", "x", "m", "$")
