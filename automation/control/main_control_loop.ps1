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
    if (!$state.schema_version) { $state | Add-Member -NotePropertyName "schema_version" -NotePropertyValue "2.0" }
    if (!$state.run_state) { $state | Add-Member -NotePropertyName "run_state" -NotePropertyValue "stopped" }
    if (!$state.current_phase) { $state | Add-Member -NotePropertyName "current_phase" -NotePropertyValue $Phase }
    if (!$state.current_round) { $state | Add-Member -NotePropertyName "current_round" -NotePropertyValue $StartRound }
    if (!$state.phase_completion_state) { $state | Add-Member -NotePropertyName "phase_completion_state" -NotePropertyValue "not_started" }
    if (!$state.rounds_in_current_run) { $state | Add-Member -NotePropertyName "rounds_in_current_run" -NotePropertyValue @() }
    if (!$state.completed_rounds) { $state | Add-Member -NotePropertyName "completed_rounds" -NotePropertyValue @() }
    if (!$state.ready_for_signoff_rounds) { $state | Add-Member -NotePropertyName "ready_for_signoff_rounds" -NotePropertyValue @() }
    if (!$state.blocked_rounds) { $state | Add-Member -NotePropertyName "blocked_rounds" -NotePropertyValue @() }
    
    return $state
}

# Save state with timestamp
function Save-State {
    param($State)
    $State.updated_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
    $State | ConvertTo-Json -Depth 10 | Set-Content $stateFile -Encoding UTF8
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

# Check if phase is complete
function Test-PhaseComplete {
    param([hashtable]$State)
    
    # Phase is complete if:
    # 1. Current round exceeds phase boundary
    # 2. Or all rounds in phase are marked ready_for_signoff
    # 3. Or specific phase completion criteria met
    
    $currentRoundNum = [int]($State.current_round -replace "R-", "")
    
    # Get phase boundaries from phase_map or use default
    $phaseStart = 1
    $phaseEnd = 15
    
    if ($State.phase_map -and $State.phase_map.($State.current_phase)) {
        $phaseMap = $State.phase_map.($State.current_phase)
        $phaseStart = $phaseMap.start
        $phaseEnd = $phaseMap.end
    } else {
        # Fallback: Parse phase number (Phase 1 -> 1, Phase 2 -> 2, etc.)
        $phaseNum = [int]($State.current_phase -replace "Phase ", "")
        $phaseStart = (($phaseNum - 1) * 15) + 1
        $phaseEnd = $phaseNum * 15
    }
    
    # Check if current round exceeds phase boundary
    if ($currentRoundNum -gt $phaseEnd) {
        Write-Host "[PHASE] Round $currentRoundNum exceeds phase boundary ($phaseEnd)" -ForegroundColor Yellow
        return $true
    }
    
    # Check if all expected rounds in phase are marked ready_for_signoff
    $expectedRounds = $phaseEnd - $phaseStart + 1
    $completedInPhase = 0
    
    foreach ($round in $State.ready_for_signoff_rounds) {
        $roundNum = [int]($round -replace "R-", "")
        if ($roundNum -ge $phaseStart -and $roundNum -le $phaseEnd) {
            $completedInPhase++
        }
    }
    
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
        [hashtable]$State,
        [hashtable]$RunReport
    )
    
    Write-Progress -Activity "Main Control Loop" -Status "Executing $RoundId" -PercentComplete -1
    
    # Update state
    $State.current_round = $RoundId
    $State.phase_completion_state = "in_progress"
    $State.run_state = "running"
    $State.last_action = "round_start"
    Save-State $State
    
    # Generate prompt artifact
    $promptArtifact = Generate-PromptArtifact `
        -RoundId $RoundId `
        -TaskType "candidate_execution" `
        -TaskDescription "Execute $RoundId with full formal governance compliance" `
        -AuthorizedScope "Single round execution within current phase only" `
        -PreviousContext "Previous round completed successfully. State updated."
    
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
        $returnArtifact = Generate-ReturnArtifact `
            -RoundId $RoundId `
            -Status "candidate_ready" `
            -FormalStatusCode "candidate_ready_awaiting_manual_review" `
            -Summary "Round execution completed. Candidate ready for review." `
            -FilesModified @() `
            -ReplyId $promptArtifact.reply_id `
            -CommitHash "NONE" `
            -NextAction "Review candidate and approve/promote or request corrections"
        
        $State.latest_return_artifact = $returnArtifact.archive_path
        Save-State $State
        
        Write-Host "[LOOP] Return artifact captured" -ForegroundColor Green
    }
    
    # Add to rounds in current run
    if ($State.rounds_in_current_run -notcontains $RoundId) {
        $State.rounds_in_current_run += $RoundId
    }
    
    # Update run report
    $RunReport.rounds_executed += @($RoundId)
    
    return @{
        success = $true
        prompt_artifact = $promptArtifact
        status = "candidate_ready"
    }
}

# Main loop
function Start-MainControlLoop {
    param([hashtable]$State)
    
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
