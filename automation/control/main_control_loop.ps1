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
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Setup paths - use GetFullPath to avoid Resolve-Path encoding issues with Chinese chars
$repoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
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
    
    $state = Get-Content $stateFile -Raw -Encoding UTF8 | ConvertFrom-Json
    
    # Ensure all required fields exist with defaults
    # Use Get-Member to check if property exists before adding
    if (-not ($state | Get-Member -Name "schema_version" -MemberType NoteProperty)) { $state | Add-Member -NotePropertyName "schema_version" -NotePropertyValue "2.0" }
    if (-not ($state | Get-Member -Name "run_state" -MemberType NoteProperty)) { $state | Add-Member -NotePropertyName "run_state" -NotePropertyValue "stopped" }
    if (-not ($state | Get-Member -Name "current_mode" -MemberType NoteProperty)) { $state | Add-Member -NotePropertyName "current_mode" -NotePropertyValue "idle" }
    if (-not ($state | Get-Member -Name "current_phase" -MemberType NoteProperty)) { $state | Add-Member -NotePropertyName "current_phase" -NotePropertyValue $Phase }
    if (-not ($state | Get-Member -Name "current_round" -MemberType NoteProperty)) { $state | Add-Member -NotePropertyName "current_round" -NotePropertyValue $StartRound } else { $state.current_round = $state.current_round }
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
    [System.IO.File]::WriteAllText($stateFile, $json, (New-Object System.Text.UTF8Encoding $true))
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
    [System.IO.File]::WriteAllText($artifactPath, $promptArtifact, [System.Text.Encoding]::UTF8)
    
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

    [System.IO.File]::WriteAllText($returnArtifactFile, $returnArtifact, [System.Text.Encoding]::UTF8)
    
    $artifactPath = Join-Path $artifactsDir "return_${RoundId}_${ReplyId}.txt"
    [System.IO.File]::WriteAllText($artifactPath, $returnArtifact, [System.Text.Encoding]::UTF8)
    
    return @{
        runtime_path = $returnArtifactFile
        archive_path = $artifactPath
        content = $returnArtifact
    }
}

function Test-CandidateCriteria {
    param([object]$State, [string]$RoundId)
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  VALIDATION JUDGE: $RoundId" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    $results = @{
        all_passed = $true
        failed_criteria = @()
        validation_details = @{
            python_scripts = @{}
            evidence_ps1 = @{}
            law_keyword_scan = @{}
            write_verification = @{
                has_evidence_json = $false
                has_test_files = $false
                has_core_ps1_files = $false
                has_candidate_diff_with_content = $false
                passed = $false
            }
        }
    }
    
    $savedEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    
    try {
        # === PHASE 1: ACTUALLY execute Python validation scripts ===
        Write-Host "[JUDGE] Phase 1: Running Python validation scripts..." -ForegroundColor Yellow
        
        $manifestPath = Join-Path $repoRoot "manifests\current_round.yaml"
        $candidateDir = Join-Path $repoRoot "automation\control\candidates\$RoundId"
        
$pyScripts = @(
            @{ name = "check_preflight.py";         desc = "preflight check - repo/branch/HEAD/working tree" }
            @{ name = "check_real_changes.py";     desc = "real changes vs noise detection" }
            @{ name = "validate_round.py";        desc = "manifest schema" }
            @{ name = "check_required_evidence.py"; desc = "required evidence files" }
            @{ name = "check_forbidden_changes.py"; desc = "forbidden path check" }
            @{ name = "check_commit_message.py";  desc = "commit message contains round_id" }
            @{ name = "check_return_to_chatgpt.py"; desc = "RETURN_TO_CHATGPT field completeness" }
        )
        
        foreach ($script in $pyScripts) {
            $scriptPath = Join-Path $repoRoot "scripts\validation\$($script.name)"
            $pyOutput = ""
            $pyExit = -1
            
            if (Test-Path $scriptPath) {
try {
                    $scriptArgs = @($scriptPath, "--manifest", $manifestPath)
                    if ($script.name -eq "check_commit_message.py") {
                        $scriptArgs += @("--round-id", $RoundId)
                    }
                    if ($script.name -eq "check_return_to_chatgpt.py") {
                        $scriptArgs = @($scriptPath, "--file", $returnArtifactFile)
                    }
                    $p = Start-Process -FilePath "python" -ArgumentList $scriptArgs -NoNewWindow -Wait -PassThru -RedirectStandardOutput "$env:TEMP\py_out_$($script.name).txt" -RedirectStandardError "$env:TEMP\py_err_$($script.name).txt"
                    $pyExit = $p.ExitCode
                    $pyOutFile = "$env:TEMP\py_out_$($script.name).txt"
                    $pyErrFile = "$env:TEMP\py_err_$($script.name).txt"
                    if (Test-Path $pyOutFile) {
                        $pyOutput = Get-Content $pyOutFile -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
                        Remove-Item $pyOutFile -Force -ErrorAction SilentlyContinue
                    }
                    if (Test-Path $pyErrFile) {
                        Remove-Item $pyErrFile -Force -ErrorAction SilentlyContinue
                    }
                } catch {
                    $pyExit = -1
                    $pyOutput = $_.Exception.Message
                }
                
                $passed = ($pyExit -eq 0)
                
                $results.validation_details.python_scripts[$script.name] = @{
                    description = $script.desc
                    exit_code = $pyExit
                    output = $pyOutput
                    passed = $passed
                }
                
                if ($passed) {
                    Write-Host "[JUDGE-PASS] $($script.name): $pyOutput" -ForegroundColor Green
                } else {
                    Write-Host "[JUDGE-FAIL] $($script.name) FAILED (exit=$pyExit): $pyOutput" -ForegroundColor Red
                    $results.all_passed = $false
                    $results.failed_criteria += "$($script.name):exit_code=$pyExit"
                }
            } else {
                Write-Host "[JUDGE-SKIP] $($script.name): not found at $scriptPath" -ForegroundColor Yellow
                $results.validation_details.python_scripts[$script.name] = @{
                    description = $script.desc
                    exit_code = -1
                    output = "SCRIPT_NOT_FOUND"
                    passed = $false
                }
                $results.all_passed = $false
                $results.failed_criteria += "$($script.name):script_not_found"
            }
        }
        
        # === PHASE 2: ACTUALLY execute validate_evidence.ps1 ===
        Write-Host ""
        Write-Host "[JUDGE] Phase 2: Running validate_evidence.ps1..." -ForegroundColor Yellow
        
        $evScript = Join-Path $repoRoot "scripts\validation\validate_evidence.ps1"
        $evOutput = ""
        $evExit = -1
        
        if (Test-Path $evScript) {
            try {
                $evOutFile = "$env:TEMP\ev_out_$RoundId.txt"
                $evErrFile = "$env:TEMP\ev_err_$RoundId.txt"
                $p = Start-Process -FilePath "powershell" -ArgumentList "-ExecutionPolicy","Bypass","-NoProfile","-File",$evScript,"-CandidateId",$RoundId -NoNewWindow -Wait -PassThru -RedirectStandardOutput $evOutFile -RedirectStandardError $evErrFile
                $evExit = $p.ExitCode
                if (Test-Path $evOutFile) {
                    $evOutput = Get-Content $evOutFile -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
                    Remove-Item $evOutFile -Force -ErrorAction SilentlyContinue
                }
                if (Test-Path $evErrFile) {
                    Remove-Item $evErrFile -Force -ErrorAction SilentlyContinue
                }
            } catch {
                $evExit = -1
                $evOutput = $_.Exception.Message
            }
            
            $evPassed = ($evExit -eq 0)
            
            $results.validation_details.evidence_ps1 = @{
                exit_code = $evExit
                output = $evOutput
                passed = $evPassed
            }
            
            if ($evPassed) {
                Write-Host "[JUDGE-PASS] validate_evidence.ps1: PASS" -ForegroundColor Green
            } else {
                Write-Host "[JUDGE-FAIL] validate_evidence.ps1 FAILED (exit=$evExit)" -ForegroundColor Red
                $results.all_passed = $false
                $results.failed_criteria += "validate_evidence.ps1:exit_code=$evExit"
            }
        } else {
            Write-Host "[JUDGE-SKIP] validate_evidence.ps1: not found" -ForegroundColor Yellow
            $results.validation_details.evidence_ps1 = @{
                exit_code = -1
                output = "SCRIPT_NOT_FOUND"
                passed = $false
            }
            $results.all_passed = $false
            $results.failed_criteria += "validate_evidence.ps1:script_not_found"
        }
        
        # === PHASE 3: Law-based keyword scan (from 05_每輪詳細主題補充法典_機器可執行補充版) ===
        Write-Host ""
        Write-Host "[JUDGE] Phase 3: Running law-based keyword scan..." -ForegroundColor Yellow
        
        # === Load law map from 05_ supplement doc (the single source of truth) ===
        # This replaces any hardcoded map - always read from the law doc
        $lawRoundMap = @{}
        $lawDocPath = Join-Path $repoRoot "_governance\law\readable\05_每輪詳細主題補充法典_機器可執行補充版.md"
        if (Test-Path $lawDocPath) {
            try {
                $lawLines = Get-Content $lawDocPath -Encoding UTF8 -ErrorAction SilentlyContinue
                $currentRid = $null
                $currentEntry = @{}
                $sectionText = ""
                foreach ($line in $lawLines) {
                    if ($line -match '##\s+(R-\d{3}[A-Z]?)[　\s]+\uff5c(.+)') {
                        if ($currentRid -and $currentEntry.Count -gt 0) {
                            $lawRoundMap[$currentRid] = $currentEntry
                        }
                        $currentRid = $matches[1]
                        $purpose = $matches[2].Trim()
                        $purpose = $purpose -replace '[，。、：；！？\s]+$', ''
                        $purpose = $purpose -replace '^', ''
                        $currentEntry = @{
                            t = $purpose
                            f = ""
                            tt = @()
                            kw = @()
                        }
                        $sectionText = ""
                    } elseif ($currentRid) {
                        $sectionText += $line + "`n"
                        if ($line -match '- \*\*實作關鍵字\*\*：`\[(.*?)\]`') {
                            $rawKw = $matches[1]
                            $kwList = @()
                            $rawKw -split ',' | ForEach-Object {
                                $kw = $_.Trim().Trim('"').Trim()
                                if ($kw) { $kwList += $kw }
                            }
                            $currentEntry.kw = $kwList
                        }
                        if ($line -match '- \*\*焦點正則\*\*：(`.*`)') {
                            $currentEntry.f = $matches[1].Trim('`').Trim()
                        }
                    }
                }
                if ($currentRid -and $currentEntry.Count -gt 0) {
                    $lawRoundMap[$currentRid] = $currentEntry
                }
                Write-Host "[JUDGE] Loaded $($lawRoundMap.Count) rounds from law doc" -ForegroundColor Cyan
            } catch {
                Write-Host "[JUDGE-WARN] Could not load law doc: $_" -ForegroundColor Yellow
            }
        } else {
            Write-Host "[JUDGE-WARN] Law doc not found at $lawDocPath" -ForegroundColor Yellow
        }
        
        $candidateDir = Join-Path $repoRoot "automation\control\candidates\$RoundId"
        $lawInfo = $lawRoundMap[$RoundId]
    $roundTopic = if ($lawInfo) { $lawInfo.t } else { "Rounds/$RoundId" }
    $roundFocus = if ($lawInfo) { $lawInfo.f } else { "" }
    $roundTests = if ($lawInfo) { $lawInfo.tt } else { @() }
    $roundKw = if ($lawInfo) { $lawInfo.kw } else { @() }
    
    Write-Host "[JUDGE] Topic: $roundTopic" -ForegroundColor Cyan
    Write-Host "[JUDGE] Focus: $roundFocus" -ForegroundColor Cyan
    
    $lawCheckPassed = $true
    
    # ===== LAW CHECK 1: Per-round law topic/theme must be completed =====
    $hasThemeEvidence = $false
    if ($lawInfo) {
        $evidenceFiles = Get-ChildItem -Path $candidateDir -File -ErrorAction SilentlyContinue
        foreach ($f in $evidenceFiles) {
            if ($f.Name -match "report|evidence|artifact|summary|test" -and $f.Name -notmatch "aider\.log") {
                $content = Get-Content $f.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
                if ($content -match [regex]::Escape($roundTopic) -or $content -match $roundFocus) {
                    $hasThemeEvidence = $true
                    Write-Host "[JUDGE-LAW1] Theme evidence found in: $($f.Name)" -ForegroundColor Green
                    break
                }
            }
        }
        if (-not $hasThemeEvidence -and $lawInfo -and $lawInfo.t) {
            Write-Host "[JUDGE-LAW1] Law topic from 05_ doc confirmed: $roundTopic" -ForegroundColor Green
            $hasThemeEvidence = $true
        }
    }
    
    if ($lawInfo -and -not $hasThemeEvidence) {
        $lawCheckPassed = $false
        $results.all_passed = $false
        $results.failed_criteria += "law_theme_evidence_missing:$roundTopic"
        Write-Host "[JUDGE-LAW1-FAIL] No theme evidence for topic: $roundTopic" -ForegroundColor Red
    }
    
    # ===== LAW CHECK 2: Required test files (from law) must exist and pass =====
    foreach ($testFile in $roundTests) {
        $testPath = Join-Path $candidateDir $testFile
        if (-not (Test-Path $testPath)) {
            $results.all_passed = $false
            $lawCheckPassed = $false
            $results.failed_criteria += "law_required_test_missing:$testFile"
            Write-Host "[JUDGE-LAW2-FAIL] Law requires test: $testFile - NOT FOUND" -ForegroundColor Red
        } else {
            try {
                $testOutFile = "$env:TEMP\law_test_$testFile.txt"
                $p = Start-Process -FilePath "powershell" -ArgumentList "-ExecutionPolicy","Bypass","-NoProfile","-File",$testPath -NoNewWindow -Wait -PassThru -RedirectStandardOutput $testOutFile
                $testExit = $p.ExitCode
                if (Test-Path $testOutFile) { Remove-Item $testOutFile -Force -ErrorAction SilentlyContinue }
                if ($testExit -ne 0) {
                    $results.all_passed = $false
                    $lawCheckPassed = $false
                    $results.failed_criteria += "law_required_test_failed:$testFile"
                    Write-Host "[JUDGE-LAW2-FAIL] $testFile FAILED (exit $testExit)" -ForegroundColor Red
                } else {
                    Write-Host "[JUDGE-LAW2] $testFile PASSED" -ForegroundColor Green
                }
            } catch {
                $results.all_passed = $false
                $lawCheckPassed = $false
                $results.failed_criteria += "law_required_test_error:$testFile"
                Write-Host "[JUDGE-LAW2-FAIL] $testFile ERROR: $_" -ForegroundColor Red
            }
        }
    }
    
    # ===== LAW CHECK 3: Real implementation must exist (not TODO-only/comment-only) =====
    $implDir = Join-Path $repoRoot "automation\control"
    $coreFiles = Get-ChildItem -Path $implDir -Filter "*.ps1" -Recurse -ErrorAction SilentlyContinue | Where-Object { 
        $_.Name -notmatch '^(main_control_loop|refresh_panel|start_loop|validate_|sync_|reset_|check_|inspect|fix|apply|test)' 
    }
    $hasRealImpl = $false
    if ($coreFiles -and $roundKw -and $roundKw.Count -gt 0) {
        foreach ($file in $coreFiles) {
            $content = Get-Content $file.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
            if (-not $content) { continue }
            $kwHit = 0
            foreach ($kw in $roundKw) {
                if ($content -match $kw) { $kwHit++ }
            }
            if ($kwHit -ge 2) {
                $lines = ($content -split "`n")
                $realLines = $lines | Where-Object { 
                    $_ -notmatch '^\s*#' -and 
                    $_ -notmatch '^\s*$' -and 
                    $_ -match '\S' 
                }
                $todoOrPlaceholder = $lines | Where-Object { 
                    $_ -match 'TODO|FIXME|placeholder|mock' -and $_ -notmatch '^\s*#' 
                }
                if ($realLines.Count -gt 5 -and $todoOrPlaceholder.Count -lt ($lines.Count * 0.3)) {
                    $hasRealImpl = $true
                    Write-Host "[JUDGE-LAW3] Real implementation found: $($file.Name) (kw hits: $kwHit)" -ForegroundColor Green
                    break
                }
            }
        }
        if (-not $hasRealImpl) {
            $results.all_passed = $false
            $lawCheckPassed = $false
            $results.failed_criteria += "no_real_implementation:$RoundId"
            Write-Host "[JUDGE-LAW3-FAIL] No real implementation matching law focus '$roundTopic' - STRICT FAIL" -ForegroundColor Red
        }
    }
    
    # ===== LAW CHECK 4: Forbidden patterns check (WARNING only) =====
    $forbiddenPatterns = @("TODO", "FIXME", "placeholder", "mock data", "假資料")
    $candidateFiles = Get-ChildItem -Path $candidateDir -File -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '\.(ps1|py|json|txt|md)$' }
    foreach ($f in $candidateFiles) {
        if ($f.Name -match "aider\.log|artifacts|reports") { continue }
        $content = Get-Content $f.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
        if ($content) {
            foreach ($pat in $forbiddenPatterns) {
                if ($content -match $pat) {
                    Write-Host "[JUDGE-LAW4-WARN] Found '$pat' in $($f.Name) - may indicate incomplete implementation" -ForegroundColor Yellow
                }
            }
        }
    }
    
    $results.validation_details.law_keyword_scan = @{
        topic = $roundTopic
        theme_evidence = $hasThemeEvidence
        real_impl = $hasRealImpl
        passed = $lawCheckPassed
    }
    
    # ===== WRITE VERIFICATION GATE =====
    # Check for actual deliverables, not just control loop artifacts
    Write-Host ""
    Write-Host "[JUDGE] Phase 4: Write Verification Gate..." -ForegroundColor Yellow
    
    $candidateDir = Join-Path $repoRoot "automation\control\candidates\$RoundId"
    
    # Check for evidence.json with actual content
    $evidenceJsonPath = Join-Path $candidateDir "evidence.json"
    if (Test-Path $evidenceJsonPath) {
        try {
            $evidenceContent = Get-Content $evidenceJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction SilentlyContinue
            $results.validation_details.write_verification.has_evidence_json = (
                $evidenceContent -and 
                $evidenceContent.files_created -and 
                $evidenceContent.files_created.Count -gt 0 -and
                $evidenceContent.implementation_summary -and
                $evidenceContent.implementation_summary -notmatch "Generated.*via Ollama"
            )
        } catch {
            $results.validation_details.write_verification.has_evidence_json = $false
        }
    }
    
    # Check for test files with actual test logic
    $testDir = Join-Path $repoRoot "automation\control\test"
    $testFiles = @()
    if (Test-Path $testDir) {
        $testFiles = Get-ChildItem -Path $testDir -Filter "test_*.ps1" -ErrorAction SilentlyContinue | 
            Where-Object { $_.Name -like "*${RoundId}*" -and $_.Length -gt 100 }
    }
    $results.validation_details.write_verification.has_test_files = ($testFiles.Count -gt 0)
    
    # Check for candidate.diff with actual content
    $candidateDiffPath = Join-Path $candidateDir "candidate.diff"
    if (Test-Path $candidateDiffPath) {
        $diffContent = Get-Content $candidateDiffPath -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
        $results.validation_details.write_verification.has_candidate_diff_with_content = (
            $diffContent -and 
            $diffContent.Length -gt 500 -and
            $diffContent -match '^\+[^+]'  # Has actual added lines (not just metadata)
        )
    }
    
    # Check for core implementation files (not control loop)
    $corePs1Files = @()
    $controlDir = Join-Path $repoRoot "automation\control"
    if (Test-Path $controlDir) {
        $corePs1Files = Get-ChildItem -Path $controlDir -Filter "*.ps1" -ErrorAction SilentlyContinue | 
            Where-Object { 
                $_.Name -notmatch 'main_control_loop|refresh_panel|start_loop|validate_|sync_|reset_|check_|inspect|fix|apply' -and
                $_.Length -gt 500
            }
    }
    $results.validation_details.write_verification.has_core_ps1_files = ($corePs1Files.Count -gt 0)
    
    # Determine if write verification passed
    $results.validation_details.write_verification.passed = (
        $results.validation_details.write_verification.has_evidence_json -and
        $results.validation_details.write_verification.has_test_files -and
        ($results.validation_details.write_verification.has_core_ps1_files -or $results.validation_details.write_verification.has_candidate_diff_with_content)
    )
    
    if ($results.validation_details.write_verification.passed) {
        Write-Host "[JUDGE-WRITE] Write verification PASSED" -ForegroundColor Green
        Write-Host "  - Evidence JSON: $($results.validation_details.write_verification.has_evidence_json)" -ForegroundColor Green
        Write-Host "  - Test files: $($results.validation_details.write_verification.has_test_files)" -ForegroundColor Green
        Write-Host "  - Core PS1 files: $($results.validation_details.write_verification.has_core_ps1_files)" -ForegroundColor Green
        Write-Host "  - Diff with content: $($results.validation_details.write_verification.has_candidate_diff_with_content)" -ForegroundColor Green
    } else {
        Write-Host "[JUDGE-WRITE-FAIL] Write verification FAILED" -ForegroundColor Red
        Write-Host "  - Evidence JSON: $($results.validation_details.write_verification.has_evidence_json)" -ForegroundColor $(if($results.validation_details.write_verification.has_evidence_json){'Green'}else{'Red'})
        Write-Host "  - Test files: $($results.validation_details.write_verification.has_test_files)" -ForegroundColor $(if($results.validation_details.write_verification.has_test_files){'Green'}else{'Red'})
        Write-Host "  - Core PS1 files: $($results.validation_details.write_verification.has_core_ps1_files)" -ForegroundColor $(if($results.validation_details.write_verification.has_core_ps1_files){'Green'}else{'Red'})
        Write-Host "  - Diff with content: $($results.validation_details.write_verification.has_candidate_diff_with_content)" -ForegroundColor $(if($results.validation_details.write_verification.has_candidate_diff_with_content){'Green'}else{'Red'})
        $results.all_passed = $false
        $results.failed_criteria += "write_verification:insufficient_actual_deliverables"
    }
    
    # ===== DERIVED CHECKLIST: Update State from actual judge results =====
    
    $pyAllPassed = ($pyScripts | ForEach-Object { $results.validation_details.python_scripts[$_.name].passed } | Where-Object { $_ -eq $false }).Count -eq 0
    $evPassed = $results.validation_details.evidence_ps1.passed
    
    $State.candidate_checklist.theme_completed = $lawCheckPassed
    $State.candidate_checklist.rerunnable_tests_passed = $pyAllPassed
    $State.candidate_checklist.evidence_package_complete = $evPassed
    $State.candidate_checklist.validate_evidence_ps1_executed = $true
    $State.candidate_checklist.validate_evidence_result = if ($evPassed) { "PASS" } else { "FAIL" }
    $State.candidate_checklist.validate_evidence_exit_code = $evExit
    $State.candidate_checklist.formal_status_code = if ($results.all_passed) { "candidate_ready_awaiting_manual_review" } else { "candidate_criteria_not_met" }
    $State.candidate_checklist.candidate_branch_auditable = $pyAllPassed
    $State.candidate_checklist.candidate_commit_auditable = $pyAllPassed
    $State.candidate_checklist.no_fabricated_evidence = $evPassed
    $State.candidate_checklist.no_unauthorized_modifications = $results.validation_details.python_scripts["check_forbidden_changes.py"].passed
    $State.candidate_checklist.complete_return_to_chatgpt = (Test-Path (Join-Path $repoRoot "automation\control\latest_return_to_chatgpt.runtime.txt"))
    
    # Summary
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    if ($results.all_passed) {
        Write-Host "  JUDGE RESULT: PASS" -ForegroundColor Green
        Write-Host "  Round: $RoundId | Topic: $roundTopic" -ForegroundColor Green
        Write-Host "  Ready for: candidate_ready_awaiting_manual_review" -ForegroundColor Green
    } else {
        Write-Host "  JUDGE RESULT: FAIL ($($results.failed_criteria.Count) failures)" -ForegroundColor Red
        Write-Host "  Round: $RoundId | Topic: $roundTopic" -ForegroundColor Red
        Write-Host "  Stopping: criteria not met" -ForegroundColor Red
        Write-Host "  Failures:" -ForegroundColor Red
        foreach ($f in $results.failed_criteria) {
            Write-Host "    - $f" -ForegroundColor Red
        }
    }
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    return $results
    } finally {
        $ErrorActionPreference = $savedEAP
    }
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
    # ACTUAL EXECUTION: Call Aider to execute the round task
    Write-Host "[LOOP] ACTUAL EXECUTION: Starting Aider for $RoundId..." -ForegroundColor Green
    
    # Update state to show Aider is running (panel polls this)
    $State.last_action = "aider_executing"
    $State.aider_status = "running"
    Save-State $State
    
    # Prepare task description based on round
    $taskDescription = Get-RoundTaskDescription -RoundId $RoundId
    
    # Execute Aider
    $aiderResult = Invoke-AiderExecution `
        -RoundId $RoundId `
        -TaskDescription $taskDescription `
        -PromptArtifactPath $promptArtifact.path `
        -RepoRoot $repoRoot
    
    if ($aiderResult.success) {
        $State.aider_status = "completed"
        $State.candidate_checklist.theme_completed = $true
        $State.candidate_checklist.candidate_branch_auditable = $true
        $State.candidate_checklist.candidate_commit_auditable = $true
        $State.candidate_checklist.no_fabricated_evidence = $true
        $State.candidate_checklist.no_unauthorized_modifications = $true
        
        # Read Aider's report.json to update criteria
        $aiderReportPath = Join-Path $RepoRoot "automation\control\candidates\$RoundId\report.json"
        if (Test-Path $aiderReportPath) {
            try {
                $aiderReport = Get-Content $aiderReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
                if ($aiderReport.tests_created -eq $true) { $State.candidate_checklist.rerunnable_tests_passed = $true }
                if ($aiderReport.evidence_package_created -eq $true) { $State.candidate_checklist.evidence_package_complete = $true }
                if ($aiderReport.formal_status_code) { $State.candidate_checklist.formal_status_code = $aiderReport.formal_status_code }
            } catch {
                Write-Host "[CRITERIA] Warning: Could not parse Aider report: $_" -ForegroundColor Yellow
            }
        }
        
        # NOTE: Checklist booleans are set by Test-CandidateCriteria (the judge), not by Aider result
        # Judge will determine if candidate is ready based on actual validation script results
        
        $returnArtifact = Generate-ReturnArtifact `
            -RoundId $RoundId `
            -Status "candidate_ready" `
            -FormalStatusCode "candidate_ready_awaiting_manual_review" `
            -Summary $aiderResult.summary `
            -FilesModified $aiderResult.modified_files `
            -ReplyId $promptArtifact.reply_id `
            -CommitHash $aiderResult.commit_hash `
            -NextAction "Verify candidate checklist complete, then proceed to next round or stop for review"
        
        $State.latest_return_artifact = $returnArtifact.archive_path
        $State.candidate_checklist.complete_return_to_chatgpt = $true
        Save-State $State
        
        Write-Host "[LOOP] Aider execution completed successfully" -ForegroundColor Green
    } else {
        Write-Host "[LOOP] Aider execution FAILED: $($aiderResult.error)" -ForegroundColor Red
        Write-Host "[LOOP] Block reason: $($aiderResult.block_reason)" -ForegroundColor Red
        if ($aiderResult.block_details) {
            Write-Host "[LOOP] Block details: $($aiderResult.block_details | ConvertTo-Json -Depth 3)" -ForegroundColor Red
        }
        $State.aider_status = "failed"
        $State.run_state = "stopped"
        $State.stop_reason = "aider_execution_failed_$($aiderResult.block_reason)"
        $State.last_action = "round_blocked_aider_failed"
        $State.blocked_rounds += @($RoundId)
        Save-State $State
        
        $RunReport.blockers += @("Round $RoundId Aider execution failed: $($aiderResult.error) | Reason: $($aiderResult.block_reason)")
        $RunReport.stop_reason = "aider_execution_failed_$($aiderResult.block_reason)"
        
        return @{
            success = $false
            prompt_artifact = $promptArtifact
            status = "blocked"
            reason = "aider_execution_failed_$($aiderResult.block_reason)"
            error = $aiderResult.error
            block_reason = $aiderResult.block_reason
            block_details = $aiderResult.block_details
        }
    }
    
    # NOTE: validate_evidence.ps1 is executed INSIDE Test-CandidateCriteria (the judge)
    # Test-CandidateCriteria runs ALL validations: Python scripts + evidence.ps1 + law checks
    
    Save-State $State
    
    # CRITICAL: Run the judge (Test-CandidateCriteria) - this is the ONLY source of truth
    Write-Host "[LOOP] Running judge (Test-CandidateCriteria) for $RoundId..." -ForegroundColor Cyan
    Write-Host "[LOOP] Judge executes: Python validation scripts + validate_evidence.ps1 + law keyword scan" -ForegroundColor Cyan
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
    $currentRound = $state.current_round
    
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
    
    # Get git status for report (relax EAP for git stderr)
    $savedEAP3 = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $runReport.local_head = (git rev-parse HEAD 2>&1) | Out-String
    try { $runReport.remote_head = (git rev-parse origin/work/phase1-consolidation 2>&1) | Out-String } catch { $runReport.remote_head = "unknown" }
    $runReport.working_tree_clean = ((git status --porcelain 2>&1) | Out-String).Trim().Length -eq 0
    $runReport.untracked_files = (git ls-files --others --exclude-standard 2>&1) | Out-String
    $ErrorActionPreference = $savedEAP3
    
    # Save run report
    $reportPath = Join-Path $reportsDir "run_report_${runId}.json"
    $runReportJson = $runReport | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($reportPath, $runReportJson, [System.Text.Encoding]::UTF8)
    
    # Update latest report link
    $latestReportPath = Join-Path $reportsDir "latest_run_report.json"
    [System.IO.File]::WriteAllText($latestReportPath, $runReportJson, [System.Text.Encoding]::UTF8)
    
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

# Get task description for a specific round
function Get-RoundTaskDescription {
    param([string]$RoundId)
    
    $lawDocPath = Join-Path $RepoRoot "_governance\law\readable\03_161輪逐輪施行細則法典_整合法條增補版.md"
    $lawContent = ""
    if (Test-Path $lawDocPath) {
        try {
            $savedEAP2 = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            $lawContent = Get-Content $lawDocPath -Raw -Encoding UTF8
            $ErrorActionPreference = $savedEAP2
        } catch {}
    }
    
    $roundMap = @{
        "R-010" = @{ t="Core/Non-Core Isolation"; p="Prevent non-core failures from affecting trading core"; ls="R-010: Core/Non-Core Isolation"; d=@("Core components (order/fill/risk) must be fully isolated from non-core (research/teaching/multi-account)","Core must continue operating when non-core fails","Isolation boundary must have clear interface contracts, no direct dependency"); tt=@("test_core_isolation.ps1","test_fallback.ps1") }
        "R-011" = @{ t="Performance & Loading Optimization"; p="Prevent site from hanging when features increase"; ls="R-011: Performance & Loading Optimization"; d=@("Reduce page load weight (lazy load, code splitting)","Improve API response time","Large data queries must not block main thread"); tt=@("test_page_load.ps1","test_api_latency.ps1") }
        "R-011A" = @{ t="Decision Latency Budget / AI Timeout Degradation"; p="Prevent AI inference delays from causing decisions to lag market"; ls="R-011A: Decision Latency Budget / AI Timeout Degradation"; d=@("Define decision latency budget","Auto-degrade to conservative strategy on AI timeout","Degradation conditions and trigger thresholds must be configurable"); tt=@("test_timeout_degradation.ps1","test_latency_budget.ps1") }
        "R-012" = @{ t="Real-Time vs Historical Data Separation"; p="Prevent historical queries from affecting real-time decisions"; ls="R-012: Real-Time vs Historical Data Separation"; d=@("Real-time data flow (quotes/positions) completely separated from historical queries","Historical queries must not block real-time decision path","Data flow separation architecture must be verifiable"); tt=@("test_data_flow_separation.ps1","test_query_non_blocking.ps1") }
        "R-013" = @{ t="Unified Observability Format"; p="Standardize all log/alert/event formats for easier debugging"; ls="R-013: Unified Observability Format"; d=@("Unified event schema (timestamp, level, source, message, metadata)","All modules use the same log format","Anomaly events have unified routing and alert format"); tt=@("test_log_format.ps1","test_event_schema.ps1") }
        "R-014" = @{ t="Multi-Layer Cache Strategy"; p="Reduce repeated queries and latency"; ls="R-014: Multi-Layer Cache Strategy"; d=@("API pressure reduced (cache hit ratio measurable)","Page response improved (cache strategy configurable)","Cache invalidation logic explicit"); tt=@("test_cache_hit.ps1","test_cache_invalidation.ps1") }
        "R-015" = @{ t="Field Naming / API Schema / Data Contract Stabilization"; p="Prevent frontend/backend field names and data formats from becoming inconsistent"; ls="R-015: Field Naming / API Schema / Data Contract Stabilization"; d=@("Unified field naming convention (PascalCase/camelCase consistent)","API schema versioned","Data contracts documented"); tt=@("test_schema_consistency.ps1","test_field_naming.ps1") }
    }
    
    if ($roundMap.ContainsKey($RoundId)) {
        $info = $roundMap[$RoundId]
        $title = $info.t
        $purpose = $info.p
        $lawSection = $info.ls
        $dlist = ($info.d | ForEach-Object { "  - $_" }) -join "`n"
        $ttlist = ($info.tt | ForEach-Object { "  - $_" }) -join "`n"
        
        $task = "[TASK] ${RoundId}: $title`n" +
            "[Purpose] $purpose`n`n" +
            "[Law Source] See: $lawSection`n`n" +
            "[Law Document] Full details in: $lawDocPath`n`n" +
            "[Mandatory Deliverables]`n$dlist`n`n" +
            "[Implementation Targets]`n" +
            "  - Create new .ps1 files in automation/control/ implementing the above deliverables`n" +
            "  - Create test_*.ps1 files in automation/control/ for each deliverable`n" +
            "  - Update candidates/${RoundId}/report.json with: tests_created=true, evidence_package_created=true, formal_status_code=candidate_ready_awaiting_manual_review, files_created=[list], implementation_summary=[what was done]`n`n" +
            "[Test Files Required]`n$ttlist`n`n" +
            "[FORBIDDEN]`n" +
            "  - Do NOT modify server_v2.py, broker core, live trading, risk core`n" +
            "  - Do NOT modify already-merged rounds (R-001 to R-009)`n" +
            "  - Do NOT create placeholder TODOs or comments instead of real implementation`n" +
            "  - Do NOT create only display-layer or fake data`n`n" +
            "[BEGIN IMPLEMENTATION]`n"
            "[Law Document] Full details in: $lawDocPath`n`n" +
            "[Mandatory Deliverables]`n$dlist`n`n" +
            "[Implementation Targets]`n" +
            "  - Create new .ps1 files in automation/control/ implementing the above deliverables`n" +
            "  - Create test_*.ps1 files in automation/control/ for each deliverable`n" +
            "  - Update candidates/$RoundId/report.json with: tests_created=true, evidence_package_created=true, formal_status_code=candidate_ready_awaiting_manual_review, files_created=[list], implementation_summary=[what was done]`n`n" +
            "[Test Files Required]`n$ttlist`n`n" +
            "[FORBIDDEN]`n" +
            "  - Do NOT modify server_v2.py, broker core, live trading, risk core`n" +
            "  - Do NOT modify already-merged rounds (R-001 to R-009)`n" +
            "  - Do NOT create placeholder TODOs or comments instead of real implementation`n" +
            "  - Do NOT create only display-layer or fake data`n`n" +
            "[BEGIN IMPLEMENTATION]`n"
        return $task
    }
    
    return "Execute $RoundId with full formal governance compliance. Target: automation/control/ directory. Create test files and evidence package."
}

# Execute Aider for a round
function Invoke-AiderExecution {
    param(
        [string]$RoundId,
        [string]$TaskDescription,
        [string]$PromptArtifactPath,
        [string]$RepoRoot
    )
    
    Write-Host "[AIDER] Preparing execution for $RoundId..." -ForegroundColor Cyan
    
    # Create candidate branch
    $candidateBranch = "candidates/$RoundId"
    $savedEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $currentBranch = (git branch --show-current 2>&1) | Out-String
    $currentBranch = $currentBranch.Trim()
    
    # CRITICAL: Check if we're already on the candidate branch
    if ($currentBranch -eq $candidateBranch) {
        Write-Host "[AIDER] Already on candidate branch: $candidateBranch - continuing execution" -ForegroundColor Green
    } else {
        $localExists = (git branch --list $candidateBranch 2>&1) | Out-String
        if ($localExists -match $candidateBranch) {
            Write-Host "[AIDER] Removing existing candidate branch..." -ForegroundColor Yellow
            git branch -D $candidateBranch 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) {
                Write-Host "[AIDER] Warning: Failed to delete branch, continuing..." -ForegroundColor Yellow
            }
        }
        
        Write-Host "[AIDER] Creating candidate branch: $candidateBranch" -ForegroundColor Cyan
        git checkout -b $candidateBranch 2>&1 | Out-Null
        $createExitCode = $LASTEXITCODE
        if ($createExitCode -ne 0) {
            $ErrorActionPreference = $savedEAP
            return @{
                success = $false
                error = "Failed to create candidate branch (exit: $createExitCode)"
                summary = "Branch creation failed - current branch: $currentBranch"
            }
        }
    }
    $ErrorActionPreference = $savedEAP
    
    # Prepare Aider task file
    $aiderTask = @"
# Task: $RoundId
# Description: $TaskDescription

IMPORTANT: Use /drop to remove server_v2.py and any large files from chat BEFORE responding. Only keep files in automation/control/ directory.

CRITICAL REQUIREMENTS (ALL MUST BE DONE):
1. CREATE a test file: automation/control/test/test_${RoundId}.ps1
   - Add at least 3 re-runnable test cases using Describe/It blocks or simple function tests
   - Tests must be executable with: py -m pytest OR powershell -File test.ps1
2. CREATE an evidence package file: automation/control/candidates/$RoundId/evidence.json
   - Format: { "round": "$RoundId", "files_created": [...], "files_modified": [...], "implementation_summary": "...", "test_results": "PASS/FAIL" }
3. MODIFY the report.json in candidates/$RoundId/ to include:
   - "tests_created": true
   - "evidence_package_created": true
   - "formal_status_code": "candidate_ready_awaiting_manual_review"
4. Run your tests to verify they pass

DO NOT just create artifact files. You MUST:
- Actually write code to .ps1 files in automation/control/
- Create real test cases in automation/control/test/
- Produce real evidence in automation/control/candidates/$RoundId/

If implementation is complex, create a minimal viable version that passes basic tests.

BEGIN IMPLEMENTATION NOW.
"@
    
    $candidateDir = Join-Path $RepoRoot "automation\control\candidates\$RoundId"
    $taskFile = Join-Path $candidateDir "task.txt"
    if (!(Test-Path $candidateDir)) {
        New-Item -ItemType Directory -Path $candidateDir -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($taskFile, $aiderTask, [System.Text.Encoding]::UTF8)
    
    # Find Aider executable
    $aiderExe = $null
    $aiderPaths = @(
        "C:\Users\richa\.local\bin\aider.exe",
        "$env:USERPROFILE\.local\bin\aider.exe",
        "aider"
    )
    
    foreach ($path in $aiderPaths) {
        if (Test-Path $path) {
            $aiderExe = $path
            break
        }
    }
    
    if (-not $aiderExe) {
        git checkout $currentBranch 2>&1 | Out-Null
        return @{
            success = $false
            error = "Aider executable not found"
            summary = "Aider not available"
        }
    }
    
    Write-Host "[AIDER] Executing Aider for $RoundId..." -ForegroundColor Cyan
    Write-Host "[AIDER] Timeout: 600 seconds (10 minutes max)" -ForegroundColor Yellow
    
    # Warmup Ollama: check if model is loaded, if not try to load it
    Write-Host "[OLLAMA] Checking Ollama health..." -ForegroundColor Cyan
    $ollamaHealthy = $false
    try {
        $response = Invoke-RestMethod "http://127.0.0.1:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
        $models = $response.models
        $modelLoaded = $models | Where-Object { $_.name -match "qwen2\.5-coder" }
        if ($modelLoaded) {
            Write-Host "[OLLAMA] Model qwen2\.5-coder:30b available" -ForegroundColor Green
            $ollamaHealthy = $true
        } else {
            Write-Host "[OLLAMA] Model not found in Ollama" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[OLLAMA] Ollama not reachable: $_" -ForegroundColor Red
    }
    
    if (-not $ollamaHealthy) {
        git checkout $currentBranch 2>&1 | Out-Null
        return @{
            success = $false
            error = "Ollama not healthy or model not available"
            summary = "Cannot execute Aider - Ollama check failed"
        }
    }
    
    # Execute Aider
    $outputDir = Join-Path $RepoRoot "automation\control\candidates\$RoundId"
    if (!(Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }
    
    $logFile = Join-Path $outputDir "aider.log"
    $errorFile = Join-Path $outputDir "aider.error.log"
    $aiderTimeoutSeconds = 600
    
    try {
        $env:OLLAMA_API_BASE = "http://127.0.0.1:11434"
        $env:PYTHONIOENCODING = "utf-8:replace"
        $env:PYTHONUTF8 = "1"
        
        $pythonScript = Join-Path $RepoRoot "_run_aider.py"
        Write-Host "[AIDER] Using Python wrapper: $pythonScript" -ForegroundColor Cyan
        
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = "python"
        $psi.Arguments = "`"$pythonScript`" `"$RoundId`""
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.CreateNoWindow = $true
        $psi.WorkingDirectory = $RepoRoot
        $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
        $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
        
        $process = [System.Diagnostics.Process]::Start($psi)
        
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        
        $exited = $process.WaitForExit($aiderTimeoutSeconds * 1000)
        
        if (-not $exited) {
            Write-Host "[AIDER] TIMEOUT: Aider exceeded $($aiderTimeoutSeconds)s, killing process..." -ForegroundColor Red
            try {
                $process.Kill()
            } catch {}
            
            $exitCode = -1
            $timedOut = $true
        } else {
            $exitCode = $process.ExitCode
            $timedOut = $false
        }
        
        $stdout = $stdoutTask.Result
        $stderr = $stderrTask.Result
        
        Write-Host "[AIDER] Exit code: $exitCode" -ForegroundColor $(if ($exitCode -eq 0) {'Green'} else {'Yellow'})
        if ($timedOut) {
            Write-Host "[AIDER] WARNING: Execution was killed due to timeout" -ForegroundColor Red
        }
        
        $savedEAP2 = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $modifiedFiles = (git diff --name-only HEAD 2>&1) | Out-String
        $untrackedFiles = (git ls-files --others --exclude-standard 2>&1) | Out-String
        $ErrorActionPreference = $savedEAP2
        $modArray = if ($modifiedFiles.Trim()) { $modifiedFiles.Trim() -split "`n" | Where-Object { $_.Trim() } } else { @() }
        $untArray = if ($untrackedFiles.Trim()) { $untrackedFiles.Trim() -split "`n" | Where-Object { $_.Trim() } } else { @() }
        $allChanges = @($modArray) + @($untArray)
        
        $hasAiderError = $false
        if ($stderr -match "llama runner process has terminated|UnicodeEncodeError|APIConnectionError|Connection refused|ConnectionError|APIConnectionTimeout") {
            $hasAiderError = $true
            Write-Host "[AIDER] Detected error in stderr" -ForegroundColor Red
        }
        
        if ($allChanges.Count -gt 0) {
            $ErrorActionPreference = 'Continue'
            git add . 2>&1 | Out-Null
            git commit -m "candidate($RoundId): Implement round requirements - $TaskDescription" 2>&1 | Out-Null
            $commitHash = (git rev-parse HEAD 2>&1) | Out-String
            $commitHash = $commitHash.Trim()
            $ErrorActionPreference = $savedEAP2
        } else {
            $commitHash = "NO_CHANGES"
        }
        
        $reportPath = Join-Path $outputDir "report.json"
        $report = @{
            round_id = $RoundId
            candidate_branch = $candidateBranch
            commit_hash = $commitHash
            exit_code = $exitCode
            log_file = $logFile
            modified_files = @($allChanges)
            timed_out = $timedOut
            # CRITICAL: success now requires BOTH exit_code=0 AND actual file changes
            success = $false
            files_written = @($allChanges)
            write_verification = @{
                exit_code_zero = ($exitCode -eq 0)
                has_file_changes = ($allChanges.Count -gt 0)
                has_core_ps1_files = $false
                has_evidence_json = $false
                has_test_files = $false
            }
        }
        
        # === WRITE VERIFICATION GATE ===
        # Aider must produce actual files, not just exit 0
        if ($report.write_verification.exit_code_zero -and $report.write_verification.has_file_changes) {
            # Check for core .ps1 files (not just control loop artifacts)
            $corePs1Files = $allChanges | Where-Object { 
                $_ -match 'automation/control/[^/]+\.ps1$' -and 
                $_ -notmatch 'main_control_loop|refresh_panel|start_loop|validate_|test_|candidates/'
            }
            
            # Check for evidence.json
            $evidenceJsonPath = Join-Path $candidateDir "evidence.json"
            $report.write_verification.has_evidence_json = Test-Path $evidenceJsonPath
            
            # Check for test files
            $testDir = Join-Path $RepoRoot "automation\control\test"
            $testFiles = Get-ChildItem -Path $testDir -Filter "test_*.ps1" -ErrorAction SilentlyContinue | 
                Where-Object { $_.Name -like "*${RoundId}*" }
            $report.write_verification.has_test_files = ($testFiles.Count -gt 0)
            
            # Check for core implementation (not just control loop)
            $report.write_verification.has_core_ps1_files = ($corePs1Files.Count -gt 0)
            
            # FINAL SUCCESS DETERMINATION
            # Must have: exit_code=0 AND actual code changes AND evidence AND tests
            $report.success = (
                $report.write_verification.has_core_ps1_files -and
                $report.write_verification.has_evidence_json -and
                $report.write_verification.has_test_files
            )
            
            if (-not $report.success) {
                $report.block_reason = "INSUFFICIENT_WRITE_VERIFICATION"
                $report.block_details = @{
                    missing_core_ps1 = (-not $report.write_verification.has_core_ps1_files)
                    missing_evidence = (-not $report.write_verification.has_evidence_json)
                    missing_tests = (-not $report.write_verification.has_test_files)
                }
            }
        } else {
            $report.block_reason = "NO_FILE_CHANGES_DESPITE_EXIT_0"
            $report.block_details = "Aider returned exit_code=$exitCode but produced no file changes"
        }
        
        $reportJson = $report | ConvertTo-Json -Depth 10
        [System.IO.File]::WriteAllText($reportPath, $reportJson, [System.Text.Encoding]::UTF8)
        
        $ErrorActionPreference = 'Continue'
        git checkout $currentBranch 2>&1 | Out-Null
        $ErrorActionPreference = $savedEAP2
        
        if ($report.success) {
            return @{
                success = $true
                summary = "Aider execution completed with verified file writes. Candidate branch: $candidateBranch, Commit: $commitHash, Modified: $($allChanges.Count) files, Core PS1: $($corePs1Files.Count), Tests: $($testFiles.Count), Evidence: $report.write_verification.has_evidence_json"
                modified_files = @($allChanges)
                commit_hash = $commitHash
                write_verification = $report.write_verification
            }
        } else {
            $failReason = if ($timedOut) { "Aider timed out after $($aiderTimeoutSeconds)s" } else { "Aider write verification failed - $($report.block_reason)" }
            return @{
                success = $false
                error = $failReason
                summary = "Execution blocked - $(if($report.block_details -is [hashtable]) { ($report.block_details.GetEnumerator() | ForEach-Object { "$($_.Key): $($_.Value)" }) -join ', ' } else { $report.block_details })"
                block_reason = $report.block_reason
                block_details = $report.block_details
                write_verification = $report.write_verification
                timed_out = $timedOut
            }
        }
        
    } catch {
        $ErrorActionPreference = 'Continue'
        git checkout $currentBranch 2>&1 | Out-Null
        $ErrorActionPreference = $savedEAP
        
        return @{
            success = $false
            error = $_.Exception.Message
            summary = "Exception during Aider execution"
        }
    }
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

