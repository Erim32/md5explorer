"""Cross-cutting dataclasses shared by multiple subsystems."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CleanupOutcome:
    """Generic result of a batch deletion operation."""

    deleted: list[Path] = field(default_factory=list)
    failed: list[Path] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return len(self.deleted)

    @property
    def failure_count(self) -> int:
        return len(self.failed)
