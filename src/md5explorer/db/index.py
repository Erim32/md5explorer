"""Indexing: walk a directory and write file metadata into SQLite."""

from __future__ import annotations

import datetime
import os
import sqlite3
import sys
from multiprocessing import Pool, cpu_count
from pathlib import Path

from md5explorer.core.hashing import md5
from md5explorer.core.utils import progress
from md5explorer.db.manager import INSERT_SQL

FileRow = tuple[str, str | None, int, str, str]


def collect_file_info(filepath: Path) -> FileRow | None:
    """Gather the metadata row for a single file.

    Module-level so it can be pickled by :mod:`multiprocessing`.
    """
    try:
        stat = filepath.stat()
        digest = md5(filepath)
        created_at = datetime.datetime.fromtimestamp(stat.st_ctime).isoformat()
        modified_at = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
        return (
            str(filepath.resolve()),
            digest,
            stat.st_size,
            created_at,
            modified_at,
        )
    except OSError:
        return None


class DbIndexScanner:
    """Scan a directory and populate the SQLite index."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose

    def collect_files(
        self,
        root: Path,
        exclusions: list[Path] | None = None,
    ) -> list[Path]:
        """List every file under ``root``, honouring absolute and name-based exclusions."""
        excl_resolved = {e.resolve() for e in (exclusions or [])}
        excl_names = {e.name for e in (exclusions or []) if not e.is_absolute()}
        files: list[Path] = []

        for dirpath, dirs, filenames in os.walk(root):
            dir_path = Path(dirpath).resolve()

            if any(dir_path == e or dir_path.is_relative_to(e) for e in excl_resolved):
                dirs.clear()
                continue

            dirs[:] = [d for d in dirs if d not in excl_names]

            for name in filenames:
                files.append(dir_path / name)

        return files

    def insert_sequential(self, conn: sqlite3.Connection, files: list[Path]) -> int:
        """Single-threaded insert with a progress bar."""
        rows: list[FileRow] = []
        for filepath in progress(files, desc="Indexing (single-thread)"):
            info = collect_file_info(filepath)
            if info:
                rows.append(info)
            elif self.verbose:
                print(f"  [WARN] Skipped: {filepath}", file=sys.stderr)

        with conn:
            conn.executemany(INSERT_SQL, rows)
        return len(rows)

    def insert_parallel(self, conn: sqlite3.Connection, files: list[Path]) -> int:
        """Multi-process insert with a progress bar."""
        nb_workers = max(1, cpu_count() - 1)
        print(f"  Workers: {nb_workers}")

        with Pool(nb_workers) as pool:
            results = list(
                progress(
                    pool.imap_unordered(collect_file_info, files),
                    total=len(files),
                    desc="Indexing (multi-process)",
                )
            )

        rows = [r for r in results if r is not None]

        with conn:
            conn.executemany(INSERT_SQL, rows)
        return len(rows)
