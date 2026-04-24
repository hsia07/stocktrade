"""
PHASE2 API Automode - C3 Slice 2: Retry with Exponential Backoff

Provides retry logic for OpenAI + Telegram dual-provider orchestration.
Slice 2 scope ONLY: retry + backoff + terminal failure contract.
NO real API calls, NO durable queue, NO DLQ persistence.
"""

import time
import random
import logging
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass

logger = logging.getLogger("api_automode_retry")


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, provider: str, attempts: int, last_error: str):
        self.provider = provider
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Retry exhausted for {provider} after {attempts} attempts: {last_error}"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": "terminal_failure",
            "provider": self.provider,
            "attempts": self.attempts,
            "last_error": self.last_error,
        }


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay_seconds: float = 1.0
    jitter: bool = False
    jitter_factor: float = 0.5

    def __post_init__(self):
        if not (1 <= self.max_retries <= 10):
            raise ValueError("max_retries must be between 1 and 10")
        if self.base_delay_seconds < 0.5:
            raise ValueError("base_delay_seconds must be >= 0.5")
        if self.base_delay_seconds > 60.0:
            raise ValueError("base_delay_seconds must be <= 60.0")


class ExponentialBackoffRetry:
    """Retry wrapper with exponential backoff."""

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt (0-indexed)."""
        delay = self.config.base_delay_seconds * (2 ** attempt)
        if self.config.jitter:
            jitter_range = delay * self.config.jitter_factor
            delay = random.uniform(delay - jitter_range, delay + jitter_range)
            delay = max(0.1, delay)  # minimum 0.1s
        return delay

    def execute(
        self, fn: Callable[[], Any], provider: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Execute fn with retry logic.

        Semantics:
            max_retries = TOTAL maximum number of attempts (including initial).
            Example: max_retries=3 means up to 3 calls total.

        Returns:
            On success: {"status": "success", "result": ..., "attempts": N}
            On terminal failure: raises RetryExhaustedError
        """
        last_error = ""

        for attempt in range(self.config.max_retries):
            try:
                result = fn()
                return {
                    "status": "success",
                    "result": result,
                    "attempts": attempt + 1,
                    "provider": provider,
                }
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"{provider} attempt {attempt + 1}/{self.config.max_retries} failed: {last_error}"
                )

                if attempt < self.config.max_retries - 1:
                    delay = self._calculate_delay(attempt)
                    logger.info(f"Retrying {provider} in {delay:.2f}s...")
                    time.sleep(delay)
                else:
                    break

        # All retries exhausted
        logger.error(f"{provider} retry exhausted after {self.config.max_retries} attempts")
        raise RetryExhaustedError(
            provider=provider,
            attempts=self.config.max_retries,
            last_error=last_error,
        )

    def execute_safe(
        self, fn: Callable[[], Any], provider: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Execute fn with retry logic, returning terminal failure dict instead of raising.

        Returns:
            On success: {"status": "success", ...}
            On terminal failure: {"status": "terminal_failure", ...}
        """
        try:
            return self.execute(fn, provider)
        except RetryExhaustedError as e:
            return e.to_dict()
