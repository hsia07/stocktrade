"""
TelegramInboundStub — test wrapper for Telegram inbound hardening.
Mirrors TelegramInboundReceiver hardening logic without real API calls.
"""

import json
import time
import yaml
import os


class TelegramInboundStub:
    def __init__(self, token=None, chat_id=None, repo_root=None):
        self.token = token or "test_token"
        self.chat_id = chat_id or "test_chat"
        self.repo_root = repo_root or os.getcwd()
        self._last_command_result = None

    def _get_chat_id_from_update(self, update):
        mes = update.get("message") if isinstance(update, dict) else None
        if not mes:
            return None
        chat = mes.get("chat") if isinstance(mes, dict) else None
        if not chat:
            return None
        return str(chat.get("id", ""))

    def _is_authorized_chat(self, update):
        actual = self._get_chat_id_from_update(update)
        return actual == self.chat_id

    def _get_current_round_state(self):
        manifest_path = os.path.join(self.repo_root, "manifests", "current_round.yaml")
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = yaml.safe_load(f) or {}
            return manifest.get("current_round", "NONE")
        except Exception:
            return "UNKNOWN"

    def _has_defined_round(self):
        round_state = self._get_current_round_state()
        if round_state in ("NONE", "UNKNOWN", "law_undefined", "undefined"):
            return False
        if not round_state:
            return False
        return True

    def parse_update(self, update):
        mes = update.get("message") if isinstance(update, dict) else None
        if not mes:
            return None
        text = mes.get("text") if isinstance(mes, dict) else None
        if not text or not text.startswith("/"):
            return None
        cmd = text.split()[0].lower()

        is_auth = self._is_authorized_chat(update)

        if cmd == "/pause":
            if not is_auth:
                self._last_command_result = "rejected"
                return None
            self._last_command_result = "paused"
            return "/pause"

        if cmd == "/start":
            if not is_auth:
                self._last_command_result = "rejected"
                return None
            if not self._has_defined_round():
                self._last_command_result = "blocked_no_round"
                return None
            self._last_command_result = "started"
            return "/start"

        if cmd == "/status":
            if not is_auth:
                self._last_command_result = "rejected"
                return None
            self._last_command_result = "status_emitted"
            return "/status"

        return None

    def get_last_command_result(self):
        return self._last_command_result
