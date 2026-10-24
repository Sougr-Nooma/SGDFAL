import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from unittest.mock import Mock, patch

import database
from main import App


class PasswordRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict(
            os.environ,
            {"SGD_DATA_DIR": self.temporary_directory.name},
        )
        self.environment.start()
        database._recovery_codes.clear()
        database.init_db()
        with closing(sqlite3.connect(database.get_database_path())) as connection:
            with connection:
                connection.execute(
                    "INSERT INTO comptes (nom, email, mot_de_passe) VALUES (?, ?, ?)",
                    ("tester", "tester@example.com", database._hash_password("old-password")),
                )

    def tearDown(self):
        database._recovery_codes.clear()
        self.environment.stop()
        self.temporary_directory.cleanup()

    def test_password_changes_only_after_matching_email_and_verified_code(self):
        self.assertFalse(database.create_recovery_code("tester", "wrong@example.com", "123456"))
        self.assertTrue(database.create_recovery_code("tester", "tester@example.com", "123456"))
        self.assertFalse(database.reset_password("tester", "tester@example.com", "new-password"))
        self.assertFalse(database.verify_recovery_code("tester", "tester@example.com", "000000"))
        self.assertTrue(database.verify_recovery_code("tester", "tester@example.com", "123456"))
        self.assertFalse(database.reset_password("tester", "wrong@example.com", "new-password"))
        self.assertTrue(database.reset_password("tester", "tester@example.com", "new-password"))
        with closing(sqlite3.connect(database.get_database_path())) as connection:
            stored_password = connection.execute(
                "SELECT mot_de_passe FROM comptes WHERE nom = ?", ("tester",)
            ).fetchone()[0]
        self.assertFalse(database._verify_password("old-password", stored_password))
        self.assertTrue(database._verify_password("new-password", stored_password))

    def test_recovery_code_is_limited_to_five_attempts(self):
        self.assertTrue(database.create_recovery_code("tester", "tester@example.com", "123456"))
        for _ in range(5):
            self.assertFalse(database.verify_recovery_code("tester", "tester@example.com", "000000"))
        self.assertFalse(database.verify_recovery_code("tester", "tester@example.com", "123456"))

    def test_settings_password_change_uses_the_same_email_recovery_flow(self):
        app = App.__new__(App)
        app.ouvrir_recuperation_mot_de_passe = Mock()
        parent = object()

        app.ouvrir_changement_mot_de_passe("tester", parent)

        app.ouvrir_recuperation_mot_de_passe.assert_called_once_with("tester", parent)


if __name__ == "__main__":
    unittest.main()
