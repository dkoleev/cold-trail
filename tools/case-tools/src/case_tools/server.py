from __future__ import annotations

import json
from dataclasses import asdict

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel

from case_tools.lint import lint
from case_tools.model import case_from_dict
from case_tools.paths import PathError, repo_root, resolve_case_path
from case_tools.solve import solve
from case_tools.validate import validate_raw

mcp = MCPServer("case-tools")


class IssueModel(BaseModel):
    severity: str
    code: str
    message: str
    path: str


class StepModel(BaseModel):
    action: str
    target: str
    gives: list[str]


class ValidateResult(BaseModel):
    valid: bool = False
    issues: list[IssueModel] = []
    error: str | None = None


class SolveResult(BaseModel):
    solvable: bool = False
    obtainable: list[str] = []
    missing_required: list[str] = []
    steps: list[StepModel] = []
    error: str | None = None


class LintResult(BaseModel):
    warnings: list[IssueModel] = []
    error: str | None = None


def _load(path: str) -> tuple[object | None, str | None]:
    try:
        full = resolve_case_path(path)
    except PathError as exc:
        return None, str(exc)
    try:
        return json.loads(full.read_text(encoding="utf-8-sig")), None
    except FileNotFoundError:
        return None, f"file not found: {path}"
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON in {path}: {exc}"
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"cannot read {path}: {exc}"


def _issues(items) -> list[IssueModel]:
    return [IssueModel(**asdict(i)) for i in items]


_INVALID = "case is invalid; run validate_case first"


@mcp.tool()
def validate_case(path: str) -> ValidateResult:
    """Validate data/<name>.json against the case format. Returns every issue at once."""
    raw, error = _load(path)
    if error:
        return ValidateResult(error=error)
    issues = validate_raw(raw)
    return ValidateResult(valid=not any(i.severity == "error" for i in issues), issues=_issues(issues))


@mcp.tool()
def solve_case(path: str) -> SolveResult:
    """Simulate a player on data/<name>.json: which clues are obtainable, in which order, and whether the required ones are."""
    raw, error = _load(path)
    if error:
        return SolveResult(error=error)
    if validate_raw(raw):
        return SolveResult(error=_INVALID)
    result = solve(case_from_dict(raw))
    return SolveResult(
        solvable=result.solvable,
        obtainable=list(result.obtainable),
        missing_required=list(result.missing_required),
        steps=[StepModel(action=s.action, target=s.target, gives=list(s.gives)) for s in result.steps],
    )


@mcp.tool()
def lint_case(path: str) -> LintResult:
    """Quality warnings for data/<name>.json (sizes, red herring, unlock depth, dead ends)."""
    raw, error = _load(path)
    if error:
        return LintResult(error=error)
    if validate_raw(raw):
        return LintResult(error=_INVALID)
    return LintResult(warnings=_issues(lint(case_from_dict(raw))))


@mcp.resource("case-format://spec")
def case_format_spec() -> str:
    """The case file format (docs/case-format.md)."""
    return (repo_root() / "docs" / "case-format.md").read_text(encoding="utf-8")


@mcp.prompt()
def design_case(theme: str) -> str:
    """Template for designing a new Cold Trail case."""
    return (
        f"Design a new Cold Trail detective case with the theme: {theme}.\n"
        "1. Read the resource case-format://spec first and follow the format exactly.\n"
        "2. Write the case to data/<name>.json.\n"
        "3. Run validate_case until there are no issues, then solve_case (the required clues must be "
        "obtainable, the killer deducible from clue texts alone), then lint_case until it has no warnings.\n"
        "4. Fair play: at least one red herring, killer deducible from the clue texts."
    )
