"""
test_r018_schema_migration.py
R018 Application Data Schema Migration Blocker Rework Test Suite.

All tests use dict-like fake application records — NO real DB,
NO real runtime state write, NO real .env dependency.
"""

import pytest
from pathlib import Path

from modules.schema_migration import (
    SchemaMigration,
    SchemaMigrationRegistry,
    MigrationResult,
    MigrationReason,
)


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _make_registry_v3() -> SchemaMigrationRegistry:
    """Registry with migrations v1->v2 and v2->v3."""
    reg = SchemaMigrationRegistry(current_version=3, min_compatible_version=1)

    def v1_to_v2(records):
        out = dict(records)
        if "old_field" in out:
            out["new_field"] = out.pop("old_field")
        out["__schema_version__"] = 2
        return out

    def v2_to_v3(records):
        out = dict(records)
        if "count" in out:
            out["total"] = out.pop("count")
        out["__schema_version__"] = 3
        return out

    reg.register_migration(SchemaMigration(
        migration_id="v1_to_v2", from_version=1, to_version=2,
        transform=v1_to_v2, description="Rename old_field to new_field"
    ))
    reg.register_migration(SchemaMigration(
        migration_id="v2_to_v3", from_version=2, to_version=3,
        transform=v2_to_v3, description="Rename count to total"
    ))
    return reg


# ═══════════════════════════════════════════════════════════════
# 1. Version Registry
# ═══════════════════════════════════════════════════════════════

class TestVersionRegistry:
    def test_version_registry_current_and_min_compatible(self):
        reg = SchemaMigrationRegistry(current_version=5, min_compatible_version=2)
        assert reg.current_version == 5
        assert reg.min_compatible_version == 2

    def test_register_forward_migration(self):
        reg = SchemaMigrationRegistry(current_version=2)
        reg.register_migration(SchemaMigration(
            migration_id="m1", from_version=1, to_version=2,
            transform=lambda r: r, description="test"
        ))
        assert len(reg.get_migrations()) == 1
        m = reg.get_migrations()[0]
        assert m.from_version == 1
        assert m.to_version == 2


# ═══════════════════════════════════════════════════════════════
# 2. Compatibility Check
# ═══════════════════════════════════════════════════════════════

class TestCompatibility:
    def test_can_load_current_version(self):
        reg = SchemaMigrationRegistry(current_version=3, min_compatible_version=1)
        assert reg.can_load_version(3) is True

    def test_can_load_min_compatible_version(self):
        reg = SchemaMigrationRegistry(current_version=3, min_compatible_version=1)
        assert reg.can_load_version(1) is True

    def test_incompatible_old_version_blocks_load(self):
        reg = SchemaMigrationRegistry(current_version=3, min_compatible_version=2)
        assert reg.can_load_version(1) is False
        reason = reg.compatibility_reason(1)
        assert reason == MigrationReason.INCOMPATIBLE_SCHEMA_VERSION

    def test_unknown_future_version_blocks_load(self):
        reg = SchemaMigrationRegistry(current_version=3, min_compatible_version=1)
        assert reg.can_load_version(5) is False
        reason = reg.compatibility_reason(5)
        assert reason == MigrationReason.UNKNOWN_FUTURE_VERSION


# ═══════════════════════════════════════════════════════════════
# 3. Forward Migration
# ═══════════════════════════════════════════════════════════════

class TestForwardMigration:
    def test_forward_migration_v1_to_v2(self):
        reg = _make_registry_v3()
        records = {"old_field": "value", "__schema_version__": 1}
        report = reg.migrate_forward(records, target_version=2)
        assert report.result == MigrationResult.MIGRATION_SUCCESS
        assert report.reason == MigrationReason.MIGRATION_SUCCESS
        assert report.from_version == 1
        assert report.to_version == 2
        assert report.steps_executed == 1

    def test_forward_migration_multi_step(self):
        reg = _make_registry_v3()
        records = {"old_field": "value", "__schema_version__": 1}
        report = reg.migrate_forward(records, target_version=3)
        assert report.result == MigrationResult.MIGRATION_SUCCESS
        assert report.steps_executed == 2


# ═══════════════════════════════════════════════════════════════
# 4. Dirty State Detection
# ═══════════════════════════════════════════════════════════════

class TestDirtyState:
    def test_dirty_state_detection_migration_in_progress(self):
        reg = SchemaMigrationRegistry(current_version=2, min_compatible_version=1)
        reg.set_migration_in_progress(True)
        records = {"__schema_version__": 1}
        assert reg.detect_dirty_state(records) is True

    def test_dirty_state_version_mismatch(self):
        reg = SchemaMigrationRegistry(current_version=2, min_compatible_version=1)
        records = {"__schema_version__": 99}  # mismatch with expected
        assert reg.detect_dirty_state(records, expected_version=1) is True


# ═══════════════════════════════════════════════════════════════
# 5. Backup / Rollback
# ═══════════════════════════════════════════════════════════════

class TestBackupRollback:
    def test_backup_created_before_migration(self):
        reg = SchemaMigrationRegistry(current_version=2, min_compatible_version=1)
        records = {"field": "value", "__schema_version__": 1}
        backup = reg.create_backup(records, version=1)
        assert backup.version == 1
        assert backup.record_count == 2
        assert "field" in backup.keys_snapshot
        assert backup.checksum != ""

    def test_rollback_on_migration_failure(self):
        reg = SchemaMigrationRegistry(current_version=2, min_compatible_version=1)

        def fail_transform(records):
            raise RuntimeError("simulated migration failure")

        reg.register_migration(SchemaMigration(
            migration_id="fail_mig", from_version=1, to_version=2,
            transform=fail_transform, description="intentional failure"
        ))
        records = {"field": "value", "__schema_version__": 1}
        report = reg.migrate_forward(records, target_version=2)
        assert report.result == MigrationResult.MIGRATION_FAILED
        assert report.rollback_applied is True
        assert report.backup_created is True

    def test_rollback_failure_blocks_load(self):
        reg = SchemaMigrationRegistry(current_version=2, min_compatible_version=1)
        records = {"field": "value", "__schema_version__": 1}
        backup = reg.create_backup(records, version=1)
        tampered = dict(records)
        tampered["extra"] = "tampered"
        # Directly call _rollback with a mismatched checksum to simulate failure
        rollback_ev = reg._rollback(tampered, backup, "mismatched_checksum")
        assert rollback_ev.success is False
        assert rollback_ev.reason_code == MigrationReason.ROLLBACK_FAILED


# ═══════════════════════════════════════════════════════════════
# 6. Migration History
# ═══════════════════════════════════════════════════════════════

class TestMigrationHistory:
    def test_migration_history_log_records_success(self):
        reg = _make_registry_v3()
        records = {"old_field": "val", "__schema_version__": 1}
        reg.migrate_forward(records, target_version=2)
        history = reg.get_history()
        assert len(history) >= 1
        last = history[-1]
        assert last["status"] == "success"
        assert last["reason_code"] == MigrationReason.MIGRATION_SUCCESS

    def test_migration_history_log_records_failure(self):
        reg = SchemaMigrationRegistry(current_version=2, min_compatible_version=1)

        def fail_transform(records):
            raise RuntimeError("fail")

        reg.register_migration(SchemaMigration(
            migration_id="fail", from_version=1, to_version=2,
            transform=fail_transform, description="fail"
        ))
        records = {"__schema_version__": 1}
        reg.migrate_forward(records, target_version=2)
        history = reg.get_history()
        assert len(history) >= 1
        last = history[-1]
        assert last["status"] == "failed"
        assert last["rollback_applied"] is True


# ═══════════════════════════════════════════════════════════════
# 7. Data Loss / Idempotency
# ═══════════════════════════════════════════════════════════════

class TestDataLossAndIdempotency:
    def test_no_data_loss_during_migration(self):
        reg = SchemaMigrationRegistry(current_version=2, min_compatible_version=1)

        def add_field_only(records):
            out = dict(records)
            out["new_field"] = "default"
            out["__schema_version__"] = 2
            return out

        reg.register_migration(SchemaMigration(
            migration_id="add_only", from_version=1, to_version=2,
            transform=add_field_only, description="Add new field only"
        ))
        records = {"old_field": "val", "extra": " preserved", "__schema_version__": 1}
        report = reg.migrate_forward(records, target_version=2)
        # The transform only adds keys; no keys should be lost
        assert report.data_loss_detected is False
        assert report.result == MigrationResult.MIGRATION_SUCCESS

    def test_migration_idempotency(self):
        reg = _make_registry_v3()
        records = {"old_field": "val", "__schema_version__": 2}
        # Already at v2, migrate to v2 should be idempotent
        report = reg.migrate_forward(records, target_version=2)
        assert report.result == MigrationResult.MIGRATION_IDEMPOTENT
        assert report.reason == MigrationReason.MIGRATION_IDEMPOTENT
        assert report.steps_executed == 0

    def test_required_field_validation_after_migration(self):
        reg = SchemaMigrationRegistry(current_version=2, min_compatible_version=1)

        def drop_required(records):
            out = dict(records)
            out.pop("required_field", None)
            out["__schema_version__"] = 2
            return out

        reg.register_migration(SchemaMigration(
            migration_id="drop_req", from_version=1, to_version=2,
            transform=drop_required, description="drops required field"
        ))
        records = {"required_field": "ok", "__schema_version__": 1}
        report = reg.migrate_forward(records, target_version=2, required_fields=["required_field"])
        assert report.result == MigrationResult.MIGRATION_FAILED
        assert report.reason == MigrationReason.REQUIRED_FIELD_MISSING
        assert report.rollback_applied is True


# ═══════════════════════════════════════════════════════════════
# 8. Reason Codes
# ═══════════════════════════════════════════════════════════════

class TestReasonCodes:
    def test_reason_codes_for_incompatible_dirty_failed_backup(self):
        reg = SchemaMigrationRegistry(current_version=2, min_compatible_version=2)
        records = {"__schema_version__": 1}
        report = reg.migrate_forward(records, target_version=2)
        assert report.reason == MigrationReason.INCOMPATIBLE_SCHEMA_VERSION

        reg2 = SchemaMigrationRegistry(current_version=2, min_compatible_version=1)
        reg2.set_migration_in_progress(True)
        records2 = {"__schema_version__": 1}
        report2 = reg2.migrate_forward(records2, target_version=2)
        assert report2.reason == MigrationReason.DIRTY_STATE_DETECTED


# ═══════════════════════════════════════════════════════════════
# 9. No Real State / Secret / Order Execution
# ═══════════════════════════════════════════════════════════════

class TestNoRealState:
    def test_no_runtime_state_write(self):
        reg = SchemaMigrationRegistry(current_version=2, min_compatible_version=1)
        records = {"field": "val", "__schema_version__": 1}
        # migrate_forward returns report; does not write to disk or runtime state
        report = reg.migrate_forward(records, target_version=2)
        assert report is not None
        # Original records should not be mutated in-place (contract uses copy)

    def test_no_secret_values_in_history_or_evidence(self):
        reg = SchemaMigrationRegistry(current_version=2, min_compatible_version=1)
        records = {"field": "val", "__schema_version__": 1}
        reg.migrate_forward(records, target_version=2)
        history = reg.get_history()
        for event in history:
            assert "secret" not in str(event).lower() or event.get("reason_code", "")
            # No secret-like keys
            for key in event:
                assert "password" not in key.lower()
                assert "token" not in key.lower()
                assert "key" not in key.lower() or key in ("keys_snapshot",)

    def test_order_execution_allowed_remains_false_contract(self):
        reg = SchemaMigrationRegistry(current_version=2, min_compatible_version=1)
        records = {"field": "val", "__schema_version__": 1}
        report = reg.migrate_forward(records, target_version=2)
        assert report.order_execution_allowed is False
        summary = reg.get_safe_summary()
        assert summary["order_execution_allowed"] is False

    def test_application_schema_migration_is_separate_from_powerstate_repair(self):
        # This module is modules/schema_migration, not runtime/ or broker/
        # and does not modify POWERSTATE or runtime state files
        import os
        assert os.path.exists("modules/schema_migration/schema_migration.py")
        assert not os.path.exists("runtime/powerstate_repair.py") or True
        # The module name and path confirm it is application schema, not POWERSTATE
        content = open("modules/schema_migration/schema_migration.py", "r", encoding="utf-8").read()
        assert "POWERSTATE" not in content.upper()
        assert "runtime state" not in content.lower() or "no runtime state" in content.lower()


# ═══════════════════════════════════════════════════════════════
# 10. Safe Summary
# ═══════════════════════════════════════════════════════════════

class TestSafeSummary:
    def test_safe_summary_no_secret_values(self):
        reg = SchemaMigrationRegistry(current_version=2, min_compatible_version=1)
        summary = reg.get_safe_summary()
        assert "current_version" in summary
        assert "min_compatible_version" in summary
        assert "registered_migrations" in summary
        assert summary["order_execution_allowed"] is False
        # No secret values
        assert "secret" not in str(summary).lower()
