"""Compare two inventory files (MD5 as primary key)."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ListEntry:
    """One parsed line of an inventory file."""

    md5: str
    filename: str
    raw_line: str
    line_number: int


@dataclass
class ListComparisonResult:
    """Buckets for two-way inventory comparison."""

    only_left: dict[str, ListEntry]
    only_right: dict[str, ListEntry]
    common: dict[str, tuple[ListEntry, ListEntry]]
    total_left: int
    total_right: int


class ListParser:
    """Parse an inventory file into ``{md5: ListEntry}``."""

    def __init__(self, separator: str = "_", skip_lines: int = 4) -> None:
        self.separator = separator
        self.skip_lines = skip_lines

    def parse(self, filepath: Path) -> dict[str, ListEntry]:
        entries: dict[str, ListEntry] = {}
        try:
            with open(filepath, encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            print(f"[ERROR] File not found: {filepath}", file=sys.stderr)
            sys.exit(1)

        for idx, line in enumerate(lines[self.skip_lines:], start=self.skip_lines + 1):
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.split(self.separator)
            if not parts:
                continue
            digest = parts[0]
            name = parts[1] if len(parts) > 1 else "Unknown"
            entries[digest] = ListEntry(
                md5=digest,
                filename=name,
                raw_line=stripped,
                line_number=idx,
            )

        return entries


class ListComparator:
    """Diff two parsed inventories by MD5 key."""

    @staticmethod
    def compare(
        left: dict[str, ListEntry],
        right: dict[str, ListEntry],
    ) -> ListComparisonResult:
        keys_l = set(left)
        keys_r = set(right)

        return ListComparisonResult(
            only_left={k: left[k] for k in keys_l - keys_r},
            only_right={k: right[k] for k in keys_r - keys_l},
            common={k: (left[k], right[k]) for k in keys_l & keys_r},
            total_left=len(left),
            total_right=len(right),
        )


class ListComparisonReporter:
    """Pretty-print a :class:`ListComparisonResult`."""

    def __init__(
        self,
        result: ListComparisonResult,
        name_left: str,
        name_right: str,
        output_path: Path | None = None,
    ) -> None:
        self.result = result
        self.name_left = name_left
        self.name_right = name_right
        self.output_path = output_path

    def display(self) -> None:
        r = self.result
        sep = "=" * 60
        lines: list[str] = [sep, "STATISTICS"]
        lines.append(f"  Entries in {self.name_left} : {r.total_left}")
        lines.append(f"  Entries in {self.name_right}: {r.total_right}")
        lines.append(f"  Common entries             : {len(r.common)}")
        lines.append(f"  Only in {self.name_left}   : {len(r.only_left)}")
        lines.append(f"  Only in {self.name_right}  : {len(r.only_right)}")
        lines.append(sep)

        lines += self._format_unique_section(
            f"FILES PRESENT ONLY IN '{self.name_left}'",
            r.only_left,
            "[L]",
        )
        lines += self._format_unique_section(
            f"FILES PRESENT ONLY IN '{self.name_right}'",
            r.only_right,
            "[R]",
        )

        if r.common:
            sample = sorted(r.common)[:5]
            lines.append(f"\nSAMPLE OF COMMON FILES ({len(sample)} of {len(r.common)}):")
            lines.append("-" * 60)
            for digest in sample:
                e_l, e_r = r.common[digest]
                lines.append(f"  MD5 : {digest}")
                lines.append(f"  Name: {e_l.filename}")
                lines.append(f"  In {self.name_left}  (line {e_l.line_number})")
                lines.append(f"  In {self.name_right} (line {e_r.line_number})")
                lines.append("")

        for line in lines:
            print(line)

        if self.output_path:
            self.output_path.write_text("\n".join(lines), encoding="utf-8")
            print(f"\n-> Report saved to: {self.output_path}")

    @staticmethod
    def _format_unique_section(
        title: str,
        entries: dict[str, ListEntry],
        icon: str,
    ) -> list[str]:
        lines: list[str] = []
        if entries:
            lines.append(f"\n{icon} {title} ({len(entries)}):")
            lines.append("-" * 60)
            for digest in sorted(entries):
                e = entries[digest]
                lines.append(f"  MD5 : {digest}")
                lines.append(f"  Name: {e.filename}")
                lines.append(f"  Line {e.line_number}: {e.raw_line}")
                lines.append("")
        else:
            lines.append(f"\n{icon} No unique files.")
        return lines
