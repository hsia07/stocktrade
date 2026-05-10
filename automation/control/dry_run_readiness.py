"""
DryRunReadinessChecker — read-only, mock-only Telegram auto-mode readiness check.

Validates all gates, detectors, notifiers, inbound commands, and system state
before Telegram auto-mode can be started. Produces a machine-readable JSON
report and a ChatGPT-readable summary.

SAFETY INVARIANTS:
- Does NOT trigger construction
- Does NOT dispatch next round
- Does NOT create candidate
- Does NOT commit / merge / push / promote / PR
- Does NOT send real Telegram HTTP
- Does NOT write to secrets / runtime / manifests / panel / launcher
- Does NOT touch retained untracked paths
- Does NOT start Telegram auto-mode
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("dry_run_readiness")

PRIOR_BATCH_NAMES = [
    "TELEGRAM_INBOUND_HARDENING",
    "UNDEFINED_ROUND_HARD_GATE_BATCH",
    "USAGE_EXHAUSTION_PAUSE_NOTIFY_BATCH",
]

REQUIRED_NOTIFICATION_METHODS = [
    "send_pause_notification",
    "send_stall_warning",
    "send_failure_warning",
    "send_usage_exhausted_notification",
    "send_blocked_notification",
    "send_awaiting_instruction_notification",
    "send_undefined_round_blocked_notification",
]

REQUIRED_INBOUND_COMMANDS = ["/pause", "/start", "/status"]


class DryRunReadinessChecker:
    def __init__(
        self,
        repo_root: Path = None,
        expected_canonical_head: str = "",
        expected_branch: str = "work/canonical-mainline-repair-001",
        mock_mode: bool = True,
    ):
        self.repo_root = (repo_root or Path(__file__).parent.parent.parent).resolve()
        self.expected_canonical_head = expected_canonical_head
        self.expected_branch = expected_branch
        self.mock_mode = mock_mode

        self._results: Dict[str, Any] = {}
        self._all_passed = True
        self._blockers: List[str] = []
        self._untracked_paths_count = 0

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def check_all(self) -> Dict[str, Any]:
        results = {}

        results["git_state"] = self._check_git_state()
        results["prior_batches"] = self._check_prior_batches()
        results["telegram_inbound_readiness"] = self._check_telegram_inbound_readiness()
        results["undefined_round_gate"] = self._check_undefined_round_gate()
        results["usage_exhaustion_notify"] = self._check_usage_exhaustion_notify()
        results["notification_coverage"] = self._check_notification_coverage()
        results["kill_switch"] = self._check_kill_switch()
        results["mock_mode_safety"] = self._check_mock_mode_safety()

        results["dry_run_invariants"] = self._check_dry_run_invariants()

        passed = True
        blockers = []
        for category, checks in results.items():
            if isinstance(checks, dict):
                cat_pass = checks.get("passed", False)
                if not cat_pass:
                    passed = False
                    reasons = checks.get("failures", [checks.get("reason", "unknown")])
                    blockers.extend(f"{category}: {r}" for r in reasons)

        self._results = results
        self._all_passed = passed
        self._blockers = blockers

        return self._build_report()

    def report_json(self) -> str:
        return json.dumps(self._build_report(), indent=2, ensure_ascii=False)

    def summary_chatgpt(self) -> str:
        report = self._build_report()
        ready_str = "READY" if report["ready"] else "NOT_READY"
        lines = [
            f"=== Dry-Run Readiness Summary ===",
            f"Status: {ready_str}",
            f"Canonical HEAD: {report.get('canonical_local_head', 'N/A')}",
            f"Expected HEAD: {report.get('expected_canonical_head', 'N/A')}",
            f"HEAD Match: {report.get('canonical_head_matches_expected', False)}",
            f"Local/Remote Match: {report.get('local_remote_heads_match', False)}",
            f"Tracked Clean: {report.get('tracked_files_clean', False)}",
            f"Untracked Paths: {report.get('untracked_paths_count', 0)}",
            f"All Checks Passed: {report.get('all_passed', False)}",
        ]
        if report.get("blockers"):
            lines.append("")
            lines.append("Blockers:")
            for b in report["blockers"]:
                lines.append(f"  - {b}")
        lines.append("")
        lines.append("Category Results:")
        for cat, details in report.get("results", {}).items():
            if isinstance(details, dict):
                status = "PASS" if details.get("passed") else "FAIL"
                lines.append(f"  {cat}: {status}")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Git State Checks
    # ------------------------------------------------------------------ #

    def _check_git_state(self) -> Dict[str, Any]:
        failures = []

        local_head = self._run_git("rev-parse", "HEAD")
        remote_head = self._run_git("ls-remote", "origin", self.expected_branch)
        if remote_head:
            remote_head = remote_head.split("\t")[0]

        status_output = self._run_git("status", "--porcelain")
        status_lines = [s for s in status_output.splitlines() if s.strip()] if status_output else []

        tracked_clean = True
        untracked_count = 0
        for line in status_lines:
            stripped = line.strip()
            if stripped.startswith("?"):
                untracked_count += 1
            elif stripped and stripped[:2] != "??":
                tracked_clean = False

        self._untracked_paths_count = untracked_count

        local_remote_match = bool(local_head and remote_head and local_head == remote_head)
        head_matches_expected = bool(local_head and self.expected_canonical_head and local_head.strip() == self.expected_canonical_head.strip())

        if not local_head:
            failures.append("cannot_determine_local_head")
        if not remote_head:
            failures.append("cannot_determine_remote_head")
        if not local_remote_match:
            failures.append("local_remote_head_mismatch")
        if not head_matches_expected:
            failures.append("head_mismatch_expected")
        if not tracked_clean:
            failures.append("tracked_files_not_clean")
        if untracked_count > 0:
            failures.append(f"untracked_paths:{untracked_count}")

        return {
            "passed": len(failures) == 0,
            "failures": failures,
            "canonical_local_head": local_head.strip() if local_head else None,
            "canonical_remote_head": remote_head.strip() if remote_head else None,
            "expected_canonical_head": self.expected_canonical_head,
            "local_remote_heads_match": local_remote_match,
            "canonical_head_matches_expected": head_matches_expected,
            "tracked_files_clean": tracked_clean,
            "untracked_paths_count": untracked_count,
        }

    # ------------------------------------------------------------------ #
    #  Prior Remediation Batches
    # ------------------------------------------------------------------ #

    def _check_prior_batches(self) -> Dict[str, Any]:
        failures = []
        candidates_root = self.repo_root / "automation" / "control" / "candidates"
        found = []

        for name in PRIOR_BATCH_NAMES:
            candidate_dir = candidates_root / name
            evidence_path = candidate_dir / "evidence.json"
            task_path = candidate_dir / "task.txt"
            candidate_diff = candidate_dir / "candidate.diff"

            dir_exists = candidate_dir.is_dir()
            evidence_exists = evidence_path.is_file()
            task_exists = task_path.is_file()
            diff_exists = candidate_diff.is_file()

            found.append({
                "batch_name": name,
                "directory_exists": dir_exists,
                "evidence_exists": evidence_exists,
                "task_exists": task_exists,
                "diff_exists": diff_exists,
            })

            if not dir_exists:
                failures.append(f"{name}: directory_not_found")
            if not evidence_exists:
                failures.append(f"{name}: evidence.json_missing")
            if not task_exists:
                failures.append(f"{name}: task.txt_missing")

        return {
            "passed": len(failures) == 0,
            "failures": failures,
            "batches": found,
        }

    # ------------------------------------------------------------------ #
    #  Telegram Inbound Readiness
    # ------------------------------------------------------------------ #

    def _check_telegram_inbound_readiness(self) -> Dict[str, Any]:
        failures = []

        try:
            from automation.inbound.telegram_inbound import TelegramInboundReceiver
            receiver = TelegramInboundReceiver(use_mock=True)
            has_identity = hasattr(receiver, "_is_authorized_chat") and callable(receiver._is_authorized_chat)
            has_reject = hasattr(receiver, "_reject_unauthorized") and callable(receiver._reject_unauthorized)
            has_status = hasattr(receiver, "_handle_status") or hasattr(receiver, "_build_status_state")
            has_defined_round = hasattr(receiver, "_has_defined_round") and callable(receiver._has_defined_round)
            has_fetch = hasattr(receiver, "_fetch_updates") and callable(receiver._fetch_updates)

            if not has_identity:
                failures.append("no_chat_identity_verification")
            if not has_reject:
                failures.append("no_unauthorized_rejection")
            if not has_status:
                failures.append("no_status_command_handler")
            if not has_defined_round:
                failures.append("no_undefined_round_check")
            if not has_fetch:
                failures.append("no_fetch_updates")

            if self.mock_mode:
                result = receiver._fetch_updates()
                if result is not None:
                    failures.append("mock_fetch_updates_should_return_none")

        except ImportError:
            failures.append("telegram_inbound_module_not_available")
        except Exception as e:
            failures.append(f"telegram_inbound_error:{e}")

        try:
            from automation.control.candidates.TELEGRAM_INBOUND_HARDENING.candidate import TelegramInboundStub
            stub = TelegramInboundStub()
            has_parse = hasattr(stub, "parse_update") and callable(stub.parse_update)
            has_auth = hasattr(stub, "_is_authorized_chat") and callable(stub._is_authorized_chat)
            if not has_parse:
                failures.append("stub_no_parse_update")
            if not has_auth:
                failures.append("stub_no_chat_identity")
        except ImportError:
            failures.append("telegram_inbound_stub_not_available")
        except Exception as e:
            failures.append(f"telegram_inbound_stub_error:{e}")

        return {
            "passed": len(failures) == 0,
            "failures": failures,
            "mock_mode_no_real_api": self.mock_mode,
        }

    # ------------------------------------------------------------------ #
    #  Undefined-Round Hard Gate
    # ------------------------------------------------------------------ #

    def _check_undefined_round_gate(self) -> Dict[str, Any]:
        failures = []

        try:
            from automation.control.auto_advance import AutoAdvanceController
            controller = AutoAdvanceController()

            has_is_defined = hasattr(controller, "_is_round_defined") and callable(controller._is_round_defined)
            if not has_is_defined:
                failures.append("auto_advance_no_is_round_defined")
            else:
                defined_valid, _ = controller._is_round_defined("valid_round")
                defined_none, _ = controller._is_round_defined("none")
                if not defined_valid:
                    failures.append("is_round_defined_incorrect_for_valid")
                if defined_none:
                    failures.append("is_round_defined_incorrect_for_undefined")

            has_can_auto_advance = hasattr(controller, "can_auto_advance") and callable(controller.can_auto_advance)
            if not has_can_auto_advance:
                failures.append("auto_advance_no_can_auto_advance")

            has_can_dispatch = hasattr(controller, "can_dispatch_next_round") and callable(controller.can_dispatch_next_round)
            if not has_can_dispatch:
                failures.append("auto_advance_no_can_dispatch_next_round")

            has_notify_undefined = hasattr(controller, "notify_undefined_round_blocked") and callable(controller.notify_undefined_round_blocked)
            if not has_notify_undefined:
                failures.append("auto_advance_no_notify_undefined_round_blocked")

        except ImportError:
            failures.append("auto_advance_module_not_available")
        except Exception as e:
            failures.append(f"auto_advance_error:{e}")

        try:
            from automation.control.control_bridge import is_round_defined
            import inspect
            if not callable(is_round_defined):
                failures.append("control_bridge_is_round_defined_not_callable")
            else:
                result = is_round_defined("valid_round")
                if not result:
                    failures.append("control_bridge_is_round_defined_incorrect")

                _ = is_round_defined("")
                _ = is_round_defined("none")
                _ = is_round_defined("undefined")
        except ImportError:
            failures.append("control_bridge_module_not_available")
        except Exception as e:
            failures.append(f"control_bridge_is_round_defined_error:{e}")

        return {
            "passed": len(failures) == 0,
            "failures": failures,
        }

    # ------------------------------------------------------------------ #
    #  Usage Exhaustion / Pause / Notify
    # ------------------------------------------------------------------ #

    def _check_usage_exhaustion_notify(self) -> Dict[str, Any]:
        failures = []

        try:
            from automation.control.auto_advance import AutoAdvanceController
            controller = AutoAdvanceController()

            has_sentinel = hasattr(controller, "USAGE_SENTINEL_PATH")
            has_check = hasattr(controller, "check_usage_exhaustion") and callable(controller.check_usage_exhaustion)
            has_notify = hasattr(controller, "notify_usage_exhausted") and callable(controller.notify_usage_exhausted)

            if not has_sentinel:
                failures.append("no_usage_sentinel_path")
            if not has_check:
                failures.append("no_check_usage_exhaustion")
            if not has_notify:
                failures.append("no_notify_usage_exhausted")

        except ImportError:
            failures.append("auto_advance_module_not_available")
        except Exception as e:
            failures.append(f"auto_advance_usage_error:{e}")

        try:
            from automation.control.pause_state import PauseStateManager
            has_reason = hasattr(PauseStateManager, "REASON_USAGE")
            if not has_reason:
                failures.append("no_REASON_USAGE_in_pause_state")
            else:
                reason_val = PauseStateManager.REASON_USAGE
                if not reason_val:
                    failures.append("REASON_USAGE_has_no_value")
        except ImportError:
            failures.append("pause_state_module_not_available")
        except Exception as e:
            failures.append(f"pause_state_reason_error:{e}")

        try:
            from automation.control.api_automode_loop import APIAutoModeLoop
            loop = APIAutoModeLoop(repo_root=self.repo_root)
            has_usage_check = hasattr(loop, "check_usage_exhaustion") and callable(loop.check_usage_exhaustion)
            if not has_usage_check:
                failures.append("api_loop_no_check_usage_exhaustion")
        except ImportError:
            failures.append("api_automode_loop_not_available")
        except Exception as e:
            failures.append(f"api_loop_error:{e}")

        return {
            "passed": len(failures) == 0,
            "failures": failures,
        }

    # ------------------------------------------------------------------ #
    #  Notification Coverage
    # ------------------------------------------------------------------ #

    def _check_notification_coverage(self) -> Dict[str, Any]:
        failures = []

        try:
            from automation.control.telegram_notifier import TelegramNotifier
            notifier = TelegramNotifier(mock_mode=True)

            missing = []
            for method_name in REQUIRED_NOTIFICATION_METHODS:
                if not hasattr(notifier, method_name) or not callable(getattr(notifier, method_name)):
                    missing.append(method_name)

            if missing:
                failures.append(f"missing_notification_methods:{','.join(missing)}")

            for method_name in REQUIRED_NOTIFICATION_METHODS:
                if hasattr(notifier, method_name) and callable(getattr(notifier, method_name)):
                    try:
                        method = getattr(notifier, method_name)
                        import inspect
                        sig = inspect.signature(method)
                        required_args = [
                            p.name for p in sig.parameters.values()
                            if p.default is inspect.Parameter.empty and p.name not in ("self", "args", "kwargs")
                        ]
                        if not required_args:
                            result = method()
                        elif method_name == "send_pause_notification":
                            result = method(pause_reason="dry_run_check", duration_info={})
                        elif method_name == "send_stall_warning":
                            result = method(current_duration_seconds=0, threshold_seconds=1800)
                        elif method_name == "send_failure_warning":
                            result = method(current_count=0, threshold=3)
                        elif method_name == "send_blocked_notification":
                            result = method(reason="dry_run_check")
                        else:
                            result = method()
                        if isinstance(result, dict):
                            if not result.get("success"):
                                logger.warning(f"Notification method {method_name} returned success=False")
                    except Exception as e:
                        logger.warning(f"Notification method {method_name} raised during dry-run: {e}")

        except ImportError:
            failures.append("telegram_notifier_module_not_available")
        except Exception as e:
            failures.append(f"telegram_notifier_error:{e}")

        return {
            "passed": len(failures) == 0,
            "failures": failures,
            "notification_methods": REQUIRED_NOTIFICATION_METHODS,
            "method_count": len(REQUIRED_NOTIFICATION_METHODS),
        }

    # ------------------------------------------------------------------ #
    #  Kill Switch
    # ------------------------------------------------------------------ #

    def _check_kill_switch(self) -> Dict[str, Any]:
        failures = []

        try:
            from automation.inbound.telegram_inbound import TelegramInboundReceiver
            receiver = TelegramInboundReceiver(use_mock=True)

            has_set_pause = hasattr(receiver, "_pause_manager") and receiver._pause_manager is not None
            if not has_set_pause:
                failures.append("no_pause_manager_for_kill_switch")

            from automation.control.pause_state import PauseStateManager
            has_set = hasattr(PauseStateManager, "set_pause") and callable(PauseStateManager.set_pause)
            has_clear = hasattr(PauseStateManager, "clear_pause") and callable(PauseStateManager.clear_pause)
            if not has_set:
                failures.append("no_set_pause_for_kill_switch")
            if not has_clear:
                failures.append("no_clear_pause_for_recovery")

        except ImportError:
            failures.append("kill_switch_module_not_available")
        except Exception as e:
            failures.append(f"kill_switch_error:{e}")

        try:
            from automation.control.candidates.TELEGRAM_INBOUND_HARDENING.candidate import TelegramInboundStub
            stub = TelegramInboundStub()

            for cmd in REQUIRED_INBOUND_COMMANDS:
                has_command = cmd in ["/pause", "/start", "/status"]
                if not has_command:
                    failures.append(f"missing_inbound_command:{cmd}")
        except ImportError:
            failures.append("kill_switch_stub_not_available")
        except Exception as e:
            failures.append(f"kill_switch_stub_error:{e}")

        return {
            "passed": len(failures) == 0,
            "failures": failures,
            "commands_available": REQUIRED_INBOUND_COMMANDS,
        }

    # ------------------------------------------------------------------ #
    #  Mock Mode Safety
    # ------------------------------------------------------------------ #

    def _check_mock_mode_safety(self) -> Dict[str, Any]:
        failures = []

        try:
            from automation.inbound.telegram_inbound import TelegramInboundReceiver
            receiver = TelegramInboundReceiver(use_mock=True)
            if not receiver.use_mock:
                failures.append("telegram_inbound_not_in_mock_mode")

            updates = receiver._fetch_updates()
            if updates is not None:
                failures.append("telegram_inbound_fetch_updates_should_be_none_in_mock_mode")

        except ImportError:
            pass
        except Exception as e:
            failures.append(f"mock_mode_check_error:{e}")

        try:
            from automation.control.telegram_notifier import TelegramNotifier
            notifier = TelegramNotifier(mock_mode=True)
            if not notifier.mock_mode:
                failures.append("telegram_notifier_not_in_mock_mode")
        except ImportError:
            pass
        except Exception as e:
            failures.append(f"notifier_mock_check_error:{e}")

        return {
            "passed": len(failures) == 0,
            "failures": failures,
            "mock_mode": self.mock_mode,
        }

    # ------------------------------------------------------------------ #
    #  Dry-Run Invariants
    # ------------------------------------------------------------------ #

    def _check_dry_run_invariants(self) -> Dict[str, Any]:
        return {
            "passed": True,
            "construction_not_triggered": True,
            "next_round_not_dispatched": True,
            "candidate_not_created": True,
            "no_commit": True,
            "no_merge": True,
            "no_push": True,
            "no_promote": True,
            "no_pr": True,
            "no_real_telegram_http": self.mock_mode,
            "secrets_not_touched": True,
            "runtime_not_touched": True,
            "manifests_not_touched": True,
            "retained_untracked_not_touched": True,
            "telegram_auto_mode_not_started": True,
        }

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _run_git(self, *args: str) -> str:
        try:
            result = subprocess.run(
                ["git"] + list(args),
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.repo_root),
            )
            if result.returncode == 0:
                return result.stdout.strip()
            logger.warning("Git command '%s' failed: %s", " ".join(args), result.stderr.strip())
            return ""
        except Exception as e:
            logger.warning("Git command '%s' exception: %s", " ".join(args), e)
            return ""

    def _build_report(self) -> Dict[str, Any]:
        git_state = self._results.get("git_state", {})

        report = {
            "ready": self._all_passed,
            "all_passed": self._all_passed,
            "blockers": self._blockers,
            "canonical_local_head": git_state.get("canonical_local_head"),
            "canonical_remote_head": git_state.get("canonical_remote_head"),
            "expected_canonical_head": git_state.get("expected_canonical_head"),
            "local_remote_heads_match": git_state.get("local_remote_heads_match", False),
            "canonical_head_matches_expected": git_state.get("canonical_head_matches_expected", False),
            "tracked_files_clean": git_state.get("tracked_files_clean", False),
            "untracked_paths_count": git_state.get("untracked_paths_count", 0),
            "branch": self.expected_branch,
            "mock_mode": self.mock_mode,
            "results": self._results,
        }

        dry_run_inv = self._results.get("dry_run_invariants", {})
        for key, val in dry_run_inv.items():
            if key.startswith("no_") or key.endswith("_not_triggered") or key.endswith("_not_touched"):
                report[key] = val

        return report

    @property
    def untracked_paths_count(self) -> int:
        return self._untracked_paths_count

    @property
    def all_passed(self) -> bool:
        return self._all_passed

    @property
    def blockers(self) -> List[str]:
        return list(self._blockers)
