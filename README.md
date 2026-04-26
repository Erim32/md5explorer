<div align="center">
    <img src="docs/logo.png" alt="Logo" width="80" height="80">
</div>

# Md5explorer

A command-line file management toolkit: duplicate detection, directory
comparison, MD5 inventories, empty-directory cleanup, and a SQLite index
for large collections.

## Installation

```bash
pip install md5explorer
```

Or, from a local checkout:

```bash
pip install -e .
```

## Quickstart

```bash
# Detect duplicates (read-only)
md5explorer scan duplicates ./photos

# Simulate deletion, keeping the newest file of each group
md5explorer scan duplicates ./photos --delete --dry-run --keep newest

# Compare two directories
md5explorer scan compare ./dir1 ./dir2

# Generate an MD5 inventory
md5explorer scan inventory ./photos -o inventory.txt

# Index a large tree into SQLite (multiprocess)
md5explorer db index ./photos

# Compare a new folder against the index
md5explorer db compare ./incoming --delete --dry-run
```

Run `md5explorer --help`, `md5explorer scan --help`, or `md5explorer db --help` for
the full option list.

## Commands

| Group | Subcommand   | Purpose                                              |
| ----- | ------------ | ---------------------------------------------------- |
| scan  | `duplicates` | Detect and optionally delete duplicate files         |
| scan  | `compare`    | Compare two directories file by file                 |
| scan  | `inventory`  | Write an MD5/name/date/path inventory to a text file |
| scan  | `diff-lists` | Diff two inventory files by MD5                      |
| scan  | `empty-dirs` | Detect and optionally delete empty directories       |
| db    | `index`      | Index a directory into the SQLite database           |
| db    | `list`       | List entries from the database                       |
| db    | `check`      | Check if a file is present in the database           |
| db    | `compare`    | Compare a directory against the indexed catalog      |

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src
mypy src
```

## License

MIT - see [LICENSE](LICENSE).
