# PowerShell pre-push hook for Windows environment
# Replaces bash-based hook for cross-platform compatibility

$ErrorActionPreference = "Stop"

$MANIFEST_PATH = "manifests\current_round.yaml"
$GOV_MANIFEST_PATH = "manifests\governance_round.yaml"

$LAST_MSG = git log -1 --pretty=%B 2>$null

Write-Host "[pre-push] run strict validation"

if ($LAST_MSG -match "^GOV-[A-Z0-9_-]+:") {
    Write-Host "[pre-push] governance commit detected, using governance manifest"
    $MANIFEST_PATH = $GOV_MANIFEST_PATH
}

$scripts = @(
    ".\scripts\validation\validate_round.py",
    ".\scripts\validation\check_forbidden_changes.py",
    ".\scripts\validation\check_required_evidence.py",
    ".\scripts\validation\check_commit_message.py"
)

foreach ($script in $scripts) {
    Write-Host "[pre-push] running $script"
    & python $script --manifest $MANIFEST_PATH
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[pre-push] FAILED: $script returned non-zero"
        exit 1
    }
}

Write-Host "[pre-push] ok"
exit 0