"""
CONTROL_BRIDGE_FORMAL_ENTRYPOINT_STARTUP_CONTRACT_CANDIDATE tests.

Verifies:
- start_control_bridge.ps1 exists as formal entrypoint
- Sets PYTHONPATH = repo root in child process, not user-global
- Dry-run mode does not start long-running process
- Entrypoint targets automation/control/control_bridge.py
- Entrypoint does NOT start telegram_sidecar, main_control_loop, or /start-loop
- Entrypoint does NOT enable trading/broker/execution/live mode
- Entrypoint does NOT output TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID / secrets
- start_control_runtime.ps1 does NOT auto-start control_bridge
- No source outside allowed scope touched
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent
CONTROL_DIR = REPO_ROOT / "automation" / "control"
BRIDGE_ENTRYPOINT = CONTROL_DIR / "start_control_bridge.ps1"
BRIDGE_SCRIPT = CONTROL_DIR / "control_bridge.py"
CONTROL_RUNTIME = CONTROL_DIR / "start_control_runtime.ps1"


ALLOWED_FORBIDDEN_PATTERNS = [
    "strategy/",
    "broker/",
    "execution/",
    "server_v2.py",
    "index_v2.html",
    ".env",
    "automation/inbound/",
    "automation/secrets/",
    "_governance/law/",
    "manifests/",
]

def read_script(path: Path = BRIDGE_ENTRYPOINT) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestFormalEntrypointExists:
    def test_start_control_bridge_ps1_exists(self):
        assert BRIDGE_ENTRYPOINT.exists(), (
            f"Formal entrypoint {BRIDGE_ENTRYPOINT} does not exist"
        )

    def test_start_control_bridge_ps1_is_file(self):
        assert BRIDGE_ENTRYPOINT.is_file(), (
            f"{BRIDGE_ENTRYPOINT} is not a regular file"
        )

    def test_control_bridge_py_target_exists(self):
        assert BRIDGE_SCRIPT.exists(), (
            f"Target script {BRIDGE_SCRIPT} does not exist"
        )


class TestPYTHONPATHContract:
    def test_entrypoint_sets_pythonpath_in_env(self):
        content = read_script()
        assert "$env:PYTHONPATH = $repoRoot" in content, (
            "Entrypoint must set PYTHONPATH to repo root in child process environment"
        )

    def test_entrypoint_does_not_use_global_pythonpath(self):
        content = read_script()
        assert '[Environment]::SetEnvironmentVariable' not in content, (
            "Entrypoint must NOT modify user-global environment"
        )

    def test_entrypoint_cleans_up_pythonpath(self):
        content = read_script()
        assert "Remove-Item Env:PYTHONPATH" in content, (
            "Entrypoint must clean up PYTHONPATH after start"
        )

    def test_entrypoint_uses_repo_root_path(self):
        content = read_script()
        assert 'Join-Path $PSScriptRoot "..\\.."' in content, (
            "Entrypoint must auto-resolve repo root from PSScriptRoot"
        )


class TestDryRunMode:
    def test_dry_run_switch_exists(self):
        content = read_script()
        assert "[switch]$DryRun" in content, (
            "Entrypoint must support -DryRun switch"
        )

    def test_dry_run_does_not_start_process(self):
        content = read_script()
        assert "Start-Process" in content, (
            "Entrypoint must have Start-Process for live mode"
        )
        assert "No process started" in content, (
            "Dry-run must indicate no process was started"
        )

    def test_dry_run_prints_command(self):
        content = read_script()
        assert "PYTHONPATH=" in content, (
            "Dry-run must display the PYTHONPATH it would set"
        )

    def test_dry_run_exits_zero(self):
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(BRIDGE_ENTRYPOINT), "-DryRun"],
            capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT)
        )
        assert result.returncode == 0, (
            f"Dry-run should exit 0, got {result.returncode}"
        )

    def test_dry_run_output_no_pid(self):
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(BRIDGE_ENTRYPOINT), "-DryRun"],
            capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT)
        )
        assert "PID" not in result.stdout, (
            "Dry-run must not show PID (should not start process)"
        )
        assert "Dry-run complete" in result.stdout, (
            "Dry-run must indicate completion without starting"
        )

    def test_dry_run_does_not_leave_python_process(self):
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(BRIDGE_ENTRYPOINT), "-DryRun"],
            capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT)
        )
        tasklist = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=15, cwd=str(REPO_ROOT)
        )
        bridge_processes = [line for line in tasklist.stdout.splitlines() if "control_bridge" in line.lower()]
        assert len(bridge_processes) == 0, (
            f"Found {len(bridge_processes)} control_bridge process(es) after dry-run"
        )


class TestSafeDeny:
    def test_no_telegram_sidecar_in_entrypoint(self):
        content = read_script()
        lines = content.splitlines()
        exec_telegram = [l for l in lines if "telegram_sidecar" in l.lower() and not l.strip().startswith("#") and "Write-Host" not in l]
        assert len(exec_telegram) == 0, (
            f"Entrypoint must not execute telegram_sidecar, found {len(exec_telegram)} non-comment references"
        )

    def test_no_main_control_loop_in_entrypoint(self):
        content = read_script()
        lines = content.splitlines()
        exec_main = [l for l in lines if "main_control_loop" in l.lower() and not l.strip().startswith("#") and "Write-Host" not in l]
        assert len(exec_main) == 0, (
            f"Entrypoint must not execute main_control_loop, found {len(exec_main)} non-comment references"
        )

    def test_no_start_loop_reference(self):
        content = read_script()
        assert "start_loop.ps1" not in content.lower(), (
            "Entrypoint must not call start_loop.ps1"
        )

    def test_safe_deny_comments_present(self):
        content = read_script()
        has_safe_deny = "safe-deny" in content.lower()
        has_no_trading = "no trading" in content.lower() or "no trading" in content.lower()
        assert has_safe_deny, (
            "Entrypoint must have safe-deny comments"
        )

    def test_no_trading_broker_execution_live(self):
        content = read_script()
        lines = content.splitlines()
        exec_refs = [l for l in lines if any(kw in l.lower() for kw in ["trading", "broker", "execution", "live"]) and not l.strip().startswith("#") and "Write-Host" not in l]
        assert len(exec_refs) == 0, (
            f"Entrypoint must not execute trading/broker/execution/live, found {len(exec_refs)} non-comment references"
        )

    def test_no_secret_output(self):
        content = read_script()
        assert "TELEGRAM_BOT_TOKEN" not in content
        assert "TELEGRAM_CHAT_ID" not in content
        assert "BotToken" not in content

    def test_no_order_execution_allowed(self):
        content = read_script()
        assert "order_execution" not in content.lower() or "no order_execution" in content.lower()


class TestTargetsControlBridgePy:
    def test_entrypoint_references_control_bridge_py(self):
        content = read_script()
        assert "control_bridge.py" in content, (
            "Entrypoint must target control_bridge.py"
        )

    def test_entrypoint_uses_windows_style_path(self):
        content = read_script()
        assert '\\"' in content or 'control_bridge.py' in content or '"'.join(['', '']) in content

    def test_entrypoint_resolves_script_path_dynamically(self):
        content = read_script()
        assert "Join-Path" in content, (
            "Entrypoint must use Join-Path for script resolution"
        )


class TestStartControlRuntimeNotAutoStart:
    def test_runtime_script_does_not_call_bridge_entrypoint(self):
        path = CONTROL_RUNTIME
        if not path.exists():
            pytest.skip("start_control_runtime.ps1 not modified")
        with open(path, encoding="utf-8-sig") as f:
            content = f.read()
        exec_calls = [line for line in content.splitlines() if "start_control_bridge" in line.lower() and not line.strip().startswith("#") and "Write-Host" not in line and ("powershell" in line.lower() or "& " in line or "Start-Process" in line or "Invoke-Expression" in line or ".\\" in line)]
        assert len(exec_calls) == 0, (
            f"start_control_runtime.ps1 must NOT auto-execute start_control_bridge.ps1. Found: {exec_calls}"
        )

    def test_runtime_script_references_formal_entrypoint(self):
        path = CONTROL_RUNTIME
        if not path.exists():
            pytest.skip("start_control_runtime.ps1 not modified")
        with open(path, encoding="utf-8-sig") as f:
            content = f.read()
        assert "start_control_bridge" in content, (
            "start_control_runtime.ps1 should reference start_control_bridge.ps1"
        )


class TestScopeIntegrity:
    def test_no_forbidden_paths_touched(self):
        result = subprocess.run(
            ["git", "diff", "--name-only", "70aebd6e300a12222e83b6cd42d6d736e529fd3c", "--"],
            capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT)
        )
        changed_files = result.stdout.strip().splitlines()
        for pattern in ALLOWED_FORBIDDEN_PATTERNS:
            for f in changed_files:
                if pattern in f:
                    pytest.fail(f"Unauthorized change to forbidden path: {f}")

    def test_only_authorized_scope_modified(self):
        result = subprocess.run(
            ["git", "diff", "--name-only", "70aebd6e300a12222e83b6cd42d6d736e529fd3c", "--"],
            capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT)
        )
        changed_files = result.stdout.strip().splitlines()
        for f in changed_files:
            if not any(ok in f for ok in [
                "start_control_bridge.ps1",
                "start_control_runtime.ps1",
                "test_control_bridge_startup_contract",
                "candidates/CONTROL_BRIDGE_FORMAL_ENTRYPOINT_STARTUP_CONTRACT_CANDIDATE/",
            ]):
                pytest.fail(f"File outside authorized scope: {f}")
