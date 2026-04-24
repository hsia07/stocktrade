"""
PHASE2 API Automode - C3 Slice 3: Slice 2 → DLQ Adapter

Routes terminal failures from Slice 2 RetryExhaustedError into Slice 3 DLQ.
Slice 3 scope ONLY: adapter + routing.
"""

from typing import Dict, Any, Optional
from automation.runtime.retry import RetryExhaustedError
from automation.runtime.dlq import DLQManager


class TerminalFailureToDLQAdapter:
    """Adapts Slice 2 terminal failures to Slice 3 DLQ entries."""

    def __init__(self, dlq_manager: DLQManager):
        self.dlq = dlq_manager

    def route(self, error: RetryExhaustedError, correlation_key: Optional[str] = None) -> str:
        """
        Route a RetryExhaustedError to the DLQ.

        Returns the DLQ entry_id.
        """
        if correlation_key is None:
            correlation_key = f"retry_{error.provider}_{error.attempts}"

        return self.dlq.add_entry(
            provider=error.provider,
            correlation_key=correlation_key,
            failure_reason=error.last_error,
            original_payload_ref=correlation_key,
            payload_snapshot={
                "attempts": error.attempts,
                "provider": error.provider,
            },
        )

    def route_dict(self, terminal_result: Dict[str, Any], correlation_key: Optional[str] = None) -> str:
        """
        Route a terminal failure dict (from execute_safe) to the DLQ.

        Returns the DLQ entry_id.
        """
        if correlation_key is None:
            correlation_key = f"dict_{terminal_result.get('provider', 'unknown')}"

        return self.dlq.add_entry(
            provider=terminal_result.get("provider", "unknown"),
            correlation_key=correlation_key,
            failure_reason=terminal_result.get("last_error", "unknown"),
            original_payload_ref=correlation_key,
            payload_snapshot={
                "attempts": terminal_result.get("attempts", 0),
                "provider": terminal_result.get("provider", "unknown"),
            },
        )
