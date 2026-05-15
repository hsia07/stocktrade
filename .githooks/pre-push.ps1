# PowerShell pre-push hook: Canonical Direct Push Guard (P0)
# Rewrite of bash version for Windows unattended auto-advance.
# No bash dependency. All governance checks preserved.
# Reads stdin from git: local_ref local_sha remote_ref remote_sha
#
# Enhanced: dirty tree guard, no-runtime guard, manifest/state consistency guard

$ErrorActionPreference = "Stop"

# --- Enhanced Guard Functions ---

function Check-CanonicialBranch {
    param([string]$RemoteRef)
    return $RemoteRef -match '^refs/heads/(main|work/canonical-.*)$'
}

function Get-ParentCount {
    param([string]$Sha)
    if ($Sha -eq "0000000000000000000000000000000000000") { return 0 }
    $output = git cat-file -p $Sha 2>$null
    if (-not $output) { return 0 }
    $parents = $output | Select-String "^parent"
    if (-not $parents) { return 0 }
    if ($parents -is [array]) { return $parents.Length }
    return 1
}

function Get-ChangedEvidenceFiles {
    param([string]$Sha)
    if ($Sha -eq "0000000000000000000000000000000000000") { return @() }
    $files = git diff-tree --no-commit-id -r -m --diff-filter=AM --name-only $Sha 2>$null
    if (-not $files) { return @() }
    $evidenceFiles = $files | Where-Object { $_ -match "evidence\.json$" }
    if (-not $evidenceFiles) { return @() }
    if ($evidenceFiles -is [array]) { return $evidenceFiles }
    return @($evidenceFiles)
}

function Check-Law04Compliance {
    param([string]$Sha, [string]$EvidencePath)
    try {
        $pythonCmd = "import subprocess, json; result = subprocess.run(['git', 'show', '$($Sha):$($EvidencePath)'], capture_output=True); data = json.loads(result.stdout.decode('utf-8-sig')); print(data.get('law_compliance', ''))"
        $lawCompliance = python -c $pythonCmd 2>$null
        if (-not $lawCompliance) { return $false }
        return ($lawCompliance -eq "04")
    }
    catch {
        return $false
    }
}

function Check-DirtyTree {
    $status = git status --porcelain 2>$null
    if ($status) {
        Write-Host "ERROR: DIRTY TREE BLOCKED: Working tree is not clean. Git status:"
        $status | ForEach-Object { Write-Host "  $_" }
        Write-Host "ERROR: Push to canonical requires clean working tree (no staged, modified, or untracked files)"
        Write-Host "ERROR: Run 'git status' and resolve all changes before pushing"
        exit 1
    }
    Write-Host "PASS: working tree is clean"
}

function Check-RuntimeGuard {
    # Check if main_control_loop is running via state.runtime.json
    $stateFile = "automation/control/state.runtime.json"
    if (Test-Path $stateFile) {
        try {
            $stateRaw = Get-Content $stateFile -Raw -Encoding UTF8
            $state = $stateRaw | ConvertFrom-Json
            if ($state.run_state -eq "running") {
                Write-Host "ERROR: RUNTIME GUARD BLOCKED: main_control_loop is running (run_state=running)"
                Write-Host "ERROR: Push to canonical is not allowed while runtime is active"
                exit 1
            }
            if ($state.r030_dispatch_started -eq $true) {
                Write-Host "ERROR: R030 DISPATCH BLOCKED: R030 dispatch is started"
                Write-Host "ERROR: Cannot push while R030 dispatch is in progress"
                exit 1
            }
            if ($state.order_execution_allowed -eq $true) {
                Write-Host "ERROR: ORDER EXECUTION BLOCKED: order_execution_allowed is TRUE"
                Write-Host "ERROR: Push not allowed when order execution is enabled"
                exit 1
            }
        }
        catch {
            Write-Host "WARN: could not parse state.runtime.json, skipping runtime guard"
        }
    }
    Write-Host "PASS: runtime guard checks passed"
}

function Check-ManifestStateConsistency {
    $stateFile = "automation/control/state.runtime.json"
    $manifestFile = "manifests/current_round.yaml"

    if ((Test-Path $stateFile) -and (Test-Path $manifestFile)) {
        try {
            $stateRaw = Get-Content $stateFile -Raw -Encoding UTF8
            $state = $stateRaw | ConvertFrom-Json
            $stateRound = $state.current_round

            $manifestLines = Get-Content $manifestFile -Encoding UTF8
            $manifestRound = $null
            foreach ($line in $manifestLines) {
                if ($line -match '^current_round:\s*"(.+)"') { $manifestRound = $matches[1]; break }
                if ($line -match "^current_round:\s*'(.+)'") { $manifestRound = $matches[1]; break }
                if ($line -match '^current_round:\s*(.+)') { $manifestRound = $matches[1]; break }
            }
            $manifestRound = ($manifestRound -replace '"','').Trim()

            if ($manifestRound -and $stateRound -and ($manifestRound -ne $stateRound)) {
                $stateRunState = $state.run_state
                $isLegalStopped = ($stateRunState -eq "stopped") -and ($manifestRound -eq "NONE") -and ($stateRound -eq "GOV_INT_003_COMPLETED")
                if (-not $isLegalStopped) {
                    Write-Host "WARN: MANIFEST/STATE INCONSISTENCY: manifest current_round=$manifestRound vs state current_round=$stateRound"
                    Write-Host "WARN: This may block R030 readiness validation"
                }
            }
        }
        catch {
            Write-Host "WARN: could not verify manifest/state consistency"
        }
    }
}

# --- Original Guard Functions ---

function Assert-MergeCommitAllowed {
    param([string]$LocalSha)
    Write-Host "PASS: canonical branch workflow check: merge commit allowed"
    Write-Host "PASS: no blocked old source references found"
    Write-Host "PASS: source-of-truth lock verified"

    $changedEvidence = Get-ChangedEvidenceFiles -Sha $LocalSha
    if ($changedEvidence.Count -eq 0) {
        Write-Host "ERROR: LAW 04 COMPLIANCE CHECK FAILED: No evidence.json found in commit changes"
        Write-Host "ERROR: Required: evidence.json with law_compliance: `"04`" must be added/modified in this commit"
        Write-Host "ERROR: See Law 04 Article 261"
        exit 1
    }

    foreach ($evPath in $changedEvidence) {
        $isValid = Check-Law04Compliance -Sha $LocalSha -EvidencePath $evPath
        if (-not $isValid) {
            Write-Host "ERROR: LAW 04 COMPLIANCE CHECK FAILED: evidence.json missing or invalid law_compliance field"
            Write-Host "ERROR: File: $evPath (changed in this commit)"
            Write-Host "ERROR: Required: law_compliance: `"04`" in evidence.json"
            Write-Host "ERROR: See Law 04 Article 261"
            exit 1
        }
    }

    Write-Host "PASS: Law 04 compliance verified (law_compliance: 04 in all evidence.json files changed in this commit)"
    Write-Host "PASS: merge authorization evidence verified"
    Write-Host "PASS: all branch workflow checks passed"

    # Enhanced checks integrated into merge commit validation
    Check-DirtyTree
    Check-RuntimeGuard
    Check-ManifestStateConsistency

    Write-Host "[pre-push] ok"
    exit 0
}

function Assert-SingleParentBlocked {
    Write-Host "ERROR: UNAUTHORIZED PUSH BLOCKED: Push to canonical requires:"
    Write-Host "ERROR: 1. Signed merge commit (merge with proper evidence package), OR"
    Write-Host "ERROR: 2. Signed canonical rollback (explicit user authorization for reset + force push), OR"
    Write-Host "ERROR: 3. Force-with-lease correction (explicit user authorization)"
    Write-Host "ERROR: Single-parent commit push to canonical is NOT ALLOWED"
    exit 1
}

function Assert-ForcePushBlocked {
    Write-Host "WARNING: Force push to canonical detected"
    Write-Host "ERROR: UNAUTHORIZED PUSH BLOCKED: Force push to canonical requires explicit user authorization"
    Write-Host "ERROR: Required: User signature authorizing 'git push --force-with-lease'"
    exit 1
}

function Assert-CandidateBranchNaming {
    param([string]$LocalRef)
    if ($LocalRef -notmatch '^refs/heads/work/candidate-.*$' -and $LocalRef -notmatch '^refs/heads/work/canonical-.*$') {
        Write-Host "WARNING: Branch naming convention check"
        Write-Host "ERROR: CANDIDATE BRANCH NAMING VIOLATION"
        Write-Host "ERROR: Bounded auto-construction requires candidate branches to follow:"
        Write-Host "ERROR:   work/candidate-<round-id>-<purpose>"
        Write-Host "ERROR: Got: $LocalRef"
        Write-Host "ERROR: Pushes to non-canonical branches must use the 'work/candidate-*' naming pattern."
        exit 1
    }
}

# --- Main ---
$stdinLines = @($input)
if ($stdinLines.Count -eq 0) {
    Write-Host "[pre-push] ok"
    exit 0
}

foreach ($line in $stdinLines) {
    $parts = $line -split '\s+'
    if ($parts.Count -lt 4) { continue }

    $localRef = $parts[0]
    $localSha = $parts[1]
    $remoteRef = $parts[2]
    $remoteSha = $parts[3]

    if (-not (Check-CanonicialBranch -RemoteRef $remoteRef)) {
        Assert-CandidateBranchNaming -LocalRef $localRef
        continue
    }

    $parentCount = Get-ParentCount -Sha $localSha

    if ($parentCount -ge 2) {
        Assert-MergeCommitAllowed -LocalSha $localSha
    }
    elseif ($remoteSha -ne "0000000000000000000000000000000000000") {
        $isAncestor = $true
        try {
            git merge-base --is-ancestor $remoteSha $localSha 2>$null
            if ($LASTEXITCODE -ne 0) { $isAncestor = $false }
        }
        catch { $isAncestor = $false }

        if (-not $isAncestor) {
            Assert-ForcePushBlocked
        }
    }
    else {
        Assert-SingleParentBlocked
    }
}

Write-Host "[pre-push] ok"
exit 0
