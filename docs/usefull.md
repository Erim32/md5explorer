## Common Usage

### Find duplicate files (read-only)

```bash
md5explorer scan duplicates ./photos
```

### Preview deletion before committing

```bash
# Step 1 — simulate (nothing is deleted)
md5explorer scan duplicates ./photos --delete --dry-run --keep newest

# Step 2 — actually delete, with confirmation prompt
md5explorer scan duplicates ./photos --delete --keep newest
```

> Use `--keep newest` to always preserve the most recently modified file in each group.

### Find and remove empty directories

```bash
# List first
md5explorer scan empty-dirs ./photos

# Then delete (leaves-first traversal)
md5explorer scan empty-dirs ./photos --delete --yes
```

### Compare two directories

```bash
# Basic comparison
md5explorer scan compare ./dir1 ./dir2

# Ignore build artifacts and save the report
md5explorer scan compare ./dir1 ./dir2 --ignore .git node_modules -o report.txt
```

### Delete only cross-directory duplicates

```bash
# Preview
md5explorer scan duplicates ./dir1 ./dir2 --cross-only --delete --dry-run

# Delete without prompt
md5explorer scan duplicates ./dir1 ./dir2 --cross-only --delete --yes
```

> `--cross-only` ignores duplicates that exist within a single directory.

### Snapshot a folder's state

```bash
md5explorer scan inventory ./photos -o inventory_2024.txt
```

Output format: `MD5<tab>NAME<tab>MODIFIED_AT<tab>PATH`

### Diff two snapshots over time

```bash
md5explorer scan inventory ./photos -o snap_v1.txt
# ... time passes ...
md5explorer scan inventory ./photos -o snap_v2.txt

md5explorer scan diff-lists snap_v1.txt snap_v2.txt
```

### Index a large tree and check incoming files against it

```bash
# Step 1 — build the index (multiprocess by default)
md5explorer db index ./archive --exclude .git node_modules

# Step 2 — compare new files against the catalog
md5explorer db compare ./incoming --delete --dry-run

# Step 3 — export the duplicate list and delete
md5explorer db compare ./incoming --export dupes.txt --delete --yes
```

> Use `--reset` to rebuild the index from scratch. Use `--slow` on low-resource machines.

### Inspect the catalog

```bash
# Browse indexed entries
md5explorer db list --limit 20

# Check whether a specific file is already indexed
md5explorer db check ./photos/image.jpg
```

### Non-interactive deletion (CI / cron)

```bash
md5explorer scan duplicates ./photos \
  --delete --yes --keep newest \
  --delete-log /var/log/md5explorer.txt
```

### Use exit codes in a shell script

```bash
md5explorer scan duplicates ./photos
case $? in
  0) echo "Clean — no duplicates found" ;;
  1) echo "Duplicates found — review before deleting" ;;
  2) echo "Deletion ran but failed for some files" ;;
esac
```
