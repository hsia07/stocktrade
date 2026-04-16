# Stocktrade Control Panel Launcher
# Run this script to start the control panel

$repoRoot = "C:\Users\richa\OneDrive\桌面\stocktrade"
$controlDir = Join-Path $repoRoot "automation\control"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Stocktrade Control Panel" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Step 1: Start Control Bridge
Write-Host "`n[1/3] Starting Control Bridge..." -ForegroundColor Yellow
$bridgeJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    python control_bridge.py
} -ArgumentList $controlDir

Write-Host "Bridge started (background job)" -ForegroundColor Green

# Step 2: Wait for initialization
Write-Host "`n[2/3] Waiting for initialization..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Step 3: Open in Chrome
Write-Host "`n[3/3] Opening in Google Chrome..." -ForegroundColor Yellow
$panelPath = Join-Path $controlDir "panel_runtime.html"

# Try Chrome paths
$chromePaths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)

$chrome = $null
foreach ($path in $chromePaths) {
    if (Test-Path $path) {
        $chrome = $path
        break
    }
}

if ($chrome) {
    Start-Process $chrome -ArgumentList $panelPath
    Write-Host "Chrome opened!" -ForegroundColor Green
} else {
    Start-Process $panelPath
    Write-Host "Opened with default browser" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Control Panel is running!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nTo stop, close this window." -ForegroundColor Gray

# Keep running to maintain bridge
while ($true) {
    Start-Sleep -Seconds 1
    $jobState = Get-Job -Id $bridgeJob.Id
    if ($jobState.State -eq 'Failed') {
        Write-Host "Bridge stopped. Press Enter to exit." -ForegroundColor Red
        Read-Host
        break
    }
}
