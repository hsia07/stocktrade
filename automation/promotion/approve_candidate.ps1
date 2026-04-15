# approve_candidate.ps1
# Candidate approval script - validates state and writes approval record

param(
    [string]$StateFile = "automation/control/state.runtime.json",
    [string]$ApprovedFile = "automation/promotion/approved_candidate.runtime.json"
)

$ErrorActionPreference = "Stop"

function Write-Message {
    param([string]$Message, [string]$Type = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] [$Type] $Message"
}

try {
    if (-not (Test-Path $StateFile)) {
        Write-Message "State file not found: $StateFile" "ERROR"
        exit 1
    }

    $state = Get-Content $StateFile -Raw -Encoding UTF8 | ConvertFrom-Json

    $errors = @()

    if ($state.mode -ne "paused_for_acceptance") {
        $errors += "mode must be 'paused_for_acceptance', current: '$($state.mode)'"
    }

    if ([string]::IsNullOrEmpty($state.latest_candidate_id)) {
        $errors += "latest_candidate_id cannot be null or empty"
    }

    if ($state.escalation_required -eq $true) {
        $errors += "escalation_required must be false"
    }

    if ($errors.Count -gt 0) {
        Write-Message "Approval validation failed:" "ERROR"
        foreach ($err in $errors) {
            Write-Message "  - $err" "ERROR"
        }
        exit 1
    }

    $approved = @{
        round_id = $state.round_id
        branch = $state.branch
        candidate_id = $state.latest_candidate_id
        approved_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
        approved_by = "user"
    }

    $dir = Split-Path $ApprovedFile -Parent
    if ($dir -and -not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    $approved | ConvertTo-Json -Depth 10 | Set-Content $ApprovedFile -Encoding UTF8

    Write-Message "Candidate approved and recorded." "OK"
    Write-Message "  round_id: $($approved.round_id)"
    Write-Message "  candidate_id: $($approved.candidate_id)"
    Write-Message "  branch: $($approved.branch)"

    exit 0
}
catch {
    Write-Message "Unexpected error: $($_.Exception.Message)" "ERROR"
    exit 1
}
