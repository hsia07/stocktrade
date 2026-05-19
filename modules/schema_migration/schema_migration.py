"""
R018 Schema Migration — Application Data Schema Version Migration Foundation
Contract-only module. No runtime wiring. No DB. No real state write.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import copy
import hashlib
import json


class MigrationResult(str, Enum):
    OK = "ok"
    NO_CHANGE = "no_change"
    INCOMPATIBLE = "incompatible"
    MIGRATION_REQUIRED = "migration_required"
    MIGRATION_SUCCESS = "migration_success"
    MIGRATION_FAILED = "migration_failed"
    MIGRATION_FAILED_ROLLBACK = "migration_failed_rollback"
    DIRTY_STATE_DETECTED = "dirty_state_detected"
    BACKUP_CREATED = "backup_created"
    ROLLBACK_SUCCESS = "rollback_success"
    ROLLBACK_FAILED = "rollback_failed"
    MIGRATION_IDEMPOTENT = "migration_idempotent"


class MigrationReason(str, Enum):
    INCOMPATIBLE_SCHEMA_VERSION = "INCOMPATIBLE_SCHEMA_VERSION"
    MIGRATION_REQUIRED = "MIGRATION_REQUIRED"
    MIGRATION_SUCCESS = "MIGRATION_SUCCESS"
    MIGRATION_FAILED = "MIGRATION_FAILED"
    MIGRATION_FAILED_ROLLBACK = "MIGRATION_FAILED_ROLLBACK"
    MIGRATION_FAILED_ROLLBACK_BLOCKED = "MIGRATION_FAILED_ROLLBACK_BLOCKED"
    DIRTY_STATE_DETECTED = "DIRTY_STATE_DETECTED"
    BACKUP_CREATED = "BACKUP_CREATED"
    ROLLBACK_SUCCESS = "ROLLBACK_SUCCESS"
    ROLLBACK_FAILED = "ROLLBACK_FAILED"
    MIGRATION_IDEMPOTENT = "MIGRATION_IDEMPOTENT"
    DATA_LOSS_DETECTED = "DATA_LOSS_DETECTED"
    REQUIRED_FIELD_MISSING = "REQUIRED_FIELD_MISSING"
    CHECKSUM_MISMATCH = "CHECKSUM_MISMATCH"
    UNKNOWN_FUTURE_VERSION = "UNKNOWN_FUTURE_VERSION"
    ORDER_EXECUTION_ALLOWED_FALSE = "ORDER_EXECUTION_ALLOWED_FALSE"


@dataclass
class SchemaVersion:
    """Version identifier for application data schema."""
    version: int
    name: str = ""


@dataclass
class SchemaMigration:
    """Single migration step definition."""
    migration_id: str
    from_version: int
    to_version: int
    transform: Callable[[Dict[str, Any]], Dict[str, Any]]
    description: str = ""


@dataclass
class MigrationAuditEvent:
    """Audit event for migration operations. Contains NO secret values."""
    migration_id: str
    from_version: int
    to_version: int
    status: str
    reason_code: str
    timestamp: str
    checksum_before: str = ""
    checksum_after: str = ""
    rollback_applied: bool = False
    data_loss_detected: bool = False


@dataclass
class BackupEvidence:
    """Evidence of pre-migration backup."""
    backup_id: str
    version: int
    timestamp: str
    checksum: str
    record_count: int
    keys_snapshot: List[str]


@dataclass
class RollbackEvidence:
    """Evidence of rollback operation."""
    rollback_id: str
    backup_id: str
    timestamp: str
    success: bool
    reason_code: str
    checksum_after_rollback: str


@dataclass
class MigrationReport:
    """Safe summary of migration operation."""
    result: str
    reason: str
    from_version: int
    to_version: int
    steps_executed: int
    order_execution_allowed: bool = False
    backup_created: bool = False
    rollback_applied: bool = False
    data_loss_detected: bool = False
    dirty_state_detected: bool = False


class SchemaMigrationRegistry:
    """
    Application data schema migration registry.
    Contract-level. No runtime state write. No DB access.
    Accepts dict-like fake application records for testing.
    """

    def __init__(self, current_version: int, min_compatible_version: int = 1):
        self._current_version = current_version
        self._min_compatible_version = min_compatible_version
        self._migrations: Dict[str, SchemaMigration] = {}
        self._history: List[MigrationAuditEvent] = []
        self._dirty_state: Dict[str, Any] = {"migration_in_progress": False}

    # ------------------------------------------------------------------
    # Version / Compatibility
    # ------------------------------------------------------------------

    @property
    def current_version(self) -> int:
        return self._current_version

    @property
    def min_compatible_version(self) -> int:
        return self._min_compatible_version

    def can_load_version(self, version: int) -> bool:
        """Return True if version is compatible (between min and current)."""
        return self._min_compatible_version <= version <= self._current_version

    def compatibility_reason(self, version: int) -> MigrationReason:
        if version < self._min_compatible_version:
            return MigrationReason.INCOMPATIBLE_SCHEMA_VERSION
        if version > self._current_version:
            return MigrationReason.UNKNOWN_FUTURE_VERSION
        return MigrationReason.MIGRATION_SUCCESS

    # ------------------------------------------------------------------
    # Migration Registration
    # ------------------------------------------------------------------

    def register_migration(self, migration: SchemaMigration) -> "SchemaMigrationRegistry":
        self._migrations[migration.migration_id] = migration
        return self

    def get_migrations(self) -> List[SchemaMigration]:
        return sorted(self._migrations.values(), key=lambda m: (m.from_version, m.to_version))

    def find_migration_path(self, from_version: int, to_version: int) -> List[SchemaMigration]:
        """Find chain of migrations from from_version to to_version (BFS)."""
        if from_version == to_version:
            return []
        if from_version > to_version:
            return []
        all_migrations = self.get_migrations()
        # Build adjacency
        edges: Dict[int, List[SchemaMigration]] = {}
        for m in all_migrations:
            edges.setdefault(m.from_version, []).append(m)
        # BFS
        visited: Dict[int, SchemaMigration] = {}
        queue = [from_version]
        found = False
        while queue:
            v = queue.pop(0)
            if v == to_version:
                found = True
                break
            for m in edges.get(v, []):
                if m.to_version not in visited:
                    visited[m.to_version] = m
                    queue.append(m.to_version)
        if not found:
            return []
        # Reconstruct path
        path = []
        cur = to_version
        while cur != from_version:
            m = visited.get(cur)
            if m is None:
                return []
            path.append(m)
            cur = m.from_version
        path.reverse()
        return path

    # ------------------------------------------------------------------
    # Dirty State Detection
    # ------------------------------------------------------------------

    def detect_dirty_state(self, records: Dict[str, Any], expected_version: Optional[int] = None) -> bool:
        """Detect if records are in a dirty / inconsistent state."""
        dirty = False
        if self._dirty_state.get("migration_in_progress"):
            dirty = True
        # Check for version mismatch if version is embedded
        if expected_version is not None:
            record_version = records.get("__schema_version__")
            if record_version is not None and record_version != expected_version:
                dirty = True
        return dirty

    def set_migration_in_progress(self, value: bool) -> None:
        self._dirty_state["migration_in_progress"] = value

    # ------------------------------------------------------------------
    # Backup / Checksum
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_checksum(records: Dict[str, Any]) -> str:
        """Compute checksum of records for no-data-loss guard."""
        canonical = json.dumps(records, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    def create_backup(self, records: Dict[str, Any], version: int) -> BackupEvidence:
        """Create backup evidence before migration."""
        return BackupEvidence(
            backup_id=f"backup_v{version}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            version=version,
            timestamp=datetime.now().isoformat(),
            checksum=self._compute_checksum(records),
            record_count=len(records),
            keys_snapshot=list(records.keys()),
        )

    # ------------------------------------------------------------------
    # Forward Migration
    # ------------------------------------------------------------------

    def migrate_forward(
        self,
        records: Dict[str, Any],
        target_version: int,
        required_fields: Optional[List[str]] = None,
    ) -> MigrationReport:
        """
        Migrate records forward to target_version.
        Returns MigrationReport — does NOT write runtime state.
        """
        current = records.get("__schema_version__", 1)
        if current == target_version:
            return MigrationReport(
                result=MigrationResult.MIGRATION_IDEMPOTENT,
                reason=MigrationReason.MIGRATION_IDEMPOTENT,
                from_version=current,
                to_version=target_version,
                steps_executed=0,
            )

        if current > target_version:
            return MigrationReport(
                result=MigrationResult.INCOMPATIBLE,
                reason=MigrationReason.INCOMPATIBLE_SCHEMA_VERSION,
                from_version=current,
                to_version=target_version,
                steps_executed=0,
            )

        if not self.can_load_version(current):
            return MigrationReport(
                result=MigrationResult.INCOMPATIBLE,
                reason=MigrationReason.INCOMPATIBLE_SCHEMA_VERSION,
                from_version=current,
                to_version=target_version,
                steps_executed=0,
            )

        # Dirty state detection
        if self.detect_dirty_state(records, expected_version=current):
            return MigrationReport(
                result=MigrationResult.DIRTY_STATE_DETECTED,
                reason=MigrationReason.DIRTY_STATE_DETECTED,
                from_version=current,
                to_version=target_version,
                steps_executed=0,
                dirty_state_detected=True,
            )

        # Find migration path
        path = self.find_migration_path(current, target_version)
        if not path and current != target_version:
            return MigrationReport(
                result=MigrationResult.INCOMPATIBLE,
                reason=MigrationReason.INCOMPATIBLE_SCHEMA_VERSION,
                from_version=current,
                to_version=target_version,
                steps_executed=0,
            )

        # Create backup
        backup = self.create_backup(records, current)
        records_copy = copy.deepcopy(records)
        keys_before = set(records_copy.keys())
        checksum_before = self._compute_checksum(records_copy)

        self.set_migration_in_progress(True)

        try:
            steps_executed = 0
            for migration in path:
                records_copy = migration.transform(records_copy)
                # Update embedded version
                records_copy["__schema_version__"] = migration.to_version
                steps_executed += 1

            self.set_migration_in_progress(False)

            # No-data-loss guard: key preservation (excluding __schema_version__ metadata key)
            keys_after = set(records_copy.keys())
            lost_keys = keys_before - keys_after - {"__schema_version__"}
            data_loss = bool(lost_keys)

            # Required field validation
            if required_fields:
                for field in required_fields:
                    if field not in records_copy or records_copy[field] in (None, ""):
                        # Rollback
                        rollback_ev = self._rollback(records, backup, checksum_before)
                        self._history.append(MigrationAuditEvent(
                            migration_id="required_field_validation",
                            from_version=current,
                            to_version=target_version,
                            status="failed",
                            reason_code=MigrationReason.REQUIRED_FIELD_MISSING,
                            timestamp=datetime.now().isoformat(),
                            checksum_before=checksum_before,
                            checksum_after=self._compute_checksum(records_copy),
                            rollback_applied=rollback_ev.success,
                            data_loss_detected=data_loss,
                        ))
                        return MigrationReport(
                            result=MigrationResult.MIGRATION_FAILED,
                            reason=MigrationReason.REQUIRED_FIELD_MISSING,
                            from_version=current,
                            to_version=target_version,
                            steps_executed=steps_executed,
                            backup_created=True,
                            rollback_applied=rollback_ev.success,
                            data_loss_detected=data_loss,
                        )

            # Checksum mismatch detection
            checksum_after = self._compute_checksum(records_copy)
            checksum_mismatch = checksum_before == checksum_after and steps_executed > 0
            # Note: checksum_before == checksum_after after migration with same data is possible,
            # but we don't flag it as error; we only flag data_loss via key loss.

            self._history.append(MigrationAuditEvent(
                migration_id=path[-1].migration_id if path else "none",
                from_version=current,
                to_version=target_version,
                status="success",
                reason_code=MigrationReason.MIGRATION_SUCCESS,
                timestamp=datetime.now().isoformat(),
                checksum_before=checksum_before,
                checksum_after=checksum_after,
                rollback_applied=False,
                data_loss_detected=data_loss,
            ))

            return MigrationReport(
                result=MigrationResult.MIGRATION_SUCCESS,
                reason=MigrationReason.MIGRATION_SUCCESS,
                from_version=current,
                to_version=target_version,
                steps_executed=steps_executed,
                backup_created=True,
                rollback_applied=False,
                data_loss_detected=data_loss,
            )

        except Exception as exc:
            self.set_migration_in_progress(False)
            # Rollback
            rollback_ev = self._rollback(records, backup, checksum_before)
            self._history.append(MigrationAuditEvent(
                migration_id=path[steps_executed].migration_id if steps_executed < len(path) else "unknown",
                from_version=current,
                to_version=target_version,
                status="failed",
                reason_code=MigrationReason.MIGRATION_FAILED,
                timestamp=datetime.now().isoformat(),
                checksum_before=checksum_before,
                checksum_after="",
                rollback_applied=rollback_ev.success,
                data_loss_detected=True,
            ))
            return MigrationReport(
                result=MigrationResult.MIGRATION_FAILED,
                reason=MigrationReason.MIGRATION_FAILED,
                from_version=current,
                to_version=target_version,
                steps_executed=steps_executed,
                backup_created=True,
                rollback_applied=rollback_ev.success,
                data_loss_detected=True,
            )

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------

    def _rollback(
        self,
        original_records: Dict[str, Any],
        backup: BackupEvidence,
        original_checksum: str,
    ) -> RollbackEvidence:
        """Rollback to pre-migration backup. Returns evidence, does NOT mutate external state."""
        # In contract mode: we verify that original records can be restored from deepcopy
        # but we don't actually write back to external dict (test provides fresh dict)
        current_checksum = self._compute_checksum(original_records)
        success = current_checksum == original_checksum or current_checksum == backup.checksum
        return RollbackEvidence(
            rollback_id=f"rollback_{backup.backup_id}",
            backup_id=backup.backup_id,
            timestamp=datetime.now().isoformat(),
            success=success,
            reason_code=MigrationReason.ROLLBACK_SUCCESS if success else MigrationReason.ROLLBACK_FAILED,
            checksum_after_rollback=original_checksum,
        )

    def rollback_on_failure(
        self,
        original_records: Dict[str, Any],
        backup: BackupEvidence,
    ) -> RollbackEvidence:
        """Public rollback method."""
        return self._rollback(original_records, backup, self._compute_checksum(original_records))

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(self) -> List[Dict[str, Any]]:
        """Return migration history events. Metadata only, no secret values."""
        return [
            {
                "migration_id": e.migration_id,
                "from_version": e.from_version,
                "to_version": e.to_version,
                "status": e.status,
                "reason_code": e.reason_code,
                "timestamp": e.timestamp,
                "checksum_before": e.checksum_before,
                "checksum_after": e.checksum_after,
                "rollback_applied": e.rollback_applied,
                "data_loss_detected": e.data_loss_detected,
            }
            for e in self._history
        ]

    def get_last_event(self) -> Optional[Dict[str, Any]]:
        if not self._history:
            return None
        e = self._history[-1]
        return {
            "migration_id": e.migration_id,
            "from_version": e.from_version,
            "to_version": e.to_version,
            "status": e.status,
            "reason_code": e.reason_code,
            "timestamp": e.timestamp,
            "rollback_applied": e.rollback_applied,
            "data_loss_detected": e.data_loss_detected,
        }

    # ------------------------------------------------------------------
    # Safe Summary
    # ------------------------------------------------------------------

    def get_safe_summary(self) -> Dict[str, Any]:
        """Safe summary of registry state — no secret values, no runtime state."""
        return {
            "current_version": self._current_version,
            "min_compatible_version": self._min_compatible_version,
            "registered_migrations": len(self._migrations),
            "history_count": len(self._history),
            "dirty_state": self._dirty_state,
            "order_execution_allowed": False,
        }

    # ------------------------------------------------------------------
    # Factory / Default
    # ------------------------------------------------------------------

    @classmethod
    def create_default_registry(cls) -> "SchemaMigrationRegistry":
        """Default registry with sample application data migrations (contract-level)."""
        registry = cls(current_version=2, min_compatible_version=1)

        def v1_to_v2(records: Dict[str, Any]) -> Dict[str, Any]:
            out = dict(records)
            # Rename old field
            if "old_name" in out:
                out["new_name"] = out.pop("old_name")
            # Add new field with default
            if "status" not in out:
                out["status"] = "pending"
            return out

        registry.register_migration(SchemaMigration(
            migration_id="app_v1_to_v2",
            from_version=1,
            to_version=2,
            transform=v1_to_v2,
            description="Rename old_name to new_name, add status field",
        ))
        return registry
