$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

$controlDir = Join-Path $repoRoot "automation\control"
$stopFlag = Join-Path $controlDir "STOP_NOW.flag"
$statePath = Join-Path $controlDir "state.runtime.json"
$templatePath = Join-Path $controlDir "state.template.json"

# Create the stop flag file
New-Item -ItemType File -Force $stopFlag | Out-Null

# Load state or use template as base
if (Test-Path $statePath) {
    $state = Get-Content $statePath -Raw | ConvertFrom-Json
} elseif (Test-Path $templatePath) {
    $state = Get-Content $templatePath -Raw | ConvertFrom-Json
} else {
    $state = [pscustomobject]@{
        schema_version = "2.0"
        run_state = "running"
        current_phase = "R-006"
        current_round = "R-006"
        phase_completion_state = "not_started"
    }
}

# Update both old and new schema fields for compatibility
$state.mode = "stopped_error"
$state.run_state = "stopped"
$state.stop_reason = "user_requested_stop_now"
$state.pause_requested = $false
$state.acceptance_mode = $false
$state.escalation_required = $true
$state.last_update = (Get-Date).ToString("s")
$state.updated_at = (Get-Date).ToString("s")
$state.last_action = "stop_now"
$state.last_error = "Immediate stop requested by user"

$state | ConvertTo-Json -Depth 10 | Set-Content $statePath -Encoding UTF8

Write-Host "Immediate stop requested." -ForegroundColor Red
Write-Host "Flag: $stopFlag"
Write-Host "State updated: $statePath"
