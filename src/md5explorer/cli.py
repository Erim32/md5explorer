"""Top-level command-line entry point.

Builds the root argparse parser, wires the ``scan`` and ``db`` command groups,
and dispatches to the matching handler module.
"""

from __future__ import annotations

import argparse
import sys

from md5explorer import __version__
from md5explorer.commands import db_cmds, scan_cmds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="md5explorer",
        description="File management CLI: duplicates, inventory, SQLite indexing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    scan_cmds.register(subparsers)
    db_cmds.register(subparsers)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        if not getattr(args, "subcommand", None):
            parser.parse_args(["scan", "--help"])
            return 0
        return scan_cmds.run(args)

    if args.command == "db":
        if not getattr(args, "subcommand", None):
            parser.parse_args(["db", "--help"])
            return 0
        return db_cmds.run(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
