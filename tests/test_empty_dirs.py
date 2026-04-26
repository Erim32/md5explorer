"""Tests for :mod:`md5explorer.scan.empty_dirs`."""

from __future__ import annotations

from pathlib import Path

from md5explorer.scan.empty_dirs import EmptyDirCleaner, EmptyDirScanner


def test_scanner_detects_leaf_directories(empty_tree: Path) -> None:
    found = EmptyDirScanner().scan(empty_tree)
    # topdown=False -> leaves first
    names = [p.name for p in found]
    assert names[0] == "c"


def test_scanner_returns_only_leaf_empty_dirs(empty_tree: Path) -> None:
    # One pass identifies filesystem-empty directories only. Parents that
    # contain empty subdirectories are only detectable after a subsequent
    # scan, once the leaves have been removed.
    found = {p.relative_to(empty_tree).as_posix() for p in EmptyDirScanner().scan(empty_tree)}
    assert found == {"a/b/c", "x", "y/z"}


def test_scanner_skips_non_empty_dirs(tmp_path: Path) -> None:
    (tmp_path / "full").mkdir()
    (tmp_path / "full" / "f.txt").write_text("x\n")
    (tmp_path / "empty").mkdir()

    found = {p.name for p in EmptyDirScanner().scan(tmp_path)}
    assert found == {"empty"}


def test_cleaner_dry_run_keeps_directories(empty_tree: Path) -> None:
    candidates = EmptyDirScanner().scan(empty_tree)
    deleted, failed = EmptyDirCleaner(dry_run=True).execute(candidates)

    assert failed == []
    assert len(deleted) == len(candidates)
    for path in candidates:
        assert path.exists(), "dry-run must not remove directories"


def test_cleaner_actually_removes_directories(empty_tree: Path) -> None:
    candidates = EmptyDirScanner().scan(empty_tree)
    deleted, failed = EmptyDirCleaner(dry_run=False).execute(candidates)

    assert failed == []
    assert len(deleted) == len(candidates)
    for path in candidates:
        assert not path.exists()
