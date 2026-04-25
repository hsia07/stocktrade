"""
R018 Schema Migration - Migration Manager

Orchestrates schema upgrades and downgrades with backup and validation.
"""

import logging
from typing import Callable, Dict, List, Optional, Any
from pathlib import Path

from automation.schema.version import SchemaVersionRegistry
from automation.schema.backup import SchemaBackupManager

logger = logging.getLogger("schema.migration")

MigrationFunc = Callable[[Any], None]


class SchemaMigrationManager:
    """Manage database schema migrations with upgrade/downgrade support."""

    def __init__(self, db_path: str, backup_dir: Optional[str] = None):
        self.db_path = db_path
        self.registry = SchemaVersionRegistry(db_path)
        self.backup = SchemaBackupManager(db_path, backup_dir)
        self._migrations: Dict[int, Dict[str, Any]] = {}

    def register(self, version: int, upgrade: MigrationFunc,
                 downgrade: Optional[MigrationFunc] = None,
                 name: str = ""):
        """Register a migration."""
        self._migrations[version] = {
            "upgrade": upgrade,
            "downgrade": downgrade,
            "name": name or f"migration_v{version}",
        }

    def get_current_version(self) -> int:
        return self.registry.get_current_version()

    def get_target_versions(self) -> List[int]:
        """Return sorted list of registered migration versions."""
        return sorted(self._migrations.keys())

    def migrate(self, target_version: Optional[int] = None) -> bool:
        """
        Migrate to target version. If None, migrates to latest.
        Returns True on success.
        """
        current = self.get_current_version()
        targets = self.get_target_versions()

        if target_version is None:
            target_version = max(targets) if targets else 0

        if current == target_version:
            logger.info(f"Already at version {current}")
            return True

        if target_version > current:
            return self._upgrade(current, target_version, targets)
        else:
            return self._downgrade(current, target_version, targets)

    def _upgrade(self, current: int, target: int, targets: List[int]) -> bool:
        """Execute upgrade migrations."""
        for version in targets:
            if current < version <= target:
                if not self._apply_migration(version, "upgrade"):
                    return False
        return True

    def _downgrade(self, current: int, target: int, targets: List[int]) -> bool:
        """Execute downgrade migrations in reverse order."""
        for version in reversed(targets):
            if target < version <= current:
                if not self._apply_migration(version, "downgrade"):
                    return False
        return True

    def _apply_migration(self, version: int, direction: str) -> bool:
        """Apply a single migration with backup and validation."""
        migration = self._migrations.get(version)
        if not migration:
            logger.error(f"Migration v{version} not registered")
            return False

        func = migration.get(direction)
        if not func:
            logger.error(f"No {direction} for v{version}")
            return False

        # Create backup before migration
        try:
            backup_path = self.backup.create_backup(version)
        except Exception as e:
            logger.error(f"Backup failed for v{version}: {e}")
            return False

        try:
            # Execute migration
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            func(conn)
            conn.commit()
            conn.close()

            if direction == "upgrade":
                self.registry.record_migration(
                    version, migration["name"],
                    rollback_available=migration.get("downgrade") is not None
                )
            else:
                self.registry.remove_version_record(version)

            logger.info(f"Applied {direction} v{version}: {migration['name']}")
            return True

        except Exception as e:
            logger.error(f"Migration v{version} failed: {e}")
            # Attempt rollback to backup
            try:
                self.backup.restore_backup(backup_path)
                logger.info(f"Restored backup after failed migration v{version}")
            except Exception as restore_err:
                logger.error(f"Restore failed: {restore_err}")
            return False

    def validate_schema(self) -> bool:
        """Run integrity check on the database."""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            result = conn.execute("PRAGMA integrity_check").fetchone()[0]
            conn.close()
            valid = result == "ok"
            if not valid:
                logger.error(f"Schema integrity check failed: {result}")
            return valid
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Return current migration status."""
        return {
            "current_version": self.get_current_version(),
            "registered_versions": self.get_target_versions(),
            "history": self.registry.get_migration_history(),
            "backups": self.backup.list_backups(),
            "integrity_check": self.validate_schema(),
        }
