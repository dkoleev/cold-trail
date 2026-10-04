import os

import pytest

from case_tools.paths import PathError, resolve_case_path


@pytest.fixture
def root(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "case01.json").write_text("{}", encoding="utf-8")
    return tmp_path


def test_valid_path_resolves_inside_data(root):
    assert resolve_case_path("data/case01.json", root) == (root / "data" / "case01.json").resolve()


@pytest.mark.parametrize(
    "bad",
    [
        "../x.json",
        "data/../x.json",
        "/abs/data/x.json",
        "C:/data/x.json",
        "data\\x.json",
        "data/sub/x.json",
        "data/x.txt",
        "data/.json",
        "data/",
        "",
        "case01.json",
        "data/x.json\n",
    ],
)
def test_rejected_paths(root, bad):
    with pytest.raises(PathError):
        resolve_case_path(bad, root)


def test_symlink_escaping_data_is_rejected(root, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "secret.json"
    outside.write_text("{}", encoding="utf-8")
    link = root / "data" / "link.json"
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not available")
    with pytest.raises(PathError):
        resolve_case_path("data/link.json", root)
