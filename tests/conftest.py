"""Shared pytest fixtures for md5explorer tests."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_TREE = FIXTURES_DIR / "sample_tree"


@pytest.fixture
def sample_tree_src() -> Path:
    """Read-only path to the committed sample tree."""
    return SAMPLE_TREE


@pytest.fixture
def sample_tree(tmp_path: Path) -> Path:
    """Writable copy of the sample tree under a temporary directory.

    Use this whenever a test might mutate files (deletion, rename, ...).
    """
    dst = tmp_path / "sample_tree"
    shutil.copytree(SAMPLE_TREE, dst)
    return dst


@pytest.fixture
def empty_tree(tmp_path: Path) -> Path:
    """A tree with only empty directories (leaves-first layout)."""
    root = tmp_path / "empty_tree"
    (root / "a" / "b" / "c").mkdir(parents=True)
    (root / "x").mkdir()
    (root / "y" / "z").mkdir(parents=True)
    return root


@pytest.fixture
def two_directories(tmp_path: Path) -> tuple[Path, Path]:
    """Two sibling directories with partially overlapping content."""
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()

    (left / "same.txt").write_text("same content\n", encoding="utf-8")
    (right / "same.txt").write_text("same content\n", encoding="utf-8")

    (left / "differ.txt").write_text("left version\n", encoding="utf-8")
    (right / "differ.txt").write_text("right version\n", encoding="utf-8")

    (left / "only_left.txt").write_text("L\n", encoding="utf-8")
    (right / "only_right.txt").write_text("R\n", encoding="utf-8")

    return left, right
