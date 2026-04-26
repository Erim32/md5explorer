"""Filesystem-level operations: duplicates, directory diffing, inventory."""

from md5explorer.scan.compare import ComparisonResult, DirectoryComparator, DirectoryScanner
from md5explorer.scan.diff_lists import (
    ListComparator,
    ListComparisonReporter,
    ListComparisonResult,
    ListEntry,
    ListParser,
)
from md5explorer.scan.duplicates import (
    KEEP_STRATEGIES,
    DeletionLogger,
    DuplicateCleaner,
    DuplicateGroup,
    DuplicateReporter,
    DuplicateScanner,
    pick_file_to_keep,
)
from md5explorer.scan.empty_dirs import EmptyDirCleaner, EmptyDirReporter, EmptyDirResult, EmptyDirScanner
from md5explorer.scan.inventory import FileInfo, InventoryReporter, InventoryScanner

__all__ = [
    "KEEP_STRATEGIES",
    "ComparisonResult",
    "DeletionLogger",
    "DirectoryComparator",
    "DirectoryScanner",
    "DuplicateCleaner",
    "DuplicateGroup",
    "DuplicateReporter",
    "DuplicateScanner",
    "EmptyDirCleaner",
    "EmptyDirReporter",
    "EmptyDirResult",
    "EmptyDirScanner",
    "FileInfo",
    "InventoryReporter",
    "InventoryScanner",
    "ListComparator",
    "ListComparisonReporter",
    "ListComparisonResult",
    "ListEntry",
    "ListParser",
    "pick_file_to_keep",
]
