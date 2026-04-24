"""
PHASE2 API Automode - C3 Slice 3: Dead Letter Queue (DLQ) Manager

Provides persistent dead letter queue for failed messages.
Slice 3 scope ONLY: DLQ persistence + schema + replay capability.
NO real API calls, NO idempotency, NO audit trail.
"""

import sqlite3
import time
import json
import uuid
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger("api_automode_dlq")


@dataclass
class DLQEntry:
    """Represents a dead letter queue entry."""
    id: str
    timestamp: float
    provider: str
    correlation_key: str
    failure_reason: str
    original_payload_ref: str
    payload_snapshot: Dict[str, Any]


class DLQManager:
    """SQLite-backed dead letter queue manager."""

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
                CREATE TABLE IF NOT EXISTS dlq (
                    id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    provider TEXT NOT NULL,
                    correlation_key TEXT NOT NULL,
                    failure_reason TEXT NOT NULL,
                    original_payload_ref TEXT NOT NULL,
                    payload_snapshot TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_dlq_timestamp ON dlq(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_dlq_provider ON dlq(provider)
            """)
            conn.commit()

    def add_entry(
        self,
        provider: str,
        correlation_key: str,
        failure_reason: str,
        original_payload_ref: str,
        payload_snapshot: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add an entry to the DLQ. Returns entry_id."""
        entry_id = str(uuid.uuid4())
        timestamp = time.time()
        if payload_snapshot is None:
            payload_snapshot = {}
        payload_json = json.dumps(payload_snapshot)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO dlq (id, timestamp, provider, correlation_key, failure_reason, original_payload_ref, payload_snapshot) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (entry_id, timestamp, provider, correlation_key, failure_reason, original_payload_ref, payload_json),
            )
            conn.commit()

        logger.info(f"DLQ entry added: {entry_id} for {provider}, reason: {failure_reason}")
        return entry_id

    def get_all_entries(self) -> List[DLQEntry]:
        """Get all DLQ entries ordered by timestamp."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, timestamp, provider, correlation_key, failure_reason, original_payload_ref, payload_snapshot FROM dlq ORDER BY timestamp"
            )
            entries = []
            for row in cursor.fetchall():
                entries.append(DLQEntry(
                    id=row[0],
                    timestamp=row[1],
                    provider=row[2],
                    correlation_key=row[3],
                    failure_reason=row[4],
                    original_payload_ref=row[5],
                    payload_snapshot=json.loads(row[6]),
                ))
            return entries

    def get_entries_by_provider(self, provider: str) -> List[DLQEntry]:
        """Get DLQ entries filtered by provider."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, timestamp, provider, correlation_key, failure_reason, original_payload_ref, payload_snapshot FROM dlq WHERE provider = ? ORDER BY timestamp",
                (provider,),
            )
            entries = []
            for row in cursor.fetchall():
                entries.append(DLQEntry(
                    id=row[0],
                    timestamp=row[1],
                    provider=row[2],
                    correlation_key=row[3],
                    failure_reason=row[4],
                    original_payload_ref=row[5],
                    payload_snapshot=json.loads(row[6]),
                ))
            return entries

    def get_count(self) -> int:
        """Count total DLQ entries."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM dlq")
            return cursor.fetchone()[0]

    def get_entry(self, entry_id: str) -> Optional[DLQEntry]:
        """Get a single DLQ entry by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, timestamp, provider, correlation_key, failure_reason, original_payload_ref, payload_snapshot FROM dlq WHERE id = ?",
                (entry_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return DLQEntry(
                id=row[0],
                timestamp=row[1],
                provider=row[2],
                correlation_key=row[3],
                failure_reason=row[4],
                original_payload_ref=row[5],
                payload_snapshot=json.loads(row[6]),
            )

    def clear_all(self):
        """Clear all DLQ entries (for testing)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM dlq")
            conn.commit()
        logger.info("DLQ cleared")

    def close(self):
        """Clean up resources."""
        logger.info("DLQManager closed")
