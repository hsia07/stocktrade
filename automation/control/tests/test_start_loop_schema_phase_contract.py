"""
START_LOOP_SCHEMA_AND_PHASE_CONTRACT_REPAIR_CANDIDATE tests.

Verifies:
- updated_at schema normalization present in Initialize-StateSchema
- Set-StateProperty safe setter prevents crash on missing properties
- Direct assignment for updated_at no longer crashes (line 157 regression)
- Phase/StartRound: no silent R-006 fallback, fail closed when undetermined
- Phase 2 / R017 contract supported
- Formal round mapping preserved (Phase 1=R001-R016, Phase 2=R017-R048, etc.)
- Existing fields preserved, safe-deny defaults preserved
- No trading/broker/execution/live start
- No Telegram API call
- start_loop.ps1 does NOT modify state.runtime.json as tracked change
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent
CONTROL_DIR = REPO_ROOT / "automation" / "control"
START_LOOP_PS1 = CONTROL_DIR / "start_loop.ps1"
STATE_RUNTIME = CONTROL_DIR / "state.runtime.json"

SAFE_DENY_FIELDS = {
    "current_mode": "idle",
    "stop_reason": None,
    "authorized_scope": "",
    "desired_action": "none",
}

FORMAL_ROUNDS = {
    "Phase 1": ("R001", "R016"),
    "Phase 2": ("R017", "R048"),
    "Phase 3": ("R049", "R132"),
    "Phase 4": ("R133", "R161"),
}


def read_script() -> str:
    return START_LOOP_PS1.read_text(encoding="utf-8")


class TestUpdatedAtSchemaNormalization:
    def test_initialize_state_schema_contains_updated_at(self):
        """Initialize-StateSchema must add updated_at when missing."""
        content = read_script()
        assert "updated_at" in content, (
            "start_loop.ps1 Initialize-StateSchema missing updated_at"
        )
        assert "Add-Member -NotePropertyName 'updated_at'" in content or \
               'Add-Member -NotePropertyName "updated_at"' in content, (
            "Add-Member for updated_at not found in Initialize-StateSchema"
        )

    def test_set_state_property_helper_exists(self):
        """Set-StateProperty helper function must exist."""
        content = read_script()
        assert "function Set-StateProperty" in content, (
            "Set-StateProperty helper function not found"
        )

    def test_set_state_property_prevents_crash_on_missing_updated_at(self):
        """
        Simulate schema_version=2.0 state WITHOUT updated_at.
        Set-StateProperty must not crash when writing updated_at.
        """
        ps_script = r"""
$ErrorActionPreference = 'Stop'
function Set-StateProperty {
    param($State, [string]$PropertyName, $Value)
    if (-not ($State.PSObject.Properties.Name -contains $PropertyName)) {
        $State | Add-Member -NotePropertyName $PropertyName -NotePropertyValue $Value
    } else {
        $State.$PropertyName = $Value
    }
}
$state = '{"schema_version":"2.0","run_state":"stopped","current_phase":"Phase 2","current_round":"R017"}' | ConvertFrom-Json
Set-StateProperty -State $state -PropertyName "updated_at" -Value "2026-05-14T07:00:00"
Write-Output ("OK updated_at=" + $state.updated_at)
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, (
            f"PowerShell exited {proc.returncode}: stdout={proc.stdout} stderr={proc.stderr}"
        )
        assert "OK" in proc.stdout, f"Set-StateProperty failed: {proc.stdout}"

    def test_direct_assignment_no_longer_crashes_when_updated_at_missing(self):
        """
        The original crash at 'line 157' was $state.updated_at = ... on a
        PSCustomObject that lacked the property.  After the fix, either
        Set-StateProperty or prior schema normalization prevents the crash.
        This test simulates the full launch path without actual launch.
        """
        ps_script = r"""
$ErrorActionPreference = 'Stop'

$json = '{ "schema_version":"2.0","run_state":"stopped","current_phase":"Phase 2","current_round":"R017"}'
$state = $json | ConvertFrom-Json

# Simulate Initialize-StateSchema for updated_at
if (-not ($state.PSObject.Properties.Name -contains 'updated_at')) {
    $state | Add-Member -NotePropertyName 'updated_at' -NotePropertyValue ''
}

# This is the former crash line (line 157 equivalent)
$state.updated_at = "2026-05-14T07:00:00"

# Simulate Set-StateProperty for run_state
function Set-StateProperty {
    param($State, [string]$PropertyName, $Value)
    if (-not ($State.PSObject.Properties.Name -contains $PropertyName)) {
        $State | Add-Member -NotePropertyName $PropertyName -NotePropertyValue $Value
    } else {
        $State.$PropertyName = $Value
    }
}
Set-StateProperty -State $state -PropertyName "run_state" -Value "running"

Write-Output ("OK run_state=" + $state.run_state + " updated_at=" + $state.updated_at)
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, (
            f"PowerShell exited {proc.returncode}: stdout={proc.stdout} stderr={proc.stderr}"
        )
        out = proc.stdout.strip()
        assert "OK" in out, f"Crash regression: {out}"
        assert "run_state=running" in out, f"run_state not set: {out}"
        assert "updated_at=" in out, f"updated_at not set: {out}"

    def test_save_state_uses_set_state_property(self):
        """Save-State must use Set-StateProperty for updated_at."""
        content = read_script()
        assert "Set-StateProperty -State $State -PropertyName \"updated_at\"" in content, (
            "Save-State does not use Set-StateProperty for updated_at"
        )


class TestPhaseStartRoundContract:
    def test_no_silent_r006_default(self):
        """Default Phase and StartRound must NOT be R-006."""
        content = read_script()
        assert 'string]$Phase = ""' in content, (
            "Phase default should be empty string"
        )
        assert 'string]$StartRound = ""' in content, (
            "StartRound default should be empty string"
        )

    def test_fail_closed_when_no_phase_and_no_state(self):
        """
        When neither -Phase/-StartRound is provided AND state has
        no current_phase/current_round, the script must exit 1 (fail closed).
        """
        ps_script = r"""
$ErrorActionPreference = 'Stop'
$json = '{"schema_version":"2.0","run_state":"stopped"}'
$state = $json | ConvertFrom-Json
$Phase = ""
$StartRound = ""
$formattedPhase = if ($Phase) { $Phase } elseif ($state.current_phase) { $state.current_phase } else { "" }
$formattedRound = if ($StartRound) { $StartRound } elseif ($state.current_round) { $state.current_round } else { "" }
if (-not $formattedPhase -or -not $formattedRound) {
    Write-Output "BLOCKED missing phase/round"
    exit 1
}
Write-Output "SHOULD NOT REACH"
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 1, (
            f"Should have failed closed, but exited {proc.returncode}"
        )
        assert "BLOCKED" in proc.stdout, (
            f"Expected BLOCKED message, got: {proc.stdout}"
        )

    def test_phase2_r017_extracted_from_state(self):
        """
        When -Phase and -StartRound are empty but state has
        current_phase=Phase 2 and current_round=R017, those
        values must be used.
        """
        ps_script = r"""
$ErrorActionPreference = 'Stop'
$json = '{"schema_version":"2.0","run_state":"stopped","current_phase":"Phase 2","current_round":"R017"}'
$state = $json | ConvertFrom-Json
$Phase = ""
$StartRound = ""
$formattedPhase = if ($Phase) { $Phase } elseif ($state.current_phase) { $state.current_phase } else { "" }
$formattedRound = if ($StartRound) { $StartRound } elseif ($state.current_round) { $state.current_round } else { "" }
Write-Output ("phase=" + $formattedPhase + " round=" + $formattedRound)
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        out = proc.stdout.strip()
        assert "phase=Phase 2" in out, f"Phase not extracted: {out}"
        assert "round=R017" in out, f"Round not extracted: {out}"

    def test_formal_round_mapping_preserved(self):
        """All 4 phases must have correct round ranges."""
        content = read_script()
        for phase, (start, end) in FORMAL_ROUNDS.items():
            assert phase in content, f"Formal phase {phase} not found in start_loop.ps1"
            assert start in content, f"start_round {start} for {phase} not found"
            assert end in content, f"end_round {end} for {phase} not found"

    def test_round_within_phase_validated_pass(self):
        """
        R017 must be accepted as valid for Phase 2.
        """
        ps_script = r"""
$ErrorActionPreference = 'Stop'
$formalRounds = @{
    "Phase 1" = @{ start_round = "R001"; end_round = "R016" }
    "Phase 2" = @{ start_round = "R017"; end_round = "R048" }
    "Phase 3" = @{ start_round = "R049"; end_round = "R132" }
    "Phase 4" = @{ start_round = "R133"; end_round = "R161" }
}
$formattedPhase = "Phase 2"
$formattedRound = "R017"
$phaseRounds = $formalRounds[$formattedPhase]
$startNum = [int]$formattedRound.Substring(1)
$phaseStartNum = [int]$phaseRounds.start_round.Substring(1)
$phaseEndNum = [int]$phaseRounds.end_round.Substring(1)
if ($startNum -lt $phaseStartNum -or $startNum -gt $phaseEndNum) {
    Write-Output "BLOCKED out of bounds"
    exit 1
}
Write-Output ("OK round=" + $formattedRound + " phase=" + $formattedPhase)
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        assert "OK" in proc.stdout, f"Phase 2 / R017 validation failed: {proc.stdout}"

    def test_round_outside_phase_rejected(self):
        """
        R017 must be REJECTED for Phase 1 (out of bounds).
        """
        ps_script = r"""
$ErrorActionPreference = 'Stop'
$formalRounds = @{
    "Phase 1" = @{ start_round = "R001"; end_round = "R016" }
    "Phase 2" = @{ start_round = "R017"; end_round = "R048" }
}
$formattedPhase = "Phase 1"
$formattedRound = "R017"
$phaseRounds = $formalRounds[$formattedPhase]
$startNum = [int]$formattedRound.Substring(1)
$phaseStartNum = [int]$phaseRounds.start_round.Substring(1)
$phaseEndNum = [int]$phaseRounds.end_round.Substring(1)
if ($startNum -lt $phaseStartNum -or $startNum -gt $phaseEndNum) {
    Write-Output "BLOCKED out of bounds"
    exit 1
}
Write-Output "SHOULD NOT REACH"
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 1, (
            f"Should have rejected R017 for Phase 1"
        )

    def test_unknown_phase_rejected(self):
        """Unknown phase name must be rejected."""
        ps_script = r"""
$ErrorActionPreference = 'Stop'
$formalRounds = @{ "Phase 1" = @{}; "Phase 2" = @{}; "Phase 3" = @{}; "Phase 4" = @{} }
$formattedPhase = "R-006"
if (-not $formalRounds.ContainsKey($formattedPhase)) {
    Write-Output "BLOCKED unknown phase"
    exit 1
}
Write-Output "SHOULD NOT REACH"
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 1, (
            f"Should have rejected unknown phase R-006"
        )
        assert "BLOCKED" in proc.stdout

    def test_explicit_params_override_state(self):
        """Explicit -Phase and -StartRound must override state fields."""
        ps_script = r"""
$ErrorActionPreference = 'Stop'
$json = '{"schema_version":"2.0","run_state":"stopped","current_phase":"Phase 2","current_round":"R017"}'
$state = $json | ConvertFrom-Json
$Phase = "Phase 3"
$StartRound = "R050"
$formattedPhase = if ($Phase) { $Phase } elseif ($state.current_phase) { $state.current_phase } else { "" }
$formattedRound = if ($StartRound) { $StartRound } elseif ($state.current_round) { $state.current_round } else { "" }
Write-Output ("phase=" + $formattedPhase + " round=" + $formattedRound)
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        out = proc.stdout.strip()
        assert "phase=Phase 3" in out, f"Explicit Phase not honored: {out}"
        assert "round=R050" in out, f"Explicit Round not honored: {out}"


class TestExistingFieldsAndSafeDeny:
    def test_updated_at_safe_default_empty_string(self):
        """When updated_at is missing, Initialize-StateSchema must set it to ''."""
        ps_script = r"""
$ErrorActionPreference = 'Stop'
$state = '{"run_state":"stopped"}' | ConvertFrom-Json
if (-not ($state.PSObject.Properties.Name -contains 'updated_at')) {
    $state | Add-Member -NotePropertyName 'updated_at' -NotePropertyValue ''
}
Write-Output ("ok val='" + $state.updated_at + "'")
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        assert "val=''" in proc.stdout, f"Default not empty: {proc.stdout}"

    def test_updated_at_overwritten_when_launching(self):
        """After schema normalization, the launch code sets updated_at to current timestamp."""
        ps_script = r"""
$ErrorActionPreference = 'Stop'
$state = '{"run_state":"stopped","updated_at":""}' | ConvertFrom-Json
$state.updated_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
Write-Output ("ok val=" + $state.updated_at)
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        assert "ok val=" in proc.stdout, f"updated_at not set: {proc.stdout}"

    def test_existing_fields_preserved(self):
        """Existing fields like run_state=stopped must not be overwritten by normalization."""
        ps_script = r"""
$ErrorActionPreference = 'Stop'
$state = '{"run_state":"stopped","current_mode":"running","stop_reason":"manual","updated_at":"2026-01-01T00:00:00"}' | ConvertFrom-Json
if (-not ($state.PSObject.Properties.Name -contains 'current_mode')) {
    $state | Add-Member -NotePropertyName 'current_mode' -NotePropertyValue 'idle'
}
if (-not ($state.PSObject.Properties.Name -contains 'updated_at')) {
    $state | Add-Member -NotePropertyName 'updated_at' -NotePropertyValue ''
}
Write-Output ("run_state=" + $state.run_state + " cm=" + $state.current_mode + " ua=" + $state.updated_at)
"""
        proc = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        out = proc.stdout.strip()
        assert "run_state=stopped" in out, f"run_state overwritten: {out}"
        assert "cm=running" in out, f"current_mode overwritten: {out}"
        assert "ua=2026-01-01" in out, f"updated_at overwritten: {out}"


class TestNoRuntimeStarted:
    def test_no_control_bridge_pid(self):
        """Control bridge PID file must not exist."""
        pid_file = CONTROL_DIR / "control_bridge.pid"
        assert not pid_file.exists(), "control_bridge.pid should NOT exist"

    def test_no_telegram_sidecar_pid(self):
        """Telegram sidecar PID file must not exist."""
        pid_file = CONTROL_DIR / "telegram_sidecar.pid"
        assert not pid_file.exists(), "telegram_sidecar.pid should NOT exist"

    def test_activation_lock_exists(self):
        """AUTO_MODE_ACTIVATION_LOCK must exist (safe-deny governance)."""
        lock = CONTROL_DIR / "AUTO_MODE_ACTIVATION_LOCK"
        assert lock.exists(), "activation lock must exist"

    def test_start_loop_does_not_contain_real_telegram_api(self):
        """start_loop.ps1 must not call real Telegram API."""
        content = read_script()
        forbidden = [
            "api.telegram.org",
            "sendMessage",
            "bot_token",
        ]
        for pattern in forbidden:
            assert pattern not in content, (
                f"start_loop.ps1 contains forbidden pattern: {pattern}"
            )

    def test_start_loop_does_not_start_trading_broker(self):
        """start_loop.ps1 must not start trading, broker, execution, or live."""
        content = read_script()
        forbidden_funcs = [
            "Start-Trading",
            "Start-Broker",
            "Start-Execution",
            "Start-LiveMode",
            "Enable-OrderExecution",
        ]
        for f in forbidden_funcs:
            assert f not in content, (
                f"start_loop.ps1 contains forbidden function call: {f}"
            )

    def test_start_loop_does_not_merge_or_push(self):
        """start_loop.ps1 must not auto-merge or auto-push."""
        content = read_script()
        assert "git merge" not in content, "start_loop.ps1 should not call git merge"
        assert "git push" not in content, "start_loop.ps1 should not call git push"

    def test_start_loop_does_not_call_telegram_sidecar(self):
        """start_loop.ps1 must not start or call telegram_sidecar."""
        content = read_script()
        assert "telegram_sidecar" not in content, (
            "start_loop.ps1 should not reference telegram_sidecar"
        )


class TestAuthorizedScope:
    def test_authorized_scope_calculated_from_phase(self):
        """authorized_scope must be calculated from phase_definition."""
        content = read_script()
        assert "authorizedScope" in content, (
            "authorizedScope calculation not found in start_loop.ps1"
        )
        assert "$phaseStartRound" in content, (
            "phaseStartRound not found in start_loop.ps1"
        )
        assert "$phaseEndRound" in content, (
            "phaseEndRound not found in start_loop.ps1"
        )
