"""Side-by-side directory comparison by relative path + MD5."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from md5explorer.core.hashing import md5

DEFAULT_IGNORED: frozenset[str] = frozenset({".git", "__pycache__"})


@dataclass
class ComparisonResult:
    """Buckets a comparison produces: identical / different / only-left / only-right."""

    identical: list[str] = field(default_factory=list)
    different: list[str] = field(default_factory=list)
    only_left: list[str] = field(default_factory=list)
    only_right: list[str] = field(default_factory=list)
    diff_hashes: dict[str, tuple[str, str]] = field(default_factory=dict)
    total_left: int = 0
    total_right: int = 0

    @property
    def are_identical(self) -> bool:
        return not self.different and not self.only_left and not self.only_right


class DirectoryScanner:
    """Index a directory as ``{relative_path: absolute_path}``."""

    def __init__(self, root: Path, ignored: set[str] | frozenset[str] | None = None) -> None:
        self.root = root
        self.ignored = ignored if ignored is not None else DEFAULT_IGNORED

    def scan(self) -> dict[str, Path]:
        files: dict[str, Path] = {}
        for dirpath, _, filenames in os.walk(self.root):
            if any(name in dirpath for name in self.ignored):
                continue
            for name in filenames:
                abs_path = Path(dirpath) / name
                rel_path = str(abs_path.relative_to(self.root))
                files[rel_path] = abs_path
        return files


class DirectoryComparator:
    """Compare two directories file by file using MD5."""

    def __init__(
        self,
        dir1: Path,
        dir2: Path,
        ignored: set[str] | frozenset[str] | None = None,
    ) -> None:
        self.dir1 = dir1
        self.dir2 = dir2
        self._scanner1 = DirectoryScanner(dir1, ignored)
        self._scanner2 = DirectoryScanner(dir2, ignored)

    def compare(self) -> ComparisonResult:
        files1 = self._scanner1.scan()
        files2 = self._scanner2.scan()
        all_keys = set(files1) | set(files2)

        result = ComparisonResult(total_left=len(files1), total_right=len(files2))

        for rel_path in sorted(all_keys):
            path1 = files1.get(rel_path)
            path2 = files2.get(rel_path)

            if path1 and path2:
                hash1 = md5(path1)
                hash2 = md5(path2)
                if hash1 == hash2:
                    result.identical.append(rel_path)
                else:
                    result.different.append(rel_path)
                    if hash1 and hash2:
                        result.diff_hashes[rel_path] = (hash1, hash2)
            elif path1:
                result.only_left.append(rel_path)
            else:
                result.only_right.append(rel_path)

        return result


class ComparisonReporter:
    """Render a :class:`ComparisonResult` to the console and optionally to disk."""

    def __init__(
        self,
        result: ComparisonResult,
        dir1: Path,
        dir2: Path,
        output_path: Path | None = None,
    ) -> None:
        self.result = result
        self.dir1 = dir1
        self.dir2 = dir2
        self.output_path = output_path

    def _format_section(self, title: str, files: list[str], icon: str) -> list[str]:
        if not files:
            return []
        lines = [f"\n{title} ({len(files)}):"]
        for f in files:
            lines.append(f"  {icon} {f}")
        return lines

    def _format_differents(self) -> list[str]:
        files = self.result.different
        if not files:
            return []
        lines = [f"\n!  Files with differing content ({len(files)}):"]
        for f in files:
            lines.append(f"  X {f}")
            hashes = self.result.diff_hashes.get(f)
            if hashes:
                lines.append(f"    left MD5 : {hashes[0]}")
                lines.append(f"    right MD5: {hashes[1]}")
        return lines

    def display(self) -> None:
        r = self.result
        sep = "=" * 60
        lines: list[str] = [sep]

        if r.are_identical:
            lines.append("OK  DIRECTORIES ARE IDENTICAL")
            lines.append(f"    {len(r.identical)} identical file(s)")
        else:
            lines.append("KO  DIRECTORIES DIFFER")
        lines.append(sep)

        lines += self._format_section(f"Files only in '{self.dir1}'", r.only_left, "->")
        lines += self._format_section(f"Files only in '{self.dir2}'", r.only_right, "->")
        lines += self._format_differents()
        lines += self._format_section("Identical files", r.identical, "=")

        lines.append(f"\n{sep}")
        lines.append(f"Total left  : {r.total_left} file(s)")
        lines.append(f"Total right : {r.total_right} file(s)")
        lines.append(
            f"Summary: {len(r.identical)} identical, {len(r.different)} different, "
            f"{len(r.only_left)} only-left, {len(r.only_right)} only-right."
        )
        lines.append(sep)

        for line in lines:
            print(line)

        if self.output_path:
            self.output_path.write_text("\n".join(lines), encoding="utf-8")
            print(f"\n-> Report saved to: {self.output_path}")
