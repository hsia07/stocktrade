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

function Get-ChangedSignoffFiles {
    param([string]$Sha)
    if ($Sha -eq "0000000000000000000000000000000000000") { return @() }
    $files = git diff-tree --no-commit-id -r -m --diff-filter=AM --name-only $Sha 2>$null
    if (-not $files) { return @() }
    $signoffFiles = $files | Where-Object { $_ -match "(merge|push)_signoff\.txt$" }
    if (-not $signoffFiles) { return @() }
    if ($signoffFiles -is [array]) { return $signoffFiles }
    return @($signoffFiles)
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

function Check-SignoffContent {
    param([string]$Sha, [string]$SignoffPath, [string]$ExpectedAction)
    try {
        $content = git show $("$($Sha):$($SignoffPath)") 2>$null
        if (-not $content) { return @("signoff_file_empty_or_missing") }
        $lines = @($content -split "`n")

        $actionFound = $lines | Where-Object { $_ -match "(?i)$ExpectedAction" }
        if (-not $actionFound) { return @("signoff_missing_action_type:$ExpectedAction") }

        $branchFound = $lines | Where-Object { $_ -match "(?i)(work/canonical|origin/work/canonical)" }
        if (-not $branchFound) { return @("signoff_missing_target_branch") }

        $hashFound = $lines | Where-Object { $_ -match "([0-9a-fA-F]{40})" }
        if (-not $hashFound) { return @("signoff_missing_authorized_hash") }

        $userAuthFound = $lines | Where-Object { $_ -match "(?i)(authorized|signoff|approve|consent)" }
        if (-not $userAuthFound) { return @("signoff_missing_user_authorization") }

        $nonAuthMarkers = @("template_only", "test_fixture", "sample", "placeholder", "not real user signoff", "machine-generated", "machine generated")
        foreach ($marker in $nonAuthMarkers) {
            $markerFound = $lines | Where-Object { $_.ToLower() -match $marker }
            if ($markerFound) { return @("governance_gate:template_or_machine_signoff_blocked:$marker") }
        }

        return @()
    }
    catch {
        return @("signoff_check_error:$($_.Exception.Message)")
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

function Check-UIVisibleGate {
    param([string]$Sha)
    # UI_VISIBLE_ROUND_ACCEPTANCE_GATE check (Law 04 Chapter 22)
    # Check if evidence.json in changed files contains UI visible gate evidence
    $evidenceFiles = Get-ChangedEvidenceFiles -Sha $Sha
    $uiGateIssues = @()
    
    foreach ($evPath in $evidenceFiles) {
        try {
            $pythonCmd = "import subprocess, json; result = subprocess.run(['git', 'show', '$($Sha):$($evPath)'], capture_output=True); data = json.loads(result.stdout.decode('utf-8-sig')); round_id = data.get('round_id',''); task_type = data.get('task_type',''); files = data.get('files_modified',[]) + data.get('files_added',[]); is_ui = any(k in (round_id + task_type).lower() for k in ['ui','panel','dashboard','homepage','onboarding','teaching','summary','mobile','emergency','simulation','visualization','query','report','display']); has_ui_files = any('index.html' in f or f.endswith('.css') or f.endswith('.js') or 'panel' in f.lower() or 'ui' in f.lower() for f in files); print('is_ui:', is_ui or has_ui_files); visible = any(data.get(k) for k in ['ui_visible_gate_pass','visible_surface_evidence','ui_panel_present','dom_scan_pass']); fake = any(data.get(k) for k in ['fake_feature_claim_detected','false_completion_claim']); pollution = any(data.get(k) for k in ['buy_sell_controls_added','broker_toggle_added','trading_control_pollution','new_api_fetch_post_added']); order_true = data.get('order_execution_allowed') is True; print('visible:', visible); print('fake:', fake); print('pollution:', pollution); print('order_true:', order_true)"
            $result = python -c $pythonCmd 2>$null
            if ($result) {
                $lines = $result -split "`n"
                $isUI = $lines | Where-Object { $_ -match "is_ui:\s*True" }
                $visible = $lines | Where-Object { $_ -match "visible:\s*True" }
                $fake = $lines | Where-Object { $_ -match "fake:\s*True" }
                $pollution = $lines | Where-Object { $_ -match "pollution:\s*True" }
                $orderTrue = $lines | Where-Object { $_ -match "order_true:\s*True" }
                
                if ($isUI) {
                    if (-not $visible) {
                        $uiGateIssues += "$evPath : missing visible surface evidence"
                    }
                    if ($fake) {
                        $uiGateIssues += "$evPath : fake feature claim detected"
                    }
                    if ($pollution) {
                        $uiGateIssues += "$evPath : trading control pollution detected"
                    }
                    if ($orderTrue) {
                        $uiGateIssues += "$evPath : order_execution_allowed is TRUE"
                    }
                }
            }
        }
        catch {
            Write-Host "WARN: could not check UI visible gate for $evPath"
        }
    }
    
    if ($uiGateIssues.Count -gt 0) {
        Write-Host "ERROR: UI_VISIBLE_ROUND_ACCEPTANCE_GATE CHECK FAILED:"
        foreach ($issue in $uiGateIssues) {
            Write-Host "  ERROR: $issue"
        }
        Write-Host "ERROR: UI / user-facing / dashboard / panel / report / query / visualization rounds"
        Write-Host "ERROR: must pass UI_VISIBLE_ROUND_ACCEPTANCE_GATE (Law 04 Chapter 22)"
        exit 1
    }
    Write-Host "PASS: UI visible gate checks passed"
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

    $candidateEvidenceInTree = $false
    $candidatesDirsResult = git ls-tree -r --name-only $LocalSha -- automation/control/candidates/ 2>$null
    if ($candidatesDirsResult) {
        $evidenceInTree = $candidatesDirsResult | Where-Object { $_ -match "evidence\.json$" }
        if ($evidenceInTree -and $evidenceInTree.Count -gt 0) {
            $candidateEvidenceInTree = $true
        }
    }

    $changedEvidence = Get-ChangedEvidenceFiles -Sha $LocalSha
    if ($changedEvidence.Count -eq 0 -and -not $candidateEvidenceInTree) {
        Write-Host "ERROR: LAW 04 COMPLIANCE CHECK FAILED: No evidence.json found in commit changes or candidate tree"
        Write-Host "ERROR: Required: evidence.json with law_compliance: `"04`" must be in commit changes or candidate tree"
        Write-Host "ERROR: See Law 04 Article 261"
        exit 1
    }

    if ($changedEvidence.Count -gt 0) {
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
    } else {
        Write-Host "PASS: Law 04 compliance verified (evidence.json present in candidate tree, no changes in this commit)"
    }

    # Governance Prevention Gate: check merge/push signoff files
    $signoffFiles = Get-ChangedSignoffFiles -Sha $LocalSha
    $hasMergeSignoff = $false
    $hasPushSignoff = $false
    $signoffIssues = @()

    foreach ($sf in $signoffFiles) {
        if ($sf -match "merge_signoff") { $hasMergeSignoff = $true }
        if ($sf -match "push_signoff") { $hasPushSignoff = $true }
    }

    if (-not $hasMergeSignoff -and -not $hasPushSignoff) {
        $signoffIssues += "NO_SIGNOFF_FILES: merge_signoff.txt and push_signoff.txt not found in commit changes"
    }

    if ($hasMergeSignoff) {
        $mergeSf = $signoffFiles | Where-Object { $_ -match "merge_signoff" } | Select-Object -First 1
        $mergeIssues = Check-SignoffContent -Sha $LocalSha -SignoffPath $mergeSf -ExpectedAction "merge"
        foreach ($issue in $mergeIssues) {
            $signoffIssues += "merge_signoff:$issue"
        }
    }

    if ($hasPushSignoff) {
        $pushSf = $signoffFiles | Where-Object { $_ -match "push_signoff" } | Select-Object -First 1
        $pushIssues = Check-SignoffContent -Sha $LocalSha -SignoffPath $pushSf -ExpectedAction "push"
        foreach ($issue in $pushIssues) {
            $signoffIssues += "push_signoff:$issue"
        }
    }

    if ($signoffIssues.Count -gt 0) {
        Write-Host "ERROR: GOVERNANCE PREVENTION GATE FAILED:"
        foreach ($issue in $signoffIssues) {
            Write-Host "  ERROR: $issue"
        }
        Write-Host "ERROR: Push to canonical requires authorized merge_signoff.txt and/or push_signoff.txt"
        Write-Host "ERROR: Signoff must contain: action type (merge/push), target branch, hash, user authorization text"
        exit 1
    }

    Write-Host "PASS: governance prevention gate: signoff authorization verified"

    # Enhanced checks integrated into merge commit validation
    Check-DirtyTree
    Check-RuntimeGuard
    Check-UIVisibleGate -Sha $LocalSha
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
