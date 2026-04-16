# validate_evidence.ps1
# 候選證據守門機制 - 證據驗證硬門檻
# 
# ⚠️ 硬規則：未執行本驗證腳本，不得標記 candidate_ready
# ⚠️ 硬規則：本驗證失敗時，只能回報 technical_unfinished / blocked
# ⚠️ 硬規則：只有本驗證通過後，才可回報 candidate_ready
#
# 使用方法：
#   .\scripts\validation\validate_evidence.ps1 -CandidateId "TASK-001"
#
# 回傳值：
#   - overall_status: "PASS" 或 "FAIL"
#   - can_mark_candidate_ready: true 或 false
#   - 若 FAIL，必須回報 technical_unfinished 或 blocked

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

# 顏色定義
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"

function Write-CheckResult {
    param($Item, $Status, $Details = "")
    $symbol = if ($Status -eq "PASS") { "✓" } else { "✗" }
    $color = if ($Status -eq "PASS") { $Green } elseif ($Status -eq "WARN") { $Yellow } else { $Red }
    Write-Host "[$symbol] $Item : $Status" -ForegroundColor $color
    if ($Details) {
        Write-Host "    $Details" -ForegroundColor Gray
    }
}

# 初始化結果
$results = @{
    candidate_id = $CandidateId
    timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    checks = @()
    overall_status = "PENDING"
    can_mark_candidate_ready = $false
    missing_evidence = @()
}

Write-Host "`n═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  候選證據驗證 - Candidate Evidence Validation" -ForegroundColor Cyan
Write-Host "  Candidate ID: $CandidateId" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

# 1. 檢查 candidate 目錄是否存在
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
    Write-Host "`n證據驗證失敗: Candidate 目錄不存在" -ForegroundColor $Red
    return $results | ConvertTo-Json -Depth 10
}

# 2. 檢查必需證據文件
$requiredFiles = @(
    @{ name = "task.txt"; description = "任務描述文件"; required = $true },
    @{ name = "aider.log"; description = "Aider 執行日誌"; required = $true },
    @{ name = "candidate.diff"; description = "代碼變更 diff"; required = $true },
    @{ name = "report.json"; description = "執行報告"; required = $true }
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

# 3. 檢查 git 狀態
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
    
    Write-CheckResult -Item "Git Status" -Status $(if (-not $hasUncommitted) { "PASS" } else { "WARN" }) -Details $(if ($hasUncommitted) { "有未提交更改" } else { "工作區乾淨" })
} catch {
    $results.checks += @{
        item = "git_status"
        error = $_.Exception.Message
    }
    Write-CheckResult -Item "Git Status" -Status "FAIL" -Details "無法取得 git 狀態"
}

# 4. 檢查 git diff
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
    Write-CheckResult -Item "Git Diff" -Status "WARN" -Details "無法取得 diff"
}

# 5. 檢查本輪指定測試證據
$testEvidenceFound = $false
if ($RequiredTests.Count -gt 0) {
    Write-Host "`n--- 測試證據檢查 ---" -ForegroundColor Yellow
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
    Write-Host "`n--- 無指定測試證據要求 ---" -ForegroundColor Yellow
}

# 6. 檢查 report.json 內容
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
        Write-CheckResult -Item "Report.json Content" -Status "FAIL" -Details "JSON 解析錯誤"
    }
}

# 7. 檢查安全開關
$hasSafetyIssues = $false
if ($StrictMode) {
    # 在嚴格模式下，任何未提交更改都視為安全問題
    if ($hasUncommitted) {
        $hasSafetyIssues = $true
        $results.checks += @{
            item = "safety_switch"
            description = "Strict mode: uncommitted changes detected"
            safe = $false
        }
        Write-CheckResult -Item "Safety Switch" -Status "FAIL" -Details "嚴格模式下不允許未提交更改"
    }
}

# 計算最終結果
$requiredChecks = $results.checks | Where-Object { $_.required -eq $true }
$allRequiredPresent = ($requiredChecks | Where-Object { $_.exists -eq $false }).Count -eq 0
$noCriticalFailures = ($results.checks | Where-Object { 
    ($_.required -eq $true -and $_.exists -eq $false) -or
    ($_.item -eq "report_json_content" -and $_.valid -eq $false)
}).Count -eq 0

# candidate_ready 條件判定
$canBeCandidateReady = $allRequiredPresent -and $noCriticalFailures -and (-not $hasSafetyIssues)

$results.can_mark_candidate_ready = $canBeCandidateReady
$results.overall_status = if ($canBeCandidateReady) { "PASS" } else { "FAIL" }

# 判定正式狀態碼
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

# 輸出結果摘要
Write-Host "`n═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  驗證結果摘要" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Overall Status: $($results.overall_status)" -ForegroundColor $(if ($results.overall_status -eq "PASS") { $Green } else { $Red })
Write-Host "Can Mark Candidate Ready: $($results.can_mark_candidate_ready)" -ForegroundColor $(if ($results.can_mark_candidate_ready) { $Green } else { $Red })

# 顯示正式狀態碼
if ($results.formal_status_code) {
    Write-Host "Formal Status Code: $($results.formal_status_code)" -ForegroundColor $(if ($results.overall_status -eq "PASS") { $Green } else { $Red })
    Write-Host "Reason: $($results.formal_status_reason)" -ForegroundColor Gray
    
    if (-not $canBeCandidateReady) {
        Write-Host "`n⚠️  驗證失敗！不得回報 completed 或 candidate_ready" -ForegroundColor $Red
        Write-Host "⚠️  必須回報: $($results.formal_status_code)" -ForegroundColor $Red
    }
}

if ($results.missing_evidence.Count -gt 0) {
    Write-Host "`nMissing Evidence:" -ForegroundColor $Red
    foreach ($item in $results.missing_evidence) {
        Write-Host "  - $item" -ForegroundColor $Red
    }
}

Write-Host "`n═══════════════════════════════════════════════════════════════`n" -ForegroundColor Cyan

# 輸出 JSON 結果
return $results | ConvertTo-Json -Depth 10
