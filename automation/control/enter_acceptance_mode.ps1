$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

$controlDir = Join-Path $repoRoot "automation\control"
$pauseFlag = Join-Path $controlDir "PAUSE_AFTER_CURRENT.flag"
$acceptanceFlag = Join-Path $controlDir "ACCEPTANCE_MODE.flag"
$statePath = Join-Path $controlDir "state.json"

New-Item -ItemType File -Force $acceptanceFlag | Out-Null

if (Test-Path $pauseFlag) {
    Remove-Item $pauseFlag -Force
}

if (Test-Path $statePath) {
    $state = Get-Content $statePath -Raw | ConvertFrom-Json
} else {
    $state = [pscustomobject]@{
        mode = "paused_for_acceptance"
        round_id = "R-006"
        branch = "work/r006-governance"
        current_cycle_id = $null
        latest_candidate_id = $null
        pause_requested = $false
        acceptance_mode = $true
        escalation_required = $false
        last_update = $null
    }
}

$state.mode = "paused_for_acceptance"
$state.pause_requested = $false
$state.acceptance_mode = $true
$state.last_update = (Get-Date).ToString("s")
$state | ConvertTo-Json -Depth 5 | Set-Content $statePath -Encoding UTF8

Write-Host "System is now paused for acceptance." -ForegroundColor Green
Write-Host "State updated: $statePath"
