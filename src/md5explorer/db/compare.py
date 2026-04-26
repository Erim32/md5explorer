"""Compare a directory against the SQLite index to surface duplicates."""

from __future__ import annotations

import datetime
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from md5explorer.core.hashing import md5
from md5explorer.core.utils import human_size, progress


@dataclass
class DbCompareMatch:
    """A file in the scanned directory that already exists in the index."""

    new_file: Path
    indexed_file: Path
    md5: str
    size: int


class DbComparator:
    """Probe each candidate file against the ``files.md5`` column."""

    def __init__(self, conn: sqlite3.Connection, verbose: bool = False) -> None:
        self.conn = conn
        self.verbose = verbose

    def compare(self, files: list[Path]) -> list[DbCompareMatch]:
        matches: list[DbCompareMatch] = []

        for filepath in progress(files, desc="Comparing against database"):
            digest = md5(filepath)
            if not digest:
                continue

            cur = self.conn.execute(
                "SELECT absolute_path FROM files WHERE md5 = ?",
                (digest,),
            )
            row = cur.fetchone()
            if row:
                indexed_path = Path(row[0]).resolve()
                new_path = filepath.resolve()
                if indexed_path != new_path:
                    try:
                        size = filepath.stat().st_size
                    except OSError:
                        size = 0
                    matches.append(
                        DbCompareMatch(
                            new_file=new_path,
                            indexed_file=indexed_path,
                            md5=digest,
                            size=size,
                        )
                    )

        return matches


class DbCompareCleaner:
    """Delete the scanned files that already exist in the index."""

    def __init__(self, dry_run: bool = True, verbose: bool = False) -> None:
        self.dry_run = dry_run
        self.verbose = verbose

    def execute(self, matches: list[DbCompareMatch]) -> tuple[list[Path], list[Path]]:
        deleted: list[Path] = []
        failed: list[Path] = []
        prefix = "[DRY-RUN] " if self.dry_run else ""

        for match in matches:
            target = match.new_file
            try:
                if not self.dry_run:
                    target.unlink()
                if self.verbose:
                    print(f"  {prefix}Deleted: {target}  (indexed copy: {match.indexed_file.name})")
                deleted.append(target)
            except PermissionError as exc:
                print(f"  [ERROR] Permission denied: {target} - {exc}", file=sys.stderr)
                failed.append(target)
            except FileNotFoundError:
                if self.verbose:
                    print(f"  [INFO] Already missing: {target}")

        return deleted, failed


class DbCompareReporter:
    """Render the directory-vs-index comparison results."""

    @staticmethod
    def report_matches(matches: list[DbCompareMatch], export_path: Path | None = None) -> None:
        if not matches:
            print("OK  No file from the scanned directory is present in the index.")
            return

        print(f"\n!  {len(matches)} file(s) already indexed:")
        print("-" * 60)
        for m in matches:
            print(f"{m.indexed_file} (ORIGINAL - MD5: {m.md5})")
            print(f"- {m.new_file} (duplicate)")

        total_size = sum(m.size for m in matches)
        print(f"\nTotal: {len(matches)} duplicate(s), {human_size(total_size)} recoverable.")

        if export_path:
            with open(export_path, "w", encoding="utf-8") as f:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"# Duplicates detected - {timestamp}\n\n")
                for m in matches:
                    f.write(f"New      : {m.new_file}\n")
                    f.write(f"Indexed  : {m.indexed_file}\n")
                    f.write(f"MD5      : {m.md5}\n\n")
            print(f"\n-> Results exported to: {export_path}")

    @staticmethod
    def report_deletion(
        matches: list[DbCompareMatch],
        deleted: list[Path],
        failed: list[Path],
        dry_run: bool,
    ) -> None:
        deleted_set = set(deleted)
        freed = sum(m.size for m in matches if m.new_file in deleted_set)
        mode = "DRY-RUN - no changes written to disk" if dry_run else "Deletion complete"
        print(f"\n{'-' * 60}")
        print(f"  {mode}")
        print(f"  Targeted : {len(matches)}")
        print(f"  Deleted  : {len(deleted)}")
        if failed:
            print(f"  Failed   : {len(failed)}")
        print(f"  Space {'estimated ' if dry_run else ''}freed: {human_size(freed)}")
        print(f"{'-' * 60}")
