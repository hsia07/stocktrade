$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

$startPs1 = Join-Path $repoRoot "automation\control\start_control_runtime.ps1"
$desktop = "C:\Users\richa\OneDrive\桌面"
$shortcutPath = Join-Path $desktop "啟動控制面板.lnk"

if (!(Test-Path $startPs1)) {
    throw "找不到 start_control_runtime.ps1：$startPs1"
}

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$startPs1`""
$shortcut.WorkingDirectory = $repoRoot
$shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,220"
$shortcut.Save()

Write-Host "Desktop shortcut created:" -ForegroundColor Green
Write-Host $shortcutPath
