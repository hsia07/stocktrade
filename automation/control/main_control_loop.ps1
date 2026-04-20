#!/usr/bin/env pwsh
# main_control_loop.ps1 - Fail-Closed Anti-False-Candidate Engine
# OpenCode = Primary Contractor Responsibility
# Aider/Tool Failure = BLOCKED (no candidate_ready)

param(
    [string]$RepoRoot = ".",
    [switch]$NoAdvance,
    [switch]$DrainMode,
    [int]$MaxRounds = 999
)

$ErrorActionPreference = "Stop"  # CHANGED: Stop on error, not Continue

$controlDir = Join-Path $RepoRoot "automation\control"
$statePath = Join-Path $controlDir "state.runtime.json"
$runHistoryPath = Join-Path $controlDir "run_history.json"
$candidatesDir = Join-Path $controlDir "candidates"
$manifestPath = Join-Path $RepoRoot "manifests\current_round.yaml"
$runRecordPath = Join-Path $RepoRoot "reports\run_record.json"
$reviewPacketPath = Join-Path $RepoRoot "reports\review_packet.md"

# ========== FAIL-CLOSED GUARD FUNCTIONS ==========

function Write-Marker {
    param([string]$Message, [string]$Color = "White")
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor $Color
}

function Guard-StartEvent {
    # GUARD C: No real Start event = BLOCKED
    param($state)
    
    if ($state.run_state -ne "running") {
        Write-Marker "GUARD_VIOLATION: No real Start event detected. State is '$($state.run_state)', expected 'running'" "Red"
        return @{passed=$false; blocker="NO_START_EVENT"}
    }
    
    if ($state.status_flags.whether_started -ne $true) {
        Write-Marker "GUARD_VIOLATION: whether_started flag is not true" "Red"
        return @{passed=$false; blocker="START_FLAG_NOT_SET"}
    }
    
    Write-Marker "GUARD_PASS: Start event verified" "Green"
    return @{passed=$true; blocker=$null}
}

function Guard-ToolExecution {
    # GUARD B: Aider/Tool failure = BLOCKED
    # Since we're OpenCode (primary), we execute directly. If we fail, we BLOCK.
    param($toolOutput, $toolExitCode)
    
    if ($toolExitCode -ne 0) {
        Write-Marker "GUARD_VIOLATION: Tool execution failed with exit code $toolExitCode" "Red"
        return @{passed=$false; blocker="TOOL_EXECUTION_FAILED"}
    }
    
    if ($toolOutput -match "error|fail|exception" -and $toolOutput -notmatch "no error|no fail") {
        Write-Marker "GUARD_VIOLATION: Tool output contains error indicators" "Red"
        return @{passed=$false; blocker="TOOL_OUTPUT_ERROR"}
    }
    
    Write-Marker "GUARD_PASS: Tool execution verified" "Green"
    return @{passed=$true; blocker=$null}
}

function Guard-FunctionalCommit {
    # GUARD D: No functional commit = BLOCKED
    param($roundId, $beforeCommit, $afterCommit)
    
    if ($beforeCommit -eq $afterCommit) {
        Write-Marker "GUARD_VIOLATION: No new commit created. Before=$beforeCommit, After=$afterCommit" "Red"
        return @{passed=$false; blocker="NO_FUNCTIONAL_COMMIT"}
    }
    
    # Check that the commit is actually NEW for this round
    $commitMessage = git -C $RepoRoot log -1 --format=%B $afterCommit 2>$null
    if ($commitMessage -notmatch $roundId) {
        Write-Marker "GUARD_VIOLATION: Commit message does not reference $roundId. Message: $commitMessage" "Red"
        return @{passed=$false; blocker="COMMIT_NOT_ROUND_SPECIFIC"}
    }
    
    Write-Marker "GUARD_PASS: Functional commit verified ($afterCommit)" "Green"
    return @{passed=$true; blocker=$null; commit=$afterCommit}
}

function Guard-CandidateDiff {
    # GUARD E: candidate.diff "Work: 0 tasks" = BLOCKED
    param($roundDir, $roundId)
    
    $diffPath = Join-Path $roundDir "candidate.diff"
    if (-not (Test-Path $diffPath)) {
        Write-Marker "GUARD_VIOLATION: candidate.diff does not exist" "Red"
        return @{passed=$false; blocker="NO_CANDIDATE_DIFF"}
    }
    
    $diffContent = Get-Content $diffPath -Raw
    if ($diffContent -match "Work:\s*0\s*tasks?") {
        Write-Marker "GUARD_VIOLATION: candidate.diff shows 'Work: 0 tasks'" "Red"
        return @{passed=$false; blocker="WORK_ZERO_TASKS"}
    }
    
    if ($diffContent -match "Work:\s*\d+\s*tasks?") {
        $taskCount = [int]($matches[0] -replace "Work:\s*" -replace "\s*tasks?")
        if ($taskCount -eq 0) {
            Write-Marker "GUARD_VIOLATION: candidate.diff shows zero tasks" "Red"
            return @{passed=$false; blocker="WORK_ZERO_TASKS"}
        }
    }
    
    Write-Marker "GUARD_PASS: candidate.diff shows actual work" "Green"
    return @{passed=$true; blocker=$null}
}

function Guard-TrackedCandidate {
    # GUARD F: Untracked candidate dir = BLOCKED
    param($roundId)
    
    $statusOutput = git -C $RepoRoot status --short "automation/control/candidates/$roundId" 2>$null
    if ($statusOutput -match "^\\?\\?") {
        Write-Marker "GUARD_VIOLATION: Candidate directory is untracked (??)" "Red"
        return @{passed=$false; blocker="UNTRACKED_CANDIDATE_DIR"}
    }
    
    if ($statusOutput -match "^A|^M") {
        Write-Marker "GUARD_PASS: Candidate directory is tracked" "Green"
        return @{passed=$true; blocker=$null}
    }
    
    # If no output, might be committed already - verify
    $committed = git -C $RepoRoot ls-files "automation/control/candidates/$roundId" 2>$null
    if ($committed) {
        Write-Marker "GUARD_PASS: Candidate directory is committed" "Green"
        return @{passed=$true; blocker=$null}
    }
    
    Write-Marker "GUARD_VIOLATION: Candidate directory not found in git" "Red"
    return @{passed=$false; blocker="CANDIDATE_NOT_IN_GIT"}
}

function Guard-NoSharedCommitReuse {
    # GUARD G: Shared unrelated commit cannot be reused
    param($commitHash, $previousRounds)
    
    foreach ($prevRound in $previousRounds) {
        if ($prevRound.candidate_commit -eq $commitHash) {
            Write-Marker "GUARD_VIOLATION: Commit $commitHash was already used by $($prevRound.round_id)" "Red"
            return @{passed=$false; blocker="SHARED_COMMIT_REUSE"}
        }
    }
    
    Write-Marker "GUARD_PASS: Commit is unique for this round" "Green"
    return @{passed=$true; blocker=$null}
}

function Guard-RealCodeChanges {
    # GUARD H: Must have actual code/scope changes, not just packaging
    param($commitHash, $RepoRoot)
    
    $changedFiles = git -C $RepoRoot diff-tree --no-commit-id --name-only -r $commitHash 2>$null
    
    # Filter out just packaging files
    $nonPackagingChanges = $changedFiles | Where-Object { 
        $_ -notmatch "evidence\.json$" -and 
        $_ -notmatch "report\.json$" -and 
        $_ -notmatch "candidate\.diff$" -and
        $_ -notmatch "task\.txt$" -and
        $_ -notmatch "run_record\.json$" -and
        $_ -notmatch "review_packet\.md$"
    }
    
    if (-not $nonPackagingChanges) {
        Write-Marker "GUARD_VIOLATION: Commit only contains packaging files, no real code changes" "Red"
        return @{passed=$false; blocker="NO_REAL_CODE_CHANGES"}
    }
    
    Write-Marker "GUARD_PASS: Commit contains real code changes: $($nonPackagingChanges -join ', ')" "Green"
    return @{passed=$true; blocker=$null; changed_files=$nonPackagingChanges}
}

# ========== LOAD STATE WITH GUARDS ==========

Write-Marker "=== FAIL-CLOSED AUTO MODE ===" "Cyan"

$state = Get-Content $statePath -Raw | ConvertFrom-Json

# GUARD C: Verify Start event
$startGuard = Guard-StartEvent -state $state
if (-not $startGuard.passed) {
    Write-Marker "=== BLOCKED: $($startGuard.blocker) ===" "Red"
    exit 1
}

$currentRound = $state.current_round
$currentPhase = $state.current_phase

Write-Marker "Round: $currentRound | Phase: $currentPhase" "Yellow"
Write-Marker "OpenCode Primary Contractor: EXECUTING" "Cyan"

# ========== OPENCODE EXECUTION (NOT AIDER) ==========
# GUARD A: OpenCode is primary, executes real work

# Record pre-execution commit
$preCommit = git -C $RepoRoot rev-parse HEAD 2>$null
Write-Marker "Pre-execution commit: $preCommit" "Gray"

# Create round directory
$roundDir = Join-Path $candidatesDir $currentRound
New-Item -ItemType Directory -Path $roundDir -Force | Out-Null

# ========== ACTUAL WORK EXECUTION (OpenCode) ==========
# This is where real functional work would be done
# For this repair task, we're fixing the engine, not doing R-011 work
# So we BLOCK and report technical_unfinished for any actual round execution

Write-Marker "=== ENGINE REPAIR MODE ===" "Yellow"
Write-Marker "Fail-closed guards installed. Ready for real execution." "Green"
Write-Marker "NOTE: Actual R-011+ work requires governance restart authorization." "Yellow"

# ========== POST-EXECUTION GUARDS ==========

# GUARD D: Verify functional commit
$postCommit = git -C $RepoRoot rev-parse HEAD 2>$null
$commitGuard = Guard-FunctionalCommit -roundId $currentRound -beforeCommit $preCommit -afterCommit $postCommit
if (-not $commitGuard.passed) {
    Write-Marker "=== BLOCKED: $($commitGuard.blocker) ===" "Red"
    
    # Mark as blocked in state
    $state.last_action = "blocked_$($commitGuard.blocker)"
    $state.status_flags.r011_status = "blocked"
    $stateJson = $state | ConvertTo-Json -Depth 4
    [System.IO.File]::WriteAllText($statePath, $stateJson)
    
    exit 1
}

# GUARD F: Verify tracked candidate
$trackedGuard = Guard-TrackedCandidate -roundId $currentRound
if (-not $trackedGuard.passed) {
    Write-Marker "=== BLOCKED: $($trackedGuard.blocker) ===" "Red"
    exit 1
}

# GUARD G: Verify no shared commit reuse
$history = Get-Content $runHistoryPath -Raw | ConvertFrom-Json
$reuseGuard = Guard-NoSharedCommitReuse -commitHash $postCommit -previousRounds $history.current_session.rounds
if (-not $reuseGuard.passed) {
    Write-Marker "=== BLOCKED: $($reuseGuard.blocker) ===" "Red"
    exit 1
}

# GUARD H: Verify real code changes
$codeGuard = Guard-RealCodeChanges -commitHash $postCommit -RepoRoot $RepoRoot
if (-not $codeGuard.passed) {
    Write-Marker "=== BLOCKED: $($codeGuard.blocker) ===" "Red"
    exit 1
}

# GUARD E: Verify candidate.diff shows actual work
$diffGuard = Guard-CandidateDiff -roundDir $roundDir -roundId $currentRound
if (-not $diffGuard.passed) {
    Write-Marker "=== BLOCKED: $($diffGuard.blocker) ===" "Red"
    exit 1
}

# ========== ALL GUARDS PASSED ==========

Write-Marker "=== ALL FAIL-CLOSED GUARDS PASSED ===" "Green"
Write-Marker "Round $currentRound has real functional implementation." "Green"

# Now and only now can we mark as candidate_ready
$state.last_action = "completed_with_real_work_$currentRound"
$state.status_flags.r011_status = "candidate_ready"
$stateJson = $state | ConvertTo-Json -Depth 4
[System.IO.File]::WriteAllText($statePath, $stateJson)

Write-Marker "=== READY FOR MANUAL REVIEW ===" "Green"