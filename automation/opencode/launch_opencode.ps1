$repo = "C:\Users\richa\OneDrive\桌面\stocktrade"
$cmdPath = Join-Path $env:APPDATA "npm\opencode.cmd"

Set-Location $repo

Write-Host ""
Write-Host "=== READ THESE FIRST ===" -ForegroundColor Cyan
Write-Host "1. automation/opencode/OPENCODE_FIXED_RULES.md"
Write-Host "2. automation/opencode/TASK_ACTIVE.md"
Write-Host "3. automation/opencode/SESSION_START_PROMPT.md"
Write-Host "4. manifests/current_round.yaml"
Write-Host "5. automation/retry_budget.yaml"
Write-Host ""

if (Test-Path $cmdPath) {
    & $cmdPath $repo
} else {
    Write-Host "找不到 opencode.cmd，請先確認 opencode 已安裝。" -ForegroundColor Yellow
}
