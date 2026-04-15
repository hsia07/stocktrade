$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

$statePath = Join-Path $repoRoot "automation\control\state.json"
$returnPath = Join-Path $repoRoot "automation\control\latest_return_to_chatgpt.txt"

if (Test-Path $statePath) {
    Write-Host "=== STATE ===" -ForegroundColor Cyan
    Get-Content $statePath
} else {
    Write-Host "state.json not found" -ForegroundColor Yellow
}

Write-Host ""

if (Test-Path $returnPath) {
    Write-Host "=== LATEST RETURN TO CHATGPT ===" -ForegroundColor Cyan
    Get-Content $returnPath
} else {
    Write-Host "latest_return_to_chatgpt.txt not found" -ForegroundColor Yellow
}
