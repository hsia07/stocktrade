$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

$controlDir = Join-Path $repoRoot "automation\control"
$statePath = Join-Path $controlDir "state.json"
$returnPath = Join-Path $controlDir "latest_return_to_chatgpt.txt"
$outputPath = Join-Path $controlDir "panel_runtime.html"

if (Test-Path $statePath) {
    $stateRaw = Get-Content $statePath -Raw
    $state = $stateRaw | ConvertFrom-Json
} else {
    throw "找不到 state.json"
}

if (Test-Path $returnPath) {
    $returnText = Get-Content $returnPath -Raw
} else {
    $returnText = "latest_return_to_chatgpt.txt not found"
}

function Escape-Html([string]$text) {
    if ($null -eq $text) { return "" }
    return [System.Net.WebUtility]::HtmlEncode($text)
}

$mode = Escape-Html $state.mode
$roundId = Escape-Html $state.round_id
$branch = Escape-Html $state.branch
$currentCycle = Escape-Html ([string]$state.current_cycle_id)
$latestCandidate = Escape-Html ([string]$state.latest_candidate_id)
$pauseRequested = Escape-Html ([string]$state.pause_requested)
$acceptanceMode = Escape-Html ([string]$state.acceptance_mode)
$escalationRequired = Escape-Html ([string]$state.escalation_required)
$lastUpdate = Escape-Html ([string]$state.last_update)

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

$html = @"
<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <title>Stocktrade Control Panel Runtime</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; background: #f6f7fb; color: #1f2937; }
    .wrap { max-width: 980px; margin: 0 auto; }
    .card { background: white; border-radius: 14px; padding: 18px; margin-bottom: 16px; box-shadow: 0 2px 10px rgba(0,0,0,0.06); }
    h1, h2 { margin-top: 0; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .status { font-size: 18px; font-weight: bold; }
    .mono { white-space: pre-wrap; font-family: Consolas, monospace; background: #111827; color: #e5e7eb; padding: 12px; border-radius: 10px; }
    .buttons { display: flex; flex-wrap: wrap; gap: 10px; }
    button { border: 0; border-radius: 10px; padding: 10px 14px; cursor: default; font-weight: bold; opacity: 0.9; }
    .primary { background: #2563eb; color: white; }
    .warn { background: #f59e0b; color: white; }
    .danger { background: #dc2626; color: white; }
    .ok { background: #16a34a; color: white; }
    .muted { color: #6b7280; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Stocktrade Control Panel Runtime</h1>
      <div class="status">目前狀態：<span id="mode">$mode</span></div>
      <div class="muted">目前輪次：$roundId</div>
      <div class="muted">目前分支：$branch</div>
      <div class="muted">最後更新：$lastUpdate</div>
    </div>

    <div class="card">
      <h2>控制按鈕（目前為展示骨架）</h2>
      <div class="buttons">
        <button class="ok">Start / Resume</button>
        <button class="warn">Drain After Current</button>
        <button class="danger">Stop Now</button>
        <button class="primary">Copy RETURN_TO_CHATGPT</button>
      </div>
      <p class="muted">此頁面內容由 refresh_panel.ps1 生成，按鈕下一階段再接本機控制腳本。</p>
    </div>

    <div class="row">
      <div class="card">
        <h2>最新狀態</h2>
        <div class="mono">$stateBlockEscaped</div>
      </div>

      <div class="card">
        <h2>最新 Candidate</h2>
        <div class="mono">latest_candidate_id: $latestCandidate
current_cycle_id: $currentCycle
escalation_required: $escalationRequired</div>
      </div>
    </div>

    <div class="card">
      <h2>RETURN_TO_CHATGPT</h2>
      <div class="mono">$returnEscaped</div>
    </div>
  </div>
</body>
</html>
"@

Set-Content -Path $outputPath -Value $html -Encoding UTF8
Write-Host "Runtime panel generated:" -ForegroundColor Green
Write-Host $outputPath
