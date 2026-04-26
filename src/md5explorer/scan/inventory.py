"""Flat-text inventory (MD5 + name + mtime + path) of a directory tree."""

from __future__ import annotations

import datetime
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from md5explorer.core.hashing import md5


@dataclass
class FileInfo:
    """Metadata for a single file captured during inventory."""

    name: str
    path: Path
    md5: str
    modified_at: str

    def to_line(self, separator: str = "_") -> str:
        return f"{self.md5}{separator}{self.name}{separator}{self.modified_at}{separator}{self.path}"


class InventoryScanner:
    """Walk a directory and collect a :class:`FileInfo` for every file."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose

    def scan(self, root: Path) -> list[FileInfo]:
        results: list[FileInfo] = []

        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                filepath = Path(dirpath) / filename
                try:
                    digest = md5(filepath)
                    if digest is None:
                        print(f"[WARN] Cannot read {filepath}", file=sys.stderr)
                        digest = "MD5_ERROR"
                    info = FileInfo(
                        name=filepath.name,
                        path=filepath,
                        md5=digest,
                        modified_at=self._get_mtime(filepath),
                    )
                    results.append(info)
                    if self.verbose:
                        print(f"  {info.md5}  {info.path}")
                    elif len(results) % 100 == 0:
                        print(f"  Processed: {len(results)} files...")
                except Exception as exc:
                    print(f"[ERROR] {filepath}: {exc}", file=sys.stderr)

        return results

    @staticmethod
    def _get_mtime(filepath: Path) -> str:
        try:
            ts = filepath.stat().st_mtime
            return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d_%H-%M-%S")
        except OSError:
            return "DATE_ERROR"


class InventoryReporter:
    """Serialize an inventory to a text file with a documented header."""

    HEADER_FORMAT = (
        "# File inventory - Format: MD5{sep}NAME{sep}MODIFIED_AT{sep}PATH\n"
        "# Generated: {date}\n"
        "# Root: {root}\n\n"
    )

    @staticmethod
    def save(
        files: list[FileInfo],
        destination: Path,
        root: Path,
        separator: str = "_",
    ) -> None:
        with open(destination, "w", encoding="utf-8") as f:
            f.write(
                InventoryReporter.HEADER_FORMAT.format(
                    sep=separator,
                    date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    root=root.resolve(),
                )
            )
            for info in files:
                f.write(info.to_line(separator) + "\n")

        print(f"\nDone. {len(files)} file(s) inventoried.")
        print(f"-> Output saved to: {destination}")
