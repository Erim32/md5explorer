# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Development install
pip install -e ".[dev]"

# Run all tests with coverage
pytest

# Lint
ruff check src tests

# Type check
mypy src

# Build distributable
python -m build

# Run CLI
md5explorer --help
python -m md5explorer --help
```

## Architecture

**md5explorer** is a CLI toolkit for file deduplication and management. Two top-level command groups:

- `md5explorer scan` — pure filesystem operations (no persistence)
- `md5explorer db` — SQLite-backed indexing for large file trees

### Module layout

```
src/md5explorer/
├── cli.py            # Entry point: builds argparse tree, dispatches to scan_cmds/db_cmds
├── core/             # Shared utilities: MD5 hashing, human_size(), progress bars, CleanupOutcome model
├── scan/             # Filesystem scanners (no DB): duplicates, compare, inventory, empty_dirs, diff_lists
├── db/               # SQLite layer: schema management (manager.py), indexing (index.py), comparison (compare.py)
└── commands/         # Argparse registration + handlers: scan_cmds.py, db_cmds.py
```

### Recurring pattern

Every feature follows **Scanner → Cleaner → Reporter**:

- **Scanner** walks directories, computes MD5s, returns structured results
- **Cleaner** plans and executes deletions; always supports `--dry-run` and `--yes` (skip confirmation)
- **Reporter** formats output to console or file

### Exit codes

| Code | Meaning                                            |
| ---- | -------------------------------------------------- |
| 0    | Success / nothing to do                            |
| 1    | Action available (duplicates or differences found) |
| 2    | Deletion ran with at least one failure             |

### Database schema

```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    absolute_path TEXT UNIQUE NOT NULL,
    md5 TEXT, size INTEGER,
    created_at TEXT, modified_at TEXT
);
CREATE INDEX idx_files_md5 ON files (md5);
```

`db index` uses `multiprocessing.Pool(cpu_count - 1)` by default; `--slow` forces single-threaded.

### Tests

`tests/conftest.py` provides fixtures (`sample_tree`, `empty_tree`, `two_directories`) backed by committed files under `tests/fixtures/sample_tree/`. Mutation tests get a writable copy via `tmp_path`.
