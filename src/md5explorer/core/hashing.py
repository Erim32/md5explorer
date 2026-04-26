"""MD5 hashing and filesystem timestamp helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path

CHUNK_SIZE = 8192


def md5(filepath: Path) -> str | None:
    """Return the MD5 hex digest of a file, or ``None`` if it is unreadable."""
    h = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
                h.update(chunk)
        return h.hexdigest()
    except (PermissionError, FileNotFoundError, OSError):
        return None


def creation_time(filepath: Path) -> float:
    """Return the file's creation timestamp.

    Falls back to the modification time on platforms without ``st_birthtime``
    (notably Linux).
    """
    try:
        stat = filepath.stat()
    except OSError:
        return float("inf")
    return getattr(stat, "st_birthtime", stat.st_mtime)


class Hasher:
    """Legacy namespace kept for backward compatibility with callers that use
    ``Hasher.md5`` / ``Hasher.get_creation_time``.

    New code should import :func:`md5` and :func:`creation_time` directly.
    """

    CHUNK_SIZE = CHUNK_SIZE

    @staticmethod
    def md5(filepath: Path) -> str | None:
        return md5(filepath)

    @staticmethod
    def get_creation_time(filepath: Path) -> float:
        return creation_time(filepath)
