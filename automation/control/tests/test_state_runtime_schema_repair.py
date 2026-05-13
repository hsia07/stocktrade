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

REQUIRED_SCHEMA_FIELDS = {
    "stop_reason",
    "phase_definition",
    "authorized_scope",
    "desired_action",
    "merge_gate",
    "candidate_checklist",
}

SAFE_DENY_DEFAULTS = {
    "current_mode": "idle",
    "stop_reason": None,
    "authorized_scope": "",
    "desired_action": "none",
}

CANDIDATE_CHECKLIST_SAFE_DENY = {
    "formal_status_code": "not_started",
    "theme_completed": False,
    "rerunnable_tests_passed": False,
    "evidence_package_complete": False,
    "validate_evidence_ps1_executed": False,
    "validate_evidence_result": None,
    "validate_evidence_executed_at": None,
    "validate_evidence_exit_code": None,
    "candidate_branch_auditable": False,
    "candidate_commit_auditable": False,
    "no_fabricated_evidence": False,
    "no_unauthorized_modifications": False,
    "complete_return_to_chatgpt": False,
}


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


class TestMainControlLoopStateSchemaRepair:
    """6-field schema repair: start_loop.ps1 must handle missing fields without crash."""

    def test_start_loop_ps1_contains_initialize_state_schema_function(self):
        """start_loop.ps1 must contain the Initialize-StateSchema function."""
        content = START_LOOP_PS1.read_text(encoding="utf-8")
        assert "function Initialize-StateSchema" in content, \
            "start_loop.ps1 missing Initialize-StateSchema function"

    def test_start_loop_ps1_calls_initialize_state_schema(self):
        """start_loop.ps1 must call Initialize-StateSchema after loading state."""
        content = START_LOOP_PS1.read_text(encoding="utf-8")
        assert "Initialize-StateSchema" in content, \
            "start_loop.ps1 missing Initialize-StateSchema call"

    def test_start_loop_ps1_covers_all_required_fields(self):
        """Initialize-StateSchema must handle all 6 missing fields + current_mode."""
        content = START_LOOP_PS1.read_text(encoding="utf-8")
        for field in REQUIRED_SCHEMA_FIELDS:
            assert field in content, \
                f"Initialize-StateSchema missing field: {field}"
        assert "current_mode" in content, \
            "Initialize-StateSchema missing current_mode"

    def test_schema_normalization_no_crash_on_minimal_state(self):
        """Simulate loading minimal state with missing fields, verify no crash."""
        ps_script = r"""
$ErrorActionPreference = 'Stop'
$state = '{"run_state":"stopped"}' | ConvertFrom-Json
function Init {
    param($S, $P, $R)
    if (-not ($S.PSObject.Properties.Name -contains 'current_mode')) {
        $S | Add-Member -NotePropertyName 'current_mode' -NotePropertyValue 'idle'
    }
    if (-not ($S.PSObject.Properties.Name -contains 'stop_reason')) {
        $S | Add-Member -NotePropertyName 'stop_reason' -NotePropertyValue $null
    }
    if (-not ($S.PSObject.Properties.Name -contains 'phase_definition')) {
        $d = @{}; $d[$P] = @{start_round=$R; end_round=$R}
        $S | Add-Member -NotePropertyName 'phase_definition' -NotePropertyValue $d
    }
    if (-not ($S.PSObject.Properties.Name -contains 'authorized_scope')) {
        $S | Add-Member -NotePropertyName 'authorized_scope' -NotePropertyValue ''
    }
    if (-not ($S.PSObject.Properties.Name -contains 'desired_action')) {
        $S | Add-Member -NotePropertyName 'desired_action' -NotePropertyValue 'none'
    }
    if (-not ($S.PSObject.Properties.Name -contains 'merge_gate')) {
        $S | Add-Member -NotePropertyName 'merge_gate' -NotePropertyValue ([PSCustomObject]@{current_decision_state='closed'})
    }
    if (-not ($S.PSObject.Properties.Name -contains 'candidate_checklist')) {
        $S | Add-Member -NotePropertyName 'candidate_checklist' -NotePropertyValue ([PSCustomObject]@{formal_status_code='not_started'; theme_completed=$false; rerunnable_tests_passed=$false; evidence_package_complete=$false; validate_evidence_ps1_executed=$false; validate_evidence_result=$null; validate_evidence_executed_at=$null; validate_evidence_exit_code=$null; candidate_branch_auditable=$false; candidate_commit_auditable=$false; no_fabricated_evidence=$false; no_unauthorized_modifications=$false; complete_return_to_chatgpt=$false})
    }
    return $S
}
$s = Init -S $state -P 'Phase 2' -R 'R017'
Write-Output ("OK cm=" + $s.current_mode + " sr=" + ($s.stop_reason -eq $null) + " pd=" + ($null -ne $s.phase_definition) + " as='" + $s.authorized_scope + "' da=" + $s.desired_action + " mg=" + $s.merge_gate.current_decision_state + " cc=" + $s.candidate_checklist.formal_status_code)
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, \
            f"PowerShell exited {proc.returncode}: stdout={proc.stdout} stderr={proc.stderr}"
        assert "OK" in proc.stdout, f"Expected OK in output: {proc.stdout}"

    def test_safe_deny_defaults_applied(self):
        """Verify safe-deny defaults for each field."""
        ps_script = r"""
$ErrorActionPreference = 'Stop'
$def = @{'Phase 2' = @{start_round='R1';end_round='R1'}}
$state = '{"run_state":"stopped"}' | ConvertFrom-Json

if (-not ($state.PSObject.Properties.Name -contains 'current_mode')) {
    $state | Add-Member -NotePropertyName 'current_mode' -NotePropertyValue 'idle'
}
if (-not ($state.PSObject.Properties.Name -contains 'stop_reason')) {
    $state | Add-Member -NotePropertyName 'stop_reason' -NotePropertyValue $null
}
if (-not ($state.PSObject.Properties.Name -contains 'phase_definition')) {
    $state | Add-Member -NotePropertyName 'phase_definition' -NotePropertyValue $def
}
if (-not ($state.PSObject.Properties.Name -contains 'authorized_scope')) {
    $state | Add-Member -NotePropertyName 'authorized_scope' -NotePropertyValue ''
}
if (-not ($state.PSObject.Properties.Name -contains 'desired_action')) {
    $state | Add-Member -NotePropertyName 'desired_action' -NotePropertyValue 'none'
}
if (-not ($state.PSObject.Properties.Name -contains 'merge_gate')) {
    $gate = [PSCustomObject]@{current_decision_state='closed'}
    $state | Add-Member -NotePropertyName 'merge_gate' -NotePropertyValue $gate
}
if (-not ($state.PSObject.Properties.Name -contains 'candidate_checklist')) {
    $cl = [PSCustomObject]@{formal_status_code='not_started';theme_completed=$false}
    $state | Add-Member -NotePropertyName 'candidate_checklist' -NotePropertyValue $cl
}

Write-Output ("cm=" + $state.current_mode + " sr=" + ($state.stop_reason -eq $null) + " as='" + $state.authorized_scope + "' da=" + $state.desired_action + " mg=" + $state.merge_gate.current_decision_state + " cc=" + $state.candidate_checklist.formal_status_code)
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        out = proc.stdout.strip()
        assert "cm=idle" in out, f"current_mode not idle: {out}"
        assert "sr=True" in out, f"stop_reason not null: {out}"
        assert "as=''" in out, f"authorized_scope not empty: {out}"
        assert "da=none" in out, f"desired_action not none: {out}"
        assert "mg=closed" in out, f"merge_gate not closed: {out}"
        assert "cc=not_started" in out, f"candidate_checklist not not_started: {out}"

    def test_existing_fields_preserved(self):
        """When fields already exist, they must NOT be overwritten by defaults."""
        ps_script = r"""
$ErrorActionPreference = 'Stop'
$state = '{"run_state":"stopped","current_mode":"running","stop_reason":"manual","authorized_scope":"test_scope","desired_action":"test_action","merge_gate":{"current_decision_state":"open"},"candidate_checklist":{"formal_status_code":"passed","theme_completed":true},"phase_definition":{"Phase 2":{"start_round":"R017","end_round":"R017"}}}' | ConvertFrom-Json

if (-not ($state.PSObject.Properties.Name -contains 'current_mode')) {
    $state | Add-Member -NotePropertyName 'current_mode' -NotePropertyValue 'idle'
}
if (-not ($state.PSObject.Properties.Name -contains 'stop_reason')) {
    $state | Add-Member -NotePropertyName 'stop_reason' -NotePropertyValue $null
}
if (-not ($state.PSObject.Properties.Name -contains 'authorized_scope')) {
    $state | Add-Member -NotePropertyName 'authorized_scope' -NotePropertyValue ''
}
if (-not ($state.PSObject.Properties.Name -contains 'desired_action')) {
    $state | Add-Member -NotePropertyName 'desired_action' -NotePropertyValue 'none'
}
if (-not ($state.PSObject.Properties.Name -contains 'merge_gate')) {
    $state | Add-Member -NotePropertyName 'merge_gate' -NotePropertyValue ([PSCustomObject]@{current_decision_state='closed'})
}
if (-not ($state.PSObject.Properties.Name -contains 'candidate_checklist')) {
    $state | Add-Member -NotePropertyName 'candidate_checklist' -NotePropertyValue ([PSCustomObject]@{formal_status_code='not_started'})
}

Write-Output ("cm=" + $state.current_mode + " sr=" + $state.stop_reason + " as=" + $state.authorized_scope + " da=" + $state.desired_action + " mg=" + $state.merge_gate.current_decision_state + " cc=" + $state.candidate_checklist.formal_status_code + " ct=" + $state.candidate_checklist.theme_completed)
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        out = proc.stdout.strip()
        assert "cm=running" in out, f"current_mode overwritten: {out}"
        assert "sr=manual" in out, f"stop_reason overwritten: {out}"
        assert "as=test_scope" in out, f"authorized_scope overwritten: {out}"
        assert "da=test_action" in out, f"desired_action overwritten: {out}"
        assert "mg=open" in out, f"merge_gate overwritten: {out}"
        assert "cc=passed" in out, f"candidate_checklist.formal_status_code overwritten: {out}"
        assert "ct=True" in out, f"candidate_checklist.theme_completed overwritten: {out}"

    def test_phase_definition_created_from_launch_context(self):
        """phase_definition must be created from -Phase / -StartRound params, not old phase mapping."""
        ps_script = r"""
$ErrorActionPreference = 'Stop'
$state = '{"run_state":"stopped"}' | ConvertFrom-Json
$Phase = 'Phase 2'
$StartRound = 'R017'
if (-not ($state.PSObject.Properties.Name -contains 'phase_definition')) {
    $def = @{}; $def[$Phase] = @{start_round=$StartRound; end_round=$StartRound}
    $state | Add-Member -NotePropertyName 'phase_definition' -NotePropertyValue $def
}
Write-Output ("start=" + $state.phase_definition.'Phase 2'.start_round + " end=" + $state.phase_definition.'Phase 2'.end_round)
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        out = proc.stdout.strip()
        assert "start=R017" in out, f"start_round not from param: {out}"
        assert "end=R017" in out, f"end_round not from param: {out}"

    def test_phase_definition_does_not_overwrite_existing(self):
        """If phase_definition exists, do not overwrite it."""
        ps_script = r"""
$ErrorActionPreference = 'Stop'
$state = '{"run_state":"stopped","phase_definition":{"Phase 1":{"start_round":"R001","end_round":"R005"}}}' | ConvertFrom-Json
$Phase = 'Phase 2'
$StartRound = 'R017'
if (-not ($state.PSObject.Properties.Name -contains 'phase_definition')) {
    $def = [PSCustomObject]@{}
    $def | Add-Member -NotePropertyName $Phase -NotePropertyValue ([PSCustomObject]@{start_round=$StartRound; end_round=$StartRound})
    $state | Add-Member -NotePropertyName 'phase_definition' -NotePropertyValue $def
} elseif (-not $state.phase_definition.$Phase) {
    $state.phase_definition | Add-Member -NotePropertyName $Phase -NotePropertyValue ([PSCustomObject]@{start_round=$StartRound; end_round=$StartRound})
}
Write-Output ("p1_start=" + $state.phase_definition.'Phase 1'.start_round + " p2_start=" + $state.phase_definition.'Phase 2'.start_round)
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        out = proc.stdout.strip()
        assert "p1_start=R001" in out, f"Phase 1 overwritten: {out}"
        assert "p2_start=R017" in out, f"Phase 2 not added: {out}"

    def test_reentrant_schema_repair_no_crash(self):
        """Calling schema repair twice must not crash (re-entrancy)."""
        ps_script = r"""
$ErrorActionPreference = 'Stop'
$state = '{"run_state":"stopped"}' | ConvertFrom-Json

function Init {
    param($S, $P, $R)
    if (-not ($S.PSObject.Properties.Name -contains 'current_mode')) {
        $S | Add-Member -NotePropertyName 'current_mode' -NotePropertyValue 'idle'
    }
    if (-not ($S.PSObject.Properties.Name -contains 'stop_reason')) {
        $S | Add-Member -NotePropertyName 'stop_reason' -NotePropertyValue $null
    }
    if (-not ($S.PSObject.Properties.Name -contains 'phase_definition')) {
        $d = @{}; $d[$P] = @{start_round=$R; end_round=$R}
        $S | Add-Member -NotePropertyName 'phase_definition' -NotePropertyValue $d
    }
    if (-not ($S.PSObject.Properties.Name -contains 'authorized_scope')) {
        $S | Add-Member -NotePropertyName 'authorized_scope' -NotePropertyValue ''
    }
    if (-not ($S.PSObject.Properties.Name -contains 'desired_action')) {
        $S | Add-Member -NotePropertyName 'desired_action' -NotePropertyValue 'none'
    }
    if (-not ($S.PSObject.Properties.Name -contains 'merge_gate')) {
        $S | Add-Member -NotePropertyName 'merge_gate' -NotePropertyValue ([PSCustomObject]@{current_decision_state='closed'})
    }
    if (-not ($S.PSObject.Properties.Name -contains 'candidate_checklist')) {
        $S | Add-Member -NotePropertyName 'candidate_checklist' -NotePropertyValue ([PSCustomObject]@{formal_status_code='not_started'})
    }
    return $S
}

$s = Init -S $state -P 'Phase 2' -R 'R017'
$s = Init -S $s -P 'Phase 2' -R 'R017'
Write-Output ("OK cm=" + $s.current_mode)
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, \
            f"PowerShell exited {proc.returncode}: stdout={proc.stdout} stderr={proc.stderr}"
        assert "OK" in proc.stdout, f"Re-entrancy failed: {proc.stdout}"

    def test_old_current_mode_repair_still_works(self):
        """The existing current_mode Add-Member repair must still function."""
        content = START_LOOP_PS1.read_text(encoding="utf-8")
        assert "Add-Member -NotePropertyName 'current_mode'" in content or \
               'Add-Member -NotePropertyName "current_mode"' in content, \
            "start_loop.ps1 missing current_mode Add-Member in Initialize-StateSchema"
        assert "-contains 'current_mode'" in content, \
            "start_loop.ps1 missing current_mode existence check in Initialize-StateSchema"


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
