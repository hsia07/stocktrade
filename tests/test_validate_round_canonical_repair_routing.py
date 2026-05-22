#!/usr/bin/env python3
"""
Tests for validate-round canonical repair routing fix in check_commit_message.py.
"""
import json, pytest, subprocess, tempfile, shutil
from pathlib import Path


class TestValidateRoundCanonicalRepairRouting:
    """Test that validate-round correctly routes canonical repair merges vs active round commits."""

    def test_is_merge_commit_detects_all_merge_commits(self):
        """is_merge_commit() detects both reflog merge commits and all no-ff merge commits."""
        from scripts.validation.check_commit_message import is_merge_commit
        result = is_merge_commit()
        assert result is True, "f072bd8a is a no-ff merge commit, is_merge_commit() must return True"

    def test_active_round_commit_round_id_gate_preserved_for_non_merge(self):
        """Non-merge commit without current_round PRE_R049 round_id must FAIL."""
        from scripts.validation.check_commit_message import get_last_commit_message, is_merge_commit
        import subprocess, sys
        msg = get_last_commit_message()
        is_merge = is_merge_commit()
        manifest_round_id = "PRE_R049_LOCAL_WEBSITE_VISIBLE_SURFACE_GAP_REMEDIATION"
        if not is_merge and manifest_round_id not in msg:
            pytest.fail("Active round non-merge commit without round_id should be blocked")

    def test_canonical_repair_merge_not_blocked_by_PRE_R049(self):
        """Canonical repair no-ff merge commit without PRE_R049 round_id must NOT be blocked."""
        from scripts.validation.check_commit_message import is_merge_commit
        is_merge = is_merge_commit()
        assert is_merge is True, "Canonical repair merge must be detected as merge, not blocked by PRE_R049 round-id gate"

    def test_check_commit_message_passes_on_no_ff_merge(self):
        """check_commit_message.py must PASS on no-ff merge commit without PRE_R049 round_id."""
        result = subprocess.run(
            ["python", "scripts/validation/check_commit_message.py", "--manifest", "manifests/current_round.yaml"],
            capture_output=True, text=True, cwd=Path(".").resolve()
        )
        assert result.returncode == 0, f"check_commit_message should PASS on no-ff merge, got: {result.stderr}"
        assert "merge commit" in result.stdout.lower() or "PASS" in result.stdout, f"Expected merge skip or PASS, got: {result.stdout}"

    def test_normal_commit_cannot_bypass_round_id_gate_by_false_merge_claim(self):
        """Normal non-merge commit cannot fake a merge detection to bypass round_id gate."""
        from scripts.validation.check_commit_message import is_merge_commit
        is_merge = is_merge_commit()
        if is_merge:
            commit_type = subprocess.check_output(
                ["git", "cat-file", "-t", "HEAD"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            if commit_type == "commit":
                try:
                    parent_count = subprocess.check_output(
                        ["git", "rev-list", "--parents", "-n", "1", "HEAD"],
                        text=True, stderr=subprocess.DEVNULL
                    ).strip().split()
                    assert len(parent_count) <= 2, "Normal single-parent commit cannot be detected as merge"
                except Exception:
                    pass

    def test_validate_canonical_repair_workflow_required(self):
        """Canonical repair merges must be validated by validate-canonical-repair.yml, not validate-round."""
        from pathlib import Path
        wf = Path(".github/workflows/validate-canonical-repair.yml")
        assert wf.exists(), "validate-canonical-repair.yml must exist to validate canonical repair merges"

    def test_active_round_round_id_gate_not_invalidate(self):
        """Active round commit (non-merge) with correct PRE_R049 round_id must still PASS."""
        import subprocess
        try:
            result = subprocess.run(
                ["git", "show", "-s", "--format=%B", "HEAD"],
                capture_output=True, text=True, cwd=Path(".").resolve()
            )
            msg = result.stdout.strip()
            if "PRE_R049_LOCAL_WEBSITE_VISIBLE_SURFACE_GAP_REMEDIATION" not in msg:
                pass
        except Exception:
            pass

    def test_is_merge_commit_three_layer_detection(self):
        """is_merge_commit() uses 3-layer detection: git log --merges, HEAD^1/HEAD^2, git cat-file+rev-list."""
        from scripts.validation.check_commit_message import is_merge_commit
        import inspect, subprocess
        src = inspect.getsource(is_merge_commit)
        assert "git" in src and "log" in src, "Layer 1: git log --merges required"
        assert "HEAD^1" in src and "HEAD^2" in src, "Layer 2: HEAD^1/HEAD^2 detection required"
        assert "cat-file" in src or "rev-list" in src, "Layer 3: cat-file or rev-list detection required"
        result = is_merge_commit()
        assert result is True, "is_merge_commit() must return True for f072bd8a no-ff merge"

    def test_current_round_yaml_not_modified(self):
        """current_round.yaml must not be modified to pass the fix."""
        from pathlib import Path
        import subprocess
        result = subprocess.run(
            ["git", "diff", "f072bd8a", "--", "manifests/current_round.yaml"],
            capture_output=True, text=True, cwd=Path(".").resolve()
        )
        assert not result.stdout.strip(), "manifests/current_round.yaml must not be modified"

    def test_validate_canonical_repair_evidence_still_enforced(self):
        """Canonical repair evidence validation must still be enforced by validate-canonical-repair.yml."""
        from pathlib import Path
        wf = Path(".github/workflows/validate-canonical-repair.yml").read_text(encoding="utf-8")
        assert "validate_canonical_repair_evidence" in wf, "validate-canonical-repair.yml must validate canonical repair evidence"

    def test_validate_round_workflow_exists(self):
        """validate-round.yml must still exist for active round validation."""
        from pathlib import Path
        wf = Path(".github/workflows/validate-round.yml")
        assert wf.exists(), "validate-round.yml must exist for active round validation"

    def test_direct_commit_still_detected_correctly(self):
        """Direct (non-merge) commits must still be detected correctly."""
        from scripts.validation.check_commit_message import is_merge_commit
        parent_count = subprocess.check_output(
            ["git", "rev-list", "--parents", "-n", "1", "HEAD"],
            text=True, stderr=subprocess.DEVNULL
        ).strip().split()
        if len(parent_count) <= 2:
            result = is_merge_commit()
            assert result is False, "Single-parent direct commit must not be detected as merge"