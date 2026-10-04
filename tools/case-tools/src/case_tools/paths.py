from __future__ import annotations

import os
import re
from pathlib import Path

_CASE_PATH = re.compile(r"data/[A-Za-z0-9_-]+\.json")


class PathError(ValueError):
    pass


def repo_root() -> Path:
    return Path(os.environ.get("CASE_TOOLS_ROOT") or Path.cwd()).resolve()


def resolve_case_path(path: str, root: Path | None = None) -> Path:
    """Accept only data/<name>.json inside the repo's data dir (symlinks resolved)."""
    base = (root or repo_root()).resolve()
    if not _CASE_PATH.fullmatch(path):
        raise PathError("path must look like data/<name>.json (relative, no subdirectories)")
    full = (base / path).resolve()
    if full.parent != (base / "data").resolve():
        raise PathError("path escapes the data/ directory")
    return full
