param(
  [string]$RepoRoot = ".",
  [string]$ManifestPath = "manifests/current_round.yaml"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location $RepoRoot
Write-Host "[scheduler] fetch latest"
git fetch --all --prune

Write-Host "[scheduler] run validation"
py ./scripts/validation/validate_round.py --manifest $ManifestPath
py ./scripts/validation/check_forbidden_changes.py --manifest $ManifestPath
py ./scripts/validation/check_required_evidence.py --manifest $ManifestPath
py ./scripts/validation/check_commit_message.py --manifest $ManifestPath

Write-Host "[scheduler] done"
