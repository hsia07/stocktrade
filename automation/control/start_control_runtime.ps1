$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

$initScript = Join-Path $repoRoot "automation\control\init_runtime_files.ps1"
$openPanelScript = Join-Path $repoRoot "automation\control\open_runtime_panel.ps1"

powershell -ExecutionPolicy Bypass -File $initScript
powershell -ExecutionPolicy Bypass -File $openPanelScript

Write-Host "Control runtime started." -ForegroundColor Green
