$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

$controlDir = Join-Path $repoRoot "automation\control"
$stopFlag = Join-Path $controlDir "STOP_NOW.flag"
$statePath = Join-Path $controlDir "state.json"

New-Item -ItemType File -Force $stopFlag | Out-Null

if (Test-Path $statePath) {
    $state = Get-Content $statePath -Raw | ConvertFrom-Json
} else {
    $state = [pscustomobject]@{
        mode = "stopped_error"
        round_id = "R-006"
        branch = "work/r006-governance"
        current_cycle_id = $null
        latest_candidate_id = $null
        pause_requested = $false
        acceptance_mode = $false
        escalation_required = $true
        last_update = $null
    }
}

$state.mode = "stopped_error"
$state.pause_requested = $false
$state.acceptance_mode = $false
$state.escalation_required = $true
$state.last_update = (Get-Date).ToString("s")
$state | ConvertTo-Json -Depth 5 | Set-Content $statePath -Encoding UTF8

Write-Host "Immediate stop requested." -ForegroundColor Red
Write-Host "Flag: $stopFlag"
Write-Host "State updated: $statePath"
