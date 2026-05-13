$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

$initScript = Join-Path $repoRoot "automation\control\init_runtime_files.ps1"
$openPanelScript = Join-Path $repoRoot "automation\control\open_runtime_panel.ps1"
$bridgeEntrypoint = Join-Path $repoRoot "automation\control\start_control_bridge.ps1"

powershell -ExecutionPolicy Bypass -File $initScript
powershell -ExecutionPolicy Bypass -File $openPanelScript

Write-Host "Control runtime started." -ForegroundColor Green
Write-Host "To start control_bridge separately: powershell -File `"$bridgeEntrypoint`"" -ForegroundColor Gray
Write-Host "NOTE: start_control_bridge.ps1 is NOT auto-started. Use it explicitly for GOV-INT-003 staged restart." -ForegroundColor Yellow
