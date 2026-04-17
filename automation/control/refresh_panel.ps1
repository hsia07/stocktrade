$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

$controlDir = Join-Path $repoRoot "automation\control"
$statePath = Join-Path $controlDir "state.runtime.json"
$returnPath = Join-Path $controlDir "latest_return_to_chatgpt.runtime.txt"
$outputPath = Join-Path $controlDir "panel_runtime.html"

if (Test-Path $statePath) {
    $stateRaw = Get-Content $statePath -Raw
    $state = $stateRaw | ConvertFrom-Json
} else {
    throw "找不到 state.runtime.json"
}

if (Test-Path $returnPath) {
    $returnText = Get-Content $returnPath -Raw
} else {
    $returnText = "latest_return_to_chatgpt.runtime.txt not found"
}

function Escape-Html([string]$text) {
    if ($null -eq $text) { return "" }
    return [System.Net.WebUtility]::HtmlEncode($text)
}

# Extract state values - support both old and new schema
$mode = [string]($state.mode)
$runState = [string]($state.run_state)
$roundId = [string]($state.round_id)
$currentRound = [string]($state.current_round)
$currentPhase = [string]($state.current_phase)
$branch = [string]($state.branch)
$currentCycle = if ($null -eq $state.current_cycle_id) { "none" } else { [string]$state.current_cycle_id }
$currentCandidate = if ($null -eq $state.current_candidate_id) { "none" } else { [string]$state.current_candidate_id }
$latestCandidate = if ($null -eq $state.latest_candidate_id) { "none" } else { [string]$state.latest_candidate_id }
$pauseRequested = [string]$state.pause_requested
$acceptanceMode = [string]$state.acceptance_mode
$escalationRequired = [string]$state.escalation_required
$lastUpdate = if ($null -eq $state.last_update) { "none" } else { [string]$state.last_update }

# New schema fields
$phaseCompletion = if ($null -eq $state.phase_completion_state) { "unknown" } else { [string]$state.phase_completion_state }
$readyForSignoff = if ($null -eq $state.ready_for_signoff) { "False" } else { [string]$state.ready_for_signoff }
$signoffRequired = if ($null -eq $state.signoff_required) { "False" } else { [string]$state.signoff_required }
$signoffGranted = if ($null -eq $state.signoff_granted) { "False" } else { [string]$state.signoff_granted }
$mergePushAllowed = if ($null -eq $state.merge_push_allowed) { "False" } else { [string]$state.merge_push_allowed }
$stopReason = if ($null -eq $state.stop_reason) { "none" } else { [string]$state.stop_reason }
$lastAction = if ($null -eq $state.last_action) { "none" } else { [string]$state.last_action }

# Determine display mode - prefer run_state if available, fall back to mode
$displayMode = if ($runState -and $runState -ne "") { $runState } else { $mode }

# 判斷是否可以核准 Candidate
$canApprove = "no"
$rejectReason = ""
if ($mode -ne "paused_for_acceptance" -and $displayMode -ne "paused_for_acceptance") {
    $rejectReason = "mode 不是 paused_for_acceptance (目前: $displayMode)"
} elseif ($latestCandidate -eq "none" -or [string]::IsNullOrEmpty($latestCandidate)) {
    $rejectReason = "latest_candidate_id 缺失"
} elseif ($escalationRequired -eq "True") {
    $rejectReason = "escalation_required 為 true"
}
if ($rejectReason -eq "") {
    $canApprove = "yes"
}

$canApproveClass = if ($canApprove -eq "yes") { "can" } else { "cannot" }

$modeLabel = switch ($displayMode) {
    "running" { "執行中" }
    "paused_for_acceptance" { "等待人工驗收" }
    "stopped" { "已停止" }
    "stopped_error" { "異常停止" }
    "phase_completed_stopped" { "Phase 完成" }
    default { $displayMode }
}

$modeClass = switch ($displayMode) {
    "running" { "running" }
    "paused_for_acceptance" { "paused" }
    "stopped" { "paused" }
    "stopped_error" { "error" }
    "phase_completed_stopped" { "paused" }
    default { "neutral" }
}

# Build state display block
$stateBlock = @"
schema_version: $($state.schema_version)
mode: $mode
run_state: $runState
current_phase: $currentPhase
current_round: $currentRound
round_id: $roundId
branch: $branch
phase_completion_state: $phaseCompletion
stop_reason: $stopReason
last_action: $lastAction
ready_for_signoff: $readyForSignoff
signoff_required: $signoffRequired
signoff_granted: $signoffGranted
merge_push_allowed: $mergePushAllowed
last_update: $lastUpdate
updated_at: $($state.updated_at)
"@

$stateBlockEscaped = Escape-Html $stateBlock
$returnEscaped = Escape-Html $returnText
$modeEscaped = Escape-Html $modeLabel
$roundEscaped = Escape-Html $roundId
$branchEscaped = Escape-Html $branch
$currentCycleEscaped = Escape-Html $currentCycle
$latestCandidateEscaped = Escape-Html $latestCandidate
$currentCandidateEscaped = Escape-Html $currentCandidate
$pauseRequestedEscaped = Escape-Html $pauseRequested
$acceptanceModeEscaped = Escape-Html $acceptanceMode
$escalationRequiredEscaped = Escape-Html $escalationRequired
$lastUpdateEscaped = Escape-Html $lastUpdate
$phaseCompletionEscaped = Escape-Html $phaseCompletion

# Phase definition and round topics extraction
$phaseStartRound = if ($state.phase_start_round) { $state.phase_start_round } else { "R-001" }
$phaseEndRound = if ($state.phase_end_round) { $state.phase_end_round } else { "R-015" }
$roundTopics = if ($state.round_topics) { $state.round_topics } else { @{ } }

# Generate selectable and non-selectable rounds HTML
$selectableRoundsHtml = ""
$nonSelectableRoundsHtml = ""

# Hard-coded round topics per formal law
$roundTopicMap = @{
    "R-007" = "異常靜默保護"
    "R-008" = "狀態機與模式切換治理"
    "R-009" = "指令與任務優先級"
    "R-006" = "控制面板完整功能落地"
    "R-005" = "歷史歸檔"
    "R-004" = "歷史歸檔"
    "R-003" = "歷史歸檔"
    "R-002" = "歷史歸檔"
    "R-001" = "歷史歸檔"
}

# Check for selectable rounds (ready_for_signoff_rounds)
if ($state.ready_for_signoff_rounds -and $state.ready_for_signoff_rounds.Count -gt 0) {
    foreach ($round in $state.ready_for_signoff_rounds) {
        $topic = if ($roundTopicMap[$round]) { $roundTopicMap[$round] } else { "未知主題" }
        $selectableRoundsHtml += @"
<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
  <input type="checkbox" id="merge_$round" style="cursor: pointer;">
  <div style="display: flex; flex-direction: column;">
    <span style="color: #86efac;">$round｜$topic</span>
    <span style="font-size: 0.9em; color: #86efac;">可簽字</span>
  </div>
</div>
"@
    }
} else {
    $selectableRoundsHtml = '<div style="color: #a9b6d3; font-style: italic; padding: 8px;">目前無可 merge 輪次</div>'
}

# Non-selectable rounds from state
if ($state.non_selectable_rounds_with_reasons) {
    $nonSelectableRoundsWithReasons = $state.non_selectable_rounds_with_reasons | ConvertTo-Json | ConvertFrom-Json
    foreach ($roundEntry in $nonSelectableRoundsWithReasons.PSObject.Properties) {
        $round = $roundEntry.Name
        $info = $roundEntry.Value
        $topic = if ($roundTopicMap[$round]) { $roundTopicMap[$round] } else { $info.topic }
        $reason = $info.reason
        $nonSelectableRoundsHtml += @"
<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px; opacity: 0.6;">
  <input type="checkbox" disabled style="cursor: not-allowed;">
  <div style="display: flex; flex-direction: column;">
    <span>$round｜$topic</span>
    <span style="font-size: 0.9em; opacity: 0.8;">尚不可 merge：$reason</span>
  </div>
</div>
"@
    }
} else {
    # Default non-selectable rounds
    $nonSelectableRoundsHtml = @"
<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px; opacity: 0.6;">
  <input type="checkbox" disabled style="cursor: not-allowed;">
  <span>R-001｜歷史歸檔｜尚不可 merge：archived_historical_round</span>
</div>
<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px; opacity: 0.6;">
  <input type="checkbox" disabled style="cursor: not-allowed;">
  <span>R-002｜歷史歸檔｜尚不可 merge：archived_historical_round</span>
</div>
"@
}

$html = @"
<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <title>Stocktrade Control Panel Runtime</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root {
      --bg: #0b1020;
      --card: rgba(255,255,255,0.08);
      --card-border: rgba(255,255,255,0.10);
      --text: #e5ecff;
      --muted: #a9b6d3;
      --shadow: 0 18px 40px rgba(0,0,0,0.28);
      --radius: 18px;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(96,165,250,0.18), transparent 30%),
        radial-gradient(circle at top right, rgba(139,92,246,0.16), transparent 28%),
        linear-gradient(180deg, #0b1020 0%, #0f172a 100%);
      min-height: 100vh;
    }

    .wrap {
      max-width: 1180px;
      margin: 0 auto;
      padding: 28px 20px 40px;
    }

    .hero {
      display: grid;
      grid-template-columns: 1.25fr 0.75fr;
      gap: 18px;
      margin-bottom: 18px;
    }

    .card {
      background: var(--card);
      border: 1px solid var(--card-border);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      padding: 20px;
    }

    .title {
      font-size: 30px;
      font-weight: 800;
      margin: 0 0 10px;
    }

    .subtitle {
      color: var(--muted);
      margin: 0;
      line-height: 1.6;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 14px;
      font-weight: 700;
      margin-bottom: 14px;
      border: 1px solid rgba(255,255,255,0.10);
    }

    .badge::before {
      content: "";
      width: 9px;
      height: 9px;
      border-radius: 999px;
      background: currentColor;
      box-shadow: 0 0 10px currentColor;
    }

    .badge.running { color: #86efac; background: rgba(34,197,94,0.12); }
    .badge.paused { color: #c4b5fd; background: rgba(139,92,246,0.14); }
    .badge.error { color: #fca5a5; background: rgba(239,68,68,0.14); }
    .badge.neutral { color: #93c5fd; background: rgba(96,165,250,0.14); }

    .mini-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }

    .metric {
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 14px;
      padding: 14px;
    }

    .metric .label {
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 6px;
    }

    .metric .value {
      font-size: 16px;
      font-weight: 700;
      word-break: break-word;
    }

    .section-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
      margin-bottom: 18px;
    }

    h2 {
      font-size: 18px;
      margin: 0 0 14px;
    }

    .mono {
      white-space: pre-wrap;
      font-family: Consolas, "Courier New", monospace;
      background: rgba(3,7,18,0.72);
      color: #dbe7ff;
      border: 1px solid rgba(255,255,255,0.08);
      padding: 14px;
      border-radius: 14px;
      line-height: 1.55;
      overflow-x: auto;
    }

    .action-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }

    .btn {
      border: 0;
      border-radius: 12px;
      padding: 11px 16px;
      font-weight: 700;
      cursor: pointer;
      font-size: 14px;
      color: white;
      transition: transform .12s ease, opacity .12s ease, background .18s ease;
    }

    .btn:hover { transform: translateY(-1px); }
    .btn:active { transform: translateY(0); }
    .btn.ok { background: linear-gradient(135deg, #16a34a, #22c55e); }
    .btn.warn { background: linear-gradient(135deg, #d97706, #f59e0b); }
    .btn.danger { background: linear-gradient(135deg, #dc2626, #ef4444); }
    .btn.primary { background: linear-gradient(135deg, #2563eb, #60a5fa); }
    .btn.processing { background: linear-gradient(135deg, #0ea5e9, #38bdf8); }
    .btn.done { background: linear-gradient(135deg, #15803d, #22c55e); }

    .helper {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
      margin-top: 10px;
    }

    .copy-status {
      margin-top: 12px;
      font-size: 14px;
      font-weight: 700;
      color: #93c5fd;
      min-height: 20px;
    }

    .danger-zone {
      margin-top: 22px;
      border: 1px solid rgba(239,68,68,0.35);
      background: rgba(239,68,68,0.08);
      border-radius: 16px;
      padding: 16px;
    }

    .danger-title {
      color: #fca5a5;
      font-weight: 800;
      margin-bottom: 8px;
    }

    .danger-text {
      color: #fecaca;
      font-size: 13px;
      line-height: 1.6;
      margin-bottom: 12px;
    }

    .inline-status {
      margin-top: 12px;
      font-size: 14px;
      font-weight: 700;
      color: #93c5fd;
      min-height: 20px;
    }

    @media (max-width: 900px) {
      .hero, .section-grid { grid-template-columns: 1fr; }
      .mini-grid { grid-template-columns: 1fr; }
      .title { font-size: 24px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div class="card">
        <div class="badge $modeClass">$modeEscaped</div>
        <h1 class="title">Stocktrade Control Panel</h1>
        <p class="subtitle">
          這是目前輪次的控制面板。你回來後可以先看這裡的狀態、最新 candidate 與要貼給 ChatGPT 的區塊。
        </p>
      </div>

      <div class="card">
        <h2>快速概覽</h2>
        <div class="mini-grid">
          <div class="metric">
            <div class="label">目前輪次</div>
            <div class="value" id="overviewRound">$roundEscaped</div>
          </div>
          <div class="metric">
            <div class="label">目前分支</div>
            <div class="value" id="overviewBranch">$branchEscaped</div>
          </div>
          <div class="metric">
            <div class="label">最新 Candidate</div>
            <div class="value" id="overviewCandidate">$latestCandidateEscaped</div>
          </div>
          <div class="metric">
            <div class="label">最後更新</div>
            <div class="value" id="overviewLastUpdate">$lastUpdateEscaped</div>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>常用操作</h2>
      <div class="action-bar">
        <button id="resumeBtn" class="btn ok" type="button" onclick="startLoop()">Start / Resume</button>
        <button id="drainBtn" class="btn warn" type="button" onclick="drainAfterCurrent()">Drain After Current</button>
        <button class="btn primary" type="button" onclick="copyReturnBlock()">一鍵複製回傳給 GPT</button>
      </div>
      <div class="helper">
        Start / Resume 會啟動主控制循環。Drain 會在當前輪次完成後暫停。Stop Now 會立即中止。
      </div>
      <div id="copyStatus" class="copy-status"></div>
      <div id="operationStatus" class="inline-status"></div>

      <div class="danger-zone">
        <div class="danger-title">危險操作區</div>
        <div class="danger-text">
          Stop Now 會立即中止流程，可能跳過正常收尾。只有在異常狀況下才使用。
        </div>
        <button id="stopBtn" class="btn danger" type="button" onclick="confirmStopNow()">Stop Now</button>
      </div>
    </div>

    <div class="card" id="signoffCard" style="display: none;">
      <h2>Merge Gate / Signoff</h2>
      <div class="mini-grid" style="margin-bottom: 14px;">
        <div class="metric">
          <div class="label">Phase 狀態</div>
          <div class="value" id="phaseStatus">unknown</div>
        </div>
        <div class="metric">
          <div class="label">Signoff 狀態</div>
          <div class="value" id="signoffStatus">not_required</div>
        </div>
        <div class="metric">
          <div class="label">Merge 權限</div>
          <div class="value" id="mergeStatus">blocked</div>
        </div>
        <div class="metric">
          <div class="label">Ready 輪次</div>
          <div class="value" id="readyRounds">none</div>
        </div>
      </div>
      <div class="action-bar">
        <button id="readySignoffBtn" class="btn primary" type="button" onclick="readyForSignoff()">標記 Ready for Signoff</button>
        <button id="grantSignoffBtn" class="btn ok" type="button" onclick="grantSignoff()" disabled>Grant Signoff</button>
      </div>
      <div id="signoffMessage" class="helper"></div>
    </div>

    <div class="card" id="mergeSelectionCard">
      <h2>可批次 Merge 輪次選擇區</h2>
      
      <div style="margin-bottom: 20px;">
        <h3 style="color: #86efac; font-size: 16px; margin-bottom: 12px;">✓ 可選區（已達 ready_for_signoff）</h3>
        <div id="selectableRoundsSection" style="background: rgba(34,197,94,0.08); border: 1px solid rgba(34,197,94,0.3); border-radius: 12px; padding: 16px;">
          $selectableRoundsHtml
        </div>
      </div>
      
      <div>
        <h3 style="color: #fca5a5; font-size: 16px; margin-bottom: 12px;">✗ 不可選區（尚不符合條件）</h3>
        <div id="nonSelectableRoundsSection" style="background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.3); border-radius: 12px; padding: 16px;">
          $nonSelectableRoundsHtml
        </div>
      </div>
      
      <div style="margin-top: 16px; padding: 12px; background: rgba(96,165,250,0.08); border-radius: 8px; font-size: 13px; color: #a9b6d3;">
        <strong>選擇規則：</strong>只有標記為 ready_for_signoff 的輪次可選擇並批次 merge。尚不可 merge 的輪次已 disabled 並顯示原因。
      </div>
    </div>

    <div class="card">
      <h2>核准 Candidate</h2>
      <div class="mini-grid" style="margin-bottom: 14px;">
        <div class="metric">
          <div class="label">可核准</div>
          <div class="value" id="canApproveValue">$canApprove</div>
        </div>
        <div class="metric">
          <div class="label">latest_candidate_id</div>
          <div class="value">$latestCandidateEscaped</div>
        </div>
        <div class="metric">
          <div class="label">current_candidate_id</div>
          <div class="value">$currentCandidateEscaped</div>
        </div>
        <div class="metric">
          <div class="label">run_state</div>
          <div class="value">$($runState)</div>
        </div>
      </div>
      <div id="approveReason" class="helper" style="color: #fca5a5;">
        $(if ($canApprove -eq "no") { "不能核准原因: $rejectReason" } else { "" })
      </div>
      <div class="action-bar" style="margin-top: 14px;">
        <button id="approveBtn" class="btn ok" type="button" onclick="confirmApproveCandidate()" $(if ($canApprove -eq "no") { 'disabled="disabled"' } )>核准 Candidate</button>
      </div>
      <div id="approveStatus" class="inline-status"></div>
    </div>

    <div class="section-grid">
      <div class="card">
        <h2>最新狀態</h2>
        <div class="mini-grid" style="margin-bottom: 14px;">
          <div class="metric">
            <div class="label">round</div>
            <div class="value" id="latestStatusRound">$currentRound</div>
          </div>
          <div class="metric">
            <div class="label">mode</div>
            <div class="value" id="latestStatusMode">$displayMode</div>
          </div>
          <div class="metric">
            <div class="label">aider</div>
            <div class="value" id="latestStatusAider">idle</div>
          </div>
          <div class="metric">
            <div class="label">candidate</div>
            <div class="value" id="latestStatusCandidate">$latestCandidateEscaped</div>
          </div>
          <div class="metric">
            <div class="label">updated</div>
            <div class="value" id="latestStatusUpdated">$lastUpdateEscaped</div>
          </div>
        </div>
        <div class="mono" id="latestStatusMono">$stateBlockEscaped</div>
      </div>

      <div class="card">
        <h2>最新 Candidate / 建議動作</h2>
        <div class="mono" id="latestCandidateMono">candidate: $latestCandidateEscaped
cycle: $currentCycle
stop_reason: $stopReason
last_action: $lastAction</div>
        <div class="helper">
          建議你回來後先確認目前 mode，再決定要不要排空後暫停、進入驗收，或恢復執行。
        </div>
      </div>
    </div>

    <div class="card">
      <h2>RETURN_TO_CHATGPT</h2>
      <div id="returnBox" class="mono">$returnEscaped</div>
      <div class="helper">
        等系統進入 <strong>paused_for_acceptance</strong> 後，你就可以直接按上面的藍色按鈕，把這整段貼回 ChatGPT。
      </div>
    </div>
  </div>

  <script>
    const API_BASE = 'http://127.0.0.1:8766';
    let statusTimer = null;

    async function copyReturnBlock() {
      const text = document.getElementById('returnBox').innerText;
      const status = document.getElementById('copyStatus');

      try {
        await navigator.clipboard.writeText(text);
        status.textContent = '已複製 RETURN_TO_CHATGPT 區塊';
      } catch (e) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        status.textContent = '已複製 RETURN_TO_CHATGPT 區塊';
      }
    }

    function setOperationStatus(message, type = 'info') {
      const status = document.getElementById('operationStatus');
      status.textContent = message;
      status.style.color = type === 'error' ? '#fca5a5' : type === 'success' ? '#86efac' : '#93c5fd';
      
      if (statusTimer) {
        clearTimeout(statusTimer);
      }
      statusTimer = setTimeout(() => {
        status.textContent = '';
      }, 5000);
    }

    async function startLoop() {
      const btn = document.getElementById('resumeBtn');
      btn.className = 'btn processing';
      btn.textContent = '啟動中...';
      btn.disabled = true;

      try {
        const response = await fetch(`${API_BASE}/start-loop`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'}
        });
        const data = await response.json();

        if (data.status === 'started' || data.status === 'success') {
          btn.className = 'btn done';
          btn.textContent = '執行中';
          setOperationStatus('主控制循環已啟動 (背景執行中)，輪詢狀態更新...', 'success');
          updateStateDisplay();
          pollLoopProgress();
        } else if (data.status === 'blocked') {
          btn.className = 'btn warn';
          btn.textContent = 'Start / Resume';
          btn.disabled = false;
          setOperationStatus('無法啟動: ' + data.reason, 'error');
        } else {
          btn.className = 'btn danger';
          btn.textContent = '啟動失敗';
          btn.disabled = false;
          setOperationStatus('啟動失敗: ' + (data.reason || 'Unknown error'), 'error');
        }
      } catch (err) {
        btn.className = 'btn danger';
        btn.textContent = '連線錯誤';
        btn.disabled = false;
        setOperationStatus('無法連接到控制橋接器，請確認 bridge 是否在執行', 'error');
      }
    }

    let loopPollTimer = null;
    function pollLoopProgress() {
      if (loopPollTimer) clearInterval(loopPollTimer);
      loopPollTimer = setInterval(async () => {
        try {
          const resp = await fetch(`${API_BASE}/loop-status`);
          const ls = await resp.json();
          const btn = document.getElementById('resumeBtn');

          if (ls.loop_active) {
            btn.textContent = '執行中: ' + (ls.current_round || '...');
            updateStateDisplay();
          } else {
            clearInterval(loopPollTimer);
            loopPollTimer = null;
            btn.className = 'btn ok';
            btn.textContent = 'Start / Resume';
            btn.disabled = false;
            updateStateDisplay();

            const lastResp = await fetch(`${API_BASE}/last-action`);
            const lastData = await lastResp.json();
            if (lastData.status === 'success') {
              setOperationStatus('循環完成', 'success');
            } else if (lastData.status === 'failed') {
              setOperationStatus('循環失敗: ' + (lastData.reason || ''), 'error');
            }
          }
        } catch (e) {}
      }, 3000);
    }

    async function drainAfterCurrent() {
      const btn = document.getElementById('drainBtn');
      btn.className = 'btn processing';
      btn.textContent = '處理中...';
      btn.disabled = true;

      try {
        const response = await fetch(`${API_BASE}/drain`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'}
        });
        const data = await response.json();

        if (data.status === 'success') {
          btn.className = 'btn done';
          btn.textContent = 'Drain 已請求';
          setOperationStatus('Drain After Current 已請求，當前輪次完成後會暫停', 'success');
        } else {
          btn.className = 'btn warn';
          btn.textContent = 'Drain After Current';
          btn.disabled = false;
          setOperationStatus('Drain 請求失敗: ' + (data.reason || 'Unknown error'), 'error');
        }
      } catch (err) {
        btn.className = 'btn warn';
        btn.textContent = 'Drain After Current';
        btn.disabled = false;
        setOperationStatus('無法連接到控制橋接器，請確認 bridge 是否在執行', 'error');
      }
    }

    async function confirmStopNow() {
      const ok = confirm('這是危險操作。Stop Now 可能跳過正常收尾。你確定要執行嗎？');
      if (!ok) {
        setOperationStatus('已取消 Stop Now');
        return;
      }

      const btn = document.getElementById('stopBtn');
      btn.className = 'btn processing';
      btn.textContent = '停止中...';
      btn.disabled = true;

      try {
        const response = await fetch(`${API_BASE}/stop-now`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'}
        });
        const data = await response.json();

        if (data.status === 'success') {
          btn.className = 'btn done';
          btn.textContent = '已停止';
          setOperationStatus('Stop Now 已執行，流程已中止', 'success');
          document.getElementById('resumeBtn').textContent = 'Start / Resume';
          document.getElementById('resumeBtn').className = 'btn ok';
          document.getElementById('resumeBtn').disabled = false;
        } else {
          btn.className = 'btn danger';
          btn.textContent = 'Stop Now';
          btn.disabled = false;
          setOperationStatus('Stop 失敗: ' + (data.reason || 'Unknown error'), 'error');
        }
      } catch (err) {
        btn.className = 'btn danger';
        btn.textContent = 'Stop Now';
        btn.disabled = false;
        setOperationStatus('無法連接到控制橋接器，請確認 bridge 是否在執行', 'error');
      }
    }

    async function readyForSignoff() {
      const btn = document.getElementById('readySignoffBtn');
      btn.className = 'btn processing';
      btn.textContent = '處理中...';
      btn.disabled = true;

      try {
        const response = await fetch(`${API_BASE}/ready-for-signoff`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'}
        });
        const data = await response.json();

        if (data.status === 'success') {
          btn.className = 'btn done';
          btn.textContent = '已標記 Ready';
          document.getElementById('grantSignoffBtn').disabled = false;
          setOperationStatus('Phase 已標記為 Ready for Signoff', 'success');
          updateStateDisplay();
        } else {
          btn.className = 'btn primary';
          btn.textContent = '標記 Ready for Signoff';
          btn.disabled = false;
          setOperationStatus('無法標記: ' + (data.reason || 'Unknown error'), 'error');
        }
      } catch (err) {
        btn.className = 'btn primary';
        btn.textContent = '標記 Ready for Signoff';
        btn.disabled = false;
        setOperationStatus('無法連接到控制橋接器，請確認 bridge 是否在執行', 'error');
      }
    }

    async function grantSignoff() {
      const ok = confirm('您即將授權 Signoff，允許後續的 merge/push 操作。\\n\\n請確認您已經：\\n1. 審查所有變更\\n2. 確認測試通過\\n3. 同意繼續進行\\n\\n確定要授權嗎？');
      if (!ok) {
        setOperationStatus('已取消 Signoff 授權');
        return;
      }

      const btn = document.getElementById('grantSignoffBtn');
      btn.className = 'btn processing';
      btn.textContent = '授權中...';
      btn.disabled = true;

      try {
        const response = await fetch(`${API_BASE}/grant-signoff`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'}
        });
        const data = await response.json();

        if (data.status === 'success') {
          btn.className = 'btn done';
          btn.textContent = 'Signoff 已授權';
          setOperationStatus('Signoff 已授權，現在可以進行 merge/push 操作', 'success');
          updateStateDisplay();
        } else {
          btn.className = 'btn ok';
          btn.textContent = 'Grant Signoff';
          btn.disabled = false;
          setOperationStatus('授權失敗: ' + (data.reason || 'Unknown error'), 'error');
        }
      } catch (err) {
        btn.className = 'btn ok';
        btn.textContent = 'Grant Signoff';
        btn.disabled = false;
        setOperationStatus('無法連接到控制橋接器，請確認 bridge 是否在執行', 'error');
      }
    }

    async function updateStateDisplay() {
      try {
        const response = await fetch(`${API_BASE}/state`);
        const state = await response.json();
        
        // Update quick overview section
        const overviewRound = document.getElementById('overviewRound');
        if (overviewRound) overviewRound.textContent = state.current_round || '—';
        const overviewBranch = document.getElementById('overviewBranch');
        if (overviewBranch) overviewBranch.textContent = state.branch || '—';
        const overviewCandidate = document.getElementById('overviewCandidate');
        if (overviewCandidate) overviewCandidate.textContent = state.latest_candidate_id || state.current_candidate_id || 'none';
        const overviewLastUpdate = document.getElementById('overviewLastUpdate');
        if (overviewLastUpdate) overviewLastUpdate.textContent = state.updated_at || state.last_update || '—';
        
        // Update latest status card
        const latestStatusRound = document.getElementById('latestStatusRound');
        if (latestStatusRound) latestStatusRound.textContent = state.current_round || '—';
        const latestStatusMode = document.getElementById('latestStatusMode');
        if (latestStatusMode) latestStatusMode.textContent = state.mode || state.run_state || '—';
        const latestStatusAider = document.getElementById('latestStatusAider');
        if (latestStatusAider) latestStatusAider.textContent = state.aider_status || 'idle';
        const latestStatusCandidate = document.getElementById('latestStatusCandidate');
        if (latestStatusCandidate) latestStatusCandidate.textContent = state.latest_candidate_id || 'none';
        const latestStatusUpdated = document.getElementById('latestStatusUpdated');
        if (latestStatusUpdated) latestStatusUpdated.textContent = state.updated_at || '—';
        
        // Update mono blocks
        const latestStatusMono = document.getElementById('latestStatusMono');
        if (latestStatusMono) latestStatusMono.textContent = 
          `round: ${state.current_round||'—'} | mode: ${state.mode||state.run_state||'—'} | aider: ${state.aider_status||'—'} | candidate: ${state.latest_candidate_id||'none'}`;
        const latestCandidateMono = document.getElementById('latestCandidateMono');
        if (latestCandidateMono) latestCandidateMono.textContent = 
          `candidate: ${state.latest_candidate_id||'none'} | cycle: ${state.current_cycle_id||'none'} | aide: ${state.aider_status||'—'} | ready: ${state.ready_for_signoff||false}`;
        
        // Update RETURN_TO_CHATGPT block dynamically
        const completed = state.completed_rounds || [];
        const blocked = state.blocked_rounds || [];
        const ready = state.ready_for_signoff_rounds || [];
        const returnBlock = [
          '=== RETURN_TO_CHATGPT ===',
          `round_id: ${state.current_round || '—'}`,
          `branch: ${state.branch || '—'}`,
          `status: ${state.run_state === 'running' ? 'candidate_running' : state.run_state || 'stopped'}`,
          `candidate_id: ${state.latest_candidate_id || state.current_candidate_id || 'none'}`,
          'summary:',
          `- mode: ${state.mode || state.run_state || '—'}`,
          `- aide: ${state.aider_status || 'idle'}`,
          `- run_state: ${state.run_state || '—'}`,
          `- current_phase: ${state.current_phase || '—'}`,
          `- phase_completion_state: ${state.phase_completion_state || '—'}`,
          `- completed_rounds: ${completed.length ? completed.join(', ') : 'none'}`,
          `- blocked_rounds: ${blocked.length ? blocked.join(', ') : 'none'}`,
          `- ready_for_signoff: ${ready.length ? ready.join(', ') : 'none'}`,
          `- latest_candidate_id: ${state.latest_candidate_id || 'none'}`,
          `- last_action: ${state.last_action || '—'}`,
          `- last_error: ${state.last_error || 'none'}`,
          `- updated_at: ${state.updated_at || '—'}`,
          'escalation_required: ' + (state.escalation_required ? 'yes' : 'no'),
          `escalation_reason: ${state.escalation_required ? (state.escalation_reason || 'escalation triggered') : 'none'}`,
          '',
          'next_recommended_action: ' + (state.run_state === 'running' ? 'wait for loop to complete, then review candidate' : 'click Start/Resume to continue'),
          '=== END_RETURN_TO_CHATGPT ===',
        ].join('\n');
        const returnBox = document.getElementById('returnBox');
        if (returnBox) returnBox.textContent = returnBlock;
        
        // Try to load actual return artifact if available
        fetch(`${API_BASE}/return-artifact`)
          .then(r => r.json())
          .then(data => {
            if (data.status === 'found' && data.content && returnBox) {
              returnBox.textContent = data.content;
            }
          })
          .catch(() => {});
        
        // Update signoff card visibility
        const signoffCard = document.getElementById('signoffCard');
        if (state.phase_completion_state === 'completed' || state.ready_for_signoff) {
          signoffCard.style.display = 'block';
          document.getElementById('phaseStatus').textContent = state.phase_completion_state || 'unknown';
          document.getElementById('signoffStatus').textContent = state.signoff_granted ? 'granted' : (state.signoff_required ? 'required' : 'not_required');
          document.getElementById('mergeStatus').textContent = state.merge_push_allowed ? 'allowed' : 'blocked';
          const rounds = state.completed_rounds || [];
          document.getElementById('readyRounds').textContent = rounds.length > 0 ? rounds.join(', ') : 'none';
          
          // Update grant button state
          document.getElementById('grantSignoffBtn').disabled = !state.ready_for_signoff || state.signoff_granted;
        } else {
          signoffCard.style.display = 'none';
        }
        
        // Update resume button state
        if (state.run_state === 'running') {
          const resumeBtn = document.getElementById('resumeBtn');
          resumeBtn.className = 'btn done';
          resumeBtn.textContent = '執行中: ' + (state.current_round || '...');
          resumeBtn.disabled = true;
        }
      } catch (err) {
        console.log('Could not fetch state:', err);
      }
    }

    async function confirmApproveCandidate() {
      const ok = confirm(
        '你即將核准 Candidate。\\n\\n' +
        '這只是核准候選人，不會直接 merge 到 master。\\n' +
        '下一步會建立 review branch 並進入 promotion 流程。\\n\\n' +
        '確定要繼續嗎？'
      );
      const status = document.getElementById('approveStatus');
      const btn = document.getElementById('approveBtn');

      if (!ok) {
        status.textContent = '已取消核准';
        status.style.color = '#fca5a5';
        return;
      }

      btn.className = 'btn processing';
      btn.textContent = '處理中...';
      btn.disabled = true;
      status.textContent = '正在執行核准與 promotion...';
      status.style.color = '#93c5fd';

      try {
        const response = await fetch(`${API_BASE}/approve-and-promote`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'}
        });
        const data = await response.json();

        console.log('Approve result:', data);

        if (data.status === 'success') {
          btn.className = 'btn done';
          btn.textContent = '已核准並建立 review branch';
          status.textContent = '核准成功！Review branch 已建立。';
          status.style.color = '#86efac';
        } else {
          btn.className = 'btn danger';
          btn.textContent = '失敗';
          btn.disabled = false;
          status.textContent = '失敗: ' + (data.reason || data.stage || 'Unknown error');
          status.style.color = '#fca5a5';
        }
      } catch (err) {
        console.error('Bridge error:', err);
        btn.className = 'btn danger';
        btn.textContent = '連線錯誤';
        btn.disabled = false;
        status.textContent = '無法連接到 control bridge，請確認 bridge 是否在執行';
        status.style.color = '#fca5a5';
      }
    }

    // Update state display on load
    updateStateDisplay();
    // Refresh state every 5 seconds
    setInterval(updateStateDisplay, 5000);
  </script>
</body>
</html>
"@

[System.IO.File]::WriteAllText($outputPath, $html, [System.Text.Encoding]::UTF8)
Write-Host "Runtime panel generated:" -ForegroundColor Green
Write-Host $outputPath
