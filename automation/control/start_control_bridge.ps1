#!/usr/bin/env pwsh
# start_control_bridge.ps1
# Formal standalone entrypoint contract for control_bridge.py
# GOV-INT-003 staged restart: starts only control_bridge, NOT telegram_sidecar or main_control_loop.
# Safe-deny: no sidecar, no main loop, no trading/broker/execution/live, no real Telegram API.
# PYTHONPATH contract: repo root is set in child process environment (not user-global).

param(
    [switch]$DryRun = $false,
    [switch]$Quiet = $false
)

$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
Set-Location $repoRoot

$bridgeScript = Join-Path (Join-Path $repoRoot "automation") (Join-Path "control" "control_bridge.py")
$logDir = Join-Path (Join-Path $repoRoot "automation") "control\logs"
$stdoutLog = Join-Path $logDir "control_bridge_stdout.log"
$stderrLog = Join-Path $logDir "control_bridge_stderr.log"

if (!(Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

if (!(Test-Path $bridgeScript)) {
    Write-Error "control_bridge.py not found at: $bridgeScript"
    exit 1
}

if (-not $Quiet) {
    Write-Host "=== CONTROL BRIDGE FORMAL ENTRYPOINT ===" -ForegroundColor Yellow
    Write-Host "Repo root: $repoRoot" -ForegroundColor Gray
    Write-Host "Target:    $bridgeScript" -ForegroundColor Gray
    Write-Host "Log dir:   $logDir" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Safe-deny: no telegram_sidecar, no main_control_loop, no /start-loop" -ForegroundColor Cyan
    Write-Host "Safe-deny: no trading/broker/execution/live mode, no order_execution" -ForegroundColor Cyan
    Write-Host "Safe-deny: no real Telegram API calls, no secret output" -ForegroundColor Cyan
    Write-Host ""
}

if ($DryRun) {
    Write-Host "=== DRY RUN MODE ===" -ForegroundColor Yellow
    Write-Host "Command that would be executed:" -ForegroundColor Gray
    Write-Host "  PYTHONPATH=$repoRoot" -ForegroundColor White
    Write-Host "  python $bridgeScript" -ForegroundColor White
    Write-Host ""
    Write-Host "Dry-run complete. No process started." -ForegroundColor Green
    exit 0
}

$env:PYTHONPATH = $repoRoot

try {
    $proc = Start-Process -FilePath "python" -ArgumentList $bridgeScript `
        -WorkingDirectory $repoRoot -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru

    if (-not $Quiet) {
        Write-Host "control_bridge started (PID: $($proc.Id))" -ForegroundColor Green
        Write-Host "stdout: $stdoutLog" -ForegroundColor Gray
        Write-Host "stderr: $stderrLog" -ForegroundColor Gray
    }

    $proc.Id
}
finally {
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
}
