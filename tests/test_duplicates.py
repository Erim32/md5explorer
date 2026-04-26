"""Tests for :mod:`md5explorer.scan.duplicates`."""

from __future__ import annotations

from pathlib import Path

import pytest

from md5explorer.scan.duplicates import KEEP_STRATEGIES, DuplicateCleaner, DuplicateScanner, pick_file_to_keep


def test_scanner_finds_single_group_with_three_copies(sample_tree: Path) -> None:
    scanner = DuplicateScanner()
    groups = scanner.scan([sample_tree])

    assert len(groups) == 1
    group = groups[0]
    assert group.total_count == 3
    names = sorted(p.name for p in group.all_files)
    assert names == ["a.txt", "b.txt", "d.txt"]


def test_scanner_cross_directory_flag(tmp_path: Path) -> None:
    d1 = tmp_path / "d1"
    d2 = tmp_path / "d2"
    d1.mkdir()
    d2.mkdir()
    (d1 / "x.txt").write_text("shared\n")
    (d2 / "x.txt").write_text("shared\n")

    scanner = DuplicateScanner()
    groups = scanner.scan([d1, d2])

    assert len(groups) == 1
    assert groups[0].is_cross_directory()


def test_scanner_missing_directory_is_reported(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    scanner = DuplicateScanner()
    groups = scanner.scan([tmp_path / "does-not-exist"])
    assert groups == []
    assert "Directory not found" in capsys.readouterr().err


@pytest.mark.parametrize("strategy", KEEP_STRATEGIES)
def test_pick_file_to_keep_accepts_all_strategies(tmp_path: Path, strategy: str) -> None:
    files = []
    for i, payload in enumerate((b"a", b"bb", b"ccc"), start=1):
        f = tmp_path / f"f{i}"
        f.write_bytes(payload)
        files.append(f)

    keeper = pick_file_to_keep(files, strategy)
    assert keeper in files


def test_pick_file_to_keep_smallest_and_largest_by_size(tmp_path: Path) -> None:
    small = tmp_path / "small"
    large = tmp_path / "large"
    small.write_bytes(b"a")
    large.write_bytes(b"a" * 100)

    assert pick_file_to_keep([small, large], "smallest") == small
    assert pick_file_to_keep([small, large], "largest") == large


def test_pick_file_to_keep_unknown_strategy_raises() -> None:
    with pytest.raises(ValueError):
        pick_file_to_keep([Path("x")], "unknown")


def test_cleaner_dry_run_does_not_delete(sample_tree: Path) -> None:
    groups = DuplicateScanner().scan([sample_tree])
    cleaner = DuplicateCleaner(strategy="first", dry_run=True)
    plan = cleaner.plan(groups, [sample_tree])

    assert len(plan) == 2  # three copies of "hello" -> keep one, delete two

    deleted, failed = cleaner.execute(plan)
    assert len(deleted) == 2
    assert failed == []
    for to_delete, _keeper in plan:
        assert to_delete.exists(), "dry-run must leave files in place"


def test_cleaner_actually_deletes_when_not_dry_run(sample_tree: Path) -> None:
    groups = DuplicateScanner().scan([sample_tree])
    cleaner = DuplicateCleaner(strategy="first", dry_run=False)
    plan = cleaner.plan(groups, [sample_tree])

    deleted, failed = cleaner.execute(plan)

    assert failed == []
    assert len(deleted) == 2
    for path in deleted:
        assert not path.exists()


def test_cleaner_cross_only_skips_intra_directory_duplicates(tmp_path: Path) -> None:
    d1 = tmp_path / "d1"
    d2 = tmp_path / "d2"
    d1.mkdir()
    d2.mkdir()
    (d1 / "a.txt").write_text("intra\n")
    (d1 / "b.txt").write_text("intra\n")
    (d2 / "c.txt").write_text("cross\n")
    (d1 / "c.txt").write_text("cross\n")

    groups = DuplicateScanner().scan([d1, d2])
    cleaner = DuplicateCleaner(strategy="first", dry_run=True, cross_only=True)
    plan = cleaner.plan(groups, [d1, d2])

    targets = {src.name for src, _ in plan}
    assert targets == {"c.txt"}
