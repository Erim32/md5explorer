"""Tests for :mod:`md5explorer.scan.compare`."""

from __future__ import annotations

from pathlib import Path

from md5explorer.scan.compare import DirectoryComparator


def test_comparator_classifies_each_path(two_directories: tuple[Path, Path]) -> None:
    left, right = two_directories
    result = DirectoryComparator(left, right).compare()

    assert result.identical == ["same.txt"]
    assert result.different == ["differ.txt"]
    assert result.only_left == ["only_left.txt"]
    assert result.only_right == ["only_right.txt"]
    assert result.are_identical is False
    assert result.total_left == 3
    assert result.total_right == 3


def test_comparator_identical_directories(tmp_path: Path) -> None:
    left = tmp_path / "l"
    right = tmp_path / "r"
    left.mkdir()
    right.mkdir()
    (left / "f.txt").write_text("same\n")
    (right / "f.txt").write_text("same\n")

    result = DirectoryComparator(left, right).compare()
    assert result.are_identical is True
    assert result.identical == ["f.txt"]


def test_comparator_captures_diff_hashes(two_directories: tuple[Path, Path]) -> None:
    left, right = two_directories
    result = DirectoryComparator(left, right).compare()
    hashes = result.diff_hashes["differ.txt"]
    assert hashes[0] != hashes[1]


def test_comparator_honors_ignored_names(tmp_path: Path) -> None:
    left = tmp_path / "l"
    right = tmp_path / "r"
    (left / ".git").mkdir(parents=True)
    (right / ".git").mkdir(parents=True)
    (left / ".git" / "HEAD").write_text("x\n")
    (right / ".git" / "HEAD").write_text("y\n")
    (left / "file.txt").write_text("same\n")
    (right / "file.txt").write_text("same\n")

    result = DirectoryComparator(left, right, ignored={".git"}).compare()
    assert result.are_identical is True
