# .githooks/check_canonical_direct_commit.ps1
# Mechanical Gate: Block unauthorized direct commits on canonical branch
# This script is called by pre-commit hook before every commit.

$ErrorActionPreference = "Stop"

$CANONICAL_BRANCH = "work/canonical-mainline-repair-001"
$currentBranch = git branch --show-current 2>$null

if ($currentBranch -ne $CANONICAL_BRANCH) {
    Write-Host "[canonical-guard] not on canonical branch ($currentBranch) -> skip"
    exit 0
}

# Check if this is a merge commit (merge commits are allowed on canonical)
$parents = git rev-parse "HEAD^@" 2>$null
$parentCount = 0
if ($parents) {
    $parentCount = @($parents -split "`n" | Where-Object { $_ }).Count
}

if ($parentCount -ge 2) {
    Write-Host "[canonical-guard] merge commit detected -> allowed"
    exit 0
}

# Check commit message for explicit authorization
$commitMsgFile = $args[0]
if ($commitMsgFile -and (Test-Path $commitMsgFile)) {
    $msg = Get-Content $commitMsgFile -Raw
    if ($msg -match "DIRECT-COMMIT-AUTHORIZED" -or $msg -match "direct commit on canonical authorized") {
        Write-Host "[canonical-guard] explicit authorization found -> allowed"
        exit 0
    }
}

# Check if this commit is creating/modifying the mechanical gate itself
# (to avoid chicken-and-egg problem when installing the gate)
$stagedFiles = git diff --cached --name-only 2>$null
$isGateInstallation = $false
foreach ($f in $stagedFiles) {
    if ($f -match "check_branch_workflow\.py" -or $f -match "check_canonical_direct_commit\.ps1" -or $f -match "pre-commit") {
        $isGateInstallation = $true
        break
    }
}

if ($isGateInstallation) {
    Write-Host "[canonical-guard] mechanical gate installation detected -> allowed (one-time exception)"
    exit 0
}

# FAIL-CLOSED: direct non-merge commit on canonical without authorization
Write-Host "[canonical-guard] FAIL: Direct non-merge commit on $CANONICAL_BRANCH is blocked." -ForegroundColor Red
Write-Host "[canonical-guard] Use side branch workflow:" -ForegroundColor Red
Write-Host "  1. git checkout -b work/[round-id]-candidate" -ForegroundColor Red
Write-Host "  2. git commit" -ForegroundColor Red
Write-Host "  3. git checkout $CANONICAL_BRANCH" -ForegroundColor Red
Write-Host "  4. git merge work/[round-id]-candidate" -ForegroundColor Red
Write-Host "[canonical-guard] Exception: emergency hotfix with 'DIRECT-COMMIT-AUTHORIZED' in commit message." -ForegroundColor Yellow

exit 1
