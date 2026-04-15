param(
  [string]$RepoRoot = ".",
  [string]$ManifestPath = "automation/current_round.yaml"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location $RepoRoot
Write-Host "[scheduler] fetch latest"
git fetch --all --prune

Write-Host "[scheduler] run validation"
python scripts/validate_round.py --manifest $ManifestPath
python scripts/check_forbidden_changes.py --manifest $ManifestPath
python scripts/check_required_evidence.py --manifest $ManifestPath

Write-Host "[scheduler] done"
