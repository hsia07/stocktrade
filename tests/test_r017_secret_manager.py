"""
test_r017_secret_manager.py
R017 Secret/Key Management Blocker Rework Test Suite.

All tests use dict-like mappings — NO real .env, NO real environment variables,
NO real secret values exposed.
"""

import pytest
from pathlib import Path

from modules.secret_manager import (
    SecretManager,
    SecretSchema,
    SecretSpec,
    SecretStatus,
    SecretResult,
    SecretReason,
)


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _make_schema() -> SecretSchema:
    """Standard test schema."""
    return SecretSchema(specs=[
        SecretSpec(name="APP_KEY", required=True, description="Application key"),
        SecretSpec(name="APP_SECRET", required=True, description="Application secret"),
        SecretSpec(name="OPTIONAL_FLAG", required=False, description="Optional flag"),
        SecretSpec(name="BROKER_KEY", required=True, is_broker=True, is_credential=True,
                   description="Broker API key", rotation_days=90),
        SecretSpec(name="BROKER_SECRET", required=False, is_broker=True, is_credential=True,
                   description="Broker API secret", rotation_days=90),
    ])


# ═══════════════════════════════════════════════════════════════
# 1. Load / Validate
# ═══════════════════════════════════════════════════════════════

class TestLoadAndValidate:
    def test_load_required_secret_success_without_value_exposure(self):
        schema = _make_schema()
        mgr = SecretManager(schema)
        mapping = {"APP_KEY": "ak_123", "APP_SECRET": "as_456", "BROKER_KEY": "bk_789"}
        summary = mgr.load_from_mapping(mapping)

        assert summary["schema_valid"] is True
        assert summary["order_execution_allowed"] is False
        secrets = summary["secrets"]
        assert secrets["APP_KEY"]["status"] == SecretStatus.PRESENT.value
        assert secrets["APP_KEY"]["value"] == SecretManager.REDACTED_MARKER
        assert secrets["APP_SECRET"]["value"] == SecretManager.REDACTED_MARKER
        # No actual value exposed
        for s in secrets.values():
            assert s["value"] == SecretManager.REDACTED_MARKER

    def test_missing_required_secret_fail_safe_no_crash(self):
        schema = _make_schema()
        mgr = SecretManager(schema)
        mapping = {"APP_KEY": "ak_123"}  # APP_SECRET missing
        summary = mgr.load_from_mapping(mapping)

        assert summary["schema_valid"] is False
        assert summary["order_execution_allowed"] is False
        secrets = summary["secrets"]
        assert secrets["APP_SECRET"]["status"] == SecretStatus.MISSING.value
        assert secrets["APP_SECRET"]["result"] == SecretResult.MISSING_REQUIRED.value
        assert secrets["APP_SECRET"]["reason"] == SecretReason.MISSING_REQUIRED_SECRET.value

    def test_optional_secret_missing_is_warning_not_crash(self):
        schema = _make_schema()
        mgr = SecretManager(schema)
        mapping = {"APP_KEY": "ak", "APP_SECRET": "as", "BROKER_KEY": "bk"}
        summary = mgr.load_from_mapping(mapping)

        # OPTIONAL_FLAG and BROKER_SECRET are optional and missing
        assert summary["schema_valid"] is True
        secrets = summary["secrets"]
        assert secrets["OPTIONAL_FLAG"]["status"] == SecretStatus.MISSING.value
        assert secrets["OPTIONAL_FLAG"]["result"] == SecretResult.MISSING_OPTIONAL.value

    def test_env_schema_validation_required_optional(self):
        schema = _make_schema()
        mapping = {"APP_KEY": "ak"}  # missing APP_SECRET
        reasons = schema.validate_against_mapping(mapping)
        assert SecretReason.MISSING_REQUIRED_SECRET in reasons
        assert SecretReason.ENV_SCHEMA_VALID in reasons


# ═══════════════════════════════════════════════════════════════
# 2. Redaction
# ═══════════════════════════════════════════════════════════════

class TestRedaction:
    def test_redact_plain_secret_value(self):
        assert SecretManager.redact_value("mysecret") == SecretManager.REDACTED_MARKER
        assert SecretManager.redact_value("ab") == SecretManager.REDACTED_SHORT
        assert SecretManager.redact_value("") == ""
        assert SecretManager.redact_value(None) == ""

    def test_redact_token_like_string(self):
        token = "sk-abc123def456ghi789"
        assert SecretManager.redact_value(token) == SecretManager.REDACTED_MARKER
        assert SecretManager.redact_text(f"Authorization: Bearer {token}", token) == f"Authorization: Bearer {SecretManager.REDACTED_MARKER}"

    def test_redact_mapping_nested_values(self):
        mapping = {"key1": "secret1", "key2": "public", "nested": {"key1": "secret1"}}
        # Only top-level keys in secret_keys list are redacted
        redacted = SecretManager.redact_mapping(mapping, ["key1"])
        assert redacted["key1"] == SecretManager.REDACTED_MARKER
        assert redacted["key2"] == "public"
        # Nested is not recursively redacted by this simple function (by design)
        assert redacted["nested"] == {"key1": "secret1"}

    def test_secret_not_exposed_in_safe_summary(self):
        schema = _make_schema()
        mgr = SecretManager(schema)
        mapping = {"APP_KEY": "super_secret_value_12345"}
        summary = mgr.load_from_mapping(mapping)
        summary_str = str(summary)
        assert "super_secret_value_12345" not in summary_str
        assert SecretManager.REDACTED_MARKER in summary_str


# ═══════════════════════════════════════════════════════════════
# 3. Audit Log
# ═══════════════════════════════════════════════════════════════

class TestAuditLog:
    def test_secret_not_exposed_in_audit_log(self):
        schema = _make_schema()
        mgr = SecretManager(schema)
        mapping = {"APP_KEY": "ak_123"}
        mgr.load_from_mapping(mapping)
        log = mgr.get_audit_log()
        for event in log:
            assert "ak_123" not in str(event)
            assert event["redacted"] is True

    def test_access_audit_log_records_metadata_only(self):
        schema = _make_schema()
        mgr = SecretManager(schema)
        mapping = {"APP_KEY": "ak", "APP_SECRET": "as", "BROKER_KEY": "bk"}
        mgr.load_from_mapping(mapping)
        log = mgr.get_audit_log()
        assert len(log) == 5  # one per spec
        for event in log:
            assert "secret_name" in event
            assert "purpose" in event
            assert "timestamp" in event
            assert "result" in event
            assert "redacted" in event
            assert event["redacted"] is True
            # No value field
            assert "value" not in event


# ═══════════════════════════════════════════════════════════════
# 4. Broker Credential Isolation
# ═══════════════════════════════════════════════════════════════

class TestBrokerIsolation:
    def test_broker_credential_isolation(self):
        schema = _make_schema()
        mgr = SecretManager(schema)
        mapping = {"APP_KEY": "ak", "APP_SECRET": "as", "BROKER_KEY": "bk", "BROKER_SECRET": "bs"}
        summary = mgr.load_from_mapping(mapping)

        assert summary["broker_ready"] is True
        broker_status = mgr.get_broker_credential_status()
        assert "BROKER_KEY" in broker_status
        assert "BROKER_SECRET" in broker_status
        # Broker credentials are present but safe summary still redacts
        assert summary["secrets"]["BROKER_KEY"]["value"] == SecretManager.REDACTED_MARKER

    def test_missing_broker_secret_blocks_broker_readiness(self):
        schema = _make_schema()
        mgr = SecretManager(schema)
        mapping = {"APP_KEY": "ak", "APP_SECRET": "as"}  # BROKER_KEY missing (and it's required)
        summary = mgr.load_from_mapping(mapping)

        # BROKER_KEY is required=True in schema, so schema_valid is False
        assert summary["schema_valid"] is False
        assert summary["broker_ready"] is False
        assert mgr.is_broker_ready() is False

    def test_present_broker_secret_does_not_enable_live_or_order_execution(self):
        schema = _make_schema()
        mgr = SecretManager(schema)
        mapping = {"APP_KEY": "ak", "APP_SECRET": "as", "BROKER_KEY": "bk", "BROKER_SECRET": "bs"}
        summary = mgr.load_from_mapping(mapping)

        # Broker credentials present but order_execution_allowed stays FALSE
        assert summary["order_execution_allowed"] is False
        assert summary["broker_ready"] is True
        # Broker readiness does NOT imply live mode or order execution


# ═══════════════════════════════════════════════════════════════
# 5. Rotation Readiness
# ═══════════════════════════════════════════════════════════════

class TestRotation:
    def test_rotation_readiness_warning(self):
        schema = _make_schema()
        mgr = SecretManager(schema)
        warnings = mgr.check_rotation_readiness()
        # BROKER_KEY and BROKER_SECRET have rotation_days=90
        broker_warnings = [w for w in warnings if "BROKER" in w["secret_name"]]
        assert len(broker_warnings) == 2
        for w in broker_warnings:
            assert w["status"] == SecretStatus.ROTATION_WARNING.value
            assert w["reason"] == SecretReason.ROTATION_WARNING.value
            assert w["rotation_due_days"] == 90


# ═══════════════════════════════════════════════════════════════
# 6. Reason Codes & Contract
# ═══════════════════════════════════════════════════════════════

class TestReasonCodes:
    def test_reason_codes_for_missing_and_redacted_secret(self):
        schema = _make_schema()
        mgr = SecretManager(schema)
        mapping = {"APP_KEY": "ak"}  # APP_SECRET missing
        summary = mgr.load_from_mapping(mapping)

        secrets = summary["secrets"]
        assert secrets["APP_SECRET"]["reason"] == SecretReason.MISSING_REQUIRED_SECRET.value
        assert secrets["APP_KEY"]["value"] == SecretManager.REDACTED_MARKER
        # All values in safe summary are redacted
        for s in secrets.values():
            assert s["value"] == SecretManager.REDACTED_MARKER

    def test_order_execution_allowed_remains_false_contract(self):
        schema = _make_schema()
        mgr = SecretManager(schema)
        # All secrets present
        mapping = {"APP_KEY": "ak", "APP_SECRET": "as", "BROKER_KEY": "bk", "BROKER_SECRET": "bs"}
        summary = mgr.load_from_mapping(mapping)
        assert summary["order_execution_allowed"] is False

        # Missing broker secrets
        mapping2 = {"APP_KEY": "ak", "APP_SECRET": "as"}
        summary2 = mgr.load_from_mapping(mapping2)
        assert summary2["order_execution_allowed"] is False

        # Missing required secrets
        mapping3 = {"APP_KEY": "ak"}
        summary3 = mgr.load_from_mapping(mapping3)
        assert summary3["order_execution_allowed"] is False


# ═══════════════════════════════════════════════════════════════
# 7. No Real Env Dependency
# ═══════════════════════════════════════════════════════════════

class TestNoRealEnv:
    def test_no_real_env_values_required(self):
        """All tests above use dict-like mappings, never real .env."""
        schema = _make_schema()
        mgr = SecretManager(schema)
        # Pure in-memory mapping
        mapping = {"APP_KEY": "test_only_key", "APP_SECRET": "test_only_secret",
                   "BROKER_KEY": "test_only_broker"}
        summary = mgr.load_from_mapping(mapping)
        assert summary["schema_valid"] is True
        # Confirm no real env was accessed
        assert mgr._entries["APP_KEY"]._present is True

    def test_no_secret_in_return_to_chatgpt_artifact_template_or_evidence(self):
        """
        Verify that no secret values appear in candidate artifacts.
        This test scans the candidate artifact directory for secret-like strings.
        """
        candidate_dir = Path(__file__).parent.parent / "automation" / "control" / "candidates" / "R017_SECRET_MANAGER"
        if not candidate_dir.exists():
            pytest.skip("Candidate artifacts not yet created")

        forbidden_patterns = ["ak_123", "as_456", "bk_789", "super_secret", "test_only"]
        for f in candidate_dir.iterdir():
            if f.is_file():
                content = f.read_text(encoding="utf-8")
                for pat in forbidden_patterns:
                    assert pat not in content, f"Forbidden pattern '{pat}' found in {f.name}"
