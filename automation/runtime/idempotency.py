"""
PHASE2 API Automode - C3 Slice 4: Idempotency Key Manager

Provides persistent idempotency store for duplicate delivery prevention.
Slice 4 scope ONLY: idempotency + dedupe + restart-safe state.
NO real API calls, NO dashboard UI, NO compliance reporting.
"""

import sqlite3
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger("api_automode_idempotency")


@dataclass
class IdempotencyRecord:
    """Represents an idempotency record."""
    idempotency_key: str
    correlation_key: str
    provider: str
    status: str  # 'pending', 'processing', 'completed', 'failed', 'dlq'
    created_at: float
    updated_at: float


class IdempotencyManager:
    """SQLite-backed idempotency key manager."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            repo_root = Path(__file__).parent.parent.parent
            db_path = str(repo_root / "automation" / "runtime" / "queue.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS idempotency (
                    idempotency_key TEXT PRIMARY KEY,
                    correlation_key TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_idempotency_corr ON idempotency(correlation_key)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_idempotency_status ON idempotency(status)
            """)
            conn.commit()

    def check(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """
        Check if an idempotency key exists.

        Returns None if not found, or dict with status if found.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT idempotency_key, correlation_key, provider, status, created_at, updated_at FROM idempotency WHERE idempotency_key = ?",
                (idempotency_key,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "idempotency_key": row[0],
                "correlation_key": row[1],
                "provider": row[2],
                "status": row[3],
                "created_at": row[4],
                "updated_at": row[5],
            }

    def register(
        self,
        idempotency_key: str,
        correlation_key: str,
        provider: str,
        status: str = "pending",
    ) -> Dict[str, Any]:
        """
        Register a new idempotency key.

        If key already exists, returns already_processed.
        Otherwise inserts and returns registered.
        """
        existing = self.check(idempotency_key)
        if existing:
            logger.info(f"Idempotency key {idempotency_key} already exists with status {existing['status']}")
            return {
                "status": "already_processed",
                "idempotency_key": idempotency_key,
                "existing_status": existing["status"],
                "correlation_key": existing["correlation_key"],
                "provider": existing["provider"],
            }

        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO idempotency (idempotency_key, correlation_key, provider, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (idempotency_key, correlation_key, provider, status, now, now),
            )
            conn.commit()

        logger.info(f"Registered idempotency key {idempotency_key} for {provider}")
        return {
            "status": "registered",
            "idempotency_key": idempotency_key,
            "correlation_key": correlation_key,
            "provider": provider,
        }

    def update_status(self, idempotency_key: str, new_status: str) -> bool:
        """Update the status of an idempotency key."""
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE idempotency SET status = ?, updated_at = ? WHERE idempotency_key = ?",
                (new_status, now, idempotency_key),
            )
            conn.commit()
            if cursor.rowcount > 0:
                logger.debug(f"Updated {idempotency_key} to {new_status}")
                return True
            return False

    def recover_processing(self) -> List[IdempotencyRecord]:
        """
        After restart, keys stuck in 'processing' are returned to 'pending'.
        Returns list of recovered records.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT idempotency_key, correlation_key, provider, status, created_at, updated_at FROM idempotency WHERE status = 'processing'"
            )
            stuck = []
            for row in cursor.fetchall():
                stuck.append(IdempotencyRecord(
                    idempotency_key=row[0],
                    correlation_key=row[1],
                    provider=row[2],
                    status=row[3],
                    created_at=row[4],
                    updated_at=row[5],
                ))

            if stuck:
                now = time.time()
                conn.execute(
                    "UPDATE idempotency SET status = 'pending', updated_at = ? WHERE status = 'processing'",
                    (now,),
                )
                conn.commit()
                logger.info(f"Recovered {len(stuck)} idempotency keys from processing to pending")

            return stuck

    def get_by_correlation_key(self, correlation_key: str) -> Optional[Dict[str, Any]]:
        """Get idempotency record by correlation key."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT idempotency_key, correlation_key, provider, status, created_at, updated_at FROM idempotency WHERE correlation_key = ? LIMIT 1",
                (correlation_key,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "idempotency_key": row[0],
                "correlation_key": row[1],
                "provider": row[2],
                "status": row[3],
                "created_at": row[4],
                "updated_at": row[5],
            }

    def clear_all(self):
        """Clear all idempotency records (for testing)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM idempotency")
            conn.commit()
        logger.info("Idempotency store cleared")

    def close(self):
        """Clean up resources."""
        logger.info("IdempotencyManager closed")
