"""
R021 Important Settings Lock

Provides protection for important system settings:
- Settings whitelist with lock status
- Unauthorized change blocking
- Authorized unlock flow
- Complete audit trail

This protects critical configurations from accidental or malicious modification.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("settings_lock")


class SettingsLock:
    """Protect important settings from unauthorized modification."""

    DEFAULT_PROTECTED_SETTINGS = {
        "chain_status": "locked",
        "current_round": "locked",
        "last_completed_round": "locked",
        "auto_run": "locked",
        "chain_control.status": "locked",
        "phase_state": "locked",
        "execution_authorized": "locked",
    }

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or Path(__file__).parent.parent.parent
        self.state_file = self.repo_root / "automation" / "control" / "settings_lock_state.json"
        self.audit_file = self.repo_root / "automation" / "control" / "settings_lock_audit.jsonl"
        self._load_state()

    def _load_state(self):
        if self.state_file.exists():
            try:
                with self.state_file.open("r", encoding="utf-8") as f:
                    self.state = json.load(f)
            except Exception:
                self.state = {"protected_settings": {}, "unlock_history": []}
        else:
            self.state = {"protected_settings": {}, "unlock_history": []}

    def _save_state(self):
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with self.state_file.open("w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save settings lock state: {e}")

    def can_modify(self, setting: str) -> bool:
        """Check if a setting can be modified without authorization."""
        return self.state.get("protected_settings", {}).get(setting, "unlocked") != "locked"

    def lock_setting(self, setting: str, locked: bool = True):
        """Lock or unlock a specific setting."""
        status = "locked" if locked else "unlocked"
        self.state["protected_settings"][setting] = status
        self._save_state()
        logger.info(f"Setting '{setting}' is now {status}")

    def is_locked(self, setting: str) -> bool:
        """Check if a setting is currently locked."""
        return self.state.get("protected_settings", {}).get(setting, "unlocked") == "locked"

    def request_unlock(self, setting: str, reason: str = "") -> Dict[str, Any]:
        """Request authorization to unlock a setting."""
        if not self.is_locked(setting):
            return {"unlock_allowed": True, "reason": "Setting is not locked"}

        unlock_token = f"unlock_{setting}_{int(time.time() * 1000)}"
        self.state["pending_unlocks"] = self.state.get("pending_unlocks", {})
        self.state["pending_unlocks"][unlock_token] = {
            "setting": setting,
            "reason": reason,
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "confirmed": False,
        }
        self._save_state()

        return {
            "unlock_allowed": False,
            "unlock_token": unlock_token,
            "reason": f"Setting '{setting}' is locked. Authorization required.",
        }

    def confirm_unlock(self, unlock_token: str) -> Dict[str, Any]:
        """Confirm an unlock request."""
        pending = self.state.get("pending_unlocks", {}).get(unlock_token)
        if not pending:
            return {"confirmed": False, "error": "Invalid token"}

        if pending.get("confirmed"):
            return {"confirmed": False, "error": "Token already used"}

        setting = pending["setting"]
        pending["confirmed"] = True
        pending["confirmed_at"] = datetime.now(timezone.utc).isoformat()

        self.state["protected_settings"][setting] = "unlocked"
        self.state["unlock_history"] = self.state.get("unlock_history", [])
        self.state["unlock_history"].append({
            "setting": setting,
            "token": unlock_token,
            "reason": pending.get("reason", ""),
            "unlocked_at": pending["confirmed_at"],
        })

        del self.state["pending_unlocks"][unlock_token]
        self._save_state()
        self._audit(setting, "unlock", "authorized", {"token": unlock_token})

        logger.info(f"Setting '{setting}' unlocked via token {unlock_token}")
        return {"confirmed": True, "setting": setting}

    def _audit(self, setting: str, action: str, result: str, details: Dict[str, Any] = None):
        """Write audit record."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "setting": setting,
            "action": action,
            "result": result,
            "details": details or {},
        }
        try:
            self.audit_file.parent.mkdir(parents=True, exist_ok=True)
            with self.audit_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit: {e}")

    def get_audit_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent audit entries."""
        if not self.audit_file.exists():
            return []
        try:
            with self.audit_file.open("r", encoding="utf-8") as f:
                lines = f.readlines()
            entries = [json.loads(line) for line in lines if line.strip()]
            return entries[-limit:]
        except Exception:
            return []

    def validate_modification(self, setting: str, proposed_value: Any = None) -> Dict[str, Any]:
        """
        Validate if a setting modification is allowed.
        Returns dict with:
        - allowed: bool
        - reason: str
        """
        if self.is_locked(setting):
            self._audit(setting, "modify_attempt", "blocked", {"proposed_value": proposed_value})
            return {
                "allowed": False,
                "reason": f"Setting '{setting}' is locked. Use request_unlock() first.",
            }

        self._audit(setting, "modify_allowed", "allowed", {"proposed_value": proposed_value})
        return {"allowed": True, "reason": ""}


def get_settings_lock(repo_root: Path = None) -> SettingsLock:
    """Factory function to get SettingsLock instance."""
    return SettingsLock(repo_root)