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

$mode = [string]$state.mode
$roundId = [string]$state.round_id
$branch = [string]$state.branch
$currentCycle = if ($null -eq $state.current_cycle_id) { "none" } else { [string]$state.current_cycle_id }
$latestCandidate = if ($null -eq $state.latest_candidate_id) { "none" } else { [string]$state.latest_candidate_id }
$pauseRequested = [string]$state.pause_requested
$acceptanceMode = [string]$state.acceptance_mode
$escalationRequired = [string]$state.escalation_required
$lastUpdate = if ($null -eq $state.last_update) { "none" } else { [string]$state.last_update }

# 判斷是否可以核准 Candidate
$canApprove = "no"
$rejectReason = ""
if ($mode -ne "paused_for_acceptance") {
    $rejectReason = "mode 不是 paused_for_acceptance (目前: $mode)"
} elseif ($latestCandidate -eq "none" -or [string]::IsNullOrEmpty($latestCandidate)) {
    $rejectReason = "latest_candidate_id 缺失"
} elseif ($escalationRequired -eq "True") {
    $rejectReason = "escalation_required 為 true"
}
if ($rejectReason -eq "") {
    $canApprove = "yes"
}

$canApproveClass = if ($canApprove -eq "yes") { "can" } else { "cannot" }

$modeLabel = switch ($mode) {
    "running" { "執行中" }
    "paused_for_acceptance" { "等待人工驗收" }
    "stopped_error" { "異常停止" }
    default { $mode }
}

$modeClass = switch ($mode) {
    "running" { "running" }
    "paused_for_acceptance" { "paused" }
    "stopped_error" { "error" }
    default { "neutral" }
}

$stateBlock = @"
mode: $mode
round_id: $roundId
branch: $branch
current_cycle_id: $currentCycle
latest_candidate_id: $latestCandidate
pause_requested: $pauseRequested
acceptance_mode: $acceptanceMode
escalation_required: $escalationRequired
last_update: $lastUpdate
"@

$stateBlockEscaped = Escape-Html $stateBlock
$returnEscaped = Escape-Html $returnText
$modeEscaped = Escape-Html $modeLabel
$roundEscaped = Escape-Html $roundId
$branchEscaped = Escape-Html $branch
$currentCycleEscaped = Escape-Html $currentCycle
$latestCandidateEscaped = Escape-Html $latestCandidate
$pauseRequestedEscaped = Escape-Html $pauseRequested
$acceptanceModeEscaped = Escape-Html $acceptanceMode
$escalationRequiredEscaped = Escape-Html $escalationRequired
$lastUpdateEscaped = Escape-Html $lastUpdate

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
            <div class="label">最新 Candidate</div>
            <div class="value">$latestCandidateEscaped</div>
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
        <button id="resumeBtn" class="btn ok" type="button" onclick="resetDrainState()">Start / Resume</button>
        <button id="drainBtn" class="btn warn" type="button" onclick="simulateDrain()">Drain After Current</button>
        <button class="btn primary" type="button" onclick="copyReturnBlock()">一鍵複製回傳給 GPT</button>
      </div>
      <div class="helper">
        目前這一版先把面板做成更清楚的可視化展示與一鍵複製。下一階段再把常用按鈕正式接到本機控制腳本。
      </div>
      <div id="copyStatus" class="copy-status"></div>
      <div id="drainStatus" class="inline-status"></div>

      <div class="danger-zone">
        <div class="danger-title">危險操作區</div>
        <div class="danger-text">
          Stop Now 會立即中止流程，可能跳過正常收尾。只有在異常狀況下才使用。
        </div>
        <button class="btn danger" type="button" onclick="confirmStopNow()">Stop Now</button>
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
          <div class="label">escalation_required</div>
          <div class="value">$escalationRequiredEscaped</div>
        </div>
        <div class="metric">
          <div class="label">mode</div>
          <div class="value">$modeEscaped</div>
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
            <div class="label">current_cycle_id</div>
            <div class="value">$currentCycleEscaped</div>
          </div>
          <div class="metric">
            <div class="label">pause_requested</div>
            <div class="value">$pauseRequestedEscaped</div>
          </div>
          <div class="metric">
            <div class="label">acceptance_mode</div>
            <div class="value">$acceptanceModeEscaped</div>
          </div>
          <div class="metric">
            <div class="label">escalation_required</div>
            <div class="value">$escalationRequiredEscaped</div>
          </div>
        </div>
        <div class="mono">$stateBlockEscaped</div>
      </div>

      <div class="card">
        <h2>最新 Candidate / 建議動作</h2>
        <div class="mono">latest_candidate_id: $latestCandidateEscaped
current_cycle_id: $currentCycleEscaped
pause_requested: $pauseRequestedEscaped
acceptance_mode: $acceptanceModeEscaped
escalation_required: $escalationRequiredEscaped</div>
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
    let drainTimer = null;

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

    function simulateDrain() {
      const btn = document.getElementById('drainBtn');
      const status = document.getElementById('drainStatus');

      btn.className = 'btn processing';
      btn.textContent = 'Progressing...';
      btn.disabled = true;
      status.textContent = '正在完成目前工作，完成後會切到已完成狀態。';

      if (drainTimer) {
        clearTimeout(drainTimer);
      }

      drainTimer = setTimeout(() => {
        btn.className = 'btn done';
        btn.textContent = '已完成';
        btn.disabled = false;
        status.textContent = 'Drain After Current 已完成。現在可以進行驗收。';
      }, 2200);
    }

    function resetDrainState() {
      const btn = document.getElementById('drainBtn');
      const status = document.getElementById('drainStatus');

      if (drainTimer) {
        clearTimeout(drainTimer);
        drainTimer = null;
      }

      btn.className = 'btn warn';
      btn.textContent = 'Drain After Current';
      btn.disabled = false;
      status.textContent = '已恢復執行。Drain 按鈕已重置。';
    }

    function confirmStopNow() {
      const ok = confirm('這是危險操作。Stop Now 可能跳過正常收尾。你確定要執行嗎？');
      const status = document.getElementById('copyStatus');
      if (ok) {
        status.textContent = '已確認 Stop Now。下一階段再把這顆按鈕正式接到本機控制腳本。';
      } else {
        status.textContent = '已取消 Stop Now。';
      }
    }

    function confirmApproveCandidate() {
      const ok = confirm(
        '你即將核准 Candidate。\n\n' +
        '這只是核准候選人，不會直接 merge 到 master。\n' +
        '下一步會建立 review branch 並進入 promotion 流程。\n\n' +
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

      fetch('http://127.0.0.1:8766/approve-and-promote', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
      })
      .then(res => res.json())
      .then(data => {
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
      })
      .catch(err => {
        console.error('Bridge error:', err);
        btn.className = 'btn danger';
        btn.textContent = '連線錯誤';
        btn.disabled = false;
        status.textContent = '無法連接到 control bridge，請確認 bridge 是否在執行';
        status.style.color = '#fca5a5';
      });
    }
  </script>
</body>
</html>
"@

Set-Content -Path $outputPath -Value $html -Encoding UTF8
Write-Host "Runtime panel generated:" -ForegroundColor Green
Write-Host $outputPath


