# md5explorer

Command-line toolkit for file management: duplicate detection, directory
comparison, MD5 inventory, empty-directory cleanup, and a SQLite-backed
catalog for large collections.

## Package layout

```
src/md5explorer/
├── cli.py                 # Root argparse parser + dispatcher
├── __main__.py            # ``python -m md5explorer``
├── core/                  # Shared primitives
│   ├── hashing.py         # MD5 and filesystem timestamps
│   ├── models.py          # Cross-cutting dataclasses
│   └── utils.py           # Formatting, prompts, progress bar
├── scan/                  # Filesystem-level operations
│   ├── duplicates.py
│   ├── compare.py
│   ├── inventory.py
│   ├── diff_lists.py
│   └── empty_dirs.py
├── db/                    # SQLite-backed catalog
│   ├── manager.py         # Schema and connection lifecycle
│   ├── index.py           # Indexing (sequential + multiprocess)
│   └── compare.py         # Directory-vs-index comparison
└── commands/              # CLI wiring
    ├── scan_cmds.py
    └── db_cmds.py
```

See [usage.md](usage.md) for command reference and examples.

See [usefull.md](usefull.md) for usefull command.
