$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

$controlDir = Join-Path $repoRoot "automation\control"

$templateState = Join-Path $controlDir "state.template.json"
$templateReturn = Join-Path $controlDir "latest_return_to_chatgpt.template.txt"

$runtimeState = Join-Path $controlDir "state.runtime.json"
$runtimeReturn = Join-Path $controlDir "latest_return_to_chatgpt.runtime.txt"

if (!(Test-Path $templateState)) {
    throw "找不到 state.template.json"
}

if (!(Test-Path $templateReturn)) {
    throw "找不到 latest_return_to_chatgpt.template.txt"
}

Copy-Item $templateState $runtimeState -Force
Copy-Item $templateReturn $runtimeReturn -Force

Write-Host "Runtime files initialized." -ForegroundColor Green
Write-Host $runtimeState
Write-Host $runtimeReturn
