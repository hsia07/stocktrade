$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

$controlDir = Join-Path $repoRoot "automation\control"
$flagPath = Join-Path $controlDir "PAUSE_AFTER_CURRENT.flag"
$statePath = Join-Path $controlDir "state.runtime.json"
$templatePath = Join-Path $controlDir "state.template.json"

# Create the flag file
New-Item -ItemType File -Force $flagPath | Out-Null

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
$state.pause_requested = $true
$state.last_update = (Get-Date).ToString("s")
$state.updated_at = (Get-Date).ToString("s")
$state.last_action = "drain_requested"

$state | ConvertTo-Json -Depth 10 | Set-Content $statePath -Encoding UTF8

Write-Host "Drain requested. Will pause after current cycle." -ForegroundColor Yellow
Write-Host "Flag: $flagPath"
Write-Host "State updated: $statePath"
