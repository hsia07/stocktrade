param(
    [int]$IntervalSeconds = 2,
    [string]$RuntimeDir = "runtime",
    [switch]$Simulation
)

$ErrorActionPreference = "Stop"

$InputFile = Join-Path $RuntimeDir "opencode_input.txt"
$OutputFile = Join-Path $RuntimeDir "opencode_output.txt"

$LAST_OUTPUT = ""

function Write-Status {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Message"
}

function Test-NewInput {
    if (-not (Test-Path $InputFile)) {
        return $false, "Input file not found"
    }
    
    $content = Get-Content $InputFile -Raw -ErrorAction SilentlyContinue
    if ([string]::IsNullOrWhiteSpace($content)) {
        return $false, "Input file is empty"
    }
    
    if ($content -eq $LAST_OUTPUT) {
        return $false, "No new content"
    }
    
    return $true, $content
}

function Write-Output-File {
    param([string]$Content)
    
    $dir = Split-Path $OutputFile -Parent
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    
    Set-Content -Path $OutputFile -Value $Content -Force
    Write-Status "Wrote result to $OutputFile"
}

function Invoke-OpenCodeCLI {
    param([string]$Instruction)
    
    Write-Status "REAL CLI MODE: Executing via OpenCode CLI"
    
    $cliPath = "opencode"
    $cliFullPath = "C:\Users\richa\AppData\Roaming\npm\opencode.cmd"
    
    if (Test-Path $cliFullPath) {
        $cliPath = $cliFullPath
    }
    
    Write-Status "CLI path: $cliPath"
    
    try {
        # Execute opencode CLI with the instruction
        # Note: opencode 1.4.8 is interactive (TUI). For automation,
        # we pass the instruction and capture output.
        $processInfo = New-Object System.Diagnostics.ProcessStartInfo
        $processInfo.FileName = $cliPath
        $processInfo.Arguments = "`"$Instruction`""
        $processInfo.RedirectStandardOutput = $true
        $processInfo.RedirectStandardError = $true
        $processInfo.UseShellExecute = $false
        $processInfo.WorkingDirectory = (Get-Location)
        
        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $processInfo
        $process.Start() | Out-Null
        
        $stdout = $process.StandardOutput.ReadToEnd()
        $stderr = $process.StandardError.ReadToEnd()
        $process.WaitForExit(30000)  # 30 second timeout
        
        if ($process.ExitCode -eq 0) {
            Write-Status "CLI execution completed successfully"
            return $stdout
        } else {
            Write-Status "CLI execution failed with exit code: $($process.ExitCode)"
            if ($stderr) {
                Write-Status "Error: $stderr"
            }
            return "ERROR: CLI execution failed. Exit code: $($process.ExitCode)`n$stderr"
        }
    } catch {
        Write-Status "ERROR: Failed to execute CLI - $($_.Exception.Message)"
        return "ERROR: $($_.Exception.Message)"
    }
}

Write-Status "Starting OpenCode Loop (REAL CLI MODE)"
Write-Status "CLI: opencode 1.4.8"
Write-Status "Monitoring: $InputFile"
Write-Status "Output: $OutputFile"
Write-Status "Interval: $IntervalSeconds seconds"
Write-Status ""

if ($Simulation) {
    Write-Status "WARNING: Simulation switch provided but real CLI mode is active"
}

while ($true) {
    Start-Sleep -Seconds $IntervalSeconds
    
    $hasNew, $content = Test-NewInput
    
    if (-not $hasNew) {
        if ($content -match "not found") {
            Write-Status "WAITING_FOR_INPUT: $content"
        }
        continue
    }
    
    Write-Status "Detected new instruction"
    
    try {
        $parsed = $content | ConvertFrom-Json
        $instruction = $parsed.instruction
        
        Write-Status "Instruction: $instruction"
        
        $result = Invoke-OpenCodeCLI -Instruction $instruction
        
        Write-Output-File -Content $result
        
        $script:LAST_OUTPUT = $content
        
    } catch {
        Write-Status "ERROR: Failed to process input - $($_.Exception.Message)"
    }
    
    Write-Status ""
}