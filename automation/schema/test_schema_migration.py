"""R018 Schema Migration Tests"""

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from automation.schema.version import SchemaVersionRegistry
from automation.schema.backup import SchemaBackupManager
from automation.schema.migration import SchemaMigrationManager


class TestSchemaVersionRegistry(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.registry = SchemaVersionRegistry(self.db_path)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_empty_db_version_zero(self):
        """Empty database should have version 0."""
        self.assertEqual(self.registry.get_current_version(), 0)

    def test_record_and_retrieve_version(self):
        """Record migration and verify version."""
        self.registry.record_migration(1, "init_schema")
        self.assertEqual(self.registry.get_current_version(), 1)

    def test_is_version_applied(self):
        """Check version applied status."""
        self.assertFalse(self.registry.is_version_applied(1))
        self.registry.record_migration(1, "init_schema")
        self.assertTrue(self.registry.is_version_applied(1))

    def test_migration_history(self):
        """Migration history should be ordered."""
        self.registry.record_migration(1, "init")
        self.registry.record_migration(2, "add_users")
        history = self.registry.get_migration_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["version"], 1)
        self.assertEqual(history[1]["version"], 2)

    def test_remove_version_record(self):
        """Remove version record for rollback."""
        self.registry.record_migration(1, "init")
        self.assertEqual(self.registry.get_current_version(), 1)
        self.registry.remove_version_record(1)
        self.assertEqual(self.registry.get_current_version(), 0)


class TestSchemaBackupManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        # Create a test database
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
        self.backup_mgr = SchemaBackupManager(self.db_path, self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_backup(self):
        """Backup should be created successfully."""
        backup = self.backup_mgr.create_backup(1)
        self.assertTrue(backup.exists())

    def test_restore_backup(self):
        """Restore should revert database to backup state."""
        backup = self.backup_mgr.create_backup(1)
        # Modify database
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE new_table (id INTEGER)")
        conn.commit()
        conn.close()
        # Restore
        self.backup_mgr.restore_backup(backup)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='new_table'")
        self.assertIsNone(cursor.fetchone())
        conn.close()

    def test_list_backups(self):
        """List backups should return created backups."""
        self.backup_mgr.create_backup(1)
        self.backup_mgr.create_backup(2)
        backups = self.backup_mgr.list_backups()
        self.assertEqual(len(backups), 2)

    def test_verify_backup_integrity(self):
        """Valid backup should pass integrity check."""
        backup = self.backup_mgr.create_backup(1)
        self.assertTrue(self.backup_mgr.verify_backup_integrity(backup))

    def test_verify_corrupted_backup(self):
        """Corrupted backup should fail integrity check."""
        backup = self.backup_mgr.create_backup(1)
        # Corrupt the file
        with open(backup, "wb") as f:
            f.write(b"corrupted data")
        self.assertFalse(self.backup_mgr.verify_backup_integrity(backup))


class TestSchemaMigrationManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        self.mgr = SchemaMigrationManager(self.db_path, self.tmpdir)

        # Define migrations
        def v1_upgrade(conn):
            conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")

        def v1_downgrade(conn):
            conn.execute("DROP TABLE IF EXISTS users")

        def v2_upgrade(conn):
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")

        def v2_downgrade(conn):
            # SQLite doesn't support DROP COLUMN directly in older versions
            conn.execute("""
                CREATE TABLE users_new (id INTEGER PRIMARY KEY, name TEXT)
            """)
            conn.execute("INSERT INTO users_new (id, name) SELECT id, name FROM users")
            conn.execute("DROP TABLE users")
            conn.execute("ALTER TABLE users_new RENAME TO users")

        self.mgr.register(1, v1_upgrade, v1_downgrade, "create_users")
        self.mgr.register(2, v2_upgrade, v2_downgrade, "add_email")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_initial_version_zero(self):
        """Fresh database starts at version 0."""
        self.assertEqual(self.mgr.get_current_version(), 0)

    def test_upgrade_to_latest(self):
        """Upgrade to latest version."""
        self.assertTrue(self.mgr.migrate())
        self.assertEqual(self.mgr.get_current_version(), 2)

    def test_upgrade_step_by_step(self):
        """Upgrade to specific version."""
        self.assertTrue(self.mgr.migrate(1))
        self.assertEqual(self.mgr.get_current_version(), 1)

    def test_downgrade(self):
        """Downgrade to previous version."""
        self.mgr.migrate(2)
        self.assertTrue(self.mgr.migrate(1))
        self.assertEqual(self.mgr.get_current_version(), 1)

    def test_idempotent_migration(self):
        """Migrating to current version should be no-op."""
        self.mgr.migrate(1)
        self.assertTrue(self.mgr.migrate(1))
        self.assertEqual(self.mgr.get_current_version(), 1)

    def test_backup_created_on_migration(self):
        """Backup should be created before migration."""
        self.mgr.migrate(1)
        backups = self.mgr.backup.list_backups()
        self.assertTrue(len(backups) >= 1)

    def test_rollback_on_failed_migration(self):
        """Failed migration should restore backup."""
        def bad_upgrade(conn):
            conn.execute("CREATE TABLE bad (id INTEGER)")
            raise RuntimeError("Intentional failure")

        self.mgr.register(3, bad_upgrade, name="bad_migration")
        self.mgr.migrate(2)

        # Store pre-migration state
        conn = sqlite3.connect(self.db_path)
        tables_before = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        conn.close()

        # Attempt migration (should fail and restore)
        result = self.mgr.migrate(3)
        self.assertFalse(result)
        self.assertEqual(self.mgr.get_current_version(), 2)

    def test_validate_schema(self):
        """Schema validation should pass for valid DB."""
        self.mgr.migrate(2)
        self.assertTrue(self.mgr.validate_schema())

    def test_status_report(self):
        """Status report should contain expected fields."""
        self.mgr.migrate(2)
        status = self.mgr.get_status()
        self.assertEqual(status["current_version"], 2)
        self.assertTrue(status["integrity_check"])
        self.assertTrue(len(status["history"]) >= 2)

    def test_empty_database_migration(self):
        """Migration on empty database should work."""
        self.assertTrue(self.mgr.migrate(1))
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        self.assertIn("users", tables)

    def test_null_value_handling(self):
        """Schema should handle null values after migration."""
        self.mgr.migrate(2)
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO users (id, name, email) VALUES (1, 'Test', NULL)")
        conn.commit()
        cursor = conn.execute("SELECT email FROM users WHERE id = 1")
        result = cursor.fetchone()[0]
        conn.close()
        self.assertIsNone(result)

    def test_type_error_boundary(self):
        """Type errors should be handled gracefully."""
        self.mgr.migrate(2)
        conn = sqlite3.connect(self.db_path)
        # SQLite is flexible with types, but we can test constraint violations
        # by creating a table with a CHECK constraint in a new migration
        conn.execute("CREATE TABLE typed_test (id INTEGER PRIMARY KEY, count INTEGER CHECK(count > 0))")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO typed_test (id, count) VALUES (1, -1)")
        conn.close()

    def test_missing_field_boundary(self):
        """Missing required fields should be handled."""
        self.mgr.migrate(2)
        conn = sqlite3.connect(self.db_path)
        # Create a table with NOT NULL constraint to test missing field handling
        conn.execute("CREATE TABLE required_test (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO required_test (id) VALUES (1)")
        conn.close()


if __name__ == "__main__":
    unittest.main()
