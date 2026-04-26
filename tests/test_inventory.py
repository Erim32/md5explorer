"""Tests for :mod:`md5explorer.scan.inventory` and :mod:`md5explorer.scan.diff_lists`."""

from __future__ import annotations

from pathlib import Path

from md5explorer.scan.diff_lists import ListComparator, ListParser
from md5explorer.scan.inventory import InventoryReporter, InventoryScanner


def test_inventory_scanner_returns_one_entry_per_file(sample_tree: Path) -> None:
    infos = InventoryScanner().scan(sample_tree)
    names = sorted(i.name for i in infos)
    # sample_tree ships 5 files + empty_leaf/.gitkeep
    assert names == [".gitkeep", "a.txt", "b.txt", "c.txt", "d.txt", "e.txt"]


def test_inventory_save_and_parse_round_trip(sample_tree: Path, tmp_path: Path) -> None:
    infos = InventoryScanner().scan(sample_tree)
    output = tmp_path / "inventory.txt"
    InventoryReporter.save(infos, output, sample_tree, separator="_")

    assert output.exists()
    entries = ListParser(separator="_", skip_lines=4).parse(output)

    # Entries are keyed by MD5; duplicates collapse into a single key.
    distinct_md5 = {i.md5 for i in infos}
    assert set(entries.keys()) == distinct_md5


def test_list_comparator_buckets(tmp_path: Path) -> None:
    left_inv = tmp_path / "left.txt"
    right_inv = tmp_path / "right.txt"

    header = "# header\n" "# header\n" "# header\n" "\n"
    left_inv.write_text(header + "aaa_file1_2024-01-01_/x\nbbb_file2_2024-01-01_/y\n", encoding="utf-8")
    right_inv.write_text(header + "bbb_file2_2024-01-01_/y\nccc_file3_2024-01-01_/z\n", encoding="utf-8")

    parser = ListParser(separator="_", skip_lines=4)
    left = parser.parse(left_inv)
    right = parser.parse(right_inv)
    result = ListComparator.compare(left, right)

    assert set(result.only_left) == {"aaa"}
    assert set(result.only_right) == {"ccc"}
    assert set(result.common) == {"bbb"}
