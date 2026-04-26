"""Tests for :mod:`md5explorer.core.hashing`."""

from __future__ import annotations

import hashlib
from pathlib import Path

from md5explorer.core.hashing import Hasher, creation_time, md5


def test_md5_returns_known_digest(tmp_path: Path) -> None:
    payload = b"md5explorer-test"
    f = tmp_path / "f.bin"
    f.write_bytes(payload)

    assert md5(f) == hashlib.md5(payload).hexdigest()


def test_md5_returns_none_for_missing_file(tmp_path: Path) -> None:
    assert md5(tmp_path / "does-not-exist") is None


def test_md5_identical_content_identical_digest(tmp_path: Path) -> None:
    (tmp_path / "a").write_bytes(b"same")
    (tmp_path / "b").write_bytes(b"same")
    assert md5(tmp_path / "a") == md5(tmp_path / "b")


def test_md5_different_content_different_digest(tmp_path: Path) -> None:
    (tmp_path / "a").write_bytes(b"alpha")
    (tmp_path / "b").write_bytes(b"beta")
    assert md5(tmp_path / "a") != md5(tmp_path / "b")


def test_creation_time_is_finite_for_existing_file(tmp_path: Path) -> None:
    f = tmp_path / "f"
    f.write_bytes(b"x")
    assert creation_time(f) != float("inf")


def test_creation_time_infinite_for_missing_file(tmp_path: Path) -> None:
    assert creation_time(tmp_path / "missing") == float("inf")


def test_legacy_hasher_namespace_delegates(tmp_path: Path) -> None:
    f = tmp_path / "f"
    f.write_bytes(b"legacy")
    assert Hasher.md5(f) == md5(f)
    assert Hasher.get_creation_time(f) == creation_time(f)
