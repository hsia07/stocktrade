# promote_candidate.ps1
# Candidate promotion script - reads approval and prepares promotion plan

param(
    [string]$ApprovedFile = "automation/promotion/approved_candidate.runtime.json",
    [string]$PlanFile = "automation/promotion/promotion_plan.runtime.json"
)

$ErrorActionPreference = "Stop"

function Write-Message {
    param([string]$Message, [string]$Type = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] [$Type] $Message"
}

try {
    if (-not (Test-Path $ApprovedFile)) {
        Write-Message "Approved candidate file not found: $ApprovedFile" "ERROR"
        Write-Message "Please run approve_candidate.ps1 first." "ERROR"
        exit 1
    }

    $approved = Get-Content $ApprovedFile -Raw -Encoding UTF8 | ConvertFrom-Json

    $errors = @()
    if ([string]::IsNullOrEmpty($approved.round_id)) {
        $errors += "round_id is missing"
    }
    if ([string]::IsNullOrEmpty($approved.candidate_id)) {
        $errors += "candidate_id is missing"
    }
    if ([string]::IsNullOrEmpty($approved.branch)) {
        $errors += "branch is missing"
    }

    if ($errors.Count -gt 0) {
        Write-Message "Approved candidate validation failed:" "ERROR"
        foreach ($err in $errors) {
            Write-Message "  - $err" "ERROR"
        }
        exit 1
    }

    $reviewBranch = "review/$($approved.candidate_id)"

    $plan = @{
        round_id = $approved.round_id
        candidate_id = $approved.candidate_id
        source_branch = $approved.branch
        review_branch = $reviewBranch
        approved_at = $approved.approved_at
        approved_by = $approved.approved_by
        plan_created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
        status = "ready_for_promotion"
        steps = @(
            @{ step = 1; description = "Create review branch from $($approved.branch)"; status = "pending" }
            @{ step = 2; description = "Run CI/CD validation"; status = "pending" }
            @{ step = 3; description = "Code review"; status = "pending" }
            @{ step = 4; description = "Merge to master (NOT IMPLEMENTED)"; status = "pending" }
        )
    }

    $dir = Split-Path $PlanFile -Parent
    if ($dir -and -not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    $plan | ConvertTo-Json -Depth 10 | Set-Content $PlanFile -Encoding UTF8

    Write-Message "Promotion plan prepared." "OK"
    Write-Message "  round_id: $($plan.round_id)"
    Write-Message "  candidate_id: $($plan.candidate_id)"
    Write-Message "  review_branch: $($plan.review_branch)"

    exit 0
}
catch {
    Write-Message "Unexpected error: $($_.Exception.Message)" "ERROR"
    exit 1
}
