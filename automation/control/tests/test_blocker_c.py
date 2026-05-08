"""
BLOCKER_C runtime tests: NEA round-scoped auto-injection registry.

Verifies:
- Each active round has its own scoped injection sections
- roadmap_only rounds are NOT in the active injection map
- inject_into_scaffold correctly enriches scaffolds
- No cross-round contamination
- Machine-checkable verification works
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from automation.control.round_injection_registry import (
    ROUND_INJECTION_MAP,
    ROADMAP_ONLY_INJECTIONS,
    get_round_injection,
    is_roadmap_only,
    get_all_active_round_ids,
    inject_into_scaffold,
    verify_injection,
    verify_no_cross_round_contamination,
)


class TestInjectionMap:
    """Round-scoped injection map integrity."""

    def test_blocker_c_has_injection(self) -> None:
        injection = get_round_injection("BLOCKER_C")
        assert injection is not None
        assert len(injection["mandatory_sections"]) > 0
        assert injection["roadmap_only"] is False

    def test_blocker_d_has_injection(self) -> None:
        injection = get_round_injection("BLOCKER_D")
        assert injection is not None
        assert len(injection["mandatory_sections"]) > 0
        assert injection["roadmap_only"] is False

    def test_auto_advance_operational_has_injection(self) -> None:
        injection = get_round_injection("AUTO_ADVANCE_OPERATIONAL")
        assert injection is not None
        assert injection["roadmap_only"] is False

    def test_unknown_round_returns_none(self) -> None:
        assert get_round_injection("NONEXISTENT") is None

    def test_case_insensitive(self) -> None:
        assert get_round_injection("blocker_c") is not None
        assert get_round_injection("Blocker_C") is not None

    def test_roadmap_only_not_in_active_map(self) -> None:
        for rid in ROADMAP_ONLY_INJECTIONS:
            assert rid not in ROUND_INJECTION_MAP, (
                f"roadmap_only round {rid} must not be in active injection map"
            )

    def test_roadmap_only_detected(self) -> None:
        assert is_roadmap_only("AUTO_ADVANCE_V0_2") is True
        assert is_roadmap_only("AUTO_ADVANCE_V1_0") is True
        assert is_roadmap_only("BLOCKER_C") is False
        assert is_roadmap_only("BLOCKER_D") is False
        assert is_roadmap_only("AUTO_ADVANCE_OPERATIONAL") is False

    def test_active_rounds_non_empty(self) -> None:
        active = get_all_active_round_ids()
        assert len(active) >= 3
        assert "BLOCKER_C" in active
        assert "BLOCKER_D" in active
        assert "AUTO_ADVANCE_OPERATIONAL" in active


class TestScopedInjection:
    """Injections must be round-scoped, not global."""

    def test_blocker_c_and_d_have_different_sections(self) -> None:
        """Each round must have DIFFERENT, non-overlapping sections."""
        c_inj = get_round_injection("BLOCKER_C")
        d_inj = get_round_injection("BLOCKER_D")
        assert c_inj is not None
        assert d_inj is not None
        c_sections = set(c_inj["mandatory_sections"])
        d_sections = set(d_inj["mandatory_sections"])
        assert c_sections != d_sections, (
            "BLOCKER_C and BLOCKER_D must have different sections"
        )
        assert c_sections.isdisjoint(d_sections), (
            "No section should be shared between BLOCKER_C and BLOCKER_D"
        )

    def test_blocker_c_and_auto_advance_have_different_sections(self) -> None:
        c_inj = get_round_injection("BLOCKER_C")
        a_inj = get_round_injection("AUTO_ADVANCE_OPERATIONAL")
        assert c_inj is not None
        assert a_inj is not None
        c_sections = set(c_inj["mandatory_sections"])
        a_sections = set(a_inj["mandatory_sections"])
        assert c_sections.isdisjoint(a_sections), (
            "BLOCKER_C and AUTO_ADVANCE_OPERATIONAL must not share sections"
        )

    def test_roadmap_and_active_sections_disjoint(self) -> None:
        """Active round sections must not overlap with roadmap-only sections."""
        active_sections = set()
        for rid, inj in ROUND_INJECTION_MAP.items():
            active_sections.update(inj.get("mandatory_sections", []))

        roadmap_sections = set()
        for rid, inj in ROADMAP_ONLY_INJECTIONS.items():
            roadmap_sections.update(inj.get("mandatory_sections", []))

        assert active_sections.isdisjoint(roadmap_sections), (
            "Active and roadmap-only sections must be disjoint"
        )


class TestInjectIntoscaffold:
    """inject_into_scaffold behavior."""

    def test_inject_blocker_c(self, tmp_path: Path) -> None:
        scaffold_dir = tmp_path / "scaffold"
        scaffold_dir.mkdir()
        result = inject_into_scaffold(scaffold_dir, "BLOCKER_C")
        assert result["injection_applied"] is True
        assert result["roadmap_only_skipped"] is False
        assert result["cross_round_injection"] is False
        assert len(result["injected_sections"]) > 0
        assert result["merge_executed"] is False
        assert result["push_executed"] is False
        assert result["promote_executed"] is False
        assert result["pr_created"] is False

    def test_inject_creates_files(self, tmp_path: Path) -> None:
        scaffold_dir = tmp_path / "scaffold"
        scaffold_dir.mkdir()
        inject_into_scaffold(scaffold_dir, "BLOCKER_C")
        assert (scaffold_dir / "task.txt").exists()
        assert (scaffold_dir / "evidence.json").exists()

    def test_inject_evidence_content(self, tmp_path: Path) -> None:
        scaffold_dir = tmp_path / "scaffold"
        scaffold_dir.mkdir()
        inject_into_scaffold(scaffold_dir, "BLOCKER_C")
        ev = json.loads(
            (scaffold_dir / "evidence.json").read_text(encoding="utf-8")
        )
        assert ev["injection_applied"] is True
        assert ev["cross_round_injection"] is False
        assert ev["roadmap_only_injected"] is False
        assert ev["merge_blocked"] is True
        assert ev["push_blocked"] is True
        assert ev["promote_blocked"] is True

    def test_roadmap_only_skipped(self, tmp_path: Path) -> None:
        scaffold_dir = tmp_path / "scaffold"
        scaffold_dir.mkdir()
        result = inject_into_scaffold(scaffold_dir, "AUTO_ADVANCE_V0_2")
        assert result["injection_applied"] is False
        assert result["roadmap_only_skipped"] is True

    def test_unknown_round_skipped(self, tmp_path: Path) -> None:
        scaffold_dir = tmp_path / "scaffold"
        scaffold_dir.mkdir()
        result = inject_into_scaffold(scaffold_dir, "NONEXISTENT")
        assert result["injection_applied"] is False
        assert "no_injection_defined_for_round" in result.get("reason", "")

    def test_inject_enriches_existing_scaffold(self, tmp_path: Path) -> None:
        scaffold_dir = tmp_path / "scaffold"
        scaffold_dir.mkdir()
        (scaffold_dir / "task.txt").write_text("=== EXISTING ===\n", encoding="utf-8")
        (scaffold_dir / "evidence.json").write_text(
            json.dumps({"round_id": "BLOCKER_C"}), encoding="utf-8"
        )
        result = inject_into_scaffold(scaffold_dir, "BLOCKER_C")
        assert result["injection_applied"] is True
        task = (scaffold_dir / "task.txt").read_text(encoding="utf-8")
        assert "EXISTING" in task
        assert "Injected mandatory sections" in task

    def test_inject_blocker_d_different_from_c(self, tmp_path: Path) -> None:
        """BLOCKER_D scaffold should get different sections than BLOCKER_C."""
        c_dir = tmp_path / "scaffold_c"
        c_dir.mkdir()
        d_dir = tmp_path / "scaffold_d"
        d_dir.mkdir()
        c_result = inject_into_scaffold(c_dir, "BLOCKER_C")
        d_result = inject_into_scaffold(d_dir, "BLOCKER_D")
        assert c_result["injected_sections"] != d_result["injected_sections"], (
            "BLOCKER_C and BLOCKER_D injections must differ"
        )


class TestVerifyInjection:
    """Machine-checkable injection verification."""

    def test_verify_valid_injection(self, tmp_path: Path) -> None:
        scaffold_dir = tmp_path / "scaffold"
        scaffold_dir.mkdir()
        inject_into_scaffold(scaffold_dir, "BLOCKER_C")
        valid, issues = verify_injection(scaffold_dir, "BLOCKER_C")
        assert valid is True, f"Expected valid, got issues={issues}"
        assert len(issues) == 0

    def test_verify_valid_blocker_d(self, tmp_path: Path) -> None:
        scaffold_dir = tmp_path / "scaffold"
        scaffold_dir.mkdir()
        inject_into_scaffold(scaffold_dir, "BLOCKER_D")
        valid, issues = verify_injection(scaffold_dir, "BLOCKER_D")
        assert valid is True, f"Expected valid, got issues={issues}"

    def test_verify_missing_scaffold_fails(self, tmp_path: Path) -> None:
        scaffold_dir = tmp_path / "nonexistent"
        valid, issues = verify_injection(scaffold_dir, "BLOCKER_C")
        assert valid is False
        assert any("scaffold_missing" in i for i in issues)

    def test_verify_no_cross_contamination(self, tmp_path: Path) -> None:
        scaffold_dir = tmp_path / "scaffold"
        scaffold_dir.mkdir()
        inject_into_scaffold(scaffold_dir, "BLOCKER_C")
        valid, issues = verify_no_cross_round_contamination(
            scaffold_dir, "BLOCKER_C"
        )
        assert valid is True, f"Expected no contamination, got issues={issues}"

    def test_verify_no_cross_contamination_blocker_d(self, tmp_path: Path) -> None:
        scaffold_dir = tmp_path / "scaffold"
        scaffold_dir.mkdir()
        inject_into_scaffold(scaffold_dir, "BLOCKER_D")
        valid, issues = verify_no_cross_round_contamination(
            scaffold_dir, "BLOCKER_D"
        )
        assert valid is True, f"Expected no contamination, got issues={issues}"

    def test_verify_blocker_d_not_contaminated_by_c(self, tmp_path: Path) -> None:
        """BLOCKER_D scaffold must not contain BLOCKER_C sections."""
        d_dir = tmp_path / "d_scaffold"
        d_dir.mkdir()
        inject_into_scaffold(d_dir, "BLOCKER_D")
        ev = json.loads(
            (d_dir / "evidence.json").read_text(encoding="utf-8")
        )
        c_injection = get_round_injection("BLOCKER_C")
        c_sections = set(c_injection["mandatory_sections"])
        d_sections = set(ev.get("injected_sections", []))
        assert c_sections.isdisjoint(d_sections), (
            "BLOCKER_D scaffold must not contain any BLOCKER_C sections"
        )
