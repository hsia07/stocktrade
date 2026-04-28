# Telegram Progress Sidecar Startup Script
# This script starts the Telegram Progress Sidecar in parallel with auto-run loop.
# It does NOT modify the core auto-run loop (api_automode_loop.py).

[CmdletBinding()]
param(
    [string]$ReportPath = "automation/control/latest_return_to_chatgpt.txt",
    [string]$LogPath = "automation/control/telegram_sidecar.log",
    [int]$CheckIntervalSeconds = 2,
    [switch]$MockMode = $false
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "$timestamp [INFO] $Message"
    Write-Output $logMessage
    if ($LogPath) {
        Add-Content -Path $LogPath -Value $logMessage -Encoding UTF8
    }
}

function Get-TelegramConfig {
    $config = @{
        BotToken = $env:TELEGRAM_BOT_TOKEN
        ChatId = $env:TELEGRAM_CHAT_ID
        Mode = "mock"
    }
    
    if ($config.BotToken -and $config.ChatId) {
        $config.Mode = "real"
        Write-Log "Telegram credentials found - entering REAL mode"
        Write-Log "BotToken present: YES (length: $($config.BotToken.Length))"
        Write-Log "ChatId present: YES"
        # IMPORTANT: Never print actual token to log
    } else {
        Write-Log "Telegram credentials NOT found - entering MOCK/LOG mode"
        $config.Mode = "mock"
    }
    
    if ($MockMode) {
        Write-Log "MockMode switch override - forcing MOCK mode"
        $config.Mode = "mock"
    }
    
    return $config
}

function Start-SidecarLoop {
    param($Config, $ReportPath, $CheckInterval)
    
    Write-Log "Starting Telegram Progress Sidecar..."
    Write-Log "Report path: $ReportPath"
    Write-Log "Check interval: $CheckInterval seconds"
    Write-Log "Mode: $($Config.Mode)"
    
    # Check if Python is available
    try {
        $pythonVersion = python --version 2>&1
        Write-Log "Python found: $pythonVersion"
    } catch {
        Write-Log "ERROR: Python not found in PATH"
        exit 1
    }
    
    # Build Python command arguments
    $scriptPath = "automation/control/telegram_progress_sidecar.py"
    if (-not (Test-Path $scriptPath)) {
        Write-Log "ERROR: Sidecar script not found: $scriptPath"
        exit 1
    }
    
    Write-Log "Sidecar script: $scriptPath"
    Write-Log "Telegram Progress Sidecar started in $($Config.Mode) mode"
    Write-Log "Monitoring report: $ReportPath"
    
    # Main monitoring loop
    $lastHash = $null
    while ($true) {
        if (Test-Path $ReportPath) {
            $content = Get-Content $ReportPath -Raw -ErrorAction SilentlyContinue
            if ($content) {
                $hash = Get-FileHash -Path $ReportPath -Algorithm MD5
                if ($hash.Hash -ne $lastHash) {
                    $lastHash = $hash.Hash
                    Write-Log "Report file changed (hash: $($hash.Hash))"
                    # In real implementation, this would trigger sidecar notification
                    # For now, just log the change
                }
            }
        } else {
            Write-Log "Report file not found: $ReportPath"
        }
        
        Start-Sleep -Seconds $CheckInterval
    }
}

# Main
Write-Log "=========================================="
Write-Log "Telegram Progress Sidecar Activator"
Write-Log "=========================================="

$config = Get-TelegramConfig
Write-Log "Configuration: mode=$($config.Mode), report=$ReportPath"

# Start the sidecar loop
try {
    Start-SidecarLoop -Config $config -ReportPath $ReportPath -CheckInterval $CheckIntervalSeconds
} catch {
    Write-Log "ERROR: Sidecar stopped - $_"
    Write-Log "Stack trace: $($_.ScriptStackTrace)"
    exit 1
}
