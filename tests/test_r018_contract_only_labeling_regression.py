"""
test_r018_contract_only_labeling_regression.py
R018 Contract-Only Labeling Regression Tests.

Tests that R018 is correctly labeled as contract-only
(no runtime wiring, no DB write, no real migration runner).
These tests prevent future false-pass regression where R018
might be mislabeled as real runtime migration.

These tests read real files — they are NOT hardcoded.
"""

import json
import os
import pytest

CANONICAL_HEAD = "968d8a94935ab9f75496d7a0d73c4f2b07240908"
R018_MODULE_PATH = "modules/schema_migration/schema_migration.py"
R018_EVIDENCE_GLOB = "automation/control/candidates/R018_*/evidence.json"
CANDIDATE_ROUND_PATCH = "_governance/audit/round_patch_mapping.md"
CURRENT_ROUND_YAML = "manifests/current_round.yaml"


class TestR018ContractOnlyLabeling:
    def test_r018_module_is_contract_only_no_runtime_wiring(self):
        path = R018_MODULE_PATH
        assert os.path.exists(path), f"R018 module not found at {path}"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        contract_markers = [
            "Contract-only",
            "no runtime",
            "No runtime",
            "contract-level",
            "No DB",
            "no DB",
            "dict-like",
        ]
        found = any(m.lower() in content.lower() for m in contract_markers)
        assert found, (
            f"{path} must explicitly declare 'contract-only' or 'no runtime' or "
            "'contract-level' or 'no DB' — no runtime wiring, no DB access"
        )

    def test_r018_module_has_no_db_imports(self):
        path = R018_MODULE_PATH
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        db_keywords = [
            "import sqlite",
            "import psycopg",
            "import mysql",
            "import pymongo",
            "import redis",
            "import sqlalchemy",
            "import aiomysql",
            "import asyncpg",
            "import aioredis",
        ]
        for kw in db_keywords:
            assert kw not in content, (
                f"{path} must not import database drivers (found '{kw}'). "
                "R018 is contract-only."
            )

    def test_r018_module_has_no_file_io_for_state(self):
        path = R018_MODULE_PATH
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        lines = content.split("\n")
        for line in lines:
            lower = line.lower()
            if "open(" in line and ("w" in lower or "a" in lower or "+" in lower):
                assert False, (
                    f"{path} must not write to files for state persistence. "
                    f"Found: {line.strip()}"
                )
            if "json.dump(" in line and "open(" in line:
                assert False, (
                    f"{path} must not use json.dump to a file for state persistence. "
                    f"Found: {line.strip()}"
                )

    def test_r018_module_migrate_forward_returns_report_not_state(self):
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from modules.schema_migration import SchemaMigrationRegistry

        reg = SchemaMigrationRegistry(current_version=2, min_compatible_version=1)
        records = {"field": "val", "__schema_version__": 1}
        report = reg.migrate_forward(records, target_version=2)
        assert report is not None
        assert hasattr(report, "result")
        assert hasattr(report, "reason")
        assert hasattr(report, "order_execution_allowed")
        assert report.order_execution_allowed is False, (
            "migrate_forward must not set order_execution_allowed to True"
        )

    def test_r018_module_evidence_not_claiming_real_migration_completed(self):
        import glob
        evidence_files = glob.glob(R018_EVIDENCE_GLOB, recursive=True)
        assert len(evidence_files) > 0, f"No R018 evidence.json found via {R018_EVIDENCE_GLOB}"
        for ef in evidence_files:
            with open(ef, "r", encoding="utf-8") as f:
                d = json.load(f)
            summary = d.get("r018_original_claim_summary", "")
            if summary:
                real_migration_claims = [
                    "real migration completed",
                    "real runtime migration",
                    "real DB migration",
                    "live migration",
                    "runtime wiring completed",
                ]
                for claim in real_migration_claims:
                    if claim.lower() in summary.lower():
                        pytest.fail(
                            f"{ef} contains false-pass claim '{claim}' in "
                            "r018_original_claim_summary. R018 is contract-only."
                        )

    def test_r018_evidence_has_contract_only_fields(self):
        import glob
        our_candidate = "automation/control/candidates/R018_FALSE_PASS_REMEDIATION_CONTRACT_LABELING_REWORK_BEFORE_R049/evidence.json"
        all_evidence = glob.glob(R018_EVIDENCE_GLOB, recursive=True)
        other_evidence = [e for e in all_evidence if our_candidate not in e]
        for ef in other_evidence:
            with open(ef, "r", encoding="utf-8") as f:
                d = json.load(f)
            if "r018_contract_only" in d:
                assert d["r018_contract_only"] is True, (
                    f"{ef}: r018_contract_only must be True if present"
                )
                assert d.get("r018_no_runtime_execution") is True
                assert d.get("r018_no_db_write") is True
                assert d.get("r018_no_real_migration_runner") is True
                assert d.get("r018_not_r049_ready") is True

    def test_r018_tests_do_not_claim_live_or_runtime_or_db(self):
        path = "tests/test_r018_schema_migration.py"
        assert os.path.exists(path), f"R018 test file not found at {path}"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        forbidden_affirmative_claims = [
            "real DB write completed",
            "real runtime wiring done",
            "live migration executed",
            "db write executed",
            "production migration",
        ]
        for claim in forbidden_affirmative_claims:
            assert claim not in content.lower(), (
                f"{path} must not contain affirmative false claim '{claim}'. "
                "Tests must not imply R018 is a live/runtime/DB migration."
            )

    def test_r018_module_no_powerstate_references(self):
        path = R018_MODULE_PATH
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "POWERSTATE" not in content.upper(), (
            f"{path} must not reference POWERSTATE. "
            "R018 is application schema only."
        )

    def test_r018_safe_summary_order_execution_allowed_false(self):
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from modules.schema_migration import SchemaMigrationRegistry

        reg = SchemaMigrationRegistry(current_version=2, min_compatible_version=1)
        summary = reg.get_safe_summary()
        assert summary.get("order_execution_allowed") is False, (
            "get_safe_summary must always return order_execution_allowed=False"
        )

    def test_candidate_evidence_json_law_compliance_is_04_string(self):
        path = "automation/control/candidates/R018_FALSE_PASS_REMEDIATION_CONTRACT_LABELING_REWORK_BEFORE_R049/evidence.json"
        assert os.path.exists(path), f"Candidate evidence.json not found at {path}"
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        lc = d.get("law_compliance")
        assert isinstance(lc, str), f"law_compliance must be string, got {type(lc).__name__}"
        assert lc == "04", f"law_compliance must be '04', got {repr(lc)}"

    def test_candidate_evidence_json_has_all_required_contract_fields(self):
        path = "automation/control/candidates/R018_FALSE_PASS_REMEDIATION_CONTRACT_LABELING_REWORK_BEFORE_R049/evidence.json"
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        required_fields = [
            "r018_was_false_pass",
            "r018_contract_only",
            "r018_no_runtime_execution",
            "r018_no_db_write",
            "r018_no_real_migration_runner",
            "r018_not_r049_ready",
            "r018_historical_false_pass_preserved",
            "law_compliance",
        ]
        for field in required_fields:
            assert field in d, f"Candidate evidence must contain '{field}'"
        assert d["r018_was_false_pass"] is True
        assert d["r018_contract_only"] is True
        assert d["r018_no_runtime_execution"] is True
        assert d["r018_no_db_write"] is True
        assert d["r018_no_real_migration_runner"] is True
        assert d["r018_not_r049_ready"] is True
        assert d["r018_historical_false_pass_preserved"] is True
        assert d["law_compliance"] == "04"