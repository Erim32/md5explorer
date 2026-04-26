"""Tests for :mod:`md5explorer.db`."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from md5explorer.db.compare import DbComparator, DbCompareCleaner
from md5explorer.db.index import DbIndexScanner, collect_file_info
from md5explorer.db.manager import DatabaseManager


def test_collect_file_info_returns_metadata(tmp_path: Path) -> None:
    f = tmp_path / "sample.bin"
    f.write_bytes(b"payload")

    row = collect_file_info(f)
    assert row is not None
    abs_path, digest, size, _created, _modified = row
    assert Path(abs_path) == f.resolve()
    assert digest is not None
    assert size == len(b"payload")


def test_collect_file_info_missing_file_returns_none(tmp_path: Path) -> None:
    assert collect_file_info(tmp_path / "ghost") is None


def test_database_manager_init_creates_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "index.sqlite"
    conn = DatabaseManager(db_path).init()
    try:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {r[0] for r in cur.fetchall()}
        assert "files" in tables
    finally:
        conn.close()


def test_database_manager_reset_drops_existing(tmp_path: Path) -> None:
    db_path = tmp_path / "index.sqlite"
    manager = DatabaseManager(db_path)
    conn = manager.init()
    conn.execute("INSERT INTO files (absolute_path, md5, size) VALUES ('/tmp/x', 'abc', 1)")
    conn.commit()
    conn.close()

    # Reset should wipe the row.
    conn = manager.init(reset=True)
    try:
        count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        assert count == 0
    finally:
        conn.close()


def test_db_index_scanner_inserts_every_file(sample_tree: Path, tmp_path: Path) -> None:
    db_path = tmp_path / "index.sqlite"
    conn = DatabaseManager(db_path).init()
    try:
        scanner = DbIndexScanner()
        files = scanner.collect_files(sample_tree)
        count = scanner.insert_sequential(conn, files)
        assert count == len(files)

        stored = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        assert stored == len(files)
    finally:
        conn.close()


def test_db_index_scanner_honors_exclusion_by_name(sample_tree: Path) -> None:
    scanner = DbIndexScanner()
    files = scanner.collect_files(sample_tree, exclusions=[Path("subdir")])

    names = {f.name for f in files}
    assert "d.txt" not in names
    assert "e.txt" not in names
    assert "a.txt" in names


def test_db_compare_finds_matches_across_trees(sample_tree: Path, tmp_path: Path) -> None:
    # Index the sample tree, then copy one of its files to a new location and
    # expect the comparator to flag the new copy as a match.
    db_path = tmp_path / "index.sqlite"
    conn = DatabaseManager(db_path).init()
    try:
        scanner = DbIndexScanner()
        scanner.insert_sequential(conn, scanner.collect_files(sample_tree))

        new_dir = tmp_path / "incoming"
        new_dir.mkdir()
        copy = new_dir / "copy.txt"
        shutil.copy(sample_tree / "a.txt", copy)

        matches = DbComparator(conn).compare([copy])
        assert len(matches) == 1
        assert matches[0].new_file == copy.resolve()
    finally:
        conn.close()


def test_db_compare_cleaner_dry_run_keeps_file(sample_tree: Path, tmp_path: Path) -> None:
    db_path = tmp_path / "index.sqlite"
    conn = DatabaseManager(db_path).init()
    try:
        scanner = DbIndexScanner()
        scanner.insert_sequential(conn, scanner.collect_files(sample_tree))

        new_dir = tmp_path / "incoming"
        new_dir.mkdir()
        copy = new_dir / "copy.txt"
        shutil.copy(sample_tree / "a.txt", copy)

        matches = DbComparator(conn).compare([copy])
        deleted, failed = DbCompareCleaner(dry_run=True).execute(matches)

        assert failed == []
        assert deleted == [copy.resolve()]
        assert copy.exists(), "dry-run must not remove files"
    finally:
        conn.close()


def test_db_manager_connect_exits_when_db_missing(tmp_path: Path) -> None:
    manager = DatabaseManager(tmp_path / "missing.sqlite")
    with pytest.raises(SystemExit):
        manager.connect()
