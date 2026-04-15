$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

$controlDir = Join-Path $repoRoot "automation\control"
$statePath = Join-Path $controlDir "state.runtime.json"
$returnPath = Join-Path $controlDir "latest_return_to_chatgpt.runtime.txt"

if (!(Test-Path $statePath)) {
    throw "找不到 state.runtime.json"
}

$state = Get-Content $statePath -Raw | ConvertFrom-Json

$status = switch ($state.mode) {
    "running" { "candidate_running" }
    "paused_for_acceptance" { "candidate_waiting_review" }
    "stopped_error" { "escalate" }
    default { "candidate_unknown" }
}

$escalationRequired = if ($state.escalation_required) { "yes" } else { "no" }
$escalationReason = if ($state.escalation_required) { "state indicates stopped_error or escalation" } else { "none" }

$nextAction = switch ($state.mode) {
    "running" { "wait for next cycle or request Drain After Current" }
    "paused_for_acceptance" { "review latest candidate and send this block to ChatGPT" }
    "stopped_error" { "inspect error state and send this block to ChatGPT" }
    default { "inspect current state" }
}

$candidateId = if ($null -eq $state.latest_candidate_id) { "none" } else { [string]$state.latest_candidate_id }

$returnBlock = @"
=== RETURN_TO_CHATGPT ===
round_id: $($state.round_id)
branch: $($state.branch)
status: $status
candidate_id: $candidateId
summary:
- mode: $($state.mode)
- pause_requested: $($state.pause_requested)
- acceptance_mode: $($state.acceptance_mode)
- escalation_required: $($state.escalation_required)
changed_files:
- none
checks:
- validate_round: not_run
- forbidden_paths: not_run
- required_evidence: not_run
- commit_message: not_run
forbidden_path_touched: no
evidence_updated:
- automation/control/state.runtime.json
- automation/control/latest_return_to_chatgpt.runtime.txt
escalation_required: $escalationRequired
escalation_reason: $escalationReason
next_recommended_action: $nextAction
=== END_RETURN_TO_CHATGPT ===
"@

Set-Content -Path $returnPath -Value $returnBlock -Encoding UTF8
Write-Host "RETURN_TO_CHATGPT synced." -ForegroundColor Green
Write-Host $returnPath

