# md5explorer — CLI Reference

`md5explorer` is a command-line tool for detecting duplicate files, comparing
directories, and managing large file trees through an SQLite-backed catalog.
All commands share the `md5explorer` entry point.

---

## Table of Contents

- [md5explorer — CLI Reference](#md5explorer--cli-reference)
  - [Table of Contents](#table-of-contents)
  - [Quickstart](#quickstart)
  - [Command Overview](#command-overview)
  - [Global Flags](#global-flags)
  - [scan commands](#scan-commands)
    - [scan duplicates](#scan-duplicates)
    - [scan compare](#scan-compare)
    - [scan inventory](#scan-inventory)
    - [scan diff-lists](#scan-diff-lists)
    - [scan empty-dirs](#scan-empty-dirs)
  - [db commands](#db-commands)
    - [db index](#db-index)
    - [db list](#db-list)
    - [db check](#db-check)
    - [db compare](#db-compare)
  - [Exit Codes](#exit-codes)

---

## Quickstart

```bash
# Detect duplicates (read-only)
md5explorer scan duplicates ./photos

# Simulate deletion, keeping the newest file in each group
md5explorer scan duplicates ./photos --delete --dry-run --keep newest

# Actually delete duplicates (with confirmation prompt)
md5explorer scan duplicates ./photos --delete --keep newest

# Compare two directories side by side
md5explorer scan compare ./dir1 ./dir2

# Generate an MD5 inventory file
md5explorer scan inventory ./photos -o inventory.txt

# Index a large directory tree into SQLite (multiprocess)
md5explorer db index ./photos

# Compare a new folder against the indexed catalog
md5explorer db compare ./incoming --delete --dry-run
```

Run `md5explorer --help`, `md5explorer scan --help`, or `md5explorer db --help`
for the full option list.

---

## Command Overview

| Group  | Subcommand   | Purpose                                              |
| ------ | ------------ | ---------------------------------------------------- |
| `scan` | `duplicates` | Detect and optionally delete duplicate files         |
| `scan` | `compare`    | Compare two directories file by file                 |
| `scan` | `inventory`  | Write an MD5/name/date/path inventory to a text file |
| `scan` | `diff-lists` | Diff two inventory files by MD5                      |
| `scan` | `empty-dirs` | Detect and optionally delete empty directories       |
| `db`   | `index`      | Index a directory into the SQLite database           |
| `db`   | `list`       | List entries from the database                       |
| `db`   | `check`      | Check whether a specific file is present in the DB   |
| `db`   | `compare`    | Compare a directory against the indexed catalog      |

---

## Global Flags

These flags are available on every command.

| Flag        | Description                          |
| ----------- | ------------------------------------ |
| `--help`    | Show help for the current command    |
| `--version` | Print the installed version and exit |

---

## scan commands

The `scan` group operates directly on the filesystem, without any database.
It is the right tool for one-off comparisons and duplicate detection on small
to medium file trees.

---

### scan duplicates

Detect duplicate files by comparing their MD5 hashes. By default, the command
is **read-only**: it reports duplicates but does not modify anything.

```
md5explorer scan duplicates <DIR> [DIR ...] [OPTIONS]
```

**Arguments**

| Argument  | Description                                                                         |
| --------- | ----------------------------------------------------------------------------------- |
| `DIR ...` | One or more directories to scan. Multiple directories are treated as a single pool. |

**Options**

| Flag                                            | Default | Description                                                                                                                                                                          |
| ----------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `--delete`                                      | off     | Enable deletion of duplicate files. Without this flag, the command is read-only.                                                                                                     |
| `--keep {first,newest,oldest,smallest,largest}` | `first` | Which file to keep in each duplicate group. Only relevant when `--delete` is set.                                                                                                    |
| `--dry-run`                                     | off     | Simulate the deletion without modifying anything. Prints what would be deleted. Overrides `--yes`.                                                                                   |
| `--yes`                                         | off     | Skip the confirmation prompt before deleting. Ignored when `--dry-run` is set.                                                                                                       |
| `--cross-only`                                  | off     | Only report/delete duplicates that appear in **more than one** of the provided directories. Duplicates within a single directory are ignored. Requires at least two `DIR` arguments. |
| `--delete-log <FILE>`                           | —       | Write the list of deleted files to a log file. Only active when `--delete` is set.                                                                                                   |

**Keep strategies**

| Value      | File kept                                       |
| ---------- | ----------------------------------------------- |
| `first`    | The first file encountered during traversal     |
| `newest`   | The file with the most recent modification date |
| `oldest`   | The file with the earliest modification date    |
| `smallest` | The file with the smallest size                 |
| `largest`  | The file with the largest size                  |

> **Note:** `--keep` is only meaningful when `--delete` is specified. When used
> without `--delete`, it is silently ignored.

**Examples**

```bash
# List duplicates in a single directory (read-only)
md5explorer scan duplicates ./photos

# Preview what would be deleted, keeping the newest file per group
md5explorer scan duplicates ./photos --delete --dry-run --keep newest

# Delete duplicates without a confirmation prompt, log deletions
md5explorer scan duplicates ./photos --delete --yes --keep newest --delete-log deletions.txt

# Find duplicates that exist in both dir1 and dir2 (ignore intra-dir dupes)
md5explorer scan duplicates ./dir1 ./dir2 --cross-only

# Delete cross-directory duplicates without confirmation
md5explorer scan duplicates ./dir1 ./dir2 --delete --cross-only --yes
```

---

### scan compare

Compare two directories **file by file**, using both relative path and MD5
hash. The output groups files into: identical, modified (same path, different
hash), only in left, only in right.

```
md5explorer scan compare <DIR1> <DIR2> [OPTIONS]
```

**Arguments**

| Argument | Description                    |
| -------- | ------------------------------ |
| `DIR1`   | The reference (left) directory |
| `DIR2`   | The target (right) directory   |

**Options**

| Flag                    | Default | Description                                                                                        |
| ----------------------- | ------- | -------------------------------------------------------------------------------------------------- |
| `--ignore <NAME> [...]` | —       | Directory or file names to exclude from both sides during traversal (e.g. `.git`, `node_modules`). |
| `-o, --output <FILE>`   | stdout  | Write the comparison report to a file instead of printing to the terminal.                         |

**Examples**

```bash
# Basic comparison
md5explorer scan compare ./dir1 ./dir2

# Ignore build artifacts and version control folders
md5explorer scan compare ./dir1 ./dir2 --ignore .git __pycache__ node_modules

# Save the report to a file
md5explorer scan compare ./dir1 ./dir2 -o report.txt

# Combine both
md5explorer scan compare ./dir1 ./dir2 --ignore .git -o report.txt
```

---

### scan inventory

Scan a directory and generate a flat inventory file. Each line follows the
format:

```
MD5<sep>NAME<sep>MODIFIED_AT<sep>PATH
```

The default separator is a tab (`\t`). The inventory file can later be used as
input for [`scan diff-lists`](#scan-diff-lists).

```
md5explorer scan inventory <DIR> [OPTIONS]
```

**Arguments**

| Argument | Description            |
| -------- | ---------------------- |
| `DIR`    | Directory to inventory |

**Options**

| Flag                  | Default | Description                                                        |
| --------------------- | ------- | ------------------------------------------------------------------ |
| `-o, --output <FILE>` | stdout  | Write the inventory to a file instead of printing to the terminal. |
| `-s, --sep <CHAR>`    | `\t`    | Field separator character to use between columns.                  |

**Examples**

```bash
# Print inventory to stdout
md5explorer scan inventory ./photos

# Save inventory to a file with the default tab separator
md5explorer scan inventory ./photos -o inventory.txt

# Use a pipe separator instead
md5explorer scan inventory ./photos -o inventory.txt -s "|"
```

---

### scan diff-lists

Compare two inventory files produced by [`scan inventory`](#scan-inventory) by
MD5 hash. The output identifies files that were added, removed, or are common
to both inventories.

```
md5explorer scan diff-lists <LIST1> <LIST2> [OPTIONS]
```

**Arguments**

| Argument | Description                        |
| -------- | ---------------------------------- |
| `LIST1`  | First inventory file (reference)   |
| `LIST2`  | Second inventory file (to compare) |

**Options**

| Flag                | Default | Description                                                                                                                                                                                                                    |
| ------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `-s, --sep <CHAR>`  | `\t`    | Field separator used in the inventory files. Must match the separator used when the inventories were generated.                                                                                                                |
| `-i, --index <INT>` | `3`     | Zero-based column index of the `PATH` field in the inventory files. Adjust this if a custom separator caused the column order to shift. Default assumes the standard `MD5<tab>NAME<tab>MODIFIED_AT<tab>PATH` format (index 3). |

**Examples**

```bash
# Diff two standard (tab-separated) inventories
md5explorer scan diff-lists inventory_v1.txt inventory_v2.txt

# Diff inventories that were generated with a custom separator
md5explorer scan diff-lists list1.txt list2.txt -s "_" -i 4
```

> **Tip:** Always use the same `-s` value here as the one used when generating
> the inventory with `scan inventory`.

---

### scan empty-dirs

Detect empty directories in a tree. Traversal is **leaves-first**, so a
directory only becomes "empty" once all its subdirectories have already been
evaluated (and potentially deleted).

```
md5explorer scan empty-dirs <DIR> [OPTIONS]
```

**Arguments**

| Argument | Description          |
| -------- | -------------------- |
| `DIR`    | Directory to inspect |

**Options**

| Flag        | Default | Description                                                                         |
| ----------- | ------- | ----------------------------------------------------------------------------------- |
| `--delete`  | off     | Delete the detected empty directories. Without this flag, the command is read-only. |
| `--dry-run` | off     | Simulate the deletion without modifying anything. Overrides `--yes`.                |
| `--yes`     | off     | Skip the confirmation prompt before deleting. Ignored when `--dry-run` is set.      |

**Examples**

```bash
# List empty directories (read-only)
md5explorer scan empty-dirs ./photos

# Preview what would be deleted
md5explorer scan empty-dirs ./photos --delete --dry-run

# Delete without confirmation
md5explorer scan empty-dirs ./photos --delete --yes
```

---

## db commands

The `db` group uses a **SQLite database** as a persistent catalog. This is the
recommended approach for large file trees, as MD5 hashes are computed once and
stored for repeated querying.

By default, the database is stored in the current working directory as
`md5explorer.sqlite`. Use `--db <FILE>` to specify a custom path.

---

### db index

Scan a directory and index all files (path + MD5 + metadata) into the SQLite
database. Hashing runs in **multiprocess mode** by default for performance.

```
md5explorer db index <DIR> [OPTIONS]
```

**Arguments**

| Argument | Description        |
| -------- | ------------------ |
| `DIR`    | Directory to index |

**Options**

| Flag                     | Default              | Description                                                                                                  |
| ------------------------ | -------------------- | ------------------------------------------------------------------------------------------------------------ |
| `--slow`                 | off                  | Disable multiprocessing and run single-threaded. Useful on systems with limited resources or when debugging. |
| `--exclude <NAME> [...]` | —                    | Directory or file names to skip during traversal (e.g. `.git`, `node_modules`).                              |
| `--reset`                | off                  | Drop and recreate the database before indexing. Use to start fresh.                                          |
| `--db <FILE>`            | `md5explorer.sqlite` | Path to the SQLite database file.                                                                            |

**Examples**

```bash
# Index with multiprocessing (default)
md5explorer db index ./photos

# Index single-threaded
md5explorer db index ./photos --slow

# Exclude common noise directories
md5explorer db index ./photos --exclude .git node_modules __pycache__

# Rebuild the index from scratch into a named database
md5explorer db index ./photos --reset --db my.sqlite
```

---

### db list

List file entries currently stored in the database.

```
md5explorer db list [OPTIONS]
```

> **Note:** This command takes no directory argument — it queries the existing
> database directly.

**Options**

| Flag            | Default              | Description                           |
| --------------- | -------------------- | ------------------------------------- |
| `--limit <INT>` | (all)                | Maximum number of entries to display. |
| `--db <FILE>`   | `md5explorer.sqlite` | Path to the SQLite database file.     |

**Examples**

```bash
# List all indexed entries
md5explorer db list

# Show only the first 20 entries
md5explorer db list --limit 20
```

---

### db check

Check whether a **specific file** is present in the database, matched by its
MD5 hash.

```
md5explorer db check <FILE> [OPTIONS]
```

> **Note:** Unlike other `db` commands, this command takes a **single file
> path**, not a directory.

**Arguments**

| Argument | Description                 |
| -------- | --------------------------- |
| `FILE`   | Path to the file to look up |

**Options**

| Flag          | Default              | Description                       |
| ------------- | -------------------- | --------------------------------- |
| `--db <FILE>` | `md5explorer.sqlite` | Path to the SQLite database file. |

**Examples**

```bash
# Check whether a specific file is already indexed
md5explorer db check ./photos/image.jpg

# Check against a named database
md5explorer db check ./photos/image.jpg --db my.sqlite
```

---

### db compare

Compare all files in a directory against the **indexed catalog**. Files are
matched by MD5 hash. The command reports which files in `DIR` are already
indexed (duplicates) and which are new.

This is similar to [`scan compare`](#scan-compare), but compares a live
directory against the database rather than against another directory.

```
md5explorer db compare <DIR> [OPTIONS]
```

**Arguments**

| Argument | Description                            |
| -------- | -------------------------------------- |
| `DIR`    | Directory to compare against the index |

**Options**

| Flag              | Default              | Description                                                                                               |
| ----------------- | -------------------- | --------------------------------------------------------------------------------------------------------- |
| `--delete`        | off                  | Delete files in `DIR` that are already present in the index. Without this flag, the command is read-only. |
| `--dry-run`       | off                  | Simulate the deletion without modifying anything. Overrides `--yes`.                                      |
| `--yes`           | off                  | Skip the confirmation prompt before deleting. Ignored when `--dry-run` is set.                            |
| `--export <FILE>` | —                    | Write the list of detected duplicates to a text file.                                                     |
| `--db <FILE>`     | `md5explorer.sqlite` | Path to the SQLite database file.                                                                         |

**Examples**

```bash
# Check which files in ./incoming already exist in the index
md5explorer db compare ./incoming

# Preview what would be deleted
md5explorer db compare ./incoming --delete --dry-run

# Export the duplicate list before deleting
md5explorer db compare ./incoming --export duplicates.txt

# Delete without confirmation and export the list
md5explorer db compare ./incoming --delete --yes --export duplicates.txt
```

---

## Exit Codes

All commands follow a consistent exit code convention, suitable for use in
shell scripts and CI pipelines.

| Code | Meaning                                                                                                                                 |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `0`  | Success — no duplicates found, directories are identical, or all deletions completed successfully.                                      |
| `1`  | Differences found or action required — duplicates or mismatches were detected, but no deletion was performed (or `--dry-run` was used). |
| `2`  | Deletion ran but encountered at least one failure — some files could not be deleted.                                                    |

**Shell script example**

```bash
md5explorer scan duplicates ./photos
if [ $? -eq 1 ]; then
  echo "Duplicates found — review before deleting."
fi
```
