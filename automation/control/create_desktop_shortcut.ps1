# Create desktop shortcut for Stocktrade Control Panel
# This is the official shortcut creation script for R-006

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop "Stocktrade Control Panel.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut($shortcutPath)

# Use the official PowerShell launcher in repo root
$psPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$scriptPath = Join-Path $repoRoot "Start-ControlPanel.ps1"

$shortcut.TargetPath = $psPath
$shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$scriptPath`""
$shortcut.WorkingDirectory = $repoRoot
$shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,14"
$shortcut.Description = "Stocktrade Automation Control Panel - Launch bridge and open panel in Chrome"
$shortcut.WindowStyle = 7  # Minimized

$shortcut.Save()

Write-Host "========================================" -ForegroundColor Green
Write-Host "Desktop shortcut created successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Shortcut Name: Stocktrade Control Panel" -ForegroundColor Cyan
Write-Host "Location: $shortcutPath" -ForegroundColor Gray
Write-Host ""
Write-Host "Double-click the shortcut to start:" -ForegroundColor Yellow
Write-Host "  1. Control Bridge (Python HTTP server)" -ForegroundColor White
Write-Host "  2. Google Chrome with Control Panel" -ForegroundColor White
Write-Host ""
