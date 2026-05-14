#!/usr/bin/env pwsh
# start_loop.ps1
# Backend script for Start/Resume button - launches the main control loop
# This provides the real backend chain: button -> bridge -> actual command

param(
    [switch]$Resume = $false,
    [string]$Phase = "",
    [string]$StartRound = "",
    [switch]$DryRun = $false
)

$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
Set-Location $repoRoot

$controlDir = Join-Path $repoRoot "automation\control"
$statePath = Join-Path $controlDir "state.runtime.json"
$loopScript = Join-Path $controlDir "main_control_loop.ps1"
$logFile = Join-Path $controlDir "logs\start_loop_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

# Ensure log directory exists
$logDir = Split-Path $logFile -Parent
if (!(Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

# Schema normalization: ensure all required state fields exist with safe-deny defaults
function Initialize-StateSchema {
    param($State, $Phase, $StartRound)

    if (-not ($State.PSObject.Properties.Name -contains 'current_mode')) {
        $State | Add-Member -NotePropertyName 'current_mode' -NotePropertyValue 'idle'
    }

    if (-not ($State.PSObject.Properties.Name -contains 'stop_reason')) {
        $State | Add-Member -NotePropertyName 'stop_reason' -NotePropertyValue $null
    }

    if (-not ($State.PSObject.Properties.Name -contains 'phase_definition')) {
        $def = [PSCustomObject]@{}
        $def | Add-Member -NotePropertyName $Phase -NotePropertyValue ([PSCustomObject]@{start_round = $StartRound; end_round = $StartRound})
        $State | Add-Member -NotePropertyName 'phase_definition' -NotePropertyValue $def
    } elseif (-not $State.phase_definition.$Phase) {
        $State.phase_definition | Add-Member -NotePropertyName $Phase -NotePropertyValue ([PSCustomObject]@{start_round = $StartRound; end_round = $StartRound})
    }

    if (-not ($State.PSObject.Properties.Name -contains 'authorized_scope')) {
        $State | Add-Member -NotePropertyName 'authorized_scope' -NotePropertyValue ''
    }

    if (-not ($State.PSObject.Properties.Name -contains 'desired_action')) {
        $State | Add-Member -NotePropertyName 'desired_action' -NotePropertyValue 'none'
    }

    if (-not ($State.PSObject.Properties.Name -contains 'merge_gate')) {
        $gate = [PSCustomObject]@{current_decision_state = 'closed'}
        $State | Add-Member -NotePropertyName 'merge_gate' -NotePropertyValue $gate
    }

    if (-not ($State.PSObject.Properties.Name -contains 'updated_at')) {
        $State | Add-Member -NotePropertyName 'updated_at' -NotePropertyValue ''
    }

    if (-not ($State.PSObject.Properties.Name -contains 'candidate_checklist')) {
        $checklist = [PSCustomObject]@{
            formal_status_code = 'not_started'
            theme_completed = $false
            rerunnable_tests_passed = $false
            evidence_package_complete = $false
            validate_evidence_ps1_executed = $false
            validate_evidence_result = $null
            validate_evidence_executed_at = $null
            validate_evidence_exit_code = $null
            candidate_branch_auditable = $false
            candidate_commit_auditable = $false
            no_fabricated_evidence = $false
            no_unauthorized_modifications = $false
            complete_return_to_chatgpt = $false
        }
        $State | Add-Member -NotePropertyName 'candidate_checklist' -NotePropertyValue $checklist
    }

    return $State
}

# Safe property setter: adds property via Add-Member if missing, then sets value.
function Set-StateProperty {
    param($State, [string]$PropertyName, $Value)
    if (-not ($State.PSObject.Properties.Name -contains $PropertyName)) {
        $State | Add-Member -NotePropertyName $PropertyName -NotePropertyValue $Value
    } else {
        $State.$PropertyName = $Value
    }
}

Write-Host "[START] Initializing control loop..." -ForegroundColor Cyan
Write-Host "[START] Mode: $(if ($Resume) { 'RESUME' } else { 'START' })" -ForegroundColor Cyan
Write-Host "[START] Mode Definition: Multi-Round Candidate Pre-Fabrication Mode" -ForegroundColor Yellow
Write-Host "[START]   - Will auto-process rounds within authorized phase" -ForegroundColor Gray
Write-Host "[START]   - Each round becomes independent candidate (not formal pass)" -ForegroundColor Gray
Write-Host "[START]   - Will NOT auto-merge or auto-push" -ForegroundColor Gray
Write-Host "[START]   - Will stop if any round fails to reach candidate_ready" -ForegroundColor Gray
Write-Host "[START]   - Merge requires explicit user signoff per round" -ForegroundColor Gray
Write-Host "[START] Phase: $Phase" -ForegroundColor Cyan
Write-Host "[START] Start Round: $StartRound" -ForegroundColor Cyan

# Load and validate state
if (!(Test-Path $statePath)) {
    throw "State file not found: $statePath"
}

$stateJson = [System.IO.File]::ReadAllText($statePath, [System.Text.Encoding]::UTF8)
$state = $stateJson | ConvertFrom-Json

# Resolve Phase / StartRound: prefer explicit params, then state fields, then fail closed
$formattedPhase = if ($Phase) { $Phase } elseif ($state.current_phase) { $state.current_phase } else { "" }
$formattedRound = if ($StartRound) { $StartRound } elseif ($state.current_round) { $state.current_round } else { "" }
if (-not $formattedPhase -or -not $formattedRound) {
    Write-Host ""
    Write-Host "[BLOCKED] Cannot determine Phase / StartRound." -ForegroundColor Red
    Write-Host "[BLOCKED] Provide -Phase and -StartRound parameters, or ensure state.runtime.json has current_phase and current_round." -ForegroundColor Yellow
    Write-Host "[BLOCKED] Current context: Phase 2 / R017" -ForegroundColor Yellow
    Write-Host ""
    $state.run_state = "stopped_error"
    $state.stop_reason = "missing_phase_or_round"
    $state.last_error = "Phase/StartRound not specified and state lacks current_phase/current_round"
    $json = $state | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($statePath, $json, [System.Text.Encoding]::UTF8)
    exit 1
}

# Formal round mapping (Phase 1 = R001-R016, Phase 2 = R017-R048, Phase 3 = R049-R132, Phase 4 = R133-R161)
$formalRounds = @{
    "Phase 1" = @{ start_round = "R001"; end_round = "R016" }
    "Phase 2" = @{ start_round = "R017"; end_round = "R048" }
    "Phase 3" = @{ start_round = "R049"; end_round = "R132" }
    "Phase 4" = @{ start_round = "R133"; end_round = "R161" }
}

# Validate formal phase name
if (-not $formalRounds.ContainsKey($formattedPhase)) {
    Write-Host ""
    Write-Host "[BLOCKED] Unknown phase: $formattedPhase" -ForegroundColor Red
    Write-Host "[BLOCKED] Valid phases: Phase 1, Phase 2, Phase 3, Phase 4" -ForegroundColor Yellow
    exit 1
}

# Validate round is within phase bounds
$phaseRounds = $formalRounds[$formattedPhase]
$startNum = [int]$formattedRound.Substring(1)  # strip leading R
$phaseStartNum = [int]$phaseRounds.start_round.Substring(1)
$phaseEndNum = [int]$phaseRounds.end_round.Substring(1)
if ($startNum -lt $phaseStartNum -or $startNum -gt $phaseEndNum) {
    Write-Host ""
    Write-Host "[BLOCKED] Round $formattedRound is not within $formattedPhase ($($phaseRounds.start_round)-$($phaseRounds.end_round))." -ForegroundColor Red
    exit 1
}

# Use resolved values
$Phase = $formattedPhase
$StartRound = $formattedRound

# Normalize state schema: add missing fields with safe-deny defaults
$state = Initialize-StateSchema -State $state -Phase $Phase -StartRound $StartRound

# Check for phase completion stop
if ($state.stop_reason -eq "phase_completed") {
    Write-Host ""
    Write-Host "[BLOCKED] Cannot start/resume - phase was completed." -ForegroundColor Red
    Write-Host "[BLOCKED] Current Phase: $($state.current_phase)" -ForegroundColor Yellow
    Write-Host "[BLOCKED] Stop Reason: phase_completed" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "[ACTION] To proceed to next phase, manual authorization is required:" -ForegroundColor Cyan
    Write-Host "  1. Review latest run report: automation\control\reports\latest_run_report.json" -ForegroundColor White
    Write-Host "  2. Provide explicit new phase authorization" -ForegroundColor White
    Write-Host "  3. Or call with -Phase parameter: start_loop.ps1 -Phase R-007 -StartRound R-007" -ForegroundColor White
    exit 1
}

# Check if already running
if ($state.run_state -eq "running" -and !$Resume) {
    Write-Host "[WARN] Loop is already running. Use -Resume flag or wait for completion." -ForegroundColor Yellow
    exit 1
}

# Clear any stale flags
$pauseFlag = Join-Path $controlDir "PAUSE_AFTER_CURRENT.flag"
$stopFlag = Join-Path $controlDir "STOP_NOW.flag"
$acceptanceFlag = Join-Path $controlDir "ACCEPTANCE_MODE.flag"

foreach ($flag in @($pauseFlag, $stopFlag, $acceptanceFlag)) {
    if (Test-Path $flag) {
        Remove-Item $flag -Force
        Write-Host "[START] Cleared stale flag: $(Split-Path $flag -Leaf)" -ForegroundColor Gray
    }
}

# Calculate authorized scope based on phase
$phaseStartRound = $state.phase_definition.($Phase).start_round
$phaseEndRound = $state.phase_definition.($Phase).end_round
$authorizedScope = "$phaseStartRound ~ $phaseEndRound"

# Update state with multi-round candidate prep mode
$allowedCurrentModes = @("idle", "multi_round_candidate_prep", "stopped", "paused")
Set-StateProperty -State $state -PropertyName "run_state" -Value "running"
Set-StateProperty -State $state -PropertyName "status_flags" -Value $state.status_flags
$state.status_flags.whether_started = $true
Set-StateProperty -State $state -PropertyName "current_mode" -Value "multi_round_candidate_prep"
Set-StateProperty -State $state -PropertyName "authorized_scope" -Value $authorizedScope
Set-StateProperty -State $state -PropertyName "last_action" -Value "loop_start_multi_round_candidate_prep"
Set-StateProperty -State $state -PropertyName "last_error" -Value $null
Set-StateProperty -State $state -PropertyName "stop_reason" -Value $null
Set-StateProperty -State $state -PropertyName "current_phase" -Value $Phase
if (-not $state.current_round) { Set-StateProperty -State $state -PropertyName "current_round" -Value $StartRound }
Set-StateProperty -State $state -PropertyName "desired_action" -Value "auto_execute_rounds_candidate_only"
if ($state.merge_gate) { $state.merge_gate.current_decision_state = "candidate_prep_in_progress" }
if ($state.candidate_checklist) { $state.candidate_checklist.formal_status_code = "candidate_prep_in_progress" }
Set-StateProperty -State $state -PropertyName "updated_at" -Value ((Get-Date).ToString("yyyy-MM-ddTHH:mm:ss"))

# Reset all 10 candidate criteria for new run
$state.candidate_checklist.theme_completed = $false
$state.candidate_checklist.rerunnable_tests_passed = $false
$state.candidate_checklist.evidence_package_complete = $false
$state.candidate_checklist.validate_evidence_ps1_executed = $false
$state.candidate_checklist.validate_evidence_result = $null
$state.candidate_checklist.validate_evidence_executed_at = $null
$state.candidate_checklist.validate_evidence_exit_code = $null
$state.candidate_checklist.candidate_branch_auditable = $false
$state.candidate_checklist.candidate_commit_auditable = $false
$state.candidate_checklist.no_fabricated_evidence = $false
$state.candidate_checklist.no_unauthorized_modifications = $false
$state.candidate_checklist.complete_return_to_chatgpt = $false

$json = $state | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($statePath, $json, [System.Text.Encoding]::UTF8)

Write-Host "[START] State updated: run_state = running, mode = multi_round_candidate_prep" -ForegroundColor Green
Write-Host "[START] Authorized scope: $authorizedScope" -ForegroundColor Gray
Write-Host "[START] Legal effect: Candidate prep only, NO auto-merge/push" -ForegroundColor Yellow

# Verify main control loop script exists
if (!(Test-Path $loopScript)) {
    $state.run_state = "stopped_error"
    $state.stop_reason = "missing_control_script"
    $state.last_error = "Main control loop script not found: $loopScript"
    Save-State -State $state
    throw "Main control loop script not found: $loopScript"
}

# Launch the main control loop
Write-Host ""
Write-Host "[START] Launching main control loop..." -ForegroundColor Green
Write-Host "[START] Script: $loopScript" -ForegroundColor Gray
Write-Host "[START] Log: $logFile" -ForegroundColor Gray
Write-Host ""

# Build arguments - pass repo root to main control loop
$loopArgs = @(
    "-RepoRoot", $repoRoot
)

if ($Resume) {
    $loopArgs += "-Resume"
}

if ($DryRun) {
    $loopArgs += "-DryRun"
}

try {
    # Start the loop and capture output with UTF-8 encoding
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "powershell.exe"
    $argStr = ($loopArgs | ForEach-Object {
        if ($_ -match '\s') { "`"$_`"" } else { $_ }
    }) -join ' '
    $psi.Arguments = "-ExecutionPolicy Bypass -NoProfile -File `"$loopScript`" $argStr"
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.WorkingDirectory = $repoRoot
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
    
    $proc = [System.Diagnostics.Process]::Start($psi)
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()
    $exitCode = $proc.ExitCode
    
    # Write output to log with UTF-8 encoding
    $logWriter = New-Object System.IO.StreamWriter($logFile, $false, [System.Text.Encoding]::UTF8)
    $logWriter.WriteLine($stdout)
    if ($stderr) { $logWriter.WriteLine($stderr) }
    $logWriter.Close()
    
    # Print stdout to console
    Write-Host $stdout
    if ($stderr) { Write-Host $stderr }
    
    if ($exitCode -eq 0) {
        Write-Host ""
        Write-Host "[START] Main control loop completed successfully." -ForegroundColor Green
        Write-Host "[START] Check run report for details." -ForegroundColor Gray
    } else {
        Write-Host ""
        Write-Host "[START] Main control loop exited with code: $exitCode" -ForegroundColor Red
        Write-Host "[START] Check log for details: $logFile" -ForegroundColor Yellow
    }
    
    exit $exitCode
    
} catch {
    Write-Host ""
    Write-Host "[START] ERROR starting control loop: $($_)" -ForegroundColor Red
    
    # Update state with error
    $state.run_state = "stopped_error"
    $state.stop_reason = "start_failed"
    $state.last_error = $_.Exception.Message
    $state | ConvertTo-Json -Depth 10 | Out-Null
    $stateJson = $state | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($statePath, $stateJson, [System.Text.Encoding]::UTF8)
    
    exit 1
}

# Helper function
function Save-State {
    param($State)
    Set-StateProperty -State $State -PropertyName "updated_at" -Value ((Get-Date).ToString("yyyy-MM-ddTHH:mm:ss"))
    $json = $State | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($statePath, $json, [System.Text.Encoding]::UTF8)
}
