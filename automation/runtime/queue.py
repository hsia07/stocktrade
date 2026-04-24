"""
PHASE2 API Automode - C3 Slice 3: SQLite-Backed Message Queue

Provides durable message queue for OpenAI + Telegram dual-provider orchestration.
Slice 3 scope ONLY: queue + ack/nack + restart recovery.
NO real API calls, NO idempotency, NO audit trail.
"""

import sqlite3
import time
import json
import uuid
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

logger = logging.getLogger("api_automode_queue")


@dataclass
class QueueMessage:
    """Represents a message in the queue."""
    id: str
    provider: str
    payload: Dict[str, Any]
    correlation_key: str
    status: str  # 'pending', 'processing', 'acked', 'dlq'
    retry_count: int
    created_at: float


class MessageQueue:
    """SQLite-backed durable message queue."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            repo_root = Path(__file__).parent.parent.parent
            db_path = str(repo_root / "automation" / "runtime" / "queue.db")
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a persistent connection for batch operations."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
        return self._conn

    def _close_conn(self):
        """Close persistent connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _init_db(self):
        """Initialize SQLite schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    correlation_key TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON messages(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created ON messages(created_at)
            """)
            conn.commit()

    def enqueue(
        self,
        provider: str,
        payload: Dict[str, Any],
        correlation_key: Optional[str] = None,
    ) -> str:
        """Enqueue a message. Returns message_id."""
        message_id = str(uuid.uuid4())
        if correlation_key is None:
            correlation_key = message_id
        payload_json = json.dumps(payload)
        created_at = time.time()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO messages (id, provider, payload, correlation_key, status, retry_count, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (message_id, provider, payload_json, correlation_key, "pending", 0, created_at),
            )
            conn.commit()

        logger.debug(f"Enqueued message {message_id} for {provider}")
        return message_id

    def dequeue(self) -> Optional[QueueMessage]:
        """Dequeue one pending message and mark it processing."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, provider, payload, correlation_key, status, retry_count, created_at FROM messages WHERE status = 'pending' ORDER BY created_at LIMIT 1"
            )
            row = cursor.fetchone()
            if not row:
                return None

            message_id = row[0]
            conn.execute(
                "UPDATE messages SET status = 'processing' WHERE id = ?",
                (message_id,),
            )
            conn.commit()

            return QueueMessage(
                id=message_id,
                provider=row[1],
                payload=json.loads(row[2]),
                correlation_key=row[3],
                status="processing",
                retry_count=row[5],
                created_at=row[6],
            )

    def ack(self, message_id: str) -> bool:
        """Acknowledge a message — marks it acked."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE messages SET status = 'acked' WHERE id = ? AND status = 'processing'",
                (message_id,),
            )
            conn.commit()
            if cursor.rowcount > 0:
                logger.debug(f"Acked message {message_id}")
                return True
            return False

    def nack(self, message_id: str, reason: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Negative acknowledge a message — increments retry count.
        If retry_count >= max_retries, move to DLQ.
        Returns dict with action taken.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT retry_count, provider, payload, correlation_key FROM messages WHERE id = ? AND status = 'processing'",
                (message_id,),
            )
            row = cursor.fetchone()
            if not row:
                return {"status": "not_found", "message_id": message_id}

            retry_count = row[0] + 1
            provider = row[1]
            payload = json.loads(row[2])
            correlation_key = row[3]

            if retry_count >= max_retries:
                # Move to DLQ status
                conn.execute(
                    "UPDATE messages SET status = 'dlq', retry_count = ? WHERE id = ?",
                    (retry_count, message_id),
                )
                conn.commit()
                logger.warning(f"Message {message_id} moved to DLQ after {retry_count} retries: {reason}")
                return {
                    "status": "dlq",
                    "message_id": message_id,
                    "provider": provider,
                    "correlation_key": correlation_key,
                    "retry_count": retry_count,
                    "failure_reason": reason,
                    "original_payload_ref": message_id,
                }
            else:
                # Return to pending for retry
                conn.execute(
                    "UPDATE messages SET status = 'pending', retry_count = ? WHERE id = ?",
                    (retry_count, message_id),
                )
                conn.commit()
                logger.info(f"Message {message_id} nacked, retry {retry_count}/{max_retries}")
                return {
                    "status": "retry",
                    "message_id": message_id,
                    "retry_count": retry_count,
                    "max_retries": max_retries,
                }

    def get_pending_count(self) -> int:
        """Count pending messages."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM messages WHERE status = 'pending'")
            return cursor.fetchone()[0]

    def get_dlq_count(self) -> int:
        """Count DLQ messages."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM messages WHERE status = 'dlq'")
            return cursor.fetchone()[0]

    def recover_pending(self) -> List[QueueMessage]:
        """
        Recover pending messages after restart.
        Messages stuck in 'processing' are returned to 'pending'.
        """
        with sqlite3.connect(self.db_path) as conn:
            # Reset stuck processing messages back to pending
            cursor = conn.execute(
                "UPDATE messages SET status = 'pending' WHERE status = 'processing'"
            )
            stuck_count = cursor.rowcount
            conn.commit()

            if stuck_count > 0:
                logger.info(f"Recovered {stuck_count} stuck messages to pending")

            # Return all pending messages
            cursor = conn.execute(
                "SELECT id, provider, payload, correlation_key, status, retry_count, created_at FROM messages WHERE status = 'pending' ORDER BY created_at"
            )
            messages = []
            for row in cursor.fetchall():
                messages.append(QueueMessage(
                    id=row[0],
                    provider=row[1],
                    payload=json.loads(row[2]),
                    correlation_key=row[3],
                    status=row[4],
                    retry_count=row[5],
                    created_at=row[6],
                ))
            return messages

    def get_message(self, message_id: str) -> Optional[QueueMessage]:
        """Get a message by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id, provider, payload, correlation_key, status, retry_count, created_at FROM messages WHERE id = ?",
                (message_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return QueueMessage(
                id=row[0],
                provider=row[1],
                payload=json.loads(row[2]),
                correlation_key=row[3],
                status=row[4],
                retry_count=row[5],
                created_at=row[6],
            )

    def bulk_dequeue_ack(self, count: int) -> int:
        """Dequeue and ack multiple messages in a single transaction for performance."""
        conn = self._get_conn()
        acked = 0
        try:
            conn.execute("BEGIN")
            for _ in range(count):
                cursor = conn.execute(
                    "SELECT id FROM messages WHERE status = 'pending' ORDER BY created_at LIMIT 1"
                )
                row = cursor.fetchone()
                if not row:
                    break
                message_id = row[0]
                conn.execute(
                    "UPDATE messages SET status = 'acked' WHERE id = ?",
                    (message_id,),
                )
                acked += 1
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return acked

    def close(self):
        """Clean up resources."""
        self._close_conn()
        logger.info("MessageQueue closed")
