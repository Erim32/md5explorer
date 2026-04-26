"""``md5explorer scan ...`` subcommands: argparse wiring + handlers."""

from __future__ import annotations

import argparse
import datetime
from pathlib import Path

from md5explorer.core.utils import confirm_duplicate_deletion, confirm_empty_dir_deletion, ensure_directory
from md5explorer.scan.compare import ComparisonReporter, DirectoryComparator
from md5explorer.scan.diff_lists import ListComparator, ListComparisonReporter, ListParser
from md5explorer.scan.duplicates import (
    KEEP_STRATEGIES,
    DeletionLogger,
    DuplicateCleaner,
    DuplicateReporter,
    DuplicateScanner,
)
from md5explorer.scan.empty_dirs import EmptyDirCleaner, EmptyDirReporter, EmptyDirScanner
from md5explorer.scan.inventory import InventoryReporter, InventoryScanner

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Attach ``scan`` and its subcommands to the top-level parser."""
    scan_parser = subparsers.add_parser("scan", help="Filesystem-level scan operations.")
    scan_sub = scan_parser.add_subparsers(dest="subcommand", metavar="<subcommand>")

    _add_duplicates_parser(scan_sub)
    _add_compare_parser(scan_sub)
    _add_inventory_parser(scan_sub)
    _add_diff_lists_parser(scan_sub)
    _add_empty_dirs_parser(scan_sub)


def _add_duplicates_parser(scan_sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    dup_parser = scan_sub.add_parser(
        "duplicates",
        help="Detect (and optionally delete) duplicate files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Keep strategies (--keep):
  first    -> keep the first file encountered during the scan  [default]
  newest   -> keep the most recently modified file
  oldest   -> keep the oldest file
  smallest -> keep the smallest file
  largest  -> keep the largest file

Examples:
  %(prog)s ./photos --delete --dry-run
  %(prog)s ./photos --delete --keep newest --yes
  %(prog)s ./dir1 ./dir2 --delete --cross-only --keep oldest
  %(prog)s ./photos --delete --yes --delete-log deletion.txt
        """,
    )
    dup_parser.add_argument("directories", nargs="+", metavar="DIR", help="Directories to scan.")
    dup_parser.add_argument("-o", "--output", metavar="FILE", help="Report file path.")
    dup_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output.")
    dup_parser.add_argument(
        "--dates",
        action="store_true",
        help="Include each file's creation date in the report.",
    )

    delete_group = dup_parser.add_argument_group("deletion")
    delete_group.add_argument("--delete", action="store_true", help="Enable duplicate deletion.")
    delete_group.add_argument("--dry-run", action="store_true", help="Simulate deletion (requires --delete).")
    delete_group.add_argument(
        "--keep",
        choices=KEEP_STRATEGIES,
        default="first",
        metavar="STRATEGY",
        help=f"Which file to keep. Values: {', '.join(KEEP_STRATEGIES)}. Default: first.",
    )
    delete_group.add_argument(
        "--cross-only",
        action="store_true",
        help="Only delete duplicates that span multiple source directories.",
    )
    delete_group.add_argument("-y", "--yes", action="store_true", help="Skip the interactive prompt.")
    delete_group.add_argument(
        "--delete-log",
        metavar="FILE",
        help="Write a detailed per-group deletion log (kept/deleted/failed).",
    )


def _add_compare_parser(scan_sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    cmp_parser = scan_sub.add_parser(
        "compare",
        help="Compare two directories file by file (name + MD5).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ./dir1 ./dir2
  %(prog)s ./dir1 ./dir2 --ignore .git __pycache__ node_modules
  %(prog)s ./dir1 ./dir2 -o report.txt
        """,
    )
    cmp_parser.add_argument("dir1", metavar="DIR1", help="First directory.")
    cmp_parser.add_argument("dir2", metavar="DIR2", help="Second directory.")
    cmp_parser.add_argument("-o", "--output", metavar="FILE", help="Report file path.")
    cmp_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output.")
    cmp_parser.add_argument(
        "--ignore",
        nargs="+",
        metavar="NAME",
        default=[".git", "__pycache__"],
        help="Directory names to skip (default: .git __pycache__).",
    )


def _add_inventory_parser(scan_sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    inv_parser = scan_sub.add_parser(
        "inventory",
        help="Build an inventory (MD5, name, date, path) for every file in a tree.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Output format (one line per file):
  MD5<sep>NAME<sep>MODIFIED_AT<sep>PATH

Examples:
  %(prog)s ./photos
  %(prog)s ./photos -o inventory.txt
  %(prog)s ./photos -o inv.txt -s "|"
        """,
    )
    inv_parser.add_argument("directory", metavar="DIR", help="Directory to inventory.")
    inv_parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Output file (default: file_list_<timestamp>.txt).",
    )
    inv_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output.")
    inv_parser.add_argument(
        "-s",
        "--separator",
        default="_",
        metavar="SEP",
        help="Field separator (default: '_').",
    )


def _add_diff_lists_parser(scan_sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    dl_parser = scan_sub.add_parser(
        "diff-lists",
        help="Compare two inventory files using the MD5 extracted from each line.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Each inventory line has the form:
  MD5<sep>NAME<sep>...

The MD5 (the first field) is used as the join key.

Examples:
  %(prog)s inventory_v1.txt inventory_v2.txt
  %(prog)s list1.txt list2.txt -s "|" -i 2
  %(prog)s list1.txt list2.txt -o diff_report.txt
        """,
    )
    dl_parser.add_argument("file1", metavar="FILE1", help="First inventory file.")
    dl_parser.add_argument("file2", metavar="FILE2", help="Second inventory file.")
    dl_parser.add_argument("-o", "--output", metavar="FILE", help="Report file path.")
    dl_parser.add_argument(
        "-s",
        "--separator",
        default="_",
        metavar="SEP",
        help="Field separator in inventory lines (default: '_').",
    )
    dl_parser.add_argument(
        "-i",
        "--skip-lines",
        type=int,
        default=4,
        metavar="N",
        help="Number of header lines to skip (default: 4).",
    )


def _add_empty_dirs_parser(scan_sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    ed_parser = scan_sub.add_parser(
        "empty-dirs",
        help="Detect (and optionally delete) empty directories recursively.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
The scan proceeds leaves-first: a directory that only contains empty
subdirectories is itself considered empty and is targeted.

Examples:
  %(prog)s ./photos
  %(prog)s ./photos --delete --dry-run
  %(prog)s ./photos --delete --yes
  %(prog)s ./photos --delete -o report.txt
        """,
    )
    ed_parser.add_argument("directory", metavar="DIR", help="Root directory to scan.")
    ed_parser.add_argument("-o", "--output", metavar="FILE", help="Report file path.")
    ed_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output.")

    ed_delete_group = ed_parser.add_argument_group("deletion")
    ed_delete_group.add_argument("--delete", action="store_true", help="Enable empty-directory deletion.")
    ed_delete_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate deletion (requires --delete).",
    )
    ed_delete_group.add_argument("-y", "--yes", action="store_true", help="Skip the interactive prompt.")


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


HANDLERS_BY_SUBCOMMAND = {
    "duplicates": "cmd_duplicates",
    "compare": "cmd_compare",
    "inventory": "cmd_inventory",
    "diff-lists": "cmd_diff_lists",
    "empty-dirs": "cmd_empty_dirs",
}


def run(args: argparse.Namespace) -> int:
    """Dispatch a parsed ``scan ...`` invocation to the matching handler."""
    handler_name = HANDLERS_BY_SUBCOMMAND.get(args.subcommand or "")
    if handler_name is None:
        return -1
    exit_code: int = globals()[handler_name](args)
    return exit_code


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def cmd_duplicates(args: argparse.Namespace) -> int:
    directories = [Path(d) for d in args.directories]
    output_path = Path(args.output) if getattr(args, "output", None) else None
    delete_log_path = Path(args.delete_log) if getattr(args, "delete_log", None) else None

    print(f"Scanning {len(directories)} director(y|ies):")
    for d in directories:
        print(f"  - {d}")
    print()

    scanner = DuplicateScanner(verbose=args.verbose)
    groups = scanner.scan(directories)

    reporter = DuplicateReporter(output_path=output_path, show_dates=getattr(args, "dates", False))
    reporter.report(groups, directories)

    if not groups:
        return 0

    if not getattr(args, "delete", False):
        print("\n(Use --delete to remove the detected duplicates.)")
        return 1

    dry_run: bool = getattr(args, "dry_run", False)
    cleaner = DuplicateCleaner(
        strategy=args.keep,
        dry_run=dry_run,
        cross_only=getattr(args, "cross_only", False),
        verbose=args.verbose,
    )

    deletion_plan = cleaner.plan(groups, directories)

    if not deletion_plan:
        print("\nNothing to delete under the current options.")
        return 0

    space_to_free = sum(f.stat().st_size for f, _ in deletion_plan if f.exists())

    if (
        not dry_run
        and not getattr(args, "yes", False)
        and not confirm_duplicate_deletion(len(deletion_plan), args.keep)
    ):
        print("Cancelled.")
        return 0

    print(f"\n{'Simulating' if dry_run else 'Deleting'}...")
    deleted, failed = cleaner.execute(deletion_plan)

    DuplicateReporter.report_deletion(
        plan=deletion_plan,
        deleted=deleted,
        failed=failed,
        dry_run=dry_run,
        freed_bytes=space_to_free,
    )

    if delete_log_path:
        logger = DeletionLogger(delete_log_path, dry_run=dry_run)
        logger.write(deletion_plan, deleted, failed)

    return 0 if not failed else 2


def cmd_compare(args: argparse.Namespace) -> int:
    dir1 = Path(args.dir1)
    dir2 = Path(args.dir2)
    output_path = Path(args.output) if getattr(args, "output", None) else None
    ignored = set(args.ignore)

    for d in (dir1, dir2):
        if not ensure_directory(d):
            return 1

    print("Comparing:")
    print(f"  left : {dir1}")
    print(f"  right: {dir2}")
    if ignored:
        print(f"  ignored: {', '.join(sorted(ignored))}")
    print()

    comparator = DirectoryComparator(dir1, dir2, ignored)
    result = comparator.compare()

    reporter = ComparisonReporter(result, dir1, dir2, output_path=output_path)
    reporter.display()

    return 0 if result.are_identical else 1


def cmd_inventory(args: argparse.Namespace) -> int:
    root = Path(args.directory)
    if not ensure_directory(root):
        return 1

    separator = args.separator
    if args.output:
        dest = Path(args.output)
    else:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = Path(f"file_list_{ts}.txt")

    print(f"Inventory of: {root.resolve()}")
    print(f"  separator: '{separator}'")
    print(f"  output   : {dest}")
    print()

    scanner = InventoryScanner(verbose=args.verbose)
    files = scanner.scan(root)

    InventoryReporter.save(files, dest, root, separator)
    return 0


def cmd_diff_lists(args: argparse.Namespace) -> int:
    file1 = Path(args.file1)
    file2 = Path(args.file2)
    output_path = Path(args.output) if getattr(args, "output", None) else None

    print("Comparing inventory files:")
    print(f"  file 1          : {file1}")
    print(f"  file 2          : {file2}")
    print(f"  separator       : '{args.separator}'")
    print(f"  header lines    : {args.skip_lines}")
    print()

    parser = ListParser(separator=args.separator, skip_lines=args.skip_lines)
    left = parser.parse(file1)
    right = parser.parse(file2)

    result = ListComparator.compare(left, right)

    reporter = ListComparisonReporter(result, file1.name, file2.name, output_path=output_path)
    reporter.display()

    return 0 if not result.only_left and not result.only_right else 1


def cmd_empty_dirs(args: argparse.Namespace) -> int:
    root = Path(args.directory)
    output_path = Path(args.output) if getattr(args, "output", None) else None
    dry_run: bool = getattr(args, "dry_run", False)

    if not ensure_directory(root):
        return 1

    print(f"Scanning for empty directories in: {root.resolve()}")
    print()

    scanner = EmptyDirScanner(verbose=args.verbose)
    found = scanner.scan(root)

    reporter = EmptyDirReporter(output_path=output_path)
    reporter.report_scan(found, root)

    if not found:
        return 0

    if not getattr(args, "delete", False):
        print("\n(Use --delete to remove the detected empty directories.)")
        return 1

    if not dry_run and not getattr(args, "yes", False) and not confirm_empty_dir_deletion(len(found)):
        print("Cancelled.")
        return 0

    print(f"\n{'Simulating' if dry_run else 'Deleting'}...")
    cleaner = EmptyDirCleaner(dry_run=dry_run, verbose=args.verbose)
    deleted, failed = cleaner.execute(found)

    EmptyDirReporter.report_deletion(
        found=found,
        deleted=deleted,
        failed=failed,
        dry_run=dry_run,
    )

    return 0 if not failed else 2


__all__ = ["register", "run"]
