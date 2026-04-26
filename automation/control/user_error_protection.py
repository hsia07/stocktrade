"""
R020 User Error Protection

Provides guards against accidental critical operations:
- Action confirmation for destructive/irreversible operations
- Conflict detection for contradictory operation sequences
- Cooldown enforcement to prevent rapid-fire mistakes
- Audit logging for all protected actions
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger("user_error_protection")


class ActionConfirmationGuard:
    """
    Require explicit confirmation before executing critical operations.
    
    Critical operations: pause, start, stop, merge, push, unfreeze
    """

    CRITICAL_ACTIONS = {
        "pause", "start", "stop", "merge", "push", "unfreeze",
        "chain_unfreeze", "runtime_activation", "dispatch",
    }

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path(__file__).parent.parent.parent
        self.confirmations: Dict[str, Dict[str, Any]] = {}

    def is_critical(self, action: str) -> bool:
        """Check if an action requires confirmation."""
        return action.lower() in self.CRITICAL_ACTIONS

    def request_confirmation(self, action: str, context: str = "") -> Dict[str, Any]:
        """
        Request confirmation for a critical action.
        
        Returns dict with:
        - requires_confirmation: bool
        - confirmation_token: str (if required)
        - warning_message: str
        """
        if not self.is_critical(action):
            return {"requires_confirmation": False, "confirmation_token": "", "warning_message": ""}

        token = f"{action}_{int(time.time() * 1000)}"
        self.confirmations[token] = {
            "action": action,
            "context": context,
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "confirmed": False,
        }

        warning = (
            f"⚠️ CRITICAL ACTION: `{action}`\n"
            f"Context: {context or 'N/A'}\n"
            f"Token: `{token}`\n"
            f"Confirm with: confirm_action('{token}')"
        )

        logger.warning(f"Confirmation required for {action}: token={token}")
        return {
            "requires_confirmation": True,
            "confirmation_token": token,
            "warning_message": warning,
        }

    def confirm_action(self, token: str) -> Dict[str, Any]:
        """Confirm a pending critical action."""
        if token not in self.confirmations:
            return {"confirmed": False, "error": "invalid_token", "action": ""}

        self.confirmations[token]["confirmed"] = True
        self.confirmations[token]["confirmed_at"] = datetime.now(timezone.utc).isoformat()
        action = self.confirmations[token]["action"]
        logger.info(f"Action confirmed: {action} (token={token})")
        return {"confirmed": True, "error": "", "action": action}

    def check_confirmed(self, token: str) -> bool:
        """Check if a token has been confirmed."""
        return self.confirmations.get(token, {}).get("confirmed", False)


class ConflictDetector:
    """
    Detect conflicting or contradictory operation sequences.
    
    Examples:
    - pause followed by start within cooldown window
    - stop followed by dispatch
    - merge followed by push without review
    """

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path(__file__).parent.parent.parent
        self.history_file = self.repo_root / "automation" / "control" / "action_history.json"
        self.history: List[Dict[str, Any]] = []
        self._load_history()

    def _load_history(self):
        if self.history_file.exists():
            try:
                with self.history_file.open("r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []

    def _save_history(self):
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with self.history_file.open("w", encoding="utf-8") as f:
                json.dump(self.history[-100:], f, indent=2)  # Keep last 100
        except Exception as e:
            logger.warning(f"Failed to save action history: {e}")

    def record_action(self, action: str, result: str, metadata: Dict[str, Any] = None):
        """Record an executed action."""
        entry = {
            "action": action,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }
        self.history.append(entry)
        self._save_history()
        logger.info(f"Action recorded: {action} -> {result}")

    def detect_conflict(self, proposed_action: str) -> Dict[str, Any]:
        """
        Check if proposed action conflicts with recent history.
        
        Returns dict with:
        - conflict_detected: bool
        - conflict_type: str or None
        - reason: str
        """
        if not self.history:
            return {"conflict_detected": False, "conflict_type": None, "reason": ""}

        last_action = self.history[-1]["action"]
        last_time = datetime.fromisoformat(self.history[-1]["timestamp"])
        now = datetime.now(timezone.utc)
        elapsed = (now - last_time).total_seconds()

        # Rule: cannot start immediately after pause (within 5s)
        if proposed_action == "start" and last_action == "pause" and elapsed < 5:
            return {
                "conflict_detected": True,
                "conflict_type": "pause_start_race",
                "reason": f"Start requested {elapsed:.1f}s after pause. Minimum 5s required.",
            }

        # Rule: cannot dispatch immediately after stop (within 3s)
        if proposed_action == "dispatch" and last_action == "stop" and elapsed < 3:
            return {
                "conflict_detected": True,
                "conflict_type": "stop_dispatch_race",
                "reason": f"Dispatch requested {elapsed:.1f}s after stop. Minimum 3s required.",
            }

        # Rule: cannot merge without prior review phase
        if proposed_action == "merge":
            recent_phases = [h["action"] for h in self.history[-10:]]
            if "merge_pre_review" not in recent_phases:
                return {
                    "conflict_detected": True,
                    "conflict_type": "missing_review_gate",
                    "reason": "Merge attempted without merge-pre review phase in recent history.",
                }

        return {"conflict_detected": False, "conflict_type": None, "reason": ""}


class ActionCooldown:
    """
    Enforce cooldown periods between repeated actions.
    Prevents rapid-fire accidental clicks or loops.
    """

    DEFAULT_COOLDOWNS = {
        "pause": 2.0,
        "start": 2.0,
        "stop": 3.0,
        "dispatch": 5.0,
        "merge": 10.0,
        "push": 10.0,
    }

    def __init__(self, repo_root: Path = None, custom_cooldowns: Dict[str, float] = None):
        self.repo_root = repo_root or Path(__file__).parent.parent.parent
        self.cooldowns = {**self.DEFAULT_COOLDOWNS, **(custom_cooldowns or {})}
        self.last_executed: Dict[str, float] = {}

    def can_execute(self, action: str) -> Dict[str, Any]:
        """
        Check if action can be executed (cooldown elapsed).
        
        Returns dict with:
        - can_execute: bool
        - remaining_cooldown: float (0 if can execute)
        - cooldown_period: float
        """
        action = action.lower()
        cooldown = self.cooldowns.get(action, 0.0)
        now = time.time()
        last = self.last_executed.get(action, 0.0)
        remaining = max(0.0, cooldown - (now - last))

        if remaining > 0:
            logger.warning(f"Action {action} on cooldown: {remaining:.1f}s remaining")
            return {
                "can_execute": False,
                "remaining_cooldown": remaining,
                "cooldown_period": cooldown,
            }

        return {
            "can_execute": True,
            "remaining_cooldown": 0.0,
            "cooldown_period": cooldown,
        }

    def record_execution(self, action: str):
        """Record that an action was executed."""
        self.last_executed[action.lower()] = time.time()
        logger.debug(f"Cooldown recorded for {action}")


class CriticalActionAudit:
    """
    Audit log for all critical actions.
    Provides non-repudiable record for governance review.
    """

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path(__file__).parent.parent.parent
        self.audit_file = self.repo_root / "automation" / "control" / "critical_action_audit.jsonl"

    def log(self, action: str, actor: str, result: str, details: Dict[str, Any] = None):
        """Append an audit entry."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "actor": actor,
            "result": result,
            "details": details or {},
        }
        try:
            self.audit_file.parent.mkdir(parents=True, exist_ok=True)
            with self.audit_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def read_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Read recent audit entries."""
        if not self.audit_file.exists():
            return []
        try:
            with self.audit_file.open("r", encoding="utf-8") as f:
                lines = f.readlines()
            entries = [json.loads(line) for line in lines if line.strip()]
            return entries[-limit:]
        except Exception as e:
            logger.warning(f"Failed to read audit log: {e}")
            return []
