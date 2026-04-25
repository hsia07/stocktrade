"""
R018 Schema Migration - Backup Manager

Creates pre-migration backups with restore capability.
"""

import shutil
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger("schema.backup")


class SchemaBackupManager:
    """Create and manage database backups before migrations."""

    BACKUP_SUFFIX = ".backup"

    def __init__(self, db_path: str, backup_dir: Optional[str] = None):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir) if backup_dir else self.db_path.parent

    def create_backup(self, version: int) -> Path:
        """Create a backup before migrating to version."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.db_path.stem}_v{version}_{timestamp}{self.BACKUP_SUFFIX}{self.db_path.suffix}"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(self.db_path, backup_path)

        # Verify backup integrity
        if not backup_path.exists():
            raise RuntimeError(f"Backup creation failed: {backup_path}")

        logger.info(f"Created backup: {backup_path}")
        return backup_path

    def restore_backup(self, backup_path: Path):
        """Restore database from backup."""
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        shutil.copy2(backup_path, self.db_path)
        logger.info(f"Restored from backup: {backup_path}")

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups for this database."""
        pattern = f"{self.db_path.stem}_v*_*{self.BACKUP_SUFFIX}{self.db_path.suffix}"
        backups = []
        for backup in self.backup_dir.glob(pattern):
            stat = backup.stat()
            backups.append({
                "path": str(backup),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            })
        return sorted(backups, key=lambda x: x["modified"], reverse=True)

    def verify_backup_integrity(self, backup_path: Path) -> bool:
        """Verify backup file is readable and non-empty."""
        try:
            if not backup_path.exists() or backup_path.stat().st_size == 0:
                return False
            # Quick SQLite integrity check
            import sqlite3
            conn = sqlite3.connect(str(backup_path))
            conn.execute("PRAGMA integrity_check").fetchone()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Backup integrity check failed: {e}")
            return False
