"""Formatting helpers, interactive prompts, and the optional tqdm fallback."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import TypeVar

try:
    from tqdm import tqdm as _tqdm
except ImportError:  # pragma: no cover - tqdm is a declared dependency
    _tqdm = None


T = TypeVar("T")


def progress(
    iterable: Iterable[T],
    *,
    desc: str | None = None,
    total: int | None = None,
) -> Iterator[T] | Iterable[T]:
    """Wrap an iterable with a tqdm progress bar when available.

    Falls back to the raw iterable (plus an optional leading message) when
    tqdm is not installed.
    """
    if _tqdm is not None:
        wrapped: Iterator[T] = _tqdm(iterable, desc=desc, total=total)
        return wrapped
    if desc:
        print(f"  {desc}...")
    return iterable


def human_size(nb_bytes: float) -> str:
    """Convert a byte count to a human-readable string (B, KB, MB, ...)."""
    size = float(nb_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def _confirm(prompt: str) -> bool:
    answer = input(prompt).strip().lower()
    return answer in ("y", "yes", "o", "oui")


def confirm_duplicate_deletion(count: int, strategy: str) -> bool:
    print(f"\n!  {count} file(s) will be permanently deleted.")
    print(f"   Keep strategy: '{strategy}'")
    print("   This action cannot be undone.")
    return _confirm("\n   Confirm? [y/n]: ")


def confirm_empty_dir_deletion(count: int) -> bool:
    print(f"\n!  {count} directory(ies) will be permanently deleted.")
    print("   This action cannot be undone.")
    return _confirm("\n   Confirm? [y/n]: ")


def confirm_db_deletion(count: int) -> bool:
    print(f"\n!  {count} file(s) will be permanently deleted.")
    print("   (files already present in the SQLite index)")
    print("   This action cannot be undone.")
    return _confirm("\n   Confirm? [y/n]: ")


def ensure_directory(path: Path, label: str = "directory") -> bool:
    """Print an error and return False if ``path`` is not an existing directory."""
    if not path.is_dir():
        import sys

        print(f"[ERROR] {label} not found: {path}", file=sys.stderr)
        return False
    return True
