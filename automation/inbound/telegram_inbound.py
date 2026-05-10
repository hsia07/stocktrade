"""
Telegram inbound receiver wiring (polling-based).
This module provides a minimal, testable inbound receiver that polls the
Telegram Bot API for updates and parses /pause, /start, and /status commands.
It includes chat identity verification, unauthorized rejection with audit,
and undefined-round hard gate for /start.
"""

import os
import time
import json
import threading
import logging
import requests
from datetime import datetime
from pathlib import Path

from automation.control.pause_state import PauseStateManager

logger = logging.getLogger("telegram_inbound")


class TelegramInboundReceiver:
    def __init__(self, repo_root=None, use_mock=False):
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.use_mock = use_mock
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        self.enabled = all([self.token, self.chat_id]) and not self.use_mock
        self._stop = False
        self._thread = None
        self._start_time = time.time()
        self._pause_manager = PauseStateManager(self.repo_root)
        self._callback = None
        self._last_audit_event = None
        self._last_command_result = None

    def set_callback(self, cb):
        self._callback = cb

    def start(self):
        if not self.enabled:
            logger.info("Telegram inbound not enabled (missing credentials or mock)")
            return
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("Telegram inbound polling started")

    def stop(self):
        self._stop = True
        if self._thread:
            self._thread.join(timeout=2)

    def _poll_loop(self):
        while not self._stop:
            try:
                updates = self._fetch_updates()
                if updates:
                    for up in updates:
                        self._process_update(up)
            except Exception as e:
                logger.exception("Error in Telegram inbound polling: %s", e)
            time.sleep(2.0)

    def _fetch_updates(self):
        if self.use_mock:
            return None
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        try:
            resp = requests.post(url, json={"timeout": 30, "allowed_updates": ["message"]}, timeout=35)
            if resp.status_code != 200:
                return None
            data = resp.json()
            results = data.get("result", [])
            return results[-5:] if results else []
        except Exception:
            return None

    def _get_chat_id_from_update(self, update):
        mes = update.get("message") if isinstance(update, dict) else None
        if not mes:
            return None
        chat = mes.get("chat") if isinstance(mes, dict) else None
        if not chat:
            return None
        return str(chat.get("id", ""))

    def _is_authorized_chat(self, update):
        if self.use_mock:
            return True
        if not self.chat_id:
            return False
        actual = self._get_chat_id_from_update(update)
        if not actual:
            return False
        return actual == self.chat_id

    def _get_current_round_state(self):
        manifest_path = self.repo_root / "manifests" / "current_round.yaml"
        try:
            import yaml
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

    def _process_update(self, update):
        mes = update.get("message") if isinstance(update, dict) else None
        if not mes:
            return
        text = mes.get("text") if isinstance(mes, dict) else None
        if not text or not text.startswith("/"):
            return
        cmd = text.split()[0].lower()

        if cmd not in {"/pause", "/start", "/status"}:
            return

        if not self._is_authorized_chat(update):
            self._reject_unauthorized(cmd, update)
            return

        if cmd == "/status":
            self._handle_status(update)
        elif cmd == "/pause":
            self._handle_command("/pause", update)
        elif cmd == "/start":
            if not self._has_defined_round():
                self._emit_inbound_return("start_blocked_no_round", update, extra={"blocked_reason": "undefined_round"})
                self._last_command_result = "blocked_no_round"
                return
            self._handle_command("/start", update)

    def _reject_unauthorized(self, cmd, update):
        logger.warning("Unauthorized chat attempted command: %s", cmd)
        self._emit_inbound_return("unauthorized_rejected", update, extra={"rejected_command": cmd})
        self._last_command_result = "rejected"

    def _handle_status(self, update):
        state = self._build_status_state()
        self._emit_inbound_return("/status", update, extra={"status_state": state})
        self._last_command_result = "status_emitted"

    def _build_status_state(self):
        pause_info = self._pause_manager.get_pause_info() if self._pause_manager else None
        is_paused = self._pause_manager.is_paused() if self._pause_manager else False
        current_round = self._get_current_round_state()
        uptime = time.time() - self._start_time
        return {
            "paused": is_paused,
            "pause_info": pause_info,
            "current_round": current_round,
            "has_defined_round": self._has_defined_round(),
            "uptime_seconds": int(uptime),
            "enabled": self.enabled,
        }

    def _handle_command(self, cmd, update):
        if not self._pause_manager:
            return
        if cmd == "/pause":
            self._pause_manager.set_pause("inbound_interaction")
            self._emit_inbound_return(cmd, update)
            self._last_command_result = "paused"
        elif cmd == "/start":
            self._pause_manager.clear_pause()
            self._emit_inbound_return(cmd, update)
            self._last_command_result = "started"

    def _emit_inbound_return(self, cmd, update, extra=None):
        state = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "inbound_command": cmd,
            "update_id": update.get("update_id") if isinstance(update, dict) else None,
        }
        if extra:
            state["extra"] = extra
        out_dir = self.repo_root / "automation" / "control" / "inbound_returns"
        os.makedirs(out_dir, exist_ok=True)
        path = out_dir / f"inbound_return_{int(time.time())}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        self._last_audit_event = state
        if self._callback:
            try:
                self._callback(cmd, update)
            except Exception:
                pass
