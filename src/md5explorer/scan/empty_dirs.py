"""Detect and optionally delete empty directories (leaves-first)."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EmptyDirResult:
    """Result bundle for an empty-directory operation."""

    found: list[Path] = field(default_factory=list)
    deleted: list[Path] = field(default_factory=list)
    failed: list[Path] = field(default_factory=list)


class EmptyDirScanner:
    """Walk a tree and return its empty directories (leaves first)."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose

    def scan(self, root: Path) -> list[Path]:
        empty: list[Path] = []
        for dirpath, _subdirs, _filenames in os.walk(root, topdown=False):
            path = Path(dirpath)
            if path == root:
                continue
            try:
                if not any(path.iterdir()):
                    if self.verbose:
                        print(f"  [EMPTY] {path}")
                    empty.append(path)
            except PermissionError:
                print(f"[WARN] Access denied: {path}", file=sys.stderr)

        return empty


class EmptyDirCleaner:
    """Remove (or simulate removing) a list of empty directories."""

    def __init__(self, dry_run: bool = True, verbose: bool = False) -> None:
        self.dry_run = dry_run
        self.verbose = verbose

    def execute(self, candidates: list[Path]) -> tuple[list[Path], list[Path]]:
        deleted: list[Path] = []
        failed: list[Path] = []
        prefix = "[DRY-RUN] " if self.dry_run else ""

        for path in candidates:
            try:
                if not self.dry_run:
                    path.rmdir()
                if self.verbose or self.dry_run:
                    print(f"  {prefix}Deleted: {path}")
                deleted.append(path)
            except PermissionError as exc:
                print(f"  [ERROR] Permission denied: {path} - {exc}", file=sys.stderr)
                failed.append(path)
            except OSError as exc:
                print(f"  [ERROR] Cannot remove '{path}': {exc}", file=sys.stderr)
                failed.append(path)

        return deleted, failed


class EmptyDirReporter:
    """Format and emit the empty-directory scan/deletion report."""

    def __init__(self, output_path: Path | None = None) -> None:
        self.output_path = output_path

    def report_scan(self, found: list[Path], root: Path) -> None:
        lines: list[str] = []
        if not found:
            lines.append("No empty directories found.")
        else:
            lines.append(f"Empty directories under '{root}':")
            for p in found:
                lines.append(f"  - {p}")
            lines.append(f"\nTotal: {len(found)} empty directory(ies) detected.")

        for line in lines:
            print(line)

        if self.output_path:
            self.output_path.write_text("\n".join(lines), encoding="utf-8")
            print(f"\n-> Report saved to: {self.output_path}")

    @staticmethod
    def report_deletion(
        found: list[Path],
        deleted: list[Path],
        failed: list[Path],
        dry_run: bool,
    ) -> None:
        mode = "DRY-RUN - no changes written to disk" if dry_run else "Deletion complete"
        print(f"\n{'-' * 60}")
        print(f"  {mode}")
        print(f"  Targeted : {len(found)}")
        print(f"  Deleted  : {len(deleted)}")
        if failed:
            print(f"  Failed   : {len(failed)}")
        print(f"{'-' * 60}")
