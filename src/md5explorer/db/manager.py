"""SQLite schema and connection management for the file index."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

DEFAULT_DB_NAME = "md5explorer_index.sqlite"


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    absolute_path TEXT UNIQUE NOT NULL,
    md5 TEXT,
    size INTEGER,
    created_at TEXT,
    modified_at TEXT
)
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_files_md5 ON files (md5)
"""

INSERT_SQL = """
INSERT OR REPLACE INTO files (absolute_path, md5, size, created_at, modified_at)
VALUES (?, ?, ?, ?, ?)
"""


class DatabaseManager:
    """Own the SQLite connection lifecycle for the file index."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def init(self, reset: bool = False) -> sqlite3.Connection:
        """Create (or reset) the index database and return an open connection."""
        if reset and self.db_path.exists():
            self.db_path.unlink()
            print(f"  Database dropped: {self.db_path}")

        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute(CREATE_TABLE_SQL)
        conn.execute(CREATE_INDEX_SQL)
        conn.commit()
        return conn

    def connect(self) -> sqlite3.Connection:
        """Open a connection to an existing database; exit if it does not exist."""
        if not self.db_path.exists():
            print(f"[ERROR] SQLite database not found: {self.db_path}", file=sys.stderr)
            print("        Run `md5explorer db index <directory>` first.", file=sys.stderr)
            sys.exit(1)
        return sqlite3.connect(str(self.db_path))
