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
            <div class="value">$roundEscaped</div>
          </div>
          <div class="metric">
            <div class="label">目前分支</div>
            <div class="value">$branchEscaped</div>
          </div>
          <div class="metric">
            <div class="label">目前 Phase</div>
            <div class="value">$phaseCompletionEscaped</div>
          </div>
          <div class="metric">
            <div class="label">最後更新</div>
            <div class="value">$lastUpdateEscaped</div>
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
            <div class="label">current_phase</div>
            <div class="value">$currentPhase</div>
          </div>
          <div class="metric">
            <div class="label">current_round</div>
            <div class="value">$currentRound</div>
          </div>
          <div class="metric">
            <div class="label">phase_completion_state</div>
            <div class="value">$phaseCompletionEscaped</div>
          </div>
          <div class="metric">
            <div class="label">stop_reason</div>
            <div class="value">$stopReason</div>
          </div>
        </div>
        <div class="mono">$stateBlockEscaped</div>
      </div>

      <div class="card">
        <h2>最新 Candidate / 建議動作</h2>
        <div class="mono">current_candidate_id: $currentCandidateEscaped
latest_candidate_id: $latestCandidateEscaped
phase_completion_state: $phaseCompletionEscaped
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

        if (data.status === 'success') {
          btn.className = 'btn done';
          btn.textContent = '執行中';
          setOperationStatus('主控制循環已啟動', 'success');
          updateStateDisplay();
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
          resumeBtn.textContent = '執行中';
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

Set-Content -Path $outputPath -Value $html -Encoding UTF8
Write-Host "Runtime panel generated:" -ForegroundColor Green
Write-Host $outputPath
