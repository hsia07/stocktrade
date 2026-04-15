# promote_candidate.ps1
# Candidate promotion script with remote push verification and audit trail

param(
    [string]$ApprovedFile = "automation/promotion/approved_candidate.runtime.json",
    [string]$PlanFile = "automation/promotion/promotion_plan.runtime.json",
    [string]$ResultFile = "automation/promotion/promotion_result.runtime.json"
)

$ErrorActionPreference = "Stop"

# Git writes informational messages to stderr, which PowerShell treats as errors
# This function runs git commands and captures output without throwing on stderr
function Invoke-GitCommand {
    param([string]$Command, [string[]]$Arguments)
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "git"
    $psi.Arguments = "$Command $Arguments"
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

function Write-Message {
    param([string]$Message, [string]$Type = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] [$Type] $Message"
}

function Write-Result {
    param([hashtable]$Data)
    $dir = Split-Path $ResultFile -Parent
    if ($dir -and -not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $Data | ConvertTo-Json -Depth 10 | Set-Content $ResultFile -Encoding UTF8
}

try {
    # Load approved candidate
    if (-not (Test-Path $ApprovedFile)) {
        Write-Message "Approved candidate file not found: $ApprovedFile" "ERROR"
        $result = @{
            status = "failed"
            stage = "validation"
            reason = "Approved candidate file not found"
            timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
        }
        Write-Result $result
        exit 1
    }

    $approved = Get-Content $ApprovedFile -Raw -Encoding UTF8 | ConvertFrom-Json

    # Validate required fields
    $errors = @()
    if ([string]::IsNullOrEmpty($approved.round_id)) { $errors += "round_id is missing" }
    if ([string]::IsNullOrEmpty($approved.candidate_id)) { $errors += "candidate_id is missing" }
    if ([string]::IsNullOrEmpty($approved.branch)) { $errors += "branch is missing" }

    if ($errors.Count -gt 0) {
        Write-Message "Approved candidate validation failed:" "ERROR"
        foreach ($err in $errors) { Write-Message "  - $err" "ERROR" }
        $result = @{
            status = "failed"
            stage = "validation"
            reason = ($errors -join "; ")
            timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
        }
        Write-Result $result
        exit 1
    }

    $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
    Set-Location $repoRoot

    $sourceBranch = $approved.branch
    $reviewBranch = "review/$($approved.candidate_id)"
    $candidateId = $approved.candidate_id

    Write-Message "=== PROMOTION START ===" "INFO"
    Write-Message "candidate_id: $candidateId" "INFO"
    Write-Message "source_branch: $sourceBranch" "INFO"
    Write-Message "review_branch: $reviewBranch" "INFO"

    # PRE-PROMOTE GUARDS
    Write-Message "Running pre-promote guards..." "INFO"

    # Check 1: Working tree must be clean
    $gitStatus = Invoke-GitCommand -Command "status" -Arguments "--porcelain"
    $statusOutput = $gitStatus.Output
    if ($statusOutput) {
        Write-Message "Working tree is not clean. Uncommitted changes found:" "ERROR"
        Write-Message $statusOutput "ERROR"
        $result = @{
            status = "failed"
            stage = "pre_promote_guard"
            guard = "working_tree_clean"
            reason = "Working tree has uncommitted changes"
            uncommitted_files = ($statusOutput -split "`n")
            timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
        }
        Write-Result $result
        exit 1
    }
    Write-Message "Guard passed: Working tree is clean" "OK"

    # Check 2: Current branch must match expected source branch
    $gitBranch = Invoke-GitCommand -Command "branch" -Arguments "--show-current"
    $currentBranch = $gitBranch.Output.Trim()
    if ($currentBranch -ne $sourceBranch) {
        Write-Message "Current branch '$currentBranch' does not match expected source branch '$sourceBranch'" "ERROR"
        $result = @{
            status = "failed"
            stage = "pre_promote_guard"
            guard = "correct_branch"
            reason = "Current branch does not match source branch"
            current_branch = $currentBranch
            expected_branch = $sourceBranch
            timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
        }
        Write-Result $result
        exit 1
    }
    Write-Message "Guard passed: On correct branch '$sourceBranch'" "OK"

    # Get source commit BEFORE any operations
    $gitCommit = Invoke-GitCommand -Command "rev-parse" -Arguments "HEAD"
    $sourceCommit = $gitCommit.Output.Trim()
    Write-Message "Source commit: $sourceCommit" "INFO"

    # Check if remote review branch already exists
    Write-Message "Checking if remote review branch exists..." "INFO"
    $gitRemote = Invoke-GitCommand -Command "ls-remote" -Arguments "--heads origin $reviewBranch"
    $remoteRef = $gitRemote.Output
    $remoteExists = -not [string]::IsNullOrWhiteSpace($remoteRef)

    if ($remoteExists) {
        Write-Message "Remote review branch already exists: origin/$reviewBranch" "WARN"
        Write-Message "Remote ref: $remoteRef" "INFO"

        # For idempotency, check if it points to same commit
        $remoteCommit = ($remoteRef -split "\s+")[0]
        if ($remoteCommit -eq $sourceCommit) {
            Write-Message "Remote branch already at same commit - treating as already_exists" "OK"
            $result = @{
                status = "already_exists"
                stage = "complete"
                idempotency = "remote_branch_already_at_target_commit"
                candidate_id = $candidateId
                source_branch = $sourceBranch
                source_commit = $sourceCommit
                review_branch = $reviewBranch
                remote_commit = $remoteCommit
                pushed_commit = $remoteCommit
                push_target = "origin"
                pushed_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
                timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
            }
            Write-Result $result

            # Also write plan file for consistency
            $plan = @{
                round_id = $approved.round_id
                candidate_id = $candidateId
                source_branch = $sourceBranch
                review_branch = $reviewBranch
                approved_at = $approved.approved_at
                approved_by = $approved.approved_by
                plan_created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
                status = "already_exists"
                review_branch_created = $true
                review_branch_pushed = $true
                source_commit = $sourceCommit
                pushed_commit = $remoteCommit
                push_target = "origin"
                steps = @(
                    @{ step = 1; description = "Validate pre-promote guards"; status = "done" }
                    @{ step = 2; description = "Check remote branch existence"; status = "done" }
                    @{ step = 3; description = "Create local review branch"; status = "skipped - already exists" }
                    @{ step = 4; description = "Push to origin"; status = "skipped - already at target" }
                    @{ step = 5; description = "Verify remote branch"; status = "done" }
                )
            }
            $plan | ConvertTo-Json -Depth 10 | Set-Content $PlanFile -Encoding UTF8

            Write-Message "=== PROMOTION ALREADY EXISTS (IDEMPOTENT) ===" "OK"
            exit 0
        } else {
            Write-Message "Remote branch exists but at different commit!" "ERROR"
            Write-Message "Local source: $sourceCommit" "ERROR"
            Write-Message "Remote: $remoteCommit" "ERROR"
            $result = @{
                status = "failed"
                stage = "idempotency_check"
                reason = "Remote review branch exists but at different commit"
                candidate_id = $candidateId
                source_commit = $sourceCommit
                remote_commit = $remoteCommit
                review_branch = $reviewBranch
                timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
            }
            Write-Result $result
            exit 1
        }
    }

    Write-Message "Remote review branch does not exist - proceeding with promotion" "OK"

    # Create or checkout local review branch
    $gitLocalBranch = Invoke-GitCommand -Command "branch" -Arguments "--list $reviewBranch"
    $localBranchExists = -not [string]::IsNullOrWhiteSpace($gitLocalBranch.Output)
    if ($localBranchExists) {
        Write-Message "Local review branch exists, checking out..." "INFO"
        $checkoutResult = Invoke-GitCommand -Command "checkout" -Arguments $reviewBranch
        Write-Message "Checkout output: $($checkoutResult.Output)" "INFO"
        if ($checkoutResult.ExitCode -ne 0) {
            Write-Message "Failed to checkout local review branch (exit: $($checkoutResult.ExitCode))" "ERROR"
            $result = @{
                status = "failed"
                stage = "branch_checkout"
                reason = "Failed to checkout local review branch"
                git_output = $checkoutResult.Output
                exit_code = $checkoutResult.ExitCode
                timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
            }
            Write-Result $result
            exit 1
        }
    } else {
        Write-Message "Creating new local review branch..." "INFO"
        $createResult = Invoke-GitCommand -Command "checkout" -Arguments "-b $reviewBranch $sourceBranch"
        Write-Message "Create output: $($createResult.Output)" "INFO"
        if ($createResult.ExitCode -ne 0) {
            Write-Message "Failed to create review branch (exit: $exitCode)" "ERROR"
            $result = @{
                status = "failed"
                stage = "branch_creation"
                reason = "Failed to create review branch"
                git_output = $createOutput
                exit_code = $exitCode
                timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
            }
            Write-Result $result
            exit 1
        }
    }
    Write-Message "Local review branch ready" "OK"

    # PUSH TO ORIGIN (PROMOTION PUSH)
    Write-Message "Pushing review branch to origin..." "INFO"
    Write-Message "Push type: PROMOTION (review/*)" "INFO"
    $pushResult = Invoke-GitCommand -Command "push" -Arguments "-u origin $reviewBranch"
    if ($pushResult.ExitCode -ne 0) {
        Write-Message "Failed to push review branch to origin" "ERROR"
        $result = @{
            status = "failed"
            stage = "remote_push"
            reason = "Failed to push review branch to origin"
            git_output = $pushResult.Output
            review_branch = $reviewBranch
            timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
        }
        Write-Result $result
        exit 1
    }
    Write-Message "Push to origin successful" "OK"

    # VERIFY REMOTE BRANCH EXISTS
    Write-Message "Verifying remote branch exists..." "INFO"
    $verifyResult = Invoke-GitCommand -Command "ls-remote" -Arguments "--heads origin $reviewBranch"
    $verifyRef = $verifyResult.Output
    if ([string]::IsNullOrWhiteSpace($verifyRef)) {
        Write-Message "Remote branch verification failed - branch not found after push" "ERROR"
        $result = @{
            status = "failed"
            stage = "remote_verification"
            reason = "Remote branch not found after push"
            review_branch = $reviewBranch
            timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
        }
        Write-Result $result
        exit 1
    }

    $pushedCommit = ($verifyRef -split "\s+")[0]
    if ($pushedCommit -ne $sourceCommit) {
        Write-Message "Remote verification failed - commit mismatch" "ERROR"
        Write-Message "Expected: $sourceCommit" "ERROR"
        Write-Message "Got: $pushedCommit" "ERROR"
        $result = @{
            status = "failed"
            stage = "remote_verification"
            reason = "Remote branch commit does not match source commit"
            expected_commit = $sourceCommit
            actual_commit = $pushedCommit
            timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
        }
        Write-Result $result
        exit 1
    }
    Write-Message "Remote verification successful: origin/$reviewBranch at $pushedCommit" "OK"

    $pushedAt = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"

    # Write detailed result
    $result = @{
        status = "success"
        stage = "complete"
        candidate_id = $candidateId
        source_branch = $sourceBranch
        source_commit = $sourceCommit
        review_branch = $reviewBranch
        pushed_commit = $pushedCommit
        push_target = "origin"
        pushed_at = $pushedAt
        timestamp = $pushedAt
        verification = @{
            ls_remote = $verifyRef
            commit_match = $true
        }
    }
    Write-Result $result

    # Write plan file
    $plan = @{
        round_id = $approved.round_id
        candidate_id = $candidateId
        source_branch = $sourceBranch
        source_commit = $sourceCommit
        review_branch = $reviewBranch
        pushed_commit = $pushedCommit
        push_target = "origin"
        pushed_at = $pushedAt
        approved_at = $approved.approved_at
        approved_by = $approved.approved_by
        plan_created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
        status = "promotion_complete"
        review_branch_created = $true
        review_branch_pushed = $true
        remote_verified = $true
        steps = @(
            @{ step = 1; description = "Validate pre-promote guards"; status = "done" }
            @{ step = 2; description = "Check remote branch existence"; status = "done" }
            @{ step = 3; description = "Create local review branch"; status = "done" }
            @{ step = 4; description = "Push to origin (PROMOTION)"; status = "done"; pushed_commit = $pushedCommit }
            @{ step = 5; description = "Verify remote branch via ls-remote"; status = "done"; verified_commit = $pushedCommit }
        )
    }
    $plan | ConvertTo-Json -Depth 10 | Set-Content $PlanFile -Encoding UTF8

    Write-Message "=== PROMOTION COMPLETE ===" "OK"
    Write-Message "Candidate: $candidateId" "OK"
    Write-Message "Source: $sourceBranch @ $sourceCommit" "OK"
    Write-Message "Review Branch: origin/$reviewBranch @ $pushedCommit" "OK"
    Write-Message "Push Type: PROMOTION (review/*)" "OK"
    Write-Message "Verification: PASSED" "OK"

    exit 0
}
catch {
    Write-Message "Unexpected error: $($_.Exception.Message)" "ERROR"
    $result = @{
        status = "failed"
        stage = "exception"
        reason = $_.Exception.Message
        timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
    }
    Write-Result $result
    exit 1
}
