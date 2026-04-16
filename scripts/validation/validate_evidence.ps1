# validate_evidence.ps1
# Candidate Evidence Gate - Hard Gate for candidate_ready
# 
# HARD RULE: Must execute this validation script before marking candidate_ready
# HARD RULE: On validation failure, only report technical_unfinished / blocked
# HARD RULE: Only after passing this validation can you report candidate_ready
#
# Usage:
#   .\scripts\validation\validate_evidence.ps1 -CandidateId "TASK-001"
#
# Returns:
#   - overall_status: "PASS" or "FAIL"
#   - can_mark_candidate_ready: true or false
#   - If FAIL, must report technical_unfinished or blocked

param(
    [Parameter(Mandatory=$true)]
    [string]$CandidateId,
    
    [Parameter(Mandatory=$false)]
    [string]$CandidateDir = "automation/control/candidates",
    
    [Parameter(Mandatory=$false)]
    [string[]]$RequiredTests = @(),
    
    [Parameter(Mandatory=$false)]
    [switch]$StrictMode
)

$ErrorActionPreference = 'Stop'

# Color definitions
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"

function Write-CheckResult {
    param($Item, $Status, $Details = "")
    $symbol = if ($Status -eq "PASS") { "[OK]" } else { "[FAIL]" }
    $color = if ($Status -eq "PASS") { $Green } elseif ($Status -eq "WARN") { $Yellow } else { $Red }
    Write-Host "[$symbol] $Item : $Status" -ForegroundColor $color
    if ($Details) {
        Write-Host "    $Details" -ForegroundColor Gray
    }
}

# Initialize results
$results = @{
    candidate_id = $CandidateId
    timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    checks = @()
    overall_status = "PENDING"
    can_mark_candidate_ready = $false
    missing_evidence = @()
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Candidate Evidence Validation" -ForegroundColor Cyan
Write-Host "  Candidate ID: $CandidateId" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check if candidate directory exists
$candidatePath = Join-Path $CandidateDir $CandidateId
$dirExists = Test-Path $candidatePath -PathType Container
$results.checks += @{
    item = "candidate_directory"
    required = $true
    exists = $dirExists
    path = $candidatePath
}
Write-CheckResult -Item "Candidate Directory" -Status $(if ($dirExists) { "PASS" } else { "FAIL" }) -Details $candidatePath

if (-not $dirExists) {
    $results.overall_status = "FAIL"
    $results.missing_evidence += "candidate_directory"
    Write-Host ""
    Write-Host "Validation Failed: Candidate directory does not exist" -ForegroundColor $Red
    return $results | ConvertTo-Json -Depth 10
}

# 2. Check required evidence files
$requiredFiles = @(
    @{ name = "task.txt"; description = "Task description file"; required = $true },
    @{ name = "aider.log"; description = "Aider execution log"; required = $true },
    @{ name = "candidate.diff"; description = "Code changes diff"; required = $true },
    @{ name = "report.json"; description = "Execution report"; required = $true }
)

foreach ($file in $requiredFiles) {
    $filePath = Join-Path $candidatePath $file.name
    $exists = Test-Path $filePath -PathType Leaf
    
    $results.checks += @{
        item = $file.name
        description = $file.description
        required = $file.required
        exists = $exists
        path = $filePath
    }
    
    if (-not $exists -and $file.required) {
        $results.missing_evidence += $file.name
    }
    
    Write-CheckResult -Item $file.name -Status $(if ($exists) { "PASS" } else { if ($file.required) { "FAIL" } else { "WARN" } }) -Details $file.description
}

# 3. Check git status
Set-Location $PSScriptRoot\..\..

try {
    $gitStatus = cmd /c "git status --short 2>&1"
    $hasUncommitted = -not [string]::IsNullOrWhiteSpace($gitStatus)
    
    $results.checks += @{
        item = "git_status"
        description = "Git working tree status"
        clean = -not $hasUncommitted
        output = $gitStatus
    }
    
    Write-CheckResult -Item "Git Status" -Status $(if (-not $hasUncommitted) { "PASS" } else { "WARN" }) -Details $(if ($hasUncommitted) { "Uncommitted changes present" } else { "Working tree clean" })
} catch {
    $results.checks += @{
        item = "git_status"
        error = $_.Exception.Message
    }
    Write-CheckResult -Item "Git Status" -Status "FAIL" -Details "Cannot get git status"
}

# 4. Check git diff
$modifiedFiles = @()
try {
    $diffFiles = cmd /c "git diff --name-only HEAD 2>&1"
    if ($diffFiles) {
        $modifiedFiles = $diffFiles -split "`r?`n" | Where-Object { $_ -ne "" }
    }
    
    $results.checks += @{
        item = "git_diff"
        description = "Modified files compared to HEAD"
        modified_count = $modifiedFiles.Count
        modified_files = $modifiedFiles
    }
    
    Write-CheckResult -Item "Git Diff" -Status "INFO" -Details "$($modifiedFiles.Count) files modified"
} catch {
    $results.checks += @{
        item = "git_diff"
        error = $_.Exception.Message
    }
    Write-CheckResult -Item "Git Diff" -Status "WARN" -Details "Cannot get diff"
}

# 5. Check test evidence if specified
$testEvidenceFound = $false
if ($RequiredTests.Count -gt 0) {
    Write-Host ""
    Write-Host "--- Test Evidence Check ---" -ForegroundColor Yellow
    foreach ($testPath in $RequiredTests) {
        $fullPath = Join-Path $PSScriptRoot "..\.." $testPath
        $exists = Test-Path $fullPath -PathType Leaf
        
        $results.checks += @{
            item = "test_evidence_$testPath"
            required = $true
            exists = $exists
            path = $fullPath
        }
        
        if (-not $exists) {
            $results.missing_evidence += "test:$testPath"
        }
        
        Write-CheckResult -Item "Test: $testPath" -Status $(if ($exists) { "PASS" } else { "FAIL" })
    }
} else {
    $testEvidenceFound = $true
    Write-Host ""
    Write-Host "--- No specific test evidence required ---" -ForegroundColor Yellow
}

# 6. Check report.json content
$reportPath = Join-Path $candidatePath "report.json"
if (Test-Path $reportPath) {
    try {
        $reportContent = Get-Content $reportPath -Raw | ConvertFrom-Json
        
        $hasExitCode = $null -ne $reportContent.exit_code
        $hasChangedFiles = $null -ne $reportContent.changed_files
        $hasStatus = $null -ne $reportContent.status
        
        $results.checks += @{
            item = "report_json_content"
            has_exit_code = $hasExitCode
            has_changed_files = $hasChangedFiles
            has_status = $hasStatus
            valid = ($hasExitCode -and $hasChangedFiles -and $hasStatus)
        }
        
        Write-CheckResult -Item "Report.json Content" -Status $(if ($hasExitCode -and $hasChangedFiles -and $hasStatus) { "PASS" } else { "FAIL" })
    } catch {
        $results.checks += @{
            item = "report_json_content"
            error = $_.Exception.Message
            valid = $false
        }
        Write-CheckResult -Item "Report.json Content" -Status "FAIL" -Details "JSON parse error"
    }
}

# 7. Check safety switch
$hasSafetyIssues = $false
if ($StrictMode) {
    if ($hasUncommitted) {
        $hasSafetyIssues = $true
        $results.checks += @{
            item = "safety_switch"
            description = "Strict mode: uncommitted changes detected"
            safe = $false
        }
        Write-CheckResult -Item "Safety Switch" -Status "FAIL" -Details "Strict mode does not allow uncommitted changes"
    }
}

# Calculate final result
$requiredChecks = $results.checks | Where-Object { $_.required -eq $true }
$allRequiredPresent = ($requiredChecks | Where-Object { $_.exists -eq $false }).Count -eq 0
$noCriticalFailures = ($results.checks | Where-Object { 
    ($_.required -eq $true -and $_.exists -eq $false) -or
    ($_.item -eq "report_json_content" -and $_.valid -eq $false)
}).Count -eq 0

# candidate_ready condition check
$canBeCandidateReady = $allRequiredPresent -and $noCriticalFailures -and (-not $hasSafetyIssues)

$results.can_mark_candidate_ready = $canBeCandidateReady
$results.overall_status = if ($canBeCandidateReady) { "PASS" } else { "FAIL" }

# Determine formal status code
if (-not $canBeCandidateReady) {
    if (-not (Test-Path $candidatePath)) {
        $results.formal_status_code = "technical_unfinished"
        $results.formal_status_reason = "candidate_directory_missing"
    } elseif ($results.missing_evidence.Count -gt 0) {
        $results.formal_status_code = "technical_unfinished"
        $results.formal_status_reason = "required_evidence_missing"
    } elseif ($hasSafetyIssues) {
        $results.formal_status_code = "blocked"
        $results.formal_status_reason = "safety_check_failed"
    } else {
        $results.formal_status_code = "technical_unfinished"
        $results.formal_status_reason = "validation_failed"
    }
} else {
    $results.formal_status_code = "candidate_ready_eligible"
    $results.formal_status_reason = "all_required_evidence_present"
}

# Output result summary
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Validation Result Summary" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Overall Status: $($results.overall_status)" -ForegroundColor $(if ($results.overall_status -eq "PASS") { $Green } else { $Red })
Write-Host "Can Mark Candidate Ready: $($results.can_mark_candidate_ready)" -ForegroundColor $(if ($results.can_mark_candidate_ready) { $Green } else { $Red })

# Display formal status code
if ($results.formal_status_code) {
    Write-Host "Formal Status Code: $($results.formal_status_code)" -ForegroundColor $(if ($results.overall_status -eq "PASS") { $Green } else { $Red })
    Write-Host "Reason: $($results.formal_status_reason)" -ForegroundColor Gray
    
    if (-not $canBeCandidateReady) {
        Write-Host ""
        Write-Host "[WARN] Validation failed! Cannot report completed or candidate_ready" -ForegroundColor $Red
        Write-Host "[WARN] Must report: $($results.formal_status_code)" -ForegroundColor $Red
    }
}

if ($results.missing_evidence.Count -gt 0) {
    Write-Host ""
    Write-Host "Missing Evidence:" -ForegroundColor $Red
    foreach ($item in $results.missing_evidence) {
        Write-Host "  - $item" -ForegroundColor $Red
    }
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Output JSON result
return $results | ConvertTo-Json -Depth 10
