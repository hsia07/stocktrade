# validate_evidence.ps1
# ?霅?摰?璈 - 霅?撽?蝖祇?瑼?
# 
# ?? 蝖祈????芸銵撽??單嚗?敺?閮?candidate_ready
# ?? 蝖祈????祇?霅仃??嚗?賢???technical_unfinished / blocked
# ?? 蝖祈????芣??祇?霅?敺??? candidate_ready
#
# 雿輻?寞?嚗?
#   .\scripts\validation\validate_evidence.ps1 -CandidateId "TASK-001"
#
# ??潘?
#   - overall_status: "PASS" ??"FAIL"
#   - can_mark_candidate_ready: true ??false
#   - ??FAIL嚗?????technical_unfinished ??blocked

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

# 憿摰儔
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

# ??????
$results = @{
    candidate_id = $CandidateId
    timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    checks = @()
    overall_status = "PENDING"
    can_mark_candidate_ready = $false
    missing_evidence = @()
}

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  Candidate Evidence Validation" -ForegroundColor Cyan
Write-Host "  Candidate ID: $CandidateId" -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# 1. 瑼Ｘ candidate ?桅??臬摮
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
    Write-Host "`n霅?撽?憭望?: Candidate ?桅?銝??? -ForegroundColor $Red
    return $results | ConvertTo-Json -Depth 10
}

# 2. 瑼Ｘ敹?霅??辣
$requiredFiles = @(
    @{ name = "task.txt"; description = "隞餃??膩?辣"; required = $true },
    @{ name = "aider.log"; description = "Aider ?瑁??亥?"; required = $true },
    @{ name = "candidate.diff"; description = "隞?Ⅳ霈 diff"; required = $true },
    @{ name = "report.json"; description = "?瑁??勗?"; required = $true }
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

# 3. 瑼Ｘ git ???
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
    
    Write-CheckResult -Item "Git Status" -Status $(if (-not $hasUncommitted) { "PASS" } else { "WARN" }) -Details $(if ($hasUncommitted) { "??漱?湔" } else { "撌乩??銋暹楊" })
} catch {
    $results.checks += @{
        item = "git_status"
        error = $_.Exception.Message
    }
    Write-CheckResult -Item "Git Status" -Status "FAIL" -Details "?⊥??? git ???
}

# 4. 瑼Ｘ git diff
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
    Write-CheckResult -Item "Git Diff" -Status "WARN" -Details "?⊥??? diff"
}

# 5. 瑼Ｘ?祈憚??皜祈岫霅?
$testEvidenceFound = $false
if ($RequiredTests.Count -gt 0) {
    Write-Host "`n--- 皜祈岫霅?瑼Ｘ ---" -ForegroundColor Yellow
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
    Write-Host "`n--- ?⊥?摰葫閰西???瘙?---" -ForegroundColor Yellow
}

# 6. 瑼Ｘ report.json ?批捆
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
        Write-CheckResult -Item "Report.json Content" -Status "FAIL" -Details "JSON 閫???航炊"
    }
}

# 7. 瑼Ｘ摰??
$hasSafetyIssues = $false
if ($StrictMode) {
    # ?典?潭芋撘?嚗遙雿?漱?湔?質??箏??典?憿?
    if ($hasUncommitted) {
        $hasSafetyIssues = $true
        $results.checks += @{
            item = "safety_switch"
            description = "Strict mode: uncommitted changes detected"
            safe = $false
        }
        Write-CheckResult -Item "Safety Switch" -Status "FAIL" -Details "?湔璅∪?銝??迂?芣?鈭斗??
    }
}

# 閮??蝯???
$requiredChecks = $results.checks | Where-Object { $_.required -eq $true }
$allRequiredPresent = ($requiredChecks | Where-Object { $_.exists -eq $false }).Count -eq 0
$noCriticalFailures = ($results.checks | Where-Object { 
    ($_.required -eq $true -and $_.exists -eq $false) -or
    ($_.item -eq "report_json_content" -and $_.valid -eq $false)
}).Count -eq 0

# candidate_ready 璇辣?文?
$canBeCandidateReady = $allRequiredPresent -and $noCriticalFailures -and (-not $hasSafetyIssues)

$results.can_mark_candidate_ready = $canBeCandidateReady
$results.overall_status = if ($canBeCandidateReady) { "PASS" } else { "FAIL" }

# ?文?甇????Ⅳ
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

# 頛詨蝯???
Write-Host "`n???????????????????????????????????????????????????????????????? -ForegroundColor Cyan
Write-Host "  撽?蝯???" -ForegroundColor Cyan
Write-Host "???????????????????????????????????????????????????????????????? -ForegroundColor Cyan
Write-Host "Overall Status: $($results.overall_status)" -ForegroundColor $(if ($results.overall_status -eq "PASS") { $Green } else { $Red })
Write-Host "Can Mark Candidate Ready: $($results.can_mark_candidate_ready)" -ForegroundColor $(if ($results.can_mark_candidate_ready) { $Green } else { $Red })

# 憿舐內甇????Ⅳ
if ($results.formal_status_code) {
    Write-Host "Formal Status Code: $($results.formal_status_code)" -ForegroundColor $(if ($results.overall_status -eq "PASS") { $Green } else { $Red })
    Write-Host "Reason: $($results.formal_status_reason)" -ForegroundColor Gray
    
    if (-not $canBeCandidateReady) {
        Write-Host "`n??  撽?憭望?嚗?敺???completed ??candidate_ready" -ForegroundColor $Red
        Write-Host "??  敹??: $($results.formal_status_code)" -ForegroundColor $Red
    }
}

if ($results.missing_evidence.Count -gt 0) {
    Write-Host "`nMissing Evidence:" -ForegroundColor $Red
    foreach ($item in $results.missing_evidence) {
        Write-Host "  - $item" -ForegroundColor $Red
    }
}

Write-Host "`n???????????????????????????????????????????????????????????????n" -ForegroundColor Cyan

# 頛詨 JSON 蝯?
return $results | ConvertTo-Json -Depth 10

