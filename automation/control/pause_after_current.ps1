$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

$controlDir = Join-Path $repoRoot "automation\control"
$flagPath = Join-Path $controlDir "PAUSE_AFTER_CURRENT.flag"
$statePath = Join-Path $controlDir "state.json"

New-Item -ItemType File -Force $flagPath | Out-Null

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

$state.pause_requested = $true
$state.last_update = (Get-Date).ToString("s")
$state | ConvertTo-Json -Depth 5 | Set-Content $statePath -Encoding UTF8

Write-Host "Drain requested. Will pause after current cycle." -ForegroundColor Yellow
Write-Host "Flag: $flagPath"
Write-Host "State updated: $statePath"
