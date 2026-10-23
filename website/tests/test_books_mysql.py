"""Opt-in real BOOK checks; AUTHOR exists only as a disposable test fixture."""

from decimal import Decimal
import os
from pathlib import Path
import re
import tempfile
import unittest
from uuid import uuid4

import pymysql

from app import create_app
from app.config import load_config, validate_config
from app.db import get_connection
from tests.test_images import upload


@unittest.skipUnless(os.environ.get("RUN_BOOK_MYSQL_TESTS") == "1",
                     "Set RUN_BOOK_MYSQL_TESTS=1 for disposable book MySQL checks")
class BookMySQLTests(unittest.TestCase):
    def setUp(self):
        config = load_config()
        for key in ("HOST", "PORT", "USER", "PASSWORD"):
            if "MYSQL_TEST_" + key in os.environ:
                config["DB_" + key] = os.environ["MYSQL_TEST_" + key]
        config["SECRET_KEY"] = "disposable-book-tests-only"
        validate_config(config)
        self.database = "library_books_test_" + uuid4().hex
        self.admin = pymysql.connect(host=config["DB_HOST"], port=config["DB_PORT"],
            user=config["DB_USER"], password=config["DB_PASSWORD"], charset="utf8mb4", autocommit=True)
        self.addCleanup(self.admin.close)
        self.addCleanup(self.drop_database)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        with self.admin.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE `{self.database}` CHARACTER SET utf8mb4")
            cursor.execute(f"USE `{self.database}`")
            # Fixture only: does not implement Ibrahim's production schema or seed work.
            cursor.execute("CREATE TABLE AUTHOR (author_id INT PRIMARY KEY AUTO_INCREMENT, "
                           "name VARCHAR(100) NOT NULL, country VARCHAR(100)) ENGINE=InnoDB")
            cursor.execute("INSERT INTO AUTHOR VALUES (1, 'Test author A', 'Test'), "
                           "(2, 'Test author B', 'Test'), (3, 'Test author C', 'Test')")
            for name in ("problem2_DDL.sql", "problem2_DML.sql"):
                script = (Path(__file__).resolve().parents[2] / name).read_text(encoding="utf-8")
                script = re.sub(r"--[^\n]*", "", script)
                script = re.sub(r"\blibrary\b", self.database, script)
                # shortcut: these fixtures contain no semicolons in strings; use a parser if that changes.
                for statement in script.split(";"):
                    if statement.strip():
                        cursor.execute(statement)
        self.app = create_app({**config, "TESTING": True, "DB_NAME": self.database,
            "SESSION_FILE_DIR": str(self.root / "sessions"), "UPLOAD_ROOT": str(self.root / "uploads")})
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session.update(user_id=1, name="Book test", csrf_token="token")

    def drop_database(self):
        if not re.fullmatch(r"library_books_test_[0-9a-f]{32}", self.database):
            raise ValueError("Refusing to drop a non-test database")
        with self.admin.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{self.database}`")

    def rows(self, sql, values=()):
        with self.app.app_context(), get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, values)
                return cursor.fetchall()

    def post(self, path="/books/add", **values):
        return self.client.post(path, data={"csrf_token": "token", "title": "Real book",
            "price": "10.50", "author_id": "1", **values})

    def test_sql_seeds_foreign_key_and_cascade(self):
        self.assertEqual(len(self.rows("SELECT * FROM BOOK")), 6)
        self.assertTrue(all(row["cover_filename"] is None for row in self.rows("SELECT * FROM BOOK")))
        with self.app.app_context(), get_connection() as connection:
            with connection.cursor() as cursor:
                with self.assertRaises(pymysql.IntegrityError):
                    cursor.execute("INSERT INTO BOOK(title, price, author_id) VALUES (%s, %s, %s)",
                                   ("Missing author", "1.00", 999))
                connection.rollback()
                cursor.execute("DELETE FROM AUTHOR WHERE author_id = %s", (1,))
            connection.commit()
        self.assertFalse(self.rows("SELECT * FROM BOOK WHERE author_id = %s", (1,)))
        self.assertEqual(len(self.rows("SELECT * FROM BOOK")), 4)

    def test_real_crud_and_cover_lifecycle(self):
        self.assertEqual(self.client.get("/books/").status_code, 200)
        self.assertEqual(self.post().status_code, 302)
        row = self.rows("SELECT * FROM BOOK ORDER BY book_id DESC LIMIT 1")[0]
        book_id = row["book_id"]
        self.assertIsNone(row["cover_filename"])
        self.assertEqual(self.post(f"/books/{book_id}/edit").status_code, 302)
        self.assertEqual(self.post(f"/books/{book_id}/edit", cover=(upload().stream, "one.png")).status_code, 302)
        row = self.rows("SELECT * FROM BOOK WHERE book_id=%s", (book_id,))[0]
        old = self.root / "uploads/books" / row["cover_filename"]
        self.assertTrue(old.exists())
        self.assertEqual(self.post(f"/books/{book_id}/edit").status_code, 302)
        self.assertTrue(old.exists())
        self.assertEqual(self.post(f"/books/{book_id}/edit", cover=(upload().stream, "two.png")).status_code, 302)
        self.assertFalse(old.exists())
        row = self.rows("SELECT * FROM BOOK WHERE book_id=%s", (book_id,))[0]
        self.assertEqual(row["price"], Decimal("10.50"))
        self.assertEqual(self.post(f"/books/{book_id}/delete").status_code, 302)
        self.assertFalse((self.root / "uploads/books" / row["cover_filename"]).exists())
        self.assertEqual(self.client.get(f"/books/{book_id}/edit").status_code, 404)

    def test_invalid_author_and_text_leave_no_files_or_rows(self):
        for values in ({"author_id": "999"}, {"price": "NaN"}, {"title": ""}):
            response = self.post(**values, cover=(upload().stream, "test.png"))
            self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.rows("SELECT * FROM BOOK")), 6)
        self.assertEqual(list((self.root / "uploads/books").glob("*")), [])
