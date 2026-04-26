"""End-to-end CLI tests that exercise ``md5explorer.cli.main``."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from md5explorer import __version__
from md5explorer.cli import build_parser, main


def test_parser_builds_cleanly() -> None:
    parser = build_parser()
    assert parser.prog == "md5explorer"


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_no_args_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([])
    assert exit_code == 0
    assert "scan" in capsys.readouterr().out


def test_scan_duplicates_on_clean_tree_returns_zero(tmp_path: Path) -> None:
    d = tmp_path / "d"
    d.mkdir()
    (d / "only.txt").write_text("unique\n")
    assert main(["scan", "duplicates", str(d)]) == 0


def test_scan_duplicates_on_dirty_tree_returns_one(sample_tree: Path) -> None:
    # Duplicates present, no --delete: exit code signals "action available".
    assert main(["scan", "duplicates", str(sample_tree)]) == 1


def test_scan_duplicates_delete_dry_run(sample_tree: Path) -> None:
    before = {p for p in sample_tree.rglob("*") if p.is_file()}
    exit_code = main(["scan", "duplicates", str(sample_tree), "--delete", "--dry-run"])
    after = {p for p in sample_tree.rglob("*") if p.is_file()}
    assert exit_code == 0
    assert before == after


def test_scan_duplicates_delete_yes_removes_files(sample_tree: Path) -> None:
    before = sum(1 for p in sample_tree.rglob("*") if p.is_file())
    exit_code = main(["scan", "duplicates", str(sample_tree), "--delete", "--yes"])
    after = sum(1 for p in sample_tree.rglob("*") if p.is_file())
    assert exit_code == 0
    assert after == before - 2  # two of the three "hello" copies removed


def test_scan_compare_identical_returns_zero(tmp_path: Path) -> None:
    left = tmp_path / "l"
    right = tmp_path / "r"
    left.mkdir()
    right.mkdir()
    (left / "f.txt").write_text("same\n")
    (right / "f.txt").write_text("same\n")
    assert main(["scan", "compare", str(left), str(right)]) == 0


def test_scan_compare_different_returns_one(two_directories: tuple[Path, Path]) -> None:
    left, right = two_directories
    assert main(["scan", "compare", str(left), str(right)]) == 1


def test_scan_inventory_writes_file(sample_tree: Path, tmp_path: Path) -> None:
    output = tmp_path / "inv.txt"
    assert main(["scan", "inventory", str(sample_tree), "-o", str(output)]) == 0
    assert output.exists()
    assert output.stat().st_size > 0


def test_scan_empty_dirs_on_tree_with_empties(empty_tree: Path) -> None:
    assert main(["scan", "empty-dirs", str(empty_tree)]) == 1


def test_scan_empty_dirs_delete_yes_removes_leaves(empty_tree: Path) -> None:
    # One invocation removes only leaf-empty directories; intermediate parents
    # that had empty children survive until the next pass.
    assert main(["scan", "empty-dirs", str(empty_tree), "--delete", "--yes"]) == 0
    assert not (empty_tree / "a" / "b" / "c").exists()
    assert not (empty_tree / "x").exists()
    assert not (empty_tree / "y" / "z").exists()


def test_db_index_and_list(sample_tree: Path, tmp_path: Path) -> None:
    db = tmp_path / "idx.sqlite"
    assert main(["db", "index", str(sample_tree), "--db", str(db), "--slow"]) == 0
    assert db.exists()
    assert main(["db", "list", "--db", str(db)]) == 0


def test_db_check_hits_and_misses(sample_tree: Path, tmp_path: Path) -> None:
    db = tmp_path / "idx.sqlite"
    main(["db", "index", str(sample_tree), "--db", str(db), "--slow"])

    present = sample_tree / "a.txt"
    assert main(["db", "check", str(present), "--db", str(db)]) == 0

    missing = tmp_path / "nowhere.txt"
    missing.write_text("brand new\n")
    assert main(["db", "check", str(missing), "--db", str(db)]) == 1


def test_db_compare_flags_copy(sample_tree: Path, tmp_path: Path) -> None:
    db = tmp_path / "idx.sqlite"
    main(["db", "index", str(sample_tree), "--db", str(db), "--slow"])

    incoming = tmp_path / "incoming"
    incoming.mkdir()
    shutil.copy(sample_tree / "a.txt", incoming / "copy.txt")

    assert main(["db", "compare", str(incoming), "--db", str(db)]) == 1
