"""``md5explorer db ...`` subcommands: argparse wiring + handlers."""

from __future__ import annotations

import argparse
from pathlib import Path

from md5explorer.core.hashing import md5
from md5explorer.core.utils import confirm_db_deletion, ensure_directory, human_size
from md5explorer.db.compare import DbComparator, DbCompareCleaner, DbCompareReporter
from md5explorer.db.index import DbIndexScanner
from md5explorer.db.manager import DEFAULT_DB_NAME, DatabaseManager

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Attach ``db`` and its subcommands to the top-level parser."""
    db_parser = subparsers.add_parser("db", help="Operations on the SQLite file index.")
    db_sub = db_parser.add_subparsers(dest="subcommand", metavar="<subcommand>")

    _add_index_parser(db_sub)
    _add_list_parser(db_sub)
    _add_check_parser(db_sub)
    _add_compare_parser(db_sub)


def _db_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--db",
        metavar="FILE",
        default=DEFAULT_DB_NAME,
        help=f"SQLite database path (default: {DEFAULT_DB_NAME}).",
    )


def _add_index_parser(db_sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    idx_parser = db_sub.add_parser(
        "index",
        help="Index the files of a directory into the SQLite database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ./photos
  %(prog)s ./photos --slow
  %(prog)s ./photos --exclude .git node_modules
  %(prog)s ./photos --reset
  %(prog)s ./photos --db my_index.sqlite
        """,
    )
    idx_parser.add_argument("directory", metavar="DIR", help="Directory to index.")
    idx_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output.")
    idx_parser.add_argument(
        "--slow",
        action="store_true",
        help="Use single-threaded mode (slower, lower memory use).",
    )
    idx_parser.add_argument(
        "--exclude",
        nargs="*",
        metavar="NAME",
        default=[],
        help="Directory names or paths to exclude from the scan.",
    )
    idx_parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate the database from scratch.",
    )
    _db_option(idx_parser)


def _add_list_parser(db_sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    lst_parser = db_sub.add_parser("list", help="List entries from the SQLite database.")
    _db_option(lst_parser)
    lst_parser.add_argument(
        "--limit",
        type=int,
        default=0,
        metavar="N",
        help="Maximum number of entries to print (0 = all).",
    )


def _add_check_parser(db_sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    chk_parser = db_sub.add_parser(
        "check",
        help="Check whether a file exists in the database (by path or MD5).",
    )
    chk_parser.add_argument("file", metavar="FILE", help="File to check.")
    _db_option(chk_parser)


def _add_compare_parser(db_sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    cmp_parser = db_sub.add_parser(
        "compare",
        help="Compare a directory against the existing SQLite index.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Compare files in a directory against those already recorded in the index
by MD5. Read-only by default (no deletion).

Examples:
  %(prog)s ./new_directory
  %(prog)s ./new_directory --export duplicates.txt
  %(prog)s ./new_directory --delete --dry-run
  %(prog)s ./new_directory --delete --yes
        """,
    )
    cmp_parser.add_argument("directory", metavar="DIR", help="Directory to compare against the index.")
    cmp_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output.")
    _db_option(cmp_parser)
    cmp_parser.add_argument(
        "--export",
        metavar="FILE",
        help="Export detailed results to a text file.",
    )

    delete_group = cmp_parser.add_argument_group("deletion")
    delete_group.add_argument(
        "--delete",
        action="store_true",
        help="Delete files from the directory that already exist in the index.",
    )
    delete_group.add_argument("--dry-run", action="store_true", help="Simulate deletion (requires --delete).")
    delete_group.add_argument("-y", "--yes", action="store_true", help="Skip the interactive prompt.")


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


HANDLERS_BY_SUBCOMMAND = {
    "index": "cmd_index",
    "list": "cmd_list",
    "check": "cmd_check",
    "compare": "cmd_compare",
}


def run(args: argparse.Namespace) -> int:
    """Dispatch a parsed ``db ...`` invocation to the matching handler."""
    handler_name = HANDLERS_BY_SUBCOMMAND.get(args.subcommand or "")
    if handler_name is None:
        return -1
    exit_code: int = globals()[handler_name](args)
    return exit_code


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def cmd_index(args: argparse.Namespace) -> int:
    root = Path(args.directory)
    if not ensure_directory(root):
        return 1

    db_path = Path(args.db)
    exclusions = [Path(e) for e in args.exclude]

    print(f"Indexing: {root.resolve()}")
    print(f"  Database : {db_path}")
    if exclusions:
        print(f"  Excluded : {', '.join(str(e) for e in exclusions)}")
    print(f"  Mode     : {'single-thread' if args.slow else 'multi-process'}")
    if args.reset:
        print("  Reset    : yes (database recreated)")
    print()

    db = DatabaseManager(db_path)
    conn = db.init(reset=args.reset)

    try:
        scanner = DbIndexScanner(verbose=args.verbose)
        files = scanner.collect_files(root, exclusions)
        print(f"  {len(files)} file(s) found")
        print()

        count = scanner.insert_sequential(conn, files) if args.slow else scanner.insert_parallel(conn, files)

        print(f"\nIndexing complete: {count} file(s) recorded in {db_path}")
    finally:
        conn.close()

    return 0


def cmd_list(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    db = DatabaseManager(db_path)
    conn = db.connect()

    try:
        query = "SELECT id, absolute_path, md5, size, created_at, modified_at FROM files"
        if args.limit > 0:
            query += f" LIMIT {args.limit}"

        cur = conn.execute(query)
        rows = cur.fetchall()

        if not rows:
            print("Database is empty.")
            return 0

        total = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]

        print(f"Database contents: {db_path}")
        print(f"  Entries shown: {len(rows)}" + (f" / {total}" if args.limit > 0 else ""))
        print("-" * 80)

        for row in rows:
            id_, path, digest, size, _created, _modified = row
            print(f"  [{id_:>6}] {digest or '-':32}  {human_size(size or 0):>10}  {path}")

        print("-" * 80)
        print(f"Total: {total} entry(ies) in database.")
    finally:
        conn.close()

    return 0


def cmd_check(args: argparse.Namespace) -> int:
    db_path = Path(args.db)
    filepath = Path(args.file)
    db = DatabaseManager(db_path)
    conn = db.connect()

    try:
        absolute_path = str(filepath.resolve())
        cur = conn.execute(
            "SELECT id, absolute_path, md5, size, created_at FROM files WHERE absolute_path = ?",
            (absolute_path,),
        )
        row = cur.fetchone()

        if row:
            id_, path, digest, size, created = row
            print("OK  File found in database:")
            print(f"  ID      : {id_}")
            print(f"  Path    : {path}")
            print(f"  MD5     : {digest or '-'}")
            print(f"  Size    : {human_size(size or 0)}")
            print(f"  Created : {created or '-'}")
            return 0

        if filepath.exists():
            digest = md5(filepath)
            if digest:
                cur = conn.execute(
                    "SELECT id, absolute_path, md5, size FROM files WHERE md5 = ?",
                    (digest,),
                )
                rows = cur.fetchall()
                if rows:
                    print(f"!  File not found by path, but an identical MD5 exists ({digest}):")
                    for r in rows:
                        print(f"  [{r[0]}] {r[1]}  ({human_size(r[3] or 0)})")
                    return 0

        print(f"KO  File not found in database: {absolute_path}")
        return 1
    finally:
        conn.close()


def cmd_compare(args: argparse.Namespace) -> int:
    root = Path(args.directory)
    if not ensure_directory(root):
        return 1

    db_path = Path(args.db)
    export_path = Path(args.export) if getattr(args, "export", None) else None
    dry_run: bool = getattr(args, "dry_run", False)

    db = DatabaseManager(db_path)
    conn = db.connect()

    try:
        print(f"Comparing: {root.resolve()}")
        print(f"  Database: {db_path}")
        print()

        scanner = DbIndexScanner(verbose=args.verbose)
        files = scanner.collect_files(root)
        print(f"  {len(files)} file(s) to compare")
        print()

        comparator = DbComparator(conn, verbose=args.verbose)
        matches = comparator.compare(files)

        DbCompareReporter.report_matches(matches, export_path=export_path)

        if not matches:
            return 0

        if not getattr(args, "delete", False):
            print("\n(Use --delete to remove files already present in the database.)")
            return 1

        if not dry_run and not getattr(args, "yes", False) and not confirm_db_deletion(len(matches)):
            print("Cancelled.")
            return 0

        print(f"\n{'Simulating' if dry_run else 'Deleting'}...")
        cleaner = DbCompareCleaner(dry_run=dry_run, verbose=args.verbose)
        deleted, failed = cleaner.execute(matches)

        DbCompareReporter.report_deletion(
            matches=matches,
            deleted=deleted,
            failed=failed,
            dry_run=dry_run,
        )

        return 0 if not failed else 2
    finally:
        conn.close()


__all__ = ["register", "run"]

__all__ = ["register", "run"]
