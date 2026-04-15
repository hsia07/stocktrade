# run_candidate_aider.ps1
# Low-interaction aider automation script for candidate branch development
# Uses Ollama with qwen2.5-coder:7b model

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Task,
    
    [Parameter(Mandatory=$true, Position=1)]
    [string[]]$Files,
    
    [string]$Model = "ollama_chat/qwen2.5-coder:7b",
    [string]$CandidateId = "",
    [switch]$YesAlways,
    [string]$OutputDir = "automation/control/aider_output"
)

$ErrorActionPreference = "Stop"

# ═══════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    Write-Host $logEntry
    return $logEntry
}

function Invoke-GitCommand {
    param([string]$Arguments)
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "git"
    $psi.Arguments = $Arguments
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.WorkingDirectory = (Get-Location).Path
    
    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    $proc.Start() | Out-Null
    
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()
    
    return @{
        ExitCode = $proc.ExitCode
        StdOut = $stdout
        StdErr = $stderr
        Output = ($stdout + "`n" + $stderr).Trim()
    }
}

function Test-CommandExists {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

# ═══════════════════════════════════════════════════════════════
# Pre-flight Checks
# ═══════════════════════════════════════════════════════════════

Write-Log "=== Aider Candidate Runner Starting ==="

# Check aider is installed
if (-not (Test-CommandExists "aider")) {
    Write-Log "aider not found in PATH. Please install aider first." "ERROR"
    exit 1
}

# Check Ollama is running
try {
    $ollamaResponse = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5
    Write-Log "Ollama is running" "OK"
    
    # Check model exists
    $modelExists = $ollamaResponse.models | Where-Object { $_.name -eq "qwen2.5-coder:7b" }
    if (-not $modelExists) {
        Write-Log "Model qwen2.5-coder:7b not found in Ollama. Pulling..." "WARN"
        # Don't auto-pull, just warn
    }
} catch {
    Write-Log "Cannot connect to Ollama at localhost:11434. Please ensure Ollama is running." "ERROR"
    exit 1
}

# ═══════════════════════════════════════════════════════════════
# Branch Guards
# ═══════════════════════════════════════════════════════════════

Write-Log "Checking branch guards..."

# Get current branch
$branchResult = Invoke-GitCommand "branch --show-current"
$currentBranch = $branchResult.Output.Trim()

Write-Log "Current branch: $currentBranch"

# Only allow work/* branches
if (-not ($currentBranch -match "^work/")) {
    Write-Log "Current branch '$currentBranch' is not a work/* branch. Only work/* branches are allowed." "ERROR"
    exit 1
}
Write-Log "Branch guard passed: On work/* branch" "OK"

# Check working tree is clean
$statusResult = Invoke-GitCommand "status --porcelain"
if ($statusResult.Output) {
    Write-Log "Working tree is not clean. Uncommitted changes:" "ERROR"
    Write-Log $statusResult.Output "ERROR"
    exit 1
}
Write-Log "Working tree is clean" "OK"

# ═══════════════════════════════════════════════════════════════
# Setup Candidate Branch
# ═══════════════════════════════════════════════════════════════

if ([string]::IsNullOrEmpty($CandidateId)) {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $CandidateId = "CAND-AIDER-$timestamp"
}

$candidateBranch = "candidates/$CandidateId"
Write-Log "Candidate ID: $CandidateId"
Write-Log "Candidate branch: $candidateBranch"

# Check if candidate branch already exists locally
$localBranchResult = Invoke-GitCommand "branch --list $candidateBranch"
if ($localBranchResult.Output) {
    Write-Log "Candidate branch $candidateBranch already exists locally. Aborting." "ERROR"
    exit 1
}

# Check if candidate branch exists on remote
$remoteCheckResult = Invoke-GitCommand "ls-remote --heads origin $candidateBranch"
if ($remoteCheckResult.Output) {
    Write-Log "Candidate branch $candidateBranch already exists on remote. Aborting." "ERROR"
    exit 1
}

# Create candidate branch
Write-Log "Creating candidate branch..."
$createResult = Invoke-GitCommand "checkout -b $candidateBranch"
if ($createResult.ExitCode -ne 0) {
    Write-Log "Failed to create candidate branch: $($createResult.Output)" "ERROR"
    exit 1
}
Write-Log "Created and switched to candidate branch: $candidateBranch" "OK"

# ═══════════════════════════════════════════════════════════════
# Validate Files
# ═══════════════════════════════════════════════════════════════

Write-Log "Validating target files..."
$validFiles = @()
$invalidFiles = @()

foreach ($file in $Files) {
    if (Test-Path $file) {
        $validFiles += $file
        Write-Log "  ✓ $file"
    } else {
        $invalidFiles += $file
        Write-Log "  ✗ $file (not found)" "WARN"
    }
}

if ($validFiles.Count -eq 0) {
    Write-Log "No valid files specified. Aborting." "ERROR"
    # Return to original branch
    Invoke-GitCommand "checkout $currentBranch" | Out-Null
    Invoke-GitCommand "branch -D $candidateBranch" | Out-Null
    exit 1
}

# ═══════════════════════════════════════════════════════════════
# Setup Output Directory
# ═══════════════════════════════════════════════════════════════

$outputPath = Join-Path (Get-Location).Path $OutputDir $CandidateId
if (-not (Test-Path $outputPath)) {
    New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
}

$taskFile = Join-Path $outputPath "task.txt"
$logFile = Join-Path $outputPath "aider.log"
$diffFile = Join-Path $outputPath "candidate.diff"
$reportFile = Join-Path $outputPath "report.json"

# Write task file
$Task | Set-Content -Path $taskFile -Encoding UTF8

# ═══════════════════════════════════════════════════════════════
# Build Aider Command
# ═══════════════════════════════════════════════════════════════

$aiderArgs = @(
    "--model", $Model,
    "--no-auto-commits",
    "--no-dirty-commits",
    "--no-show-model-warnings",
    "--no-check-model-accepts-settings",
    "--message", $Task
)

# Add files
foreach ($file in $validFiles) {
    $aiderArgs += "--file"
    $aiderArgs += $file
}

# Optional: Add yes-always (explicit opt-in only)
if ($YesAlways) {
    Write-Log "WARNING: --yes-always is enabled. This allows aider to make changes without confirmation." "WARN"
    $aiderArgs += "--yes-always"
} else {
    Write-Log "Running in low-interaction mode (no --yes-always). Aider may prompt for confirmation." "INFO"
}

Write-Log "Aider command: aider $aiderArgs"

# ═══════════════════════════════════════════════════════════════
# Run Aider
# ═══════════════════════════════════════════════════════════════

Write-Log "Starting aider..."
$aiderStartTime = Get-Date

$exitCode = 0
try {
    # Run aider and capture output
    $aiderOutput = & aider @aiderArgs 2>&1
    $exitCode = $LASTEXITCODE
    
    # Write log
    $aiderOutput | Set-Content -Path $logFile -Encoding UTF8
    
    Write-Log "Aider completed with exit code: $exitCode"
} catch {
    Write-Log "Error running aider: $_" "ERROR"
    $exitCode = 1
    $aiderOutput = $_.Exception.Message
    $aiderOutput | Set-Content -Path $logFile -Encoding UTF8
}

$aiderEndTime = Get-Date

# ═══════════════════════════════════════════════════════════════
# Post-processing
# ═══════════════════════════════════════════════════════════════

Write-Log "Generating diff..."
$diffResult = Invoke-GitCommand "diff HEAD"
$diffResult.Output | Set-Content -Path $diffFile -Encoding UTF8

Write-Log "Diff saved to: $diffFile"

# Check for changes
$hasChanges = $false
if ($diffResult.Output -or (Invoke-GitCommand "status --porcelain" | Select-Object -ExpandProperty Output)) {
    $hasChanges = $true
}

# ═══════════════════════════════════════════════════════════════
# Generate Report
# ═══════════════════════════════════════════════════════════════

$report = @{
    candidate_id = $CandidateId
    source_branch = $currentBranch
    candidate_branch = $candidateBranch
    task = $Task
    files = $validFiles
    model = $Model
    yes_always = $YesAlways.IsPresent
    start_time = $aiderStartTime.ToString("yyyy-MM-ddTHH:mm:ss")
    end_time = $aiderEndTime.ToString("yyyy-MM-ddTHH:mm:ss")
    duration_seconds = [math]::Round(($aiderEndTime - $aiderStartTime).TotalSeconds, 2)
    aider_exit_code = $exitCode
    has_changes = $hasChanges
    auto_commit = $false
    auto_push = $false
    status = if ($exitCode -eq 0) { "completed" } else { "completed_with_errors" }
    outputs = @{
        task_file = $taskFile
        log_file = $logFile
        diff_file = $diffFile
        report_file = $reportFile
    }
}

$report | ConvertTo-Json -Depth 10 | Set-Content -Path $reportFile -Encoding UTF8

Write-Log "Report saved to: $reportFile"

# ═══════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════

Write-Log "=== Aider Candidate Runner Complete ==="
Write-Log ""
Write-Log "Summary:"
Write-Log "  Candidate ID: $CandidateId"
Write-Log "  Source Branch: $currentBranch"
Write-Log "  Candidate Branch: $candidateBranch"
Write-Log "  Files Modified: $($validFiles.Count)"
Write-Log "  Has Changes: $hasChanges"
Write-Log "  Auto-Commit: NO"
Write-Log "  Auto-Push: NO"
Write-Log ""
Write-Log "Outputs:"
Write-Log "  Task: $taskFile"
Write-Log "  Log: $logFile"
Write-Log "  Diff: $diffFile"
Write-Log "  Report: $reportFile"
Write-Log ""
Write-Log "Next Steps:"
Write-Log "  1. Review changes: git diff"
Write-Log "  2. Stage changes: git add <files>"
Write-Log "  3. Commit manually: git commit -m '...'"
Write-Log "  4. Push to remote: git push -u origin $candidateBranch"
Write-Log ""
Write-Log "To return to source branch: git checkout $currentBranch"

exit 0
