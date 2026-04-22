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

function Invoke-Simulation {
    param([string]$Instruction)
    
    Write-Status "SIMULATION MODE: Processing instruction (no real OpenCode CLI call)"
    
    $simulatedResponse = @"
================================================================================
FORMAL RETURN TO CHATGPT - SIMULATED RESPONSE
================================================================================

round_id: SIMULATED_BRIDGE_LOOP
task_type: simulation_response
reply_id: SIM-$(Get-Date -Format "yyyyMMdd-HHmmss")

status: simulation_completed
formal_status_code: no_execution_simulation

implementation_summary: |
  Simulation mode: This is a simulated response to demonstrate the bridge loop.
  No actual OpenCode CLI execution was performed.
  
  Received instruction: $Instruction
  
  In production, this would:
  1. Parse the instruction
  2. Execute via OpenCode CLI
  3. Capture the real RETURN_TO_CHATGPT
  4. Write to runtime/opencode_output.txt

validation_summary: |
  - Loop detected new input: YES
  - Simulation mode: YES
  - Output written: YES
  - Lane frozen: PRESERVED (simulation only)
  - Remote untrusted: PRESERVED (simulation only)

next_action: |
  Bridge continues polling. In production:
  - Telegram approval flow handles high-risk operations
  - Real OpenCode CLI executes approved instructions
  - Results written to runtime/opencode_output.txt

================================================================================
END OF SIMULATION
================================================================================
"@
    
    return $simulatedResponse
}

Write-Status "Starting OpenCode Loop (Simulation Mode)"
Write-Status "Monitoring: $InputFile"
Write-Status "Output: $OutputFile"
Write-Status "Interval: $IntervalSeconds seconds"
Write-Status ""

if ($Simulation) {
    Write-Status "RUNNING IN SIMULATION MODE - No real OpenCode CLI calls"
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
        
        $result = Invoke-Simulation -Instruction $instruction
        
        Write-Output-File -Content $result
        
        $script:LAST_OUTPUT = $content
        
    } catch {
        Write-Status "ERROR: Failed to process input - $($_.Exception.Message)"
    }
    
    Write-Status ""
}