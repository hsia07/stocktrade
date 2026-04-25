"""
R018 Schema Migration - Version Registry

Tracks schema versions in SQLite databases with audit trail.
"""

import sqlite3
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger("schema.version")


class SchemaVersionRegistry:
    """Manage schema version table in SQLite databases."""

    VERSION_TABLE = "_schema_version"

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_version_table()

    def _ensure_version_table(self):
        """Create version tracking table if not exists."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.VERSION_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER NOT NULL UNIQUE,
                    applied_at TEXT NOT NULL,
                    migration_name TEXT NOT NULL,
                    checksum TEXT,
                    rollback_available INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def get_current_version(self) -> int:
        """Return current schema version. Returns 0 if no migrations applied."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"SELECT MAX(version) FROM {self.VERSION_TABLE}"
            )
            result = cursor.fetchone()[0]
            return result if result is not None else 0

    def record_migration(self, version: int, migration_name: str,
                         checksum: Optional[str] = None,
                         rollback_available: bool = False):
        """Record a successful migration."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"""
                INSERT OR REPLACE INTO {self.VERSION_TABLE}
                (version, applied_at, migration_name, checksum, rollback_available)
                VALUES (?, ?, ?, ?, ?)
            """, (
                version,
                datetime.now(timezone.utc).isoformat(),
                migration_name,
                checksum or "",
                1 if rollback_available else 0
            ))
            conn.commit()
        logger.info(f"Recorded migration: {migration_name} -> v{version}")

    def get_migration_history(self) -> List[Dict[str, Any]]:
        """Return full migration history."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                f"SELECT * FROM {self.VERSION_TABLE} ORDER BY version"
            )
            return [dict(row) for row in cursor.fetchall()]

    def is_version_applied(self, version: int) -> bool:
        """Check if a specific version has been applied."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"SELECT 1 FROM {self.VERSION_TABLE} WHERE version = ?",
                (version,)
            )
            return cursor.fetchone() is not None

    def remove_version_record(self, version: int):
        """Remove a version record (used during rollback)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"DELETE FROM {self.VERSION_TABLE} WHERE version = ?",
                (version,)
            )
            conn.commit()
        logger.info(f"Removed version record: v{version}")
