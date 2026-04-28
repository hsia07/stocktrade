"""
PHASE2 API Automode - C3 Slice 1+: Unified Runtime Loop with
Construction Bootstrap, Telegram Phase Notify, and Pause/Start Semantics

This is a MOCK runtime loop for the OpenAI + Telegram dual-provider
orchestration system. It contains NO real OpenAI or Telegram API calls
except for minimal authorized status notifications.

Acceptance Criteria:
1. New round dispatch enters construction bootstrap when no candidate exists
2. Telegram notifications sent on phase transitions
3. /pause generates full RETURN_TO_CHATGPT and writes to output channel
4. /start resumes from structured state, rejects when frozen/gated
5. STOP_NOW.flag causes clean exit within <= 5s
"""

import os
import sys
import time
import json
import signal
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

# Slice 3 integration: queue available for future message-driven processing
try:
    from automation.runtime.queue import MessageQueue
    from automation.runtime.dlq import DLQManager
except ImportError:
    MessageQueue = None
    DLQManager = None

# Slice 4 integration: idempotency and audit trail available
try:
    from automation.runtime.idempotency import IdempotencyManager
    from automation.runtime.audit_trail import AuditTrailManager
except ImportError:
    IdempotencyManager = None
    AuditTrailManager = None

# Control plane integration
try:
    from automation.control.pause_state import PauseStateManager
    from automation.control.auto_advance import AutoAdvanceController
    from automation.control.status_reporter import StatusReporter
    from automation.control.status_scheduler import StatusScheduler
    from automation.control.phase_state import RoundPhase
    from automation.control.candidate_checker import CandidateChecker
    from automation.control.return_report import ReturnReportGenerator
except ImportError:
    PauseStateManager = None
    AutoAdvanceController = None
    StatusReporter = None
    StatusScheduler = None
    RoundPhase = None
    CandidateChecker = None
    ReturnReportGenerator = None

# R020 User Error Protection integration
try:
    from automation.control.user_error_protection import (
        ActionConfirmationGuard,
        ConflictDetector,
        ActionCooldown,
        CriticalActionAudit,
    )
except ImportError:
    ActionConfirmationGuard = None
    ConflictDetector = None
    ActionCooldown = None
    CriticalActionAudit = None

# Configuration
REPO_ROOT = Path(__file__).parent.parent.parent
STOP_NOW_FLAG = REPO_ROOT / "automation" / "control" / "STOP_NOW.flag"
MANIFEST_PATH = REPO_ROOT / "manifests" / "current_round.yaml"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
TICK_INTERVAL = 2.0
STOP_CHECK_INTERVAL = 0.5

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("api_automode_loop")


class AutomodeRuntimeLoop:
    """Mock unified runtime loop with construction bootstrap and phase tracking."""

    def __init__(self):
        self._running = False
        self._shutdown_requested = False
        self._tick_count = 0
        self._start_time: Optional[float] = None
        self._stop_time: Optional[float] = None
        self._current_phase = RoundPhase.NONE if RoundPhase else "none"
        self._current_round = "NONE"
        self._connection_failures = 0
        self._max_failures = 3
        self._metrics: Dict[str, Any] = {
            "ticks": 0,
            "mock_work_items": 0,
            "mock_dispatches": 0,
            "errors": 0,
            "start_time": None,
            "stop_time": None,
            "phase_transitions": [],
        }
        self._queue = MessageQueue() if MessageQueue else None
        self._dlq = DLQManager() if DLQManager else None
        self._idempotency = IdempotencyManager() if IdempotencyManager else None
        self._audit_trail = AuditTrailManager() if AuditTrailManager else None
        self._pause_manager = PauseStateManager(REPO_ROOT) if PauseStateManager else None
        self._scheduler = StatusScheduler(REPO_ROOT) if StatusScheduler else None
        # R020 User Error Protection guards
        self._confirmation_guard = ActionConfirmationGuard(REPO_ROOT) if ActionConfirmationGuard else None
        self._conflict_detector = ConflictDetector(REPO_ROOT) if ConflictDetector else None
        self._action_cooldown = ActionCooldown(REPO_ROOT) if ActionCooldown else None
        self._critical_audit = CriticalActionAudit(REPO_ROOT) if CriticalActionAudit else None
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        logger.info("Signal handlers registered for SIGINT and SIGTERM")

    def _signal_handler(self, signum, frame):
        sig_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        logger.info(f"Received {sig_name}, requesting graceful shutdown...")
        self._shutdown_requested = True

    def _protect_critical_action(self, action: str, confirmation_token: str = "", context: str = "") -> Dict[str, Any]:
        """
        R020 User Error Protection: Validate critical action before execution.
        
        Checks (in order):
        1. ActionCooldown - has enough time elapsed since last execution?
        2. ConflictDetector - does this action conflict with recent history?
        3. ActionConfirmationGuard - is confirmation provided for critical actions?
        4. CriticalActionAudit - log the action attempt
        
        Returns dict with:
        - allowed: bool
        - reason: str
        - confirmation_required: bool
        - confirmation_token: str
        """
        if not any([self._confirmation_guard, self._conflict_detector, self._action_cooldown, self._critical_audit]):
            # Guards not available - allow (fail-open for missing module, but log)
            return {"allowed": True, "reason": "", "confirmation_required": False, "confirmation_token": ""}

        # 1. Cooldown check
        if self._action_cooldown:
            cooldown_result = self._action_cooldown.can_execute(action)
            if not cooldown_result["can_execute"]:
                self._audit_action(action, "blocked_cooldown", {"remaining_cooldown": cooldown_result["remaining_cooldown"]})
                return {
                    "allowed": False,
                    "reason": f"Action '{action}' on cooldown: {cooldown_result['remaining_cooldown']:.1f}s remaining",
                    "confirmation_required": False,
                    "confirmation_token": "",
                }

        # 2. Conflict detection
        if self._conflict_detector:
            conflict_result = self._conflict_detector.detect_conflict(action)
            if conflict_result["conflict_detected"]:
                self._audit_action(action, "blocked_conflict", {"conflict_type": conflict_result["conflict_type"]})
                return {
                    "allowed": False,
                    "reason": conflict_result["reason"],
                    "confirmation_required": False,
                    "confirmation_token": "",
                }

        # 3. Confirmation check for critical actions
        if self._confirmation_guard and self._confirmation_guard.is_critical(action):
            if not confirmation_token:
                req = self._confirmation_guard.request_confirmation(action, context)
                self._audit_action(action, "blocked_missing_confirmation", {"context": context})
                return {
                    "allowed": False,
                    "reason": req["warning_message"],
                    "confirmation_required": True,
                    "confirmation_token": req["confirmation_token"],
                }
            if not self._confirmation_guard.check_confirmed(confirmation_token):
                self._audit_action(action, "blocked_invalid_token", {"token": confirmation_token})
                return {
                    "allowed": False,
                    "reason": f"Confirmation token '{confirmation_token}' not confirmed or invalid",
                    "confirmation_required": True,
                    "confirmation_token": confirmation_token,
                }

        # Action is allowed - record execution and audit
        if self._action_cooldown:
            self._action_cooldown.record_execution(action)
        if self._conflict_detector:
            self._conflict_detector.record_action(action, "allowed")
        self._audit_action(action, "allowed", {"context": context})

        return {"allowed": True, "reason": "", "confirmation_required": False, "confirmation_token": ""}

    def _audit_action(self, action: str, result: str, details: Dict[str, Any] = None):
        """R020: Log critical action to audit trail."""
        if self._critical_audit:
            self._critical_audit.log(action, "api_automode_loop", result, details or {})

    def _check_stop_now(self) -> bool:
        return STOP_NOW_FLAG.exists()

    def _check_pause(self) -> bool:
        if self._pause_manager:
            return self._pause_manager.is_paused()
        return False

    def _transition_phase(self, new_phase: str, round_id: str = "", extra: str = ""):
        """Transition to a new phase and log/notify."""
        old_phase = self._current_phase
        if old_phase == new_phase:
            return
        self._current_phase = new_phase
        self._metrics["phase_transitions"].append({
            "from": old_phase,
            "to": new_phase,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Phase transition: {old_phase} -> {new_phase} (round={round_id})")

        # Send Telegram notification for key phases
        if self._scheduler and RoundPhase:
            if new_phase in {
                RoundPhase.ROUND_ENTERED.value,
                RoundPhase.CONSTRUCTION_BOOTSTRAP.value,
                RoundPhase.CONSTRUCTION_IN_PROGRESS.value,
                RoundPhase.CANDIDATE_MATERIALIZING.value,
                RoundPhase.STOPPED.value,
            }:
                try:
                    result = self._scheduler.notify_phase_transition(new_phase, round_id or self._current_round, extra)
                    if not result.get("success"):
                        logger.warning(f"Telegram phase notify failed: {result.get('error')}")
                except Exception as e:
                    logger.warning(f"Phase notify exception: {e}")

    def _load_manifest_state(self) -> Dict[str, Any]:
        """Load minimal state from current_round.yaml."""
        try:
            import yaml
            if MANIFEST_PATH.exists():
                with MANIFEST_PATH.open("r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load manifest: {e}")
        return {}

    def _save_manifest_state(self, updates: Dict[str, Any]):
        """Save updates to current_round.yaml (minimal safe write)."""
        try:
            import yaml
            state = self._load_manifest_state()
            state.update(updates)
            with MANIFEST_PATH.open("w", encoding="utf-8") as f:
                yaml.safe_dump(state, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")

    def _dispatch_next_round(self, confirmation_token: str = "") -> Dict[str, Any]:
        """
        Dispatch the next round if current_round is NONE.

        Returns dispatch result dict.
        """
        # R020 protection: validate dispatch action
        protection = self._protect_critical_action("dispatch", confirmation_token, "Round dispatch from runtime loop")
        if not protection["allowed"]:
            logger.warning(f"Dispatch blocked by user error protection: {protection['reason']}")
            return {"dispatched": False, "reason": protection["reason"], "confirmation_required": protection["confirmation_required"], "confirmation_token": protection["confirmation_token"]}

        manifest = self._load_manifest_state()
        current_round = manifest.get("current_round", "NONE")
        next_round = manifest.get("next_round_to_dispatch", "")

        if current_round != "NONE" or not next_round:
            return {"dispatched": False, "reason": "no_dispatch_needed"}

        # Update manifest: dispatch next round
        self._save_manifest_state({
            "current_round": next_round,
            "phase_state": RoundPhase.ROUND_ENTERED.value if RoundPhase else "round_entered",
        })
        self._current_round = next_round
        self._transition_phase(
            RoundPhase.ROUND_ENTERED.value if RoundPhase else "round_entered",
            next_round,
            "Round dispatched from structured state",
        )
        logger.info(f"Dispatched round {next_round}")

        # Check if candidate exists
        if CandidateChecker:
            checker = CandidateChecker(REPO_ROOT)
            candidate_info = checker.check_candidate_exists(next_round)
            if candidate_info.get("exists"):
                logger.info(f"Candidate found for {next_round}: {candidate_info['branch']}")
                self._transition_phase(
                    RoundPhase.CANDIDATE_READY.value if RoundPhase else "candidate_ready",
                    next_round,
                )
                return {"dispatched": True, "round": next_round, "candidate_exists": True}
            else:
                logger.info(f"No candidate for {next_round}; entering construction")
                # Enter construction bootstrap, then immediately progress to in-progress
                self._save_manifest_state({
                    "phase_state": RoundPhase.CONSTRUCTION_BOOTSTRAP.value if RoundPhase else "construction_bootstrap",
                })
                self._transition_phase(
                    RoundPhase.CONSTRUCTION_BOOTSTRAP.value if RoundPhase else "construction_bootstrap",
                    next_round,
                    "No materialized candidate; entering construction bootstrap",
                )
                # Progress to construction_in_progress immediately
                self._enter_construction_in_progress(next_round)
                return {"dispatched": True, "round": next_round, "candidate_exists": False, "construction_in_progress": True}

        return {"dispatched": True, "round": next_round, "candidate_exists": False}

    def _enter_construction_in_progress(self, round_id: str):
        """
        Enter construction_in_progress phase. This is the active working state
        where the agent builds the candidate. Not a terminal stop.
        """
        self._save_manifest_state({
            "phase_state": RoundPhase.CONSTRUCTION_IN_PROGRESS.value if RoundPhase else "construction_in_progress",
        })
        self._transition_phase(
            RoundPhase.CONSTRUCTION_IN_PROGRESS.value if RoundPhase else "construction_in_progress",
            round_id,
            "Candidate construction in progress; agent may begin implementation",
        )
        logger.info(f"Round {round_id} now in construction_in_progress; bootstrap context active")

    def _handle_pause(self, confirmation_token: str = "") -> Dict[str, Any]:
        """
        Handle PAUSE.flag: safe stop, generate full RETURN_TO_CHATGPT.

        Returns pause result dict.
        """
        if not self._pause_manager:
            return {"paused": False, "reason": "pause_manager_not_available"}

        if not self._pause_manager.is_paused():
            return {"paused": False, "reason": "not_paused"}

        # R020 protection: validate pause action
        protection = self._protect_critical_action("pause", confirmation_token, "Pause from PAUSE.flag")
        if not protection["allowed"]:
            logger.warning(f"Pause blocked by user error protection: {protection['reason']}")
            return {"paused": False, "reason": protection["reason"], "blocked": True, "confirmation_required": protection["confirmation_required"], "confirmation_token": protection["confirmation_token"]}

        logger.info("PAUSE.flag detected - initiating safe stop")

        # Build structured state
        state = {}
        if self._scheduler:
            state = self._scheduler.build_state()

        # Generate full RETURN_TO_CHATGPT
        report = ""
        if ReturnReportGenerator:
            generator = ReturnReportGenerator(REPO_ROOT)
            report = generator.generate_pause_report(state, pause_reason="pause_flag_active")
            generator.write_report(report, filename="LATEST_PAUSE_RETURN_TO_CHATGPT.txt")
            logger.info("Full RETURN_TO_CHATGPT pause report generated")

        # Send Telegram pause notification
        if self._scheduler:
            try:
                self._scheduler.notify_phase_transition(
                    RoundPhase.STOPPED.value if RoundPhase else "stopped",
                    self._current_round,
                    f"Paused: {state.get('stop_reason', 'manual_pause_requested')}",
                )
            except Exception as e:
                logger.warning(f"Telegram pause notify failed: {e}")

        self._transition_phase(
            RoundPhase.STOPPED.value if RoundPhase else "stopped",
            self._current_round,
        )

        return {
            "paused": True,
            "reason": state.get("stop_reason", "pause_flag_active"),
            "report_written": bool(report),
            "report_path": str(REPO_ROOT / "automation" / "control" / "LATEST_PAUSE_RETURN_TO_CHATGPT.txt"),
        }

    def _log_control_state(self):
        if PauseStateManager and AutoAdvanceController and StatusReporter:
            logger.info("Auto-advance control layer: ACTIVE")
            logger.info("Pause state: %s", "PAUSED" if self._check_pause() else "RUNNING")
            self._report_status()
        else:
            logger.debug("Auto-advance control layer: not loaded")

    def _report_status(self):
        if not StatusReporter:
            return
        try:
            reporter = StatusReporter(REPO_ROOT)
            state = {
                "current_round": self._current_round,
                "next_round": "awaiting_dispatch",
                "auto_advanced": False,
                "stop_reason": "",
                "stop_gate_type": "",
                "evidence_complete": False,
                "candidate_branch": "",
                "candidate_commit": "",
                "awaiting_review": False,
                "lane_frozen": False,
            }
            summary = reporter.generate_summary(state)
            formatted = reporter.format_for_telegram(summary)
            logger.info("Status report:\n%s", formatted)
        except Exception as e:
            logger.warning("Status report generation failed: %s", e)

    def _mock_construction_work(self):
        """Mock construction work during bootstrap phase."""
        self._tick_count += 1
        logger.info(
            f"Construction work: tick={self._tick_count}, "
            f"round={self._current_round}, phase=construction_in_progress"
        )

    def _mock_generate_work_item(self) -> Optional[Dict[str, Any]]:
        self._tick_count += 1
        return {
            "tick": self._tick_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": "mock_openai",
            "status": "mock_generated",
            "content_hash": f"mock_hash_{self._tick_count}",
        }

    def _mock_dispatch(self, work_item: Dict[str, Any]) -> bool:
        logger.debug(f"Mock dispatch: tick={work_item['tick']}, provider=mock_telegram")
        return True

    def _process_tick(self):
        try:
            if self._check_stop_now():
                # R020 protection: validate stop action
                protection = self._protect_critical_action("stop", "", "STOP_NOW.flag triggered")
                if not protection["allowed"]:
                    logger.warning(f"Stop blocked by user error protection: {protection['reason']}")
                    # Do not shutdown; continue ticking
                    self._metrics["ticks"] = self._tick_count
                    return
                logger.info("STOP_NOW.flag detected, initiating clean shutdown")
                self._shutdown_requested = True
                return

            # 0. Check connection failures (Phase A)
            if self._connection_failures >= self._max_failures:
                logger.warning(f"Connection failures reached {self._max_failures}, entering paused_after_failure")
                if self._pause_manager:
                    checkpoint_data = {
                        "checkpoint_version": "1.0",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "round_id": self._current_round,
                        "current_step": "paused_after_failure",
                        "phase": self._current_phase if isinstance(self._current_phase, str) else str(self._current_phase),
                        "pause_reason": "paused_after_failure",
                        "connection_failures": self._connection_failures,
                        "recoverable": False
                    }
                    self._pause_manager.set_pause(reason="paused_after_failure", checkpoint_data=checkpoint_data)
                return

            # 1. Handle pause
            pause_result = self._handle_pause()
            if pause_result.get("paused"):
                logger.info("Loop paused by PAUSE.flag; entering idle ticks")
                # In paused mode we still tick but do no work
                self._metrics["ticks"] = self._tick_count
                return
            if pause_result.get("blocked"):
                # R020: pause was blocked by protection; continue normal operation
                logger.warning(f"Pause blocked: {pause_result.get('reason')}")

            # 2. Dispatch next round if needed
            manifest = self._load_manifest_state()
            if manifest.get("current_round", "NONE") == "NONE" and manifest.get("next_round_to_dispatch"):
                dispatch_result = self._dispatch_next_round()
                if dispatch_result.get("confirmation_required"):
                    # R020: dispatch needs confirmation; skip this tick
                    logger.warning(f"Dispatch requires confirmation: {dispatch_result.get('confirmation_token')}")
                    self._metrics["ticks"] = self._tick_count
                    return
                if dispatch_result.get("dispatched") and dispatch_result.get("construction_in_progress"):
                    # In construction_in_progress: we continue to construction work below
                    logger.info("In construction_in_progress; continuing with bootstrap work")
                elif dispatch_result.get("dispatched") and not dispatch_result.get("candidate_exists", True):
                    # Fallback for old bootstrap path (should not happen with new logic)
                    logger.info("In construction bootstrap; waiting for candidate materialization")
                    self._metrics["ticks"] = self._tick_count
                    return

            # 3. Check if we are in construction_in_progress and should do bootstrap work
            manifest = self._load_manifest_state()
            current_phase = manifest.get("phase_state", "")
            if current_phase == (RoundPhase.CONSTRUCTION_IN_PROGRESS.value if RoundPhase else "construction_in_progress"):
                # In construction phase: perform mock construction work instead of normal work
                self._mock_construction_work()
                self._metrics["ticks"] = self._tick_count
                return

            # 4. Normal mock work
            work_item = self._mock_generate_work_item()
            if work_item:
                self._metrics["mock_work_items"] += 1
                success = self._mock_dispatch(work_item)
                if success:
                    self._metrics["mock_dispatches"] += 1

            self._metrics["ticks"] = self._tick_count

        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Error in tick {self._tick_count}: {e}")

    def start(self, confirmation_token: str = ""):
        self._start_time = time.time()
        self._running = True
        self._metrics["start_time"] = datetime.now(timezone.utc).isoformat()

        # R020 protection: validate start action
        protection = self._protect_critical_action("start", confirmation_token, "Runtime loop start")
        if not protection["allowed"]:
            logger.error(f"Start blocked by user error protection: {protection['reason']}")
            self._running = False
            return {"started": False, "reason": protection["reason"], "confirmation_required": protection["confirmation_required"], "confirmation_token": protection["confirmation_token"]}

        logger.info("=" * 60)
        logger.info("API AUTOMODE RUNTIME LOOP - WITH CONSTRUCTION BOOTSTRAP")
        logger.info("=" * 60)
        logger.info(f"STOP_NOW flag path: {STOP_NOW_FLAG}")
        logger.info(f"Tick interval: {TICK_INTERVAL}s")
        logger.info("NO REAL OpenAI/Telegram business calls in this loop")
        logger.info("R020 User Error Protection: ACTIVE")
        logger.info("=" * 60)
        self._log_control_state()
        logger.info("=" * 60)
        logger.info("Loop started")

        try:
            while self._running and not self._shutdown_requested:
                self._process_tick()

                if self._shutdown_requested:
                    break

                slept = 0.0
                while slept < TICK_INTERVAL and not self._shutdown_requested:
                    time.sleep(STOP_CHECK_INTERVAL)
                    slept += STOP_CHECK_INTERVAL
                    if self._check_stop_now():
                        logger.info("STOP_NOW.flag detected during sleep")
                        self._shutdown_requested = True
                        break

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received")
            self._shutdown_requested = True

        finally:
            self._shutdown()

    def _shutdown(self):
        self._running = False
        self._stop_time = time.time()
        self._metrics["stop_time"] = datetime.now(timezone.utc).isoformat()

        runtime = 0.0
        if self._start_time:
            runtime = self._stop_time - self._start_time

        logger.info("=" * 60)
        logger.info("SHUTDOWN COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total runtime: {runtime:.2f}s")
        logger.info(f"Total ticks: {self._tick_count}")
        logger.info(f"Mock work items: {self._metrics['mock_work_items']}")
        logger.info(f"Mock dispatches: {self._metrics['mock_dispatches']}")
        logger.info(f"Errors: {self._metrics['errors']}")
        logger.info("=" * 60)

        metrics_file = REPO_ROOT / "automation" / "runtime" / "slice1_metrics.json"
        try:
            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump(self._metrics, f, indent=2)
            logger.info(f"Metrics written to {metrics_file}")
        except Exception as e:
            logger.error(f"Failed to write metrics: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        return self._metrics.copy()


def main():
    loop = AutomodeRuntimeLoop()
    loop.start()
    return 0


if __name__ == "__main__":
    sys.exit(main())
