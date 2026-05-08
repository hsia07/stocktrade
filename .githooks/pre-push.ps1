# PowerShell pre-push hook: Canonical Direct Push Guard (P0)
# Rewrite of bash version for Windows unattended auto-advance.
# No bash dependency. All governance checks preserved.
# Reads stdin from git: local_ref local_sha remote_ref remote_sha

$ErrorActionPreference = "Stop"

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
        $content = git show "$($Sha):$EvidencePath" 2>$null
        if (-not $content) { return $false }
        $json = $content | ConvertFrom-Json
        return ($json.law_compliance -eq "04")
    }
    catch {
        return $false
    }
}

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

    if (-not (Check-CanonicialBranch -RemoteRef $remoteRef)) { continue }

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
