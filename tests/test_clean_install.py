import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import database


class CleanInstallDatabaseTests(unittest.TestCase):
    def test_new_install_creates_empty_local_database_without_seed_accounts(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_directory = Path(temporary_directory) / "fresh-install" / "Data"
            with patch.dict(os.environ, {"SGD_DATA_DIR": str(data_directory)}):
                database.init_db()
                path = database.get_database_path()
                with closing(sqlite3.connect(path)) as connection:
                    accounts = connection.execute("SELECT nom FROM comptes").fetchall()
                    expenses = connection.execute("SELECT id FROM depenses").fetchall()
                    revenues = connection.execute("SELECT id FROM revenus").fetchall()

            self.assertTrue(path.is_file())
            self.assertEqual(accounts, [])
            self.assertEqual(expenses, [])
            self.assertEqual(revenues, [])

    def test_existing_install_database_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_directory = Path(temporary_directory) / "Data"
            data_directory.mkdir()
            expected_database = data_directory / "restaurant.db"
            with closing(sqlite3.connect(expected_database)) as connection:
                connection.execute("CREATE TABLE preserved (value TEXT NOT NULL)")
                connection.execute("INSERT INTO preserved VALUES ('keep existing data')")
                connection.commit()

            with patch.dict(os.environ, {"SGD_DATA_DIR": str(data_directory)}):
                database.init_db()
                with closing(sqlite3.connect(database.get_database_path())) as connection:
                    preserved = connection.execute("SELECT value FROM preserved").fetchone()
                    accounts = connection.execute("SELECT nom FROM comptes").fetchall()

            self.assertEqual(preserved, ("keep existing data",))
            self.assertEqual(accounts, [])

    def test_frozen_install_uses_writable_data_subdirectory_and_ignores_bundled_db(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            install_directory = Path(temporary_directory) / "SGD"
            install_directory.mkdir()
            bundled_database = install_directory / "restaurant.db"
            with closing(sqlite3.connect(bundled_database)) as connection:
                connection.execute("CREATE TABLE bundled (value TEXT)")
                connection.execute("INSERT INTO bundled VALUES ('must not be copied')")

            with patch.dict(os.environ, {"SGD_DATA_DIR": ""}):
                with patch.object(database.sys, "frozen", True, create=True), patch.object(
                    database.sys, "executable", str(install_directory / "GestionRestaurant.exe")
                ):
                    database.init_db()
                    installed_database = database.get_database_path()
                    with closing(sqlite3.connect(installed_database)) as connection:
                        tables = {
                            row[0]
                            for row in connection.execute(
                                "SELECT name FROM sqlite_master WHERE type='table'"
                            )
                        }
                        accounts = connection.execute("SELECT nom FROM comptes").fetchall()

            self.assertEqual(installed_database.resolve(), (install_directory / "Data" / "restaurant.db").resolve())
            self.assertNotIn("bundled", tables)
            self.assertEqual(accounts, [])
            self.assertTrue(bundled_database.is_file())

    def test_macos_install_uses_user_application_support_directory(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            home_directory = Path(temporary_directory)
            expected_database = (
                home_directory
                / "Library"
                / "Application Support"
                / "SGD"
                / "Data"
                / "restaurant.db"
            )
            with patch.dict(os.environ, {"SGD_DATA_DIR": ""}):
                with patch.object(database.sys, "platform", "darwin"), patch.object(
                    database.Path, "home", return_value=home_directory
                ):
                    database.init_db()
                    installed_database = database.get_database_path()

            self.assertEqual(installed_database, expected_database)
            self.assertTrue(installed_database.is_file())


if __name__ == "__main__":
    unittest.main()
