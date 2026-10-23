"""Opt-in MySQL checks. Only generated, disposable databases are created/deleted."""

import os
from pathlib import Path
import re
import tempfile
import unittest
from uuid import uuid4

import bcrypt
import pymysql

from app import create_app
from tests import TEST_CONFIG


@unittest.skipUnless(os.environ.get("RUN_MYSQL_TESTS") == "1", "Set RUN_MYSQL_TESTS=1 for disposable MySQL checks")
class MySQLTests(unittest.TestCase):
    def setUp(self):
        self.connection = pymysql.connect(
            host=os.environ.get("MYSQL_TEST_HOST", "127.0.0.1"),
            port=int(os.environ.get("MYSQL_TEST_PORT", "3306")),
            user=os.environ["MYSQL_TEST_USER"],
            password=os.environ["MYSQL_TEST_PASSWORD"],
            charset="utf8mb4",
            autocommit=True,
        )
        self.database = "library_setup_test_" + uuid4().hex
        self.addCleanup(self.connection.close)
        self.addCleanup(self.drop_test_database)
        self.root = Path(__file__).resolve().parents[2]

    def drop_test_database(self):
        # Never accept a user/database setting as a deletion target.
        if not re.fullmatch(r"library_setup_test_[0-9a-f]{32}", self.database):
            raise ValueError("Refusing to delete a non-test database")
        with self.connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{self.database}`")

    def execute_script(self, path, original_database):
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"--[^\n]*", "", text)
        text = re.sub(rf"\b{original_database}\b", self.database, text)
        with self.connection.cursor() as cursor:
            # shortcut: fixtures have no semicolons in strings; use a SQL parser if that changes.
            for statement in text.split(";"):
                if statement.strip():
                    cursor.execute(statement)

    def test_company_seed_and_foreign_keys(self):
        self.execute_script(self.root / "problem1_DDL.sql", "company")
        self.execute_script(self.root / "problem1_DML.sql", "company")
        with self.connection.cursor() as cursor:
            for table in ("EMPLOYEE", "DEPARTMENT", "PROJECT"):
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                self.assertGreaterEqual(cursor.fetchone()[0], 3)
            cursor.execute("SELECT COUNT(*) FROM EMPLOYEE WHERE Dno IS NULL")
            self.assertEqual(cursor.fetchone()[0], 0)
            cursor.execute("INSERT INTO DEPARTMENT VALUES (4, 'Audit test', '100000001', '2026-01-01')")
            with self.assertRaises(pymysql.IntegrityError):
                cursor.execute("DELETE FROM EMPLOYEE WHERE ssn = '100000001'")
            with self.assertRaises(pymysql.IntegrityError):
                cursor.execute("INSERT INTO PROJECT VALUES (104, 'Invalid', 'Test', 999)")

    def test_real_registration_login_and_logout(self):
        self.execute_script(self.root / "website/database/auth.sql", "registration")
        with tempfile.TemporaryDirectory() as directory:
            app = create_app({
                **TEST_CONFIG,
                "DB_HOST": os.environ.get("MYSQL_TEST_HOST", "127.0.0.1"),
                "DB_PORT": os.environ.get("MYSQL_TEST_PORT", "3306"),
                "DB_USER": os.environ["MYSQL_TEST_USER"],
                "DB_PASSWORD": os.environ["MYSQL_TEST_PASSWORD"],
                "AUTH_DB_NAME": self.database,
                "SESSION_FILE_DIR": directory,
            })
            client = app.test_client()

            def token(path):
                self.assertEqual(client.get(path).status_code, 200)
                with client.session_transaction() as session:
                    return session["csrf_token"]

            data = {"name": "<script>test</script>", "email": "audit@example.com",
                    "password": "test-password", "confirm_password": "test-password"}
            response = client.post("/register", data={**data, "csrf_token": token("/register")})
            self.assertEqual(response.location, "/")
            home = client.get("/")
            self.assertIn(b"&lt;script&gt;test&lt;/script&gt;", home.data)
            self.assertNotIn(b"<script>test</script>", home.data)
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT password_hash FROM users WHERE email = %s", (data["email"],))
                self.assertTrue(bcrypt.checkpw(b"test-password", cursor.fetchone()[0].encode()))
            with client.session_transaction() as session:
                logout_token = session["csrf_token"]
            self.assertEqual(client.post("/logout", data={"csrf_token": logout_token}).location, "/login")
            self.assertEqual(client.get("/").location, "/login")
            response = client.post("/login", data={**data, "csrf_token": token("/login")})
            self.assertEqual(response.location, "/")
            self.assertEqual(client.get("/").status_code, 200)
            response = client.post("/register", data={**data, "csrf_token": token("/register")})
            self.assertIn(b"Email already exists", response.data)
