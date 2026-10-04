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
