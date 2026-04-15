# Test file for aider automation
# This is a simple file to test the run_candidate_aider.ps1 script

$TestVersion = "1.0.0"
$TestStatus = "ready"

function Get-TestStatus {
    return $TestStatus
}

function Set-TestStatus {
    param([string]$Status)
    $TestStatus = $Status
    return $TestStatus
}
