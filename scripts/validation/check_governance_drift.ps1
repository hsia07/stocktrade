#!/usr/bin/env pwsh
# check_governance_drift.ps1
# Governance Drift Detection Script
# 
# HARD RULE: Must execute this validation before promoting/merging single-round branches
# HARD RULE: If governance drift detected, must report BLOCKED with resolution suggestions
# HARD RULE: Single-round branches must not modify governance files
#
# Usage:
#   .\scripts\validation\check_governance_drift.ps1 -TargetBranch "candidates/R7-SILENCE-PROTECTION-001" -BaseBranch "work/r006-governance"
#   .\scripts\validation\check_governance_drift.ps1 -TargetBranch "review/R8-STATE-MACHINE-001"
#
# Returns:
#   - governance_drift: true/false
#   - decision: PASS / BLOCK
#   - drifted_files: list of governance files that differ
#   - suggested_resolution: actionable next steps

param(
    [Parameter(Mandatory=$true)]
    [string]$TargetBranch,
    
    [Parameter(Mandatory=$false)]
    [string]$BaseBranch = "work/phase1-consolidation",
    
    [Parameter(Mandatory=$false)]
    [switch]$AllowGovernanceTask = $false
)

$ErrorActionPreference = 'Stop'

# Color definitions for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Cyan = "Cyan"

function Write-Result {
    param($Type, $Message, $Color = $Green)
    Write-Host "[$Type] $Message" -ForegroundColor $Color
}

# Governance file patterns that should not be modified by single-round branches
$GovernancePatterns = @(
    "CURRENT_GOVERNANCE_BASELINE.md",
    "_governance/law/00_入口與使用規則/*",
    "_governance/law/04_交易系統法典補強版_20260416_修正版.md",
    "_governance/law/readable/*"
)

# Initialize result structure
$result = @{
    target_branch = $TargetBranch
    base_work_branch = $BaseBranch
    governance_drift_detected = $false
    drifted_files = @()
    decision = "PASS"
    suggested_resolution = @()
    timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor $Cyan
Write-Host "  Governance Drift Check" -ForegroundColor $Cyan
Write-Host "  Target: $TargetBranch" -ForegroundColor $Cyan
Write-Host "  Base: $BaseBranch" -ForegroundColor $Cyan
Write-Host "================================================================" -ForegroundColor $Cyan
Write-Host ""

# Step 1: Verify branches exist
try {
    $null = git rev-parse --verify $TargetBranch 2>&1
    Write-Result "OK" "Target branch exists: $TargetBranch"
} catch {
    Write-Result "FAIL" "Target branch does not exist: $TargetBranch" $Red
    $result.decision = "BLOCK"
    $result.suggested_resolution = @("Verify branch name exists: git branch -a | Select-String '$TargetBranch'")
    return $result | ConvertTo-Json -Depth 10
}

try {
    $null = git rev-parse --verify $BaseBranch 2>&1
    Write-Result "OK" "Base branch exists: $BaseBranch"
} catch {
    Write-Result "FAIL" "Base branch does not exist: $BaseBranch" $Red
    $result.decision = "BLOCK"
    $result.suggested_resolution = @("Verify base branch exists: git rev-parse --verify $BaseBranch")
    return $result | ConvertTo-Json -Depth 10
}

# Step 2: Get list of changed files
Write-Host "--- Checking for governance file changes ---" -ForegroundColor $Yellow

$changedFiles = @()
try {
    $output = git diff --name-only "$BaseBranch...$TargetBranch" 2>&1
    if ($output) {
        $changedFiles = $output -split "`r?`n" | Where-Object { $_ -ne "" }
    }
    Write-Host "Files changed between $BaseBranch and $TargetBranch`: $($changedFiles.Count)" -ForegroundColor $Yellow
} catch {
    Write-Result "FAIL" "Failed to get diff: $_" $Red
    $result.decision = "BLOCK"
    $result.suggested_resolution = @("Check git status and branch validity")
    return $result | ConvertTo-Json -Depth 10
}

# Step 3: Check for governance file drift
$governanceDriftDetected = $false
$driftedGovernanceFiles = @()

foreach ($file in $changedFiles) {
    $isGovernanceFile = $false
    
    foreach ($pattern in $GovernancePatterns) {
        if ($pattern -like "*/*") {
            # Directory pattern
            if ($file -like $pattern) {
                $isGovernanceFile = $true
                break
            }
        } else {
            # Exact file match
            if ($file -eq $pattern) {
                $isGovernanceFile = $true
                break
            }
        }
    }
    
    if ($isGovernanceFile) {
        $governanceDriftDetected = $true
        $driftedGovernanceFiles += $file
        Write-Result "DRIFT" "Governance file modified: $file" $Red
    }
}

# Step 4: Determine decision
if ($governanceDriftDetected) {
    if ($AllowGovernanceTask) {
        Write-Result "WARN" "Governance drift detected, but --AllowGovernanceTask flag is set" $Yellow
        Write-Result "WARN" "Ensure this is a legitimate governance task, not a single-round feature" $Yellow
        $result.decision = "PASS_WITH_WARNING"
    } else {
        Write-Result "BLOCK" "Governance drift detected in single-round branch!" $Red
        $result.governance_drift_detected = $true
        $result.drifted_files = $driftedGovernanceFiles
        $result.decision = "BLOCK"
        $result.suggested_resolution = @(
            "Option 1: Rebase target branch onto latest work branch:`n   git checkout $TargetBranch`n   git rebase $BaseBranch",
            "Option 2: Replay branch from latest work branch:`n   git checkout -b <new_branch> $BaseBranch`n   # Cherry-pick only feature commits",
            "Option 3: Split governance changes into separate governance task:`n   # Create dedicated governance task branch`n   # Apply governance changes there only"
        )
    }
} else {
    Write-Result "PASS" "No governance drift detected" $Green
    $result.governance_drift_detected = $false
    $result.decision = "PASS"
    $result.suggested_resolution = @("Proceed with promote/merge workflow")
}

# Step 5: Output full result
Write-Host ""
Write-Host "================================================================" -ForegroundColor $Cyan
Write-Host "  Governance Drift Check Result" -ForegroundColor $Cyan
Write-Host "================================================================" -ForegroundColor $Cyan
Write-Host ""

$result | ConvertTo-Json -Depth 10 | Write-Host

# Exit with appropriate code
if ($result.decision -eq "BLOCK") {
    exit 1
} else {
    exit 0
}
