$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

$controlDir = Join-Path $repoRoot "automation\control"
$pauseFlag = Join-Path $controlDir "PAUSE_AFTER_CURRENT.flag"
$acceptanceFlag = Join-Path $controlDir "ACCEPTANCE_MODE.flag"
$stopFlag = Join-Path $controlDir "STOP_NOW.flag"
$statePath = Join-Path $controlDir "state.runtime.json"

if (Test-Path $pauseFlag) {
    Remove-Item $pauseFlag -Force
}

if (Test-Path $acceptanceFlag) {
    Remove-Item $acceptanceFlag -Force
}

if (Test-Path $stopFlag) {
    Remove-Item $stopFlag -Force
}

if (Test-Path $statePath) {
    $state = Get-Content $statePath -Raw | ConvertFrom-Json
} else {
    $state = [pscustomobject]@{
        mode = "running"
        round_id = "R-006"
        branch = "work/r006-governance"
        current_cycle_id = $null
        latest_candidate_id = $null
        pause_requested = $false
        acceptance_mode = $false
        escalation_required = $false
        last_update = $null
    }
}

$state.mode = "running"
$state.pause_requested = $false
$state.acceptance_mode = $false
$state.escalation_required = $false
$state.last_update = (Get-Date).ToString("s")
$state | ConvertTo-Json -Depth 5 | Set-Content $statePath -Encoding UTF8

Write-Host "Loop resumed." -ForegroundColor Green
Write-Host "State updated: $statePath"

