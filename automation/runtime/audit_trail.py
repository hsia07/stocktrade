"""
PHASE2 API Automode - C3 Slice 4: Audit Trail Manager

Provides persistent audit event store for message lineage tracking.
Slice 4 scope ONLY: audit events + lineage query.
NO real API calls, NO dashboard UI, NO compliance reporting.
"""

import sqlite3
import time
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger("api_automode_audit_trail")


@dataclass
class AuditEvent:
    """Represents an audit event."""
    id: int
    timestamp: float
    provider: str
    correlation_key: str
    idempotency_key: str
    stage: str
    outcome: str
    metadata: Optional[Dict[str, Any]]


class AuditTrailManager:
    """SQLite-backed audit trail manager."""

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
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    provider TEXT NOT NULL,
                    correlation_key TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_corr ON audit_events(correlation_key)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_idempotency ON audit_events(idempotency_key)
            """)
            conn.commit()

    def record_event(
        self,
        provider: str,
        correlation_key: str,
        idempotency_key: str,
        stage: str,
        outcome: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Record an audit event.

        Returns the event ID.
        """
        timestamp = time.time()
        metadata_json = json.dumps(metadata) if metadata else None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO audit_events (timestamp, provider, correlation_key, idempotency_key, stage, outcome, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (timestamp, provider, correlation_key, idempotency_key, stage, outcome, metadata_json),
            )
            conn.commit()
            event_id = cursor.lastrowid

        logger.debug(f"Audit event recorded: {stage}/{outcome} for {correlation_key}")
        return event_id

    def get_lineage(self, correlation_key: str) -> List[AuditEvent]:
        """
        Get all audit events for a correlation key, ordered by timestamp.

        Returns ordered list of AuditEvent objects.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, timestamp, provider, correlation_key, idempotency_key, stage, outcome, metadata FROM audit_events WHERE correlation_key = ? ORDER BY timestamp, id",
                (correlation_key,),
            )
            events = []
            for row in cursor.fetchall():
                meta = json.loads(row[7]) if row[7] else None
                events.append(AuditEvent(
                    id=row[0],
                    timestamp=row[1],
                    provider=row[2],
                    correlation_key=row[3],
                    idempotency_key=row[4],
                    stage=row[5],
                    outcome=row[6],
                    metadata=meta,
                ))
            return events

    def get_events_by_idempotency_key(self, idempotency_key: str) -> List[AuditEvent]:
        """Get all audit events for an idempotency key."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, timestamp, provider, correlation_key, idempotency_key, stage, outcome, metadata FROM audit_events WHERE idempotency_key = ? ORDER BY timestamp, id",
                (idempotency_key,),
            )
            events = []
            for row in cursor.fetchall():
                meta = json.loads(row[7]) if row[7] else None
                events.append(AuditEvent(
                    id=row[0],
                    timestamp=row[1],
                    provider=row[2],
                    correlation_key=row[3],
                    idempotency_key=row[4],
                    stage=row[5],
                    outcome=row[6],
                    metadata=meta,
                ))
            return events

    def get_events_by_stage(self, stage: str, limit: int = 100) -> List[AuditEvent]:
        """Get recent audit events by stage."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, timestamp, provider, correlation_key, idempotency_key, stage, outcome, metadata FROM audit_events WHERE stage = ? ORDER BY timestamp DESC LIMIT ?",
                (stage, limit),
            )
            events = []
            for row in cursor.fetchall():
                meta = json.loads(row[7]) if row[7] else None
                events.append(AuditEvent(
                    id=row[0],
                    timestamp=row[1],
                    provider=row[2],
                    correlation_key=row[3],
                    idempotency_key=row[4],
                    stage=row[5],
                    outcome=row[6],
                    metadata=meta,
                ))
            return events

    def get_count(self) -> int:
        """Count total audit events."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM audit_events")
            return cursor.fetchone()[0]

    def clear_all(self):
        """Clear all audit events (for testing)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM audit_events")
            conn.commit()
        logger.info("Audit trail cleared")

    def close(self):
        """Clean up resources."""
        logger.info("AuditTrailManager closed")
