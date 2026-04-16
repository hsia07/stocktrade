#!/usr/bin/env pwsh
# main_control_loop.ps1
# Main Control Loop for Stocktrade Automation
# Orchestrates candidate execution, prompt/artifact generation, and phase boundary management
#
# HARD RULE: Must generate formal prompt artifact before each OpenCode call
# HARD RULE: Must capture formal return artifact after each round
# HARD RULE: Must check phase boundary and auto-stop when phase completes
# HARD RULE: Must not auto-continue to next phase without user authorization

param(
    [string]$Phase = "Phase 1",
    [string]$StartRound = "R-006",
    [string]$RepoRoot = ".",
    [string]$ControlDir = "automation\control",
    [string]$ArtifactsDir = "automation\control\artifacts",
    [string]$LogsDir = "automation\control\logs",
    [string]$ReportsDir = "automation\control\reports",
    [switch]$Resume = $false,
    [switch]$DryRun = $false,
    [int]$MaxRounds = 100,
    [int]$PhaseBoundary = 161
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "Continue"

# Setup paths
$repoRoot = Resolve-Path $RepoRoot
$controlDir = Join-Path $repoRoot $ControlDir
$artifactsDir = Join-Path $repoRoot $ArtifactsDir
$logsDir = Join-Path $repoRoot $LogsDir
$reportsDir = Join-Path $repoRoot $ReportsDir

# State files
$stateFile = Join-Path $controlDir "state.runtime.json"
$templateStateFile = Join-Path $controlDir "state.template.json"
$returnArtifactFile = Join-Path $controlDir "latest_return_to_chatgpt.runtime.txt"
$returnTemplateFile = Join-Path $controlDir "latest_return_to_chatgpt.template.txt"

# Control flags
$pauseFlag = Join-Path $controlDir "PAUSE_AFTER_CURRENT.flag"
$stopFlag = Join-Path $controlDir "STOP_NOW.flag"
$acceptanceFlag = Join-Path $controlDir "ACCEPTANCE_MODE.flag"

# Ensure directories exist
foreach ($dir in @($artifactsDir, $logsDir, $reportsDir)) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# Initialize or load state
function Initialize-State {
    if (!(Test-Path $stateFile)) {
        if (Test-Path $templateStateFile) {
            Copy-Item $templateStateFile $stateFile -Force
        } else {
            throw "State template not found: $templateStateFile"
        }
    }
    
    $state = Get-Content $stateFile -Raw | ConvertFrom-Json
    
    # Ensure all required fields exist with defaults
    # Use Get-Member to check if property exists before adding
    if (-not ($state | Get-Member -Name "schema_version" -MemberType NoteProperty)) { $state | Add-Member -NotePropertyName "schema_version" -NotePropertyValue "2.0" }
    if (-not ($state | Get-Member -Name "run_state" -MemberType NoteProperty)) { $state | Add-Member -NotePropertyName "run_state" -NotePropertyValue "stopped" }
    if (-not ($state | Get-Member -Name "current_mode" -MemberType NoteProperty)) { $state | Add-Member -NotePropertyName "current_mode" -NotePropertyValue "idle" }
    if (-not ($state | Get-Member -Name "current_phase" -MemberType NoteProperty)) { $state | Add-Member -NotePropertyName "current_phase" -NotePropertyValue $Phase }
    if (-not ($state | Get-Member -Name "current_round" -MemberType NoteProperty)) { $state | Add-Member -NotePropertyName "current_round" -NotePropertyValue $StartRound }
    if (-not ($state | Get-Member -Name "phase_completion_state" -MemberType NoteProperty)) { $state | Add-Member -NotePropertyName "phase_completion_state" -NotePropertyValue "not_started" }
    if (-not ($state | Get-Member -Name "rounds_in_current_run" -MemberType NoteProperty)) { $state | Add-Member -NotePropertyName "rounds_in_current_run" -NotePropertyValue @() }
    if (-not ($state | Get-Member -Name "completed_rounds" -MemberType NoteProperty)) { $state | Add-Member -NotePropertyName "completed_rounds" -NotePropertyValue @() }
    if (-not ($state | Get-Member -Name "completed_candidate_rounds" -MemberType NoteProperty)) { $state | Add-Member -NotePropertyName "completed_candidate_rounds" -NotePropertyValue @() }
    if (-not ($state | Get-Member -Name "ready_for_signoff_rounds" -MemberType NoteProperty)) { $state | Add-Member -NotePropertyName "ready_for_signoff_rounds" -NotePropertyValue @() }
    if (-not ($state | Get-Member -Name "blocked_rounds" -MemberType NoteProperty)) { $state | Add-Member -NotePropertyName "blocked_rounds" -NotePropertyValue @() }
    if (-not ($state | Get-Member -Name "authorized_scope" -MemberType NoteProperty)) { $state | Add-Member -NotePropertyName "authorized_scope" -NotePropertyValue $null }
    
    # Ensure candidate checklist exists (10 formal criteria + 2 metadata fields)
    if (!$state.candidate_checklist) {
        $state | Add-Member -NotePropertyName "candidate_checklist" -NotePropertyValue (ConvertFrom-Json '{
            "theme_completed": false,
            "rerunnable_tests_passed": false,
            "evidence_package_complete": false,
            "validate_evidence_ps1_executed": false,
            "validate_evidence_result": null,
            "validate_evidence_executed_at": null,
            "validate_evidence_exit_code": null,
            "formal_status_code": null,
            "candidate_branch_auditable": false,
            "candidate_commit_auditable": false,
            "no_fabricated_evidence": false,
            "no_unauthorized_modifications": false,
            "complete_return_to_chatgpt": false
        }')
    }
    
    # Ensure merge gate exists
    if (!$state.merge_gate) {
        $state | Add-Member -NotePropertyName "merge_gate" -NotePropertyValue (ConvertFrom-Json '{
            "user_can_review_multiple_candidates": true,
            "user_cannot_auto_merge_multiple": true,
            "merge_requires_per_round_explicit_signoff": true,
            "at_decision_point_provide_merge_command": false,
            "must_wait_for_explicit_user_ok": true,
            "explicit_ok_keywords": ["好", "同意", "ok", "approve", "yes"],
            "auto_push_master": false,
            "later_candidate_does_not_imply_earlier_complete": true,
            "current_decision_state": "waiting_for_candidates"
        }')
    }
    
    # Ensure forbidden scope guardrails exist
    if (!$state.forbidden_scope_guardrails) {
        $state | Add-Member -NotePropertyName "forbidden_scope_guardrails" -NotePropertyValue (ConvertFrom-Json '{
            "master_branch": { "blocked": true, "reason": "master_branch_protected" },
            "server_v2_py": { "blocked": true, "requires_explicit_auth": true, "reason": "core_server_file" },
            "broker_core": { "blocked": true, "reason": "broker_core_protected" },
            "live_trading": { "blocked": true, "reason": "live_trading_protected" },
            "risk_core": { "blocked": true, "reason": "risk_core_protected" },
            "future_phase_content": { "blocked": true, "reason": "future_phase_protected" },
            "unrelated_promotion_panel_governance": { "blocked": true, "reason": "scope_restricted" },
            "action_on_violation": "stop_and_report_blocked"
        }')
    }
    
    # Ensure aider scheduling exists
    if (!$state.aider_scheduling) {
        $state | Add-Member -NotePropertyName "aider_scheduling" -NotePropertyValue (ConvertFrom-Json '{
            "current_task_id": null,
            "current_task_description": null,
            "target_files": [],
            "aider_args_used": {
                "file": null,
                "message": null,
                "message_file": null,
                "no_auto_commits": true,
                "no_dirty_commits": true,
                "yes_always": false
            },
            "last_execution": {
                "task_id": null,
                "exit_code": null,
                "files_written": [],
                "status": null,
                "disposition": null
            },
            "rules": {
                "one_shot_per_call": true,
                "max_files_per_task": 2,
                "minimal_context_required": true,
                "no_full_repo_understanding": true,
                "no_cross_round_mixed_tasks": true,
                "disposition_on_text_only": ["no_change", "not_applied", "needs_manual_review"]
            }
        }')
    }
    
    return $state
}

# Save state with timestamp
function Save-State {
    param($State)
    $State.updated_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
    $json = $State | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($stateFile, $json, [System.Text.Encoding]::UTF8)
}

# Generate unique run ID
function New-RunId {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $random = -join ((65..90) + (97..122) | Get-Random -Count 6 | ForEach-Object { [char]$_ })
    return "RUN_${timestamp}_${random}"
}

# Check control flags
function Check-ControlFlags {
    $flags = @{
        pause_requested = Test-Path $pauseFlag
        stop_requested = Test-Path $stopFlag
        acceptance_mode = Test-Path $acceptanceFlag
    }
    return $flags
}

# Clear control flags
function Clear-ControlFlags {
    foreach ($flag in @($pauseFlag, $stopFlag, $acceptanceFlag)) {
        if (Test-Path $flag) {
            Remove-Item $flag -Force
        }
    }
}

# Generate formal prompt artifact
function Generate-PromptArtifact {
    param(
        [string]$RoundId,
        [string]$TaskType,
        [string]$TaskDescription,
        [string]$AuthorizedScope,
        [string]$PreviousContext
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    $replyId = "${RoundId}-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    
    $promptArtifact = @"
=== FORMAL PROMPT ARTIFACT ===
generated_at: $timestamp
round_id: $RoundId
task_type: $TaskType
reply_id: $replyId

[PROJECT_CONTEXT_START]
專案：stocktrade
repo 路徑：C:\Users\richa\OneDrive\桌面\stocktrade

嚴格依現行正式法典執行，不得自行放寬。

現行正式法典優先順序：
1. 02_交易系統極限嚴格母表法典.docx
2. 03_161輪逐輪施行細則法典_整合法條增補版.docx
3. 04_交易系統法典補強版_20260416_修正版.md
4. 01_系統白話總覽與功能說明.docx

前情狀態：
$PreviousContext

本次授權範圍：
$AuthorizedScope

本次禁止事項：
- 不准修改交易策略核心
- 不准修改風控核心
- 不准修改正式法典 01/02/03
- 不准未經簽字執行 merge/push
- 不准自動跨 phase 續跑
- 不准生成簡化摘要取代正式 artifact

角色定位：
OpenCode - 施工員 / 驗證官 / 回報官，不是最終放行者，不是自由重構員

正式回報規則：
1. RETURN_TO_CHATGPT 是正式主體輸出區，不是摘要區
2. 所有關鍵結論、狀態碼、證據、修改檔案、git 狀態、下一步，都必須完整寫入 RETURN_TO_CHATGPT
3. 不得只回摘要
4. 前面若有說明，不得比 RETURN_TO_CHATGPT 更完整

本次任務：
$TaskDescription

完成標準：
- 功能完整實現
- 有最小可重跑驗證證據
- 符合 governance drift 規則
- 不得破壞既有可用鏈路

狀態碼要求：
- completed: 功能完整且驗證通過
- technical_unfinished: 有缺漏但無擴權
- blocked: 有 blockers 需解決

REPLY_ID: $replyId
[OPENCODE_END]
=== END FORMAL PROMPT ARTIFACT ===
"@

    $artifactPath = Join-Path $artifactsDir "prompt_${RoundId}_${replyId}.txt"
    Set-Content -Path $artifactPath -Value $promptArtifact -Encoding UTF8
    
    return @{
        path = $artifactPath
        reply_id = $replyId
        content = $promptArtifact
    }
}

# Generate formal return artifact
function Generate-ReturnArtifact {
    param(
        [string]$RoundId,
        [string]$Status,
        [string]$FormalStatusCode,
        [string]$Summary,
        [array]$FilesModified,
        [string]$ReplyId,
        [string]$CommitHash = "NONE",
        [string]$NextAction = "Awaiting user review"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    
    $returnArtifact = @"
=== RETURN_TO_CHATGPT ===
round_id: $RoundId
reply_id: $ReplyId
timestamp: $timestamp
status: $Status
formal_status_code: $FormalStatusCode

summary:
$Summary

files_modified:
$(if ($FilesModified) { $FilesModified | ForEach-Object { "- $_" } } else { "- NONE" })

commit_hash: $CommitHash

escalation_required: no
escalation_reason: none

next_recommended_action: $NextAction

=== END_RETURN_TO_CHATGPT ===
"@

    Set-Content -Path $returnArtifactFile -Value $returnArtifact -Encoding UTF8
    
    $artifactPath = Join-Path $artifactsDir "return_${RoundId}_${ReplyId}.txt"
    Set-Content -Path $artifactPath -Value $returnArtifact -Encoding UTF8
    
    return @{
        runtime_path = $returnArtifactFile
        archive_path = $artifactPath
        content = $returnArtifact
    }
}

# Check if all 10 candidate criteria are met
function Test-CandidateCriteria {
    param([object]$State, [string]$RoundId)
    
    Write-Host "[CRITERIA] Checking 10 candidate criteria for $RoundId..." -ForegroundColor Cyan
    
    $checklist = $State.candidate_checklist
    $results = @{
        all_passed = $true
        failed_criteria = @()
    }
    
    # 1. Unique theme completed
    if (-not $checklist.theme_completed) {
        $results.all_passed = $false
        $results.failed_criteria += "theme_completed"
        Write-Host "[CRITERIA-FAIL] Theme not completed" -ForegroundColor Red
    }
    
    # 2. Re-runnable tests passed
    if (-not $checklist.rerunnable_tests_passed) {
        $results.all_passed = $false
        $results.failed_criteria += "rerunnable_tests_passed"
        Write-Host "[CRITERIA-FAIL] Tests not passed" -ForegroundColor Red
    }
    
    # 3. Evidence package complete
    if (-not $checklist.evidence_package_complete) {
        $results.all_passed = $false
        $results.failed_criteria += "evidence_package_complete"
        Write-Host "[CRITERIA-FAIL] Evidence package incomplete" -ForegroundColor Red
    }
    
    # 4. validate_evidence.ps1 executed
    if (-not $checklist.validate_evidence_ps1_executed) {
        $results.all_passed = $false
        $results.failed_criteria += "validate_evidence_ps1_executed"
        Write-Host "[CRITERIA-FAIL] validate_evidence.ps1 not executed" -ForegroundColor Red
    }
    
    # 5. Formal status code = candidate_ready_awaiting_manual_review
    if ($checklist.formal_status_code -ne "candidate_ready_awaiting_manual_review") {
        $results.all_passed = $false
        $results.failed_criteria += "formal_status_code != candidate_ready_awaiting_manual_review"
        Write-Host "[CRITERIA-FAIL] formal_status_code = $($checklist.formal_status_code), expected: candidate_ready_awaiting_manual_review" -ForegroundColor Red
    }
    
    # 6. Candidate branch auditable
    if (-not $checklist.candidate_branch_auditable) {
        $results.all_passed = $false
        $results.failed_criteria += "candidate_branch_auditable"
        Write-Host "[CRITERIA-FAIL] Candidate branch not auditable" -ForegroundColor Red
    }
    
    # 7. Candidate commit auditable
    if (-not $checklist.candidate_commit_auditable) {
        $results.all_passed = $false
        $results.failed_criteria += "candidate_commit_auditable"
        Write-Host "[CRITERIA-FAIL] Candidate commit not auditable" -ForegroundColor Red
    }
    
    # 8. No fabricated evidence
    if (-not $checklist.no_fabricated_evidence) {
        $results.all_passed = $false
        $results.failed_criteria += "no_fabricated_evidence"
        Write-Host "[CRITERIA-FAIL] Fabricated evidence detected" -ForegroundColor Red
    }
    
    # 9. No unauthorized modifications
    if (-not $checklist.no_unauthorized_modifications) {
        $results.all_passed = $false
        $results.failed_criteria += "no_unauthorized_modifications"
        Write-Host "[CRITERIA-FAIL] Unauthorized modifications detected" -ForegroundColor Red
    }
    
    # 10. Complete RETURN_TO_CHATGPT
    if (-not $checklist.complete_return_to_chatgpt) {
        $results.all_passed = $false
        $results.failed_criteria += "complete_return_to_chatgpt"
        Write-Host "[CRITERIA-FAIL] RETURN_TO_CHATGPT incomplete" -ForegroundColor Red
    }
    
    if ($results.all_passed) {
        Write-Host "[CRITERIA] All 10 criteria PASSED for $RoundId" -ForegroundColor Green
    } else {
        Write-Host "[CRITERIA] FAILED: Round blocked, stopping at current round" -ForegroundColor Red
        Write-Host "[CRITERIA] Failed criteria: $($results.failed_criteria -join ', ')" -ForegroundColor Red
        Write-Host "[CRITERIA] STOP REASON: candidate_criteria_not_met - Will NOT proceed to next round" -ForegroundColor Red
    }
    
    return $results
}

# Check if phase is complete
function Test-PhaseComplete {
    param([object]$State)
    
    # Phase is complete if:
    # 1. Current round exceeds phase boundary
    # 2. Or all rounds in phase are marked ready_for_signoff
    # 3. Or specific phase completion criteria met
    
    $currentRoundNum = [int]($State.current_round -replace "R-", "")
    
    # Get phase boundaries from phase_definition (HARD-CODED per formal law)
    $phaseStartNum = 1
    $phaseEndNum = 15
    
    if ($State.phase_definition -and $State.phase_definition.($State.current_phase)) {
        $phaseDef = $State.phase_definition.($State.current_phase)
        # Parse R-XXX format to get numeric values
        $phaseStartNum = [int]($phaseDef.start_round -replace "R-", "")
        $phaseEndNum = [int]($phaseDef.end_round -replace "R-", "")
        # Handle special case R-045A -> 45
        if ($phaseDef.end_round -match "R-(\d+)A") {
            $phaseEndNum = [int]$matches[1]
        }
    } else {
        # Fallback: Hard-coded phase boundaries per formal law
        switch ($State.current_phase) {
            "Phase 1" { $phaseStartNum = 1; $phaseEndNum = 15 }
            "Phase 2" { $phaseStartNum = 16; $phaseEndNum = 45 }
            "Phase 3" { $phaseStartNum = 46; $phaseEndNum = 128 }
            "Phase 4" { $phaseStartNum = 129; $phaseEndNum = 161 }
            default { $phaseStartNum = 1; $phaseEndNum = 15 }
        }
    }
    
    Write-Host "[PHASE-DEBUG] Current: $currentRoundNum | Phase: $($State.current_phase) | Range: $phaseStartNum-$phaseEndNum" -ForegroundColor Gray
    
    # Check if current round exceeds phase boundary
    if ($currentRoundNum -gt $phaseEndNum) {
        Write-Host "[PHASE] Round $currentRoundNum exceeds phase boundary ($phaseEndNum)" -ForegroundColor Yellow
        return $true
    }
    
    # Check if all expected rounds in phase are marked ready_for_signoff
    $expectedRounds = $phaseEndNum - $phaseStartNum + 1
    $completedInPhase = 0
    
    foreach ($round in $State.ready_for_signoff_rounds) {
        $roundNum = [int]($round -replace "R-", "")
        if ($roundNum -ge $phaseStartNum -and $roundNum -le $phaseEndNum) {
            $completedInPhase++
        }
    }
    
    Write-Host "[PHASE-DEBUG] Completed in phase: $completedInPhase / $expectedRounds" -ForegroundColor Gray
    
    if ($completedInPhase -ge $expectedRounds) {
        Write-Host "[PHASE] All $expectedRounds rounds in $($State.current_phase) marked ready_for_signoff" -ForegroundColor Green
        return $true
    }
    
    return $false
}

# Execute a single round
function Invoke-Round {
    param(
        [string]$RoundId,
        [object]$State,
        [object]$RunReport
    )
    
    Write-Progress -Activity "Main Control Loop" -Status "Executing $RoundId" -PercentComplete -1
    
    # CRITICAL: Reset all 10 candidate criteria for this round
    $State.candidate_checklist.theme_completed = $false
    $State.candidate_checklist.rerunnable_tests_passed = $false
    $State.candidate_checklist.evidence_package_complete = $false
    $State.candidate_checklist.validate_evidence_ps1_executed = $false
    $State.candidate_checklist.validate_evidence_result = $null
    $State.candidate_checklist.validate_evidence_executed_at = $null
    $State.candidate_checklist.validate_evidence_exit_code = $null
    $State.candidate_checklist.formal_status_code = "candidate_prep_in_progress"
    $State.candidate_checklist.candidate_branch_auditable = $false
    $State.candidate_checklist.candidate_commit_auditable = $false
    $State.candidate_checklist.no_fabricated_evidence = $false
    $State.candidate_checklist.no_unauthorized_modifications = $false
    $State.candidate_checklist.complete_return_to_chatgpt = $false
    
    # Update state
    $State.current_round = $RoundId
    $State.phase_completion_state = "in_progress"
    $State.run_state = "running"
    $State.last_action = "round_start"
    $State.current_candidate_id = $null
    Save-State $State
    
    Write-Host "[LOOP] ===== STARTING $RoundId (Candidate Pre-Fabrication Mode) =====" -ForegroundColor Cyan
    Write-Host "[LOOP] Mode: multi_round_candidate_prep" -ForegroundColor Yellow
    Write-Host "[LOOP] Legal Effect: Candidate != Formal Pass | NO auto-merge/push" -ForegroundColor Yellow
    
    # Generate prompt artifact
    $promptArtifact = Generate-PromptArtifact `
        -RoundId $RoundId `
        -TaskType "candidate_execution_multi_round_prep" `
        -TaskDescription "Execute $RoundId to create independent candidate. Must reach candidate_ready_awaiting_manual_review before proceeding to next round. NO auto-merge/push. Candidate != formal pass." `
        -AuthorizedScope "Single round execution within current phase only. Stop if any round not candidate_ready." `
        -PreviousContext "Multi-round candidate prep mode active. Each round independent candidate. Previous rounds: $($State.completed_candidate_rounds -join ', ')"
    
    $State.latest_prompt_artifact = $promptArtifact.path
    Save-State $State
    
    Write-Host "[LOOP] Prompt artifact generated: $($promptArtifact.reply_id)" -ForegroundColor Cyan
    
    # IN A REAL IMPLEMENTATION:
    # Here we would call the actual OpenCode execution
    # For now, this is a placeholder that simulates the execution
    # and waits for the return artifact to be provided
    
    if (!$DryRun) {
        Write-Host "[LOOP] Waiting for round execution..." -ForegroundColor Yellow
        Write-Host "[LOOP] In production, this would call OpenCode with the prompt artifact" -ForegroundColor Gray
        
        # Simulate execution time
        Start-Sleep -Seconds 2
        
        # For demonstration, generate a mock return artifact
        # IN PRODUCTION: This would be generated by actual OpenCode execution
        $returnArtifact = Generate-ReturnArtifact `
            -RoundId $RoundId `
            -Status "candidate_ready" `
            -FormalStatusCode "candidate_ready_awaiting_manual_review" `
            -Summary "Round execution completed. Candidate ready for review. NOT formal pass. Merge requires explicit signoff." `
            -FilesModified @() `
            -ReplyId $promptArtifact.reply_id `
            -CommitHash "NONE" `
            -NextAction "Verify candidate checklist complete, then proceed to next round or stop for review"
        
        $State.latest_return_artifact = $returnArtifact.archive_path
        $State.candidate_checklist.complete_return_to_chatgpt = $true
        Save-State $State
        
        Write-Host "[LOOP] Return artifact captured" -ForegroundColor Green
    }
    
    # CRITICAL: Execute validate_evidence.ps1 for current round
    Write-Host "[LOOP] Executing validate_evidence.ps1 for $RoundId..." -ForegroundColor Cyan
    
    $validateEvidenceScript = Join-Path $repoRoot "scripts\validation\validate_evidence.ps1"
    $evidenceValidationPassed = $false
    $evidenceValidationOutput = ""
    
    if (Test-Path $validateEvidenceScript) {
        try {
            $validationStartTime = Get-Date
            # Note: validate_evidence.ps1 uses -CandidateId parameter
            $evidenceValidationOutput = & powershell -ExecutionPolicy Bypass -NoProfile -File $validateEvidenceScript -CandidateId $RoundId 2>&1
            $validationExitCode = $LASTEXITCODE
            $validationEndTime = Get-Date
            
            if ($validationExitCode -eq 0) {
                $evidenceValidationPassed = $true
                $State.candidate_checklist.validate_evidence_result = "PASS"
                Write-Host "[LOOP] validate_evidence.ps1 PASSED for $RoundId" -ForegroundColor Green
            } else {
                $evidenceValidationPassed = $false
                $State.candidate_checklist.validate_evidence_result = "FAIL"
                Write-Host "[LOOP] validate_evidence.ps1 FAILED for $RoundId (Exit Code: $validationExitCode)" -ForegroundColor Red
                Write-Host "[LOOP] Validation Output: $evidenceValidationOutput" -ForegroundColor Red
            }
            
            $State.candidate_checklist.validate_evidence_ps1_executed = $true
            $State.candidate_checklist.validate_evidence_executed_at = $validationEndTime.ToString("yyyy-MM-ddTHH:mm:ss")
            $State.candidate_checklist.validate_evidence_exit_code = $validationExitCode
            
        } catch {
            Write-Host "[LOOP] ERROR executing validate_evidence.ps1: $($_)" -ForegroundColor Red
            $State.candidate_checklist.validate_evidence_ps1_executed = $true
            $State.candidate_checklist.validate_evidence_result = "ERROR"
            $State.candidate_checklist.validate_evidence_error = $_.Exception.Message
            $evidenceValidationPassed = $false
        }
    } else {
        Write-Host "[LOOP] WARNING: validate_evidence.ps1 not found at $validateEvidenceScript" -ForegroundColor Yellow
        $State.candidate_checklist.validate_evidence_ps1_executed = $false
        $State.candidate_checklist.validate_evidence_result = "SCRIPT_NOT_FOUND"
        $evidenceValidationPassed = $false
    }
    
    Save-State $State
    
    # CRITICAL: Check all 10 candidate criteria before proceeding
    Write-Host "[LOOP] Validating 10 candidate criteria for $RoundId..." -ForegroundColor Cyan
    $criteriaResults = Test-CandidateCriteria -State $State -RoundId $RoundId
    
    if (-not $criteriaResults.all_passed) {
        Write-Host "[LOOP] BLOCKED: $RoundId failed candidate criteria" -ForegroundColor Red
        Write-Host "[LOOP] Failed: $($criteriaResults.failed_criteria -join ', ')" -ForegroundColor Red
        
        $State.run_state = "stopped"
        $State.stop_reason = "candidate_criteria_not_met"
        $State.last_action = "round_blocked_criteria_not_met"
        $State.blocked_rounds += @($RoundId)
        Save-State $State
        
        $RunReport.blockers += @("Round $RoundId failed candidate criteria: $($criteriaResults.failed_criteria -join ', ')")
        $RunReport.stop_reason = "candidate_criteria_not_met"
        
        return @{
            success = $false
            prompt_artifact = $promptArtifact
            status = "blocked"
            reason = "candidate_criteria_not_met"
            failed_criteria = $criteriaResults.failed_criteria
        }
    }
    
    # Candidate criteria met - mark as ready
    Write-Host "[LOOP] $RoundId candidate criteria PASSED" -ForegroundColor Green
    $State.candidate_checklist.formal_status_code = "candidate_ready_awaiting_manual_review"
    $State.current_candidate_id = $RoundId
    
    # Add to rounds in current run
    if ($State.rounds_in_current_run -notcontains $RoundId) {
        $State.rounds_in_current_run += $RoundId
    }
    
    # Track completed candidate rounds (NOT formal pass rounds)
    if ($State.completed_candidate_rounds -notcontains $RoundId) {
        $State.completed_candidate_rounds += @($RoundId)
    }
    
    # Update run report
    $RunReport.rounds_executed += @($RoundId)
    
    Write-Host "[LOOP] $RoundId candidate ready. Awaiting manual review." -ForegroundColor Green
    Write-Host "[LOOP] ===== COMPLETED $RoundId (Candidate Only, NOT Formal Pass) =====" -ForegroundColor Cyan
    
    return @{
        success = $true
        prompt_artifact = $promptArtifact
        status = "candidate_ready_awaiting_manual_review"
        is_candidate_not_formal_pass = $true
    }
}

# Main loop
function Start-MainControlLoop {
    param([object]$State)
    
    $runId = New-RunId
    $startTime = Get-Date
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  MAIN CONTROL LOOP STARTED" -ForegroundColor Cyan
    Write-Host "  Run ID: $runId" -ForegroundColor Cyan
    Write-Host "  Phase: $Phase" -ForegroundColor Cyan
    Write-Host "  Start Round: $StartRound" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Initialize run report
    $runReport = @{
        run_id = $runId
        phase_id = $Phase
        start_round = $StartRound
        start_time = $startTime.ToString("yyyy-MM-ddTHH:mm:ss")
        end_time = $null
        rounds_executed = @()
        rounds_completed = @()
        rounds_blocked = @()
        phase_boundary_stopped = $false
        stop_reason = $null
        artifacts_generated = @()
        blockers = @()
        local_head = $null
        remote_head = $null
        working_tree_clean = $null
        untracked_files = @()
    }
    
    # Clear control flags at start (unless resuming)
    if (!$Resume) {
        Clear-ControlFlags
    }
    
    $roundCounter = 0
    $currentRound = $StartRound
    
    while ($roundCounter -lt $MaxRounds) {
        # Check control flags
        $flags = Check-ControlFlags
        
        if ($flags.stop_requested) {
            Write-Host "[LOOP] STOP flag detected. Stopping immediately." -ForegroundColor Red
            $State.run_state = "stopped"
            $State.stop_reason = "manual_stop"
            $State.last_action = "stop_flag_detected"
            Save-State $State
            
            $runReport.stop_reason = "manual_stop"
            break
        }
        
        if ($flags.acceptance_mode) {
            Write-Host "[LOOP] ACCEPTANCE_MODE flag detected. Pausing for manual review." -ForegroundColor Yellow
            $State.run_state = "paused_for_acceptance"
            $State.stop_reason = "acceptance_mode_requested"
            $State.last_action = "acceptance_mode_entered"
            Save-State $State
            
            $runReport.stop_reason = "acceptance_mode_requested"
            break
        }
        
        # Check phase boundary
        if (Test-PhaseComplete -State $State) {
            Write-Host "[LOOP] PHASE BOUNDARY DETECTED. Auto-stopping." -ForegroundColor Yellow
            $State.run_state = "phase_completed_stopped"
            $State.stop_reason = "phase_completed"
            $State.phase_completion_state = "completed"
            $State.signoff_required = $true
            $State.last_action = "phase_boundary_auto_stop"
            Save-State $State
            
            $runReport.phase_boundary_stopped = $true
            $runReport.stop_reason = "phase_completed"
            
            Write-Host "[LOOP] Phase $Phase completed. Waiting for manual authorization to proceed." -ForegroundColor Yellow
            break
        }
        
        # Execute round
        try {
            $roundResult = Invoke-Round -RoundId $currentRound -State $State -RunReport $runReport
            
            if ($roundResult.success) {
                $runReport.rounds_completed += @($currentRound)
                $State.completed_rounds += @($currentRound)
                
                # Check if round is ready for signoff (would need actual criteria)
                # For now, assume candidate_ready means ready_for_signoff
                if ($roundResult.status -eq "candidate_ready") {
                    $State.ready_for_signoff_rounds += @($currentRound)
                }
            } else {
                # CRITICAL: Round failed criteria - STOP at current round, do NOT proceed
                Write-Host "[LOOP] CRITICAL: Round $currentRound blocked. STOPPING at current round." -ForegroundColor Red
                Write-Host "[LOOP] Stop reason: $($roundResult.reason)" -ForegroundColor Red
                Write-Host "[LOOP] Will NOT proceed to next round. User must fix and resume." -ForegroundColor Red
                
                $State.run_state = "stopped"
                $State.stop_reason = $roundResult.reason
                $State.last_action = "round_blocked_stop_at_current"
                Save-State $State
                
                $runReport.stop_reason = $roundResult.reason
                $runReport.rounds_blocked += @($currentRound)
                
                break  # EXIT LOOP - do not increment to next round
            }
            
            Save-State $State
            
            # Check if we should pause after current
            if ($flags.pause_requested) {
                Write-Host "[LOOP] PAUSE_AFTER_CURRENT flag detected. Pausing after $currentRound." -ForegroundColor Yellow
                $State.run_state = "paused_for_acceptance"
                $State.stop_reason = "drain_after_current"
                $State.last_action = "drain_requested_pause"
                Save-State $State
                
                $runReport.stop_reason = "drain_after_current"
                break
            }
            
        } catch {
            Write-Host "[LOOP] ERROR executing $currentRound`: $($_)" -ForegroundColor Red
            $State.run_state = "stopped_error"
            $State.stop_reason = "execution_error"
            $State.last_error = $_.Exception.Message
            $State.last_action = "round_execution_failed"
            Save-State $State
            
            $runReport.blockers += @("Round $currentRound failed: $($_)")
            $runReport.stop_reason = "execution_error"
            break
        }
        
        # Increment to next round
        $roundNum = [int]($currentRound -replace "R-", "")
        $nextRoundNum = $roundNum + 1
        $currentRound = "R-$($nextRoundNum.ToString().PadLeft(3, '0'))"
        $roundCounter++
        
        Write-Host "[LOOP] Round completed. Moving to next: $currentRound" -ForegroundColor Gray
        Start-Sleep -Seconds 1
    }
    
    # Finalize run report
    $endTime = Get-Date
    $runReport.end_time = $endTime.ToString("yyyy-MM-ddTHH:mm:ss")
    $runReport.duration_seconds = [int]($endTime - $startTime).TotalSeconds
    
    # Get git status for report
    $runReport.local_head = git rev-parse HEAD 2>&1
    try { $runReport.remote_head = git rev-parse origin/work/r006-governance 2>&1 } catch { $runReport.remote_head = "unknown" }
    $runReport.working_tree_clean = (git status --porcelain 2>&1 | Measure-Object).Count -eq 0
    $runReport.untracked_files = git ls-files --others --exclude-standard 2>&1
    
    # Save run report
    $reportPath = Join-Path $reportsDir "run_report_${runId}.json"
    $runReport | ConvertTo-Json -Depth 10 | Set-Content $reportPath -Encoding UTF8
    
    # Update latest report link
    $latestReportPath = Join-Path $reportsDir "latest_run_report.json"
    $runReport | ConvertTo-Json -Depth 10 | Set-Content $latestReportPath -Encoding UTF8
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  MAIN CONTROL LOOP COMPLETED" -ForegroundColor Cyan
    Write-Host "  Run ID: $runId" -ForegroundColor Cyan
    Write-Host "  Rounds Executed: $($runReport.rounds_executed.Count)" -ForegroundColor Cyan
    Write-Host "  Stop Reason: $($runReport.stop_reason)" -ForegroundColor Cyan
    Write-Host "  Report: $reportPath" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    return $runReport
}

# Main execution
$state = Initialize-State

# If resume mode and state shows stopped_error, reset to allow restart
if ($Resume -and $state.run_state -eq "stopped_error") {
    $state.run_state = "resuming"
    $state.stop_reason = $null
    $state.last_error = $null
    Save-State $state
}

# Check if we should auto-stop due to phase completion
if ($state.stop_reason -eq "phase_completed") {
    Write-Host "[INIT] Phase was previously completed. Auto-stop enforced." -ForegroundColor Yellow
    Write-Host "[INIT] New phase authorization required to proceed." -ForegroundColor Yellow
    Write-Host "[INIT] Current state preserved. Manual Start with new phase required." -ForegroundColor Yellow
    exit 0
}

# Start the main loop
$finalReport = Start-MainControlLoop -State $state

# Exit with appropriate code
if ($finalReport.stop_reason -eq "execution_error") {
    exit 1
} else {
    exit 0
}
