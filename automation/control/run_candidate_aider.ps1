# run_candidate_aider.ps1
# Run Aider on candidate branch with strict safety controls

param(
    [string]$Task,
    [string]$TaskFile,
    [string]$CandidateId,
    [string]$SourceBranch = "work/r006-governance",
    [string]$AiderPath,
    [switch]$AllowDirtyStart,
    [switch]$YesAlways
)

$ErrorActionPreference = "Stop"

function Resolve-AiderPath {
    param([string]$ExplicitPath)
    
    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        if (Test-Path $ExplicitPath) {
            Write-Host "[INFO] Using explicit AiderPath: $ExplicitPath" -ForegroundColor Green
            return $ExplicitPath
        }
        Write-Host "[WARN] Explicit AiderPath not found: $ExplicitPath" -ForegroundColor Yellow
    }
    
    try {
        $cmd = Get-Command aider -ErrorAction Stop
        if ($cmd.Source) {
            Write-Host "[INFO] Found aider via Get-Command: $($cmd.Source)" -ForegroundColor Green
            return $cmd.Source
        }
    } catch {
        Write-Host "[INFO] aider not found in PATH via Get-Command" -ForegroundColor Gray
    }
    
    $fallbackPaths = @(
        "C:\Users\richa\.local\bin\aider.exe",
        "$env:USERPROFILE\.local\bin\aider.exe"
    )
    
    foreach ($path in $fallbackPaths) {
        if (Test-Path $path) {
            Write-Host "[INFO] Found aider at fallback path: $path" -ForegroundColor Green
            return $path
        }
    }
    
    return $null
}

$AiderExe = Resolve-AiderPath -ExplicitPath $AiderPath

if (-not $AiderExe) {
    Write-Host ""
    Write-Host "[ERROR] BLOCKED: Cannot resolve aider executable" -ForegroundColor Red
    Write-Host "[ERROR] Tried:"
    Write-Host "  1. Explicit -AiderPath parameter"
    Write-Host "  2. Get-Command aider"
    Write-Host "  3. Fallback paths (C:\Users\richa\.local\bin\aider.exe)"
    Write-Host ""
    Write-Host "[ACTION] Provide -AiderPath with full path to aider.exe"
    exit 1
}

Write-Host ""
Write-Host "[INFO] Validating aider installation..." -ForegroundColor Cyan

try {
    $versionOutput = & $AiderExe --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "aider --version returned exit code $LASTEXITCODE"
    }
    Write-Host "[OK] aider version: $versionOutput" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] BLOCKED: aider validation failed" -ForegroundColor Red
    Write-Host "[ERROR] Path: $AiderExe"
    Write-Host "[ERROR] Exception: $($_.Exception.Message)"
    exit 1
}

Write-Host ""
Write-Host "=== AIDER PATH RESOLUTION SUCCESS ===" -ForegroundColor Green
Write-Host "Path: $AiderExe" -ForegroundColor Gray
Write-Host "Version: $versionOutput" -ForegroundColor Gray
Write-Host ""

$env:OLLAMA_API_BASE = "http://127.0.0.1:11434"
Write-Host "[INFO] Set OLLAMA_API_BASE=$env:OLLAMA_API_BASE" -ForegroundColor Gray

Write-Host ""
Write-Host "[INFO] Running pre-flight checks..." -ForegroundColor Cyan

$currentBranch = git branch --show-current 2>&1
if ($currentBranch -notmatch '^work/') {
    Write-Host "[ERROR] BLOCKED: Not on work/* branch" -ForegroundColor Red
    Write-Host "[ERROR] Current: $currentBranch"
    exit 1
}
Write-Host "[OK] On work branch: $currentBranch" -ForegroundColor Green

$status = git status --porcelain 2>&1
if ($status) {
    if (-not $AllowDirtyStart) {
        Write-Host "[ERROR] BLOCKED: Working tree is not clean" -ForegroundColor Red
        Write-Host "[HINT] Use -AllowDirtyStart to bypass (not recommended)"
        exit 1
    }
    Write-Host "[WARN] Working tree is dirty (AllowDirtyStart enabled)" -ForegroundColor Yellow
} else {
    Write-Host "[OK] Working tree is clean" -ForegroundColor Green
}

if ([string]::IsNullOrWhiteSpace($CandidateId)) {
    Write-Host "[ERROR] BLOCKED: -CandidateId is required" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Candidate ID: $CandidateId" -ForegroundColor Green

$taskContent = ""
if ($TaskFile -and (Test-Path $TaskFile)) {
    $taskContent = Get-Content $TaskFile -Raw
    Write-Host "[OK] Task loaded from file: $TaskFile" -ForegroundColor Green
} elseif ($Task) {
    $taskContent = $Task
    Write-Host "[OK] Task provided via parameter" -ForegroundColor Green
} else {
    Write-Host "[ERROR] BLOCKED: Either -Task or -TaskFile must be provided" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[INFO] Checking forbidden paths..." -ForegroundColor Cyan

$forbiddenPaths = @(
    "server_v2.py",
    "automation/control/control_bridge.py",
    "automation/control/refresh_panel.ps1",
    "automation/promotion/promote_candidate.ps1",
    "automation/promotion/approve_candidate.ps1"
)

$taskLower = $taskContent.ToLower()
$foundForbidden = @()
foreach ($fp in $forbiddenPaths) {
    if ($taskLower -match [regex]::Escape($fp.ToLower())) {
        $foundForbidden += $fp
    }
}

if ($foundForbidden.Count -gt 0) {
    Write-Host "[ERROR] BLOCKED: Task references forbidden paths" -ForegroundColor Red
    Write-Host "[ERROR] Forbidden: $($foundForbidden -join ', ')"
    exit 1
}
Write-Host "[OK] No forbidden paths detected in task" -ForegroundColor Green

Write-Host ""
Write-Host "[INFO] Creating candidate branch..." -ForegroundColor Cyan

$candidateBranch = "candidates/$CandidateId"

$localExists = git branch --list $candidateBranch 2>&1
if ($localExists) {
    Write-Host "[ERROR] BLOCKED: Local candidate branch already exists: $candidateBranch" -ForegroundColor Red
    exit 1
}

$remoteExists = git ls-remote --heads origin $candidateBranch 2>&1
if ($remoteExists) {
    Write-Host "[ERROR] BLOCKED: Remote candidate branch already exists: origin/$candidateBranch" -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Creating branch $candidateBranch from $currentBranch..." -ForegroundColor Gray
git checkout -b $candidateBranch 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to create candidate branch" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Created and switched to: $candidateBranch" -ForegroundColor Green

$outputDir = "automation/control/candidates/$CandidateId"
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

$taskFile = "$outputDir/task.txt"
$logFile = "$outputDir/aider.log"
$diffFile = "$outputDir/candidate.diff"
$reportFile = "$outputDir/report.json"

$taskContent | Set-Content $taskFile -Encoding UTF8
Write-Host "[OK] Task saved to: $taskFile" -ForegroundColor Gray

Write-Host ""
Write-Host "[INFO] Preparing aider command..." -ForegroundColor Cyan

$aiderArgs = @(
    "--model", "ollama_chat/qwen2.5-coder:7b",
    "--no-auto-commits",
    "--no-dirty-commits",
    "--no-show-model-warnings",
    "--no-check-model-accepts-settings",
    "--message", $taskContent
)

if ($YesAlways) {
    $aiderArgs += "--yes-always"
    Write-Host "[WARN] --yes-always enabled (explicit opt-in)" -ForegroundColor Yellow
}

Write-Host "[INFO] Model: ollama_chat/qwen2.5-coder:7b" -ForegroundColor Gray
Write-Host "[INFO] Auto-commit: DISABLED" -ForegroundColor Green
Write-Host "[INFO] Auto-push: DISABLED" -ForegroundColor Green
Write-Host "[INFO] Dirty-commit: DISABLED" -ForegroundColor Green

Write-Host ""
Write-Host "[INFO] Executing aider (single-round mode)..." -ForegroundColor Cyan
Write-Host "[INFO] Start time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

$startTime = Get-Date
$exitCode = 0

try {
    & $AiderExe @aiderArgs 2>&1 | Tee-Object -FilePath $logFile
    $exitCode = $LASTEXITCODE
} catch {
    Write-Host "[ERROR] Exception during aider execution: $($_.Exception.Message)" -ForegroundColor Red
    $exitCode = 1
}

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host ""
Write-Host "[INFO] End time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host "[INFO] Duration: $($duration.ToString('hh\:mm\:ss'))" -ForegroundColor Gray

Write-Host ""
Write-Host "[INFO] Checking for out-of-scope changes..." -ForegroundColor Cyan

$changedFiles = git diff --name-only HEAD 2>&1
$untrackedFiles = git ls-files --others --exclude-standard 2>&1
$allChanges = @($changedFiles) + @($untrackedFiles) | Where-Object { $_ }

$modifiedForbidden = @()
foreach ($fp in $forbiddenPaths) {
    $fpPattern = $fp -replace '\\', '/'
    if ($allChanges | Where-Object { $_ -match [regex]::Escape($fpPattern) }) {
        $modifiedForbidden += $fp
    }
}

$outOfScopeDetected = $modifiedForbidden.Count -gt 0

git diff HEAD > $diffFile 2>&1
Write-Host "[OK] Diff saved to: $diffFile" -ForegroundColor Gray

$report = @{
    candidate_id = $CandidateId
    candidate_branch = $candidateBranch
    source_branch = $currentBranch
    aider_path = $AiderExe
    aider_version = $versionOutput
    ollama_api_base = $env:OLLAMA_API_BASE
    model = "ollama_chat/qwen2.5-coder:7b"
    start_time = $startTime.ToString("yyyy-MM-ddTHH:mm:ss")
    end_time = $endTime.ToString("yyyy-MM-ddTHH:mm:ss")
    duration_seconds = [int]$duration.TotalSeconds
    exit_code = $exitCode
    status = if ($exitCode -eq 0 -and -not $outOfScopeDetected) { "success" } elseif ($outOfScopeDetected) { "out_of_scope_detected" } else { "failed" }
    auto_commits = $false
    auto_push = $false
    dirty_commits = $false
    yes_always = $YesAlways.IsPresent
    task_file = $taskFile
    log_file = $logFile
    diff_file = $diffFile
    changed_files = @($allChanges)
    out_of_scope_detected = $outOfScopeDetected
    modified_forbidden_paths = @($modifiedForbidden)
}

$report | ConvertTo-Json -Depth 10 | Set-Content $reportFile -Encoding UTF8
Write-Host "[OK] Report saved to: $reportFile" -ForegroundColor Gray

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "          EXECUTION SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Candidate:    $CandidateId" -ForegroundColor White
Write-Host "Branch:       $candidateBranch" -ForegroundColor White
Write-Host "Status:       $($report.status)" -ForegroundColor $(if($report.status -eq 'success'){'Green'}else{'Yellow'})
Write-Host "Exit Code:    $exitCode" -ForegroundColor $(if($exitCode -eq 0){'Green'}else{'Red'})
Write-Host "Auto-commit:  DISABLED" -ForegroundColor Green
Write-Host "Auto-push:    DISABLED" -ForegroundColor Green
Write-Host "Dirty-commit: DISABLED" -ForegroundColor Green
Write-Host ""

if ($outOfScopeDetected) {
    Write-Host "[WARN] OUT-OF-SCOPE CHANGES DETECTED:" -ForegroundColor Red
    foreach ($mf in $modifiedForbidden) {
        Write-Host "  - $mf" -ForegroundColor Red
    }
}

Write-Host "Output Directory: $outputDir" -ForegroundColor Gray
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

exit $exitCode
