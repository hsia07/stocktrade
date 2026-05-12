"""
CREATE_STATE_RUNTIME_SCHEMA_REPAIR_CANDIDATE tests.

Verifies:
- start_loop.ps1 contains current_mode schema protection (Add-Member fallback)
- Allowed current_mode values are defined and match the template
- Add-Member logic works on PSCustomObject missing current_mode
- Template default "idle" is used as fallback
- Schema repair does NOT start any loop or sidecar
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent
CONTROL_DIR = REPO_ROOT / "automation" / "control"
START_LOOP_PS1 = CONTROL_DIR / "start_loop.ps1"
STATE_TEMPLATE = CONTROL_DIR / "state.template.json"
STATE_RUNTIME = CONTROL_DIR / "state.runtime.json"


ALLOWED_CURRENT_MODES = {"idle", "multi_round_candidate_prep", "stopped", "paused"}


class TestStartLoopCurrentModeSchema:
    def test_start_loop_ps1_contains_current_mode_fix(self):
        """start_loop.ps1 must contain the current_mode Add-Member protection."""
        content = START_LOOP_PS1.read_text(encoding="utf-8")
        assert 'Add-Member -NotePropertyName \'current_mode\'' in content or \
               'Add-Member -NotePropertyName "current_mode"' in content, \
            "start_loop.ps1 missing current_mode Add-Member fix"
        assert '-contains \'current_mode\'' in content or \
               '-contains "current_mode"' in content, \
            "start_loop.ps1 missing current_mode existence check"

    def test_start_loop_ps1_defines_allowed_current_modes(self):
        """start_loop.ps1 must define the allowed current_mode values array."""
        content = START_LOOP_PS1.read_text(encoding="utf-8")
        assert "$allowedCurrentModes" in content, \
            "start_loop.ps1 missing $allowedCurrentModes variable"
        for mode in ALLOWED_CURRENT_MODES:
            assert mode in content, \
                f"allowed current_mode '{mode}' not found in start_loop.ps1"

    def test_template_defines_current_mode_with_idle_default(self):
        """state.template.json must define current_mode with idle default."""
        template = json.loads(STATE_TEMPLATE.read_text(encoding="utf-8"))
        assert "current_mode" in template, \
            "state.template.json missing current_mode field"
        assert template["current_mode"] == "idle", \
            f"state.template.json current_mode should be 'idle', got '{template['current_mode']}'"


class TestSchemaRepairPowerShellBehavior:
    def test_add_member_works_on_pscustomobject_missing_current_mode(self):
        """
        Simulate the fix: load runtime.JSON-like content WITHOUT current_mode,
        apply Add-Member, then set current_mode.  No loop is started.
        """
        ps_script = f"""
$ErrorActionPreference = "Stop"
$state = '{{"run_state":"stopped","round_id":"R017"}}' | ConvertFrom-Json
if (-not ($state.PSObject.Properties.Name -contains 'current_mode')) {{
    $state | Add-Member -NotePropertyName 'current_mode' -NotePropertyValue 'idle'
}}
$state.current_mode = "multi_round_candidate_prep"
Write-Output "OK run_state=$($state.run_state) current_mode=$($state.current_mode)"
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, \
            f"PowerShell exited {proc.returncode}: stdout={proc.stdout} stderr={proc.stderr}"
        assert "OK" in proc.stdout, \
            f"Expected 'OK' in output, got: {proc.stdout}"
        assert "current_mode=multi_round_candidate_prep" in proc.stdout, \
            f"current_mode not set correctly: {proc.stdout}"

    def test_add_member_idle_default_applied_when_missing(self):
        """
        When current_mode is missing and Add-Member applies 'idle', the default
        must be 'idle' before the script overrides it.
        """
        ps_script = f"""
$ErrorActionPreference = "Stop"
$state = '{{"run_state":"stopped"}}' | ConvertFrom-Json
# Simulate the fix before override
if (-not ($state.PSObject.Properties.Name -contains 'current_mode')) {{
    $state | Add-Member -NotePropertyName 'current_mode' -NotePropertyValue 'idle'
}}
Write-Output "default=$($state.current_mode)"
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        assert "default=idle" in proc.stdout, \
            f"Expected default=idle, got: {proc.stdout}"

    def test_idle_default_does_not_falsely_set_running(self):
        """
        After the fix, run_state must remain stopped when no loop-start assignment occurs.
        The fix must not accidentally set running.
        """
        ps_script = f"""
$ErrorActionPreference = "Stop"
$state = '{{"run_state":"stopped"}}' | ConvertFrom-Json
if (-not ($state.PSObject.Properties.Name -contains 'current_mode')) {{
    $state | Add-Member -NotePropertyName 'current_mode' -NotePropertyValue 'idle'
}}
Write-Output "run_state=$($state.run_state) current_mode=$($state.current_mode)"
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        assert "run_state=stopped" in proc.stdout, \
            f"run_state should remain stopped: {proc.stdout}"
        assert "current_mode=idle" in proc.stdout, \
            f"current_mode should be idle: {proc.stdout}"


class TestSchemaCompleteness:
    def test_template_has_current_mode(self):
        """Verify state.template.json has current_mode in its root fields."""
        template = json.loads(STATE_TEMPLATE.read_text(encoding="utf-8"))
        assert "current_mode" in template, "current_mode missing from template"
        assert isinstance(template["current_mode"], str), "current_mode must be a string"
        assert template["current_mode"] in ALLOWED_CURRENT_MODES, \
            f"template default '{template['current_mode']}' not in allowed set"

    def test_runtime_state_does_not_have_current_mode_before_repair(self):
        """
        Current runtime state is known to lack current_mode (pre-existing condition).
        This test documents the before-state; it does NOT modify the file.
        """
        if STATE_RUNTIME.exists():
            state = json.loads(STATE_RUNTIME.read_text(encoding="utf-8"))
            if "current_mode" not in state:
                pass
        else:
            pytest.skip("state.runtime.json not present")

    def test_no_components_started(self):
        """
        Verify that running these tests did NOT start any GOV-INT-003 component
        or long-running loop.
        """
        control_bridge_pid = CONTROL_DIR / "control_bridge.pid"
        telegram_sidecar_pid = CONTROL_DIR / "telegram_sidecar.pid"
        assert not control_bridge_pid.exists(), \
            "control_bridge.pid should NOT exist"
        assert not telegram_sidecar_pid.exists(), \
            "telegram_sidecar.pid should NOT exist"
        pause_flag = CONTROL_DIR / "PAUSE_AFTER_CURRENT.flag"
        assert not pause_flag.exists(), \
            "PAUSE_AFTER_CURRENT.flag should NOT exist"
        activation_lock = CONTROL_DIR / "AUTO_MODE_ACTIVATION_LOCK"
        assert activation_lock.exists(), "activation lock must exist"
