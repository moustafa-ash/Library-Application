import tempfile
import unittest
from unittest.mock import MagicMock, patch

import bcrypt
import pymysql
from app import create_app

from tests import TEST_CONFIG


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.session_dir = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                **TEST_CONFIG,
                "SESSION_FILE_DIR": self.session_dir.name,
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.session_dir.cleanup()

    def token(self, path="/login"):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as session:
            return session["csrf_token"]

    def database(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        cursor = connection.cursor.return_value.__enter__.return_value
        return connection, cursor

    def test_home_requires_login_and_templates_render(self):
        self.assertEqual(self.client.get("/").location, "/login")
        for path in ("/login", "/register"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'name="csrf_token"', response.data)
            self.assertNotIn(b"to-do", response.data.lower())
        self.assertEqual(self.client.get("/missing").status_code, 404)
        self.assertEqual(self.client.get("/logout").status_code, 405)

    def test_csrf_rejects_missing_and_invalid_tokens_before_database_access(self):
        with patch("app.auth.get_connection") as connect:
            for path in ("/login", "/register", "/logout"):
                self.assertEqual(self.client.post(path).status_code, 400)
                self.assertEqual(
                    self.client.post(path, data={"csrf_token": "bad"}).status_code, 400
                )
            connect.assert_not_called()

    def test_registration_validation_preserves_text_but_never_passwords(self):
        token = self.token("/register")
        with patch("app.auth.get_connection") as connect:
            response = self.client.post(
                "/register",
                data={
                    "csrf_token": token,
                    "name": "Moustafa",
                    "email": "invalid",
                    "password": "private-password",
                    "confirm_password": "different",
                },
            )
            self.assertIn(b"valid email", response.data)
            self.assertIn(b"Passwords do not match", response.data)
            self.assertIn(b'value="Moustafa"', response.data)
            self.assertNotIn(b"private-password", response.data)
            connect.assert_not_called()

    def test_multibyte_password_limit_is_checked_before_hashing(self):
        token = self.token("/register")
        with patch("app.auth.get_connection") as connect:
            response = self.client.post(
                "/register",
                data={
                    "csrf_token": token,
                    "name": "Student",
                    "email": "student@example.com",
                    "password": "é" * 37,
                    "confirm_password": "é" * 37,
                },
            )
            self.assertIn(b"72 bytes", response.data)
            connect.assert_not_called()

    def test_registration_hashes_password_commits_and_rotates_session(self):
        token = self.token("/register")
        before = self.client.get_cookie("session").value
        connection, cursor = self.database()
        cursor.lastrowid = 7
        salt = bcrypt.gensalt(rounds=4)
        with (
            patch("app.auth.get_connection", return_value=connection) as connect,
            patch("app.auth.bcrypt.gensalt", return_value=salt),
        ):
            response = self.client.post(
                "/register",
                data={
                    "csrf_token": token,
                    "name": "Moustafa",
                    "email": "student@example.com",
                    "password": "safe-password",
                    "confirm_password": "safe-password",
                },
            )
        self.assertEqual(response.location, "/")
        connect.assert_called_once_with("test_registration")
        query, values = cursor.execute.call_args.args
        self.assertIn("VALUES (%s, %s, %s)", query)
        self.assertTrue(bcrypt.checkpw(b"safe-password", values[2].encode()))
        connection.commit.assert_called_once()
        self.assertNotEqual(before, self.client.get_cookie("session").value)
        with self.client.session_transaction() as session:
            self.assertEqual(session["user_id"], 7)
            self.assertNotIn("csrf_token", session)
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_login_uses_parameters_and_rejects_wrong_password(self):
        token = self.token()
        connection, cursor = self.database()
        cursor.fetchone.return_value = {
            "user_id": 9,
            "name": "Student",
            "password_hash": bcrypt.hashpw(
                b"correct", bcrypt.gensalt(rounds=4)
            ).decode(),
        }
        with patch("app.auth.get_connection", return_value=connection):
            response = self.client.post(
                "/login",
                data={
                    "csrf_token": token,
                    "email": "' OR 1=1 --",
                    "password": "wrong",
                },
            )
        self.assertIn(b"Invalid email or password", response.data)
        self.assertEqual(cursor.execute.call_args.args[1], ("' OR 1=1 --",))
        with self.client.session_transaction() as session:
            self.assertNotIn("user_id", session)

    def test_login_logout_and_csrf_rotation(self):
        token = self.token()
        before = self.client.get_cookie("session").value
        connection, cursor = self.database()
        cursor.fetchone.return_value = {
            "user_id": 9,
            "name": "Student",
            "password_hash": bcrypt.hashpw(
                b"correct", bcrypt.gensalt(rounds=4)
            ).decode(),
        }
        with patch("app.auth.get_connection", return_value=connection):
            response = self.client.post(
                "/login",
                data={
                    "csrf_token": token,
                    "email": "student@example.com",
                    "password": "correct",
                },
            )
        self.assertEqual(response.location, "/")
        self.assertNotEqual(before, self.client.get_cookie("session").value)
        self.assertEqual(
            self.client.post("/logout", data={"csrf_token": token}).status_code, 400
        )
        self.client.get("/")
        with self.client.session_transaction() as session:
            new_token = session["csrf_token"]
        self.assertEqual(
            self.client.post("/logout", data={"csrf_token": new_token}).location,
            "/login",
        )
        self.assertEqual(self.client.get("/").location, "/login")

    def test_duplicate_email_and_database_errors_are_safe(self):
        token = self.token("/register")
        data = {
            "csrf_token": token,
            "name": "Student",
            "email": "student@example.com",
            "password": "safe",
            "confirm_password": "safe",
        }
        with patch(
            "app.auth.get_connection",
            side_effect=pymysql.IntegrityError(1062, "private detail"),
        ):
            response = self.client.post("/register", data=data)
        self.assertIn(b"Email already exists", response.data)
        with (
            patch(
                "app.auth.get_connection",
                side_effect=pymysql.OperationalError(1045, "private detail"),
            ),
            self.assertLogs(self.app.logger, level="ERROR"),
        ):
            response = self.client.post("/login", data=data)
        self.assertIn(b"Unable to log in", response.data)
        self.assertNotIn(b"private detail", response.data)


if __name__ == "__main__":
    unittest.main()
