"""Duplicate file detection, keep-strategy planning, and deletion."""

from __future__ import annotations

import datetime
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from md5explorer.core.hashing import creation_time, md5
from md5explorer.core.utils import human_size

KEEP_STRATEGIES: tuple[str, ...] = ("first", "newest", "oldest", "smallest", "largest")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclass
class DuplicateGroup:
    """A set of files sharing the same MD5 hash, grouped by source directory."""

    hash_: str
    files_by_dir: dict[str, list[Path]] = field(default_factory=lambda: defaultdict(list))

    @property
    def all_files(self) -> list[Path]:
        return [f for files in self.files_by_dir.values() for f in files]

    @property
    def total_count(self) -> int:
        return sum(len(f) for f in self.files_by_dir.values())

    def is_cross_directory(self) -> bool:
        return len(self.files_by_dir) > 1


# ---------------------------------------------------------------------------
# Keep strategies
# ---------------------------------------------------------------------------


def pick_file_to_keep(files: list[Path], strategy: str) -> Path:
    if strategy == "first":
        return files[0]
    if strategy == "newest":
        return max(files, key=creation_time)
    if strategy == "oldest":
        return min(files, key=creation_time)
    if strategy == "smallest":
        return min(files, key=lambda p: p.stat().st_size)
    if strategy == "largest":
        return max(files, key=lambda p: p.stat().st_size)
    raise ValueError(f"Unknown keep strategy: {strategy!r}")


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


class DuplicateScanner:
    """Walk directories and group files that share the same MD5 digest."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose

    def scan(self, directories: list[Path]) -> list[DuplicateGroup]:
        raw: dict[str, DuplicateGroup] = {}

        for idx, root in enumerate(directories):
            dir_key = f"dir_{idx}"
            if not root.is_dir():
                print(f"[ERROR] Directory not found: {root}", file=sys.stderr)
                continue

            for dirpath, _, filenames in os.walk(root):
                for filename in filenames:
                    filepath = Path(dirpath) / filename
                    file_hash = md5(filepath)
                    if file_hash is None:
                        print(f"[WARN] Cannot read {filepath}", file=sys.stderr)
                        continue
                    if self.verbose:
                        print(f"  {file_hash}  {filepath}")
                    group = raw.setdefault(file_hash, DuplicateGroup(hash_=file_hash))
                    existing = group.files_by_dir[dir_key]
                    if filepath not in existing:
                        existing.append(filepath)

        return self._filter_duplicates(raw, len(directories))

    @staticmethod
    def _filter_duplicates(raw: dict[str, DuplicateGroup], nb_dirs: int) -> list[DuplicateGroup]:
        result: list[DuplicateGroup] = []
        for group in raw.values():
            has_internal = any(len(paths) > 1 for paths in group.files_by_dir.values())
            has_cross = group.is_cross_directory() and nb_dirs >= 2
            if has_internal or has_cross:
                result.append(group)
        return result


# ---------------------------------------------------------------------------
# Cleaner
# ---------------------------------------------------------------------------


class DuplicateCleaner:
    """Plan and execute deletion of duplicates, preserving one file per group."""

    def __init__(
        self,
        strategy: str = "first",
        dry_run: bool = True,
        cross_only: bool = False,
        verbose: bool = False,
    ) -> None:
        if strategy not in KEEP_STRATEGIES:
            raise ValueError(f"Invalid strategy: {strategy!r}. Choose from {KEEP_STRATEGIES}.")
        self.strategy = strategy
        self.dry_run = dry_run
        self.cross_only = cross_only
        self.verbose = verbose

    def plan(
        self,
        groups: list[DuplicateGroup],
        directories: list[Path],
    ) -> list[tuple[Path, Path]]:
        del directories  # kept for API compatibility
        plan: list[tuple[Path, Path]] = []
        for group in groups:
            if self.cross_only and not group.is_cross_directory():
                continue
            all_files = group.all_files
            keeper = pick_file_to_keep(all_files, self.strategy)
            for f in all_files:
                if f != keeper:
                    plan.append((f, keeper))
        return plan

    def execute(self, plan: list[tuple[Path, Path]]) -> tuple[list[Path], list[Path]]:
        deleted: list[Path] = []
        failed: list[Path] = []
        prefix = "[DRY-RUN] " if self.dry_run else ""

        for to_delete, keeper in plan:
            try:
                if not self.dry_run:
                    to_delete.unlink()
                if self.verbose:
                    print(f"  {prefix}Deleted: {to_delete}  (kept: {keeper.name})")
                deleted.append(to_delete)
            except PermissionError as exc:
                print(f"  [ERROR] Permission denied: {to_delete} - {exc}", file=sys.stderr)
                failed.append(to_delete)
            except FileNotFoundError:
                if self.verbose:
                    print(f"  [INFO] Already missing: {to_delete}")

        return deleted, failed


# ---------------------------------------------------------------------------
# Reporters
# ---------------------------------------------------------------------------


class DuplicateReporter:
    """Format and emit duplicate-scan results."""

    def __init__(self, output_path: Path | None = None, show_dates: bool = False) -> None:
        self.show_dates = show_dates
        self.output_path = output_path

    def report(self, groups: list[DuplicateGroup], directories: list[Path]) -> None:
        lines = self._build_lines(groups, directories)
        for line in lines:
            print(line)
        if self.output_path:
            self.output_path.write_text("\n".join(lines), encoding="utf-8")
            print(f"\n-> Report saved to: {self.output_path}")

    def _build_lines(self, groups: list[DuplicateGroup], directories: list[Path]) -> list[str]:
        lines: list[str] = []
        multi_dir = len(directories) >= 2

        if not groups:
            lines.append("No duplicate or shared files found.")
            return lines

        label = "Duplicate or shared files found:" if multi_dir else "Duplicate files found:"
        lines.append(label)

        for group in groups:
            lines.append(f"\nMD5 hash: {group.hash_}")
            for dir_key, paths in group.files_by_dir.items():
                dir_idx = int(dir_key.split("_")[1])
                lines.append(f"  [{directories[dir_idx]}]")
                for p in paths:
                    if self.show_dates:
                        date_str = datetime.datetime.fromtimestamp(creation_time(p)).strftime("%Y-%m-%d %H:%M:%S")
                        lines.append(f"    - {p}  (created {date_str})")
                    else:
                        lines.append(f"    - {p}")
            if multi_dir and group.is_cross_directory():
                lines.append("  -> File present in multiple directories")

        lines.append(f"\nTotal: {len(groups)} duplicate group(s) detected.")
        return lines

    @staticmethod
    def report_deletion(
        plan: list[tuple[Path, Path]],
        deleted: list[Path],
        failed: list[Path],
        dry_run: bool,
        freed_bytes: int,
    ) -> None:
        mode = "DRY-RUN - no changes written to disk" if dry_run else "Deletion complete"
        print(f"\n{'-' * 60}")
        print(f"  {mode}")
        print(f"  Targeted : {len(plan)}")
        print(f"  Deleted  : {len(deleted)}")
        if failed:
            print(f"  Failed   : {len(failed)}")
        print(f"  Space {'estimated ' if dry_run else ''}freed: {human_size(freed_bytes)}")
        print(f"{'-' * 60}")


class DeletionLogger:
    """Write a per-group deletion log showing kept/deleted/failed files."""

    def __init__(self, log_path: Path, dry_run: bool = False) -> None:
        self.log_path = log_path
        self.dry_run = dry_run

    def write(
        self,
        plan: list[tuple[Path, Path]],
        deleted: list[Path],
        failed: list[Path],
    ) -> None:
        deleted_set = set(deleted)
        failed_set = set(failed)
        prefix = "[DRY-RUN] " if self.dry_run else ""

        groups: dict[Path, list[Path]] = defaultdict(list)
        for to_delete, keeper in plan:
            groups[keeper].append(to_delete)

        with open(self.log_path, "w", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"# Deletion log - {prefix}{timestamp}\n\n")

            for keeper, targets in groups.items():
                f.write(f"Duplicates of: {keeper.name}\n")
                f.write(f"  [KEEP]   {keeper}\n")
                for target in targets:
                    if target in failed_set:
                        f.write(f"  [FAIL]   {target}\n")
                    elif target in deleted_set:
                        f.write(f"  [{prefix.strip() or 'DEL'}]    {target}\n")
                    else:
                        f.write(f"  [SKIP]   {target}\n")
                f.write("\n")

            f.write(f"Totals: targeted={len(plan)}, deleted={len(deleted)}, failed={len(failed)}\n")

        print(f"\n-> Deletion log saved to: {self.log_path}")
