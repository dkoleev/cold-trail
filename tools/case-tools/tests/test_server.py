import asyncio
import json
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from conftest import MINI


@pytest.fixture
def root(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "data" / "mini.json").write_text(json.dumps(MINI), encoding="utf-8")
    bom = "﻿" + json.dumps(MINI)
    (tmp_path / "data" / "bom.json").write_text(bom, encoding="utf-8")
    (tmp_path / "data" / "broken.json").write_text("{not json", encoding="utf-8")
    bad = dict(MINI, start="nowhere")
    (tmp_path / "data" / "bad.json").write_text(json.dumps(bad), encoding="utf-8")
    (tmp_path / "docs" / "case-format.md").write_text("# spec", encoding="utf-8")
    return tmp_path


def with_session(root: Path, fn):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "case_tools"],
        env={**os.environ, "CASE_TOOLS_ROOT": str(root)},
    )

    async def go():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await fn(session)

    return asyncio.run(go())


def call(root, name, path):
    async def fn(s):
        return await s.call_tool(name, {"path": path})

    return with_session(root, fn)


def test_lists_the_three_tools(root):
    async def fn(s):
        return {t.name for t in (await s.list_tools()).tools}

    assert with_session(root, fn) == {"validate_case", "solve_case", "lint_case"}


def test_validate_valid_case(root):
    res = call(root, "validate_case", "data/mini.json")
    assert res.is_error is False
    assert res.structured_content["valid"] is True
    assert res.structured_content["issues"] == []


def test_validate_reports_issues(root):
    res = call(root, "validate_case", "data/bad.json")
    assert res.structured_content["valid"] is False
    assert res.structured_content["issues"][0]["code"] == "unknown-ref"


def test_solve_returns_ordered_steps(root):
    res = call(root, "solve_case", "data/mini.json")
    data = res.structured_content
    assert data["solvable"] is True
    assert [s["action"] for s in data["steps"]] == ["go", "examine", "go", "talk"]


def test_solve_refuses_an_invalid_case(root):
    data = call(root, "solve_case", "data/bad.json").structured_content
    assert data["solvable"] is False
    assert "validate_case" in data["error"]


def test_lint_returns_warnings(root):
    data = call(root, "lint_case", "data/mini.json").structured_content
    assert "size-locations" in [w["code"] for w in data["warnings"]]


def test_bom_prefixed_file_is_read(root):
    assert call(root, "validate_case", "data/bom.json").structured_content["valid"] is True


@pytest.mark.parametrize("path", ["../etc/passwd", "data/../x.json", "/abs/data/mini.json", "data/sub/x.json"])
def test_path_outside_data_is_rejected_without_crashing(root, path):
    res = call(root, "validate_case", path)
    assert res.is_error is False
    assert res.structured_content["error"]


def test_missing_and_broken_files_give_a_structured_error_and_server_survives(root):
    async def fn(s):
        missing = await s.call_tool("validate_case", {"path": "data/missing.json"})
        broken = await s.call_tool("validate_case", {"path": "data/broken.json"})
        after = await s.call_tool("validate_case", {"path": "data/mini.json"})
        return missing, broken, after

    missing, broken, after = with_session(root, fn)
    assert "not found" in missing.structured_content["error"]
    assert "invalid JSON" in broken.structured_content["error"]
    assert after.structured_content["valid"] is True


def test_resource_serves_the_format_spec(root):
    async def fn(s):
        return await s.read_resource("case-format://spec")

    assert with_session(root, fn).contents[0].text == "# spec"


def test_prompt_mentions_theme_and_tools(root):
    async def fn(s):
        return await s.get_prompt("design_case", {"theme": "lighthouse"})

    text = with_session(root, fn).messages[0].content.text
    assert "lighthouse" in text
    assert "validate_case" in text and "solve_case" in text and "lint_case" in text
