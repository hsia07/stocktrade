$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

$syncScript = Join-Path $repoRoot "automation\control\sync_return_block.ps1"
$refreshScript = Join-Path $repoRoot "automation\control\refresh_panel.ps1"
$panelPath = (Resolve-Path (Join-Path $repoRoot "automation\control\panel_runtime.html")).Path
$panelUrl = "file:///" + ($panelPath -replace "\\","/")

powershell -ExecutionPolicy Bypass -File $syncScript
powershell -ExecutionPolicy Bypass -File $refreshScript

$chromePaths = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LocalAppData\Google\Chrome\Application\chrome.exe"
)

$edgePaths = @(
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:LocalAppData\Microsoft\Edge\Application\msedge.exe"
)

$browser = $null

foreach ($p in $chromePaths) {
    if (Test-Path $p) { $browser = $p; break }
}

if (-not $browser) {
    foreach ($p in $edgePaths) {
        if (Test-Path $p) { $browser = $p; break }
    }
}

if (-not $browser) {
    throw "找不到 Chrome 或 Edge 的執行檔，請先安裝其中一個瀏覽器，或告訴我你用哪個瀏覽器。"
}

Start-Process -FilePath $browser -ArgumentList $panelUrl

Write-Host "Runtime panel opened in browser." -ForegroundColor Green
Write-Host $browser
