"""Opt-in real BOOK/AUTHOR checks using disposable catalog databases."""

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
from app.images import save_image
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
        self.assertGreaterEqual(len(self.rows("SELECT * FROM AUTHOR")), 3)
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

    def test_library_schema_types_keys_and_required_country(self):
        columns = self.rows("SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE FROM information_schema.COLUMNS "
                            "WHERE TABLE_SCHEMA = %s", (self.database,))
        actual = {(row["TABLE_NAME"].upper(), row["COLUMN_NAME"]): (row["COLUMN_TYPE"], row["IS_NULLABLE"])
                  for row in columns}
        self.assertEqual(actual, {
            ("AUTHOR", "author_id"): ("int", "NO"), ("AUTHOR", "name"): ("varchar(100)", "NO"),
            ("AUTHOR", "country"): ("varchar(100)", "NO"), ("AUTHOR", "photo_filename"): ("varchar(36)", "YES"),
            ("BOOK", "book_id"): ("int", "NO"), ("BOOK", "title"): ("varchar(255)", "NO"),
            ("BOOK", "price"): ("decimal(10,2)", "NO"), ("BOOK", "author_id"): ("int", "NO"),
            ("BOOK", "cover_filename"): ("varchar(36)", "YES"),
        })
        keys = self.rows("SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE "
                         "WHERE TABLE_SCHEMA = %s AND CONSTRAINT_NAME = 'PRIMARY'", (self.database,))
        self.assertEqual({(row["TABLE_NAME"].upper(), row["COLUMN_NAME"]) for row in keys},
                         {("AUTHOR", "author_id"), ("BOOK", "book_id")})
        rules = self.rows("SELECT DELETE_RULE FROM information_schema.REFERENTIAL_CONSTRAINTS "
                          "WHERE CONSTRAINT_SCHEMA = %s AND CONSTRAINT_NAME = 'fk_book_author'", (self.database,))
        self.assertEqual(rules[0]["DELETE_RULE"], "CASCADE")

    def test_real_author_crud_country_and_photo_lifecycle(self):
        values = {"csrf_token": "token", "name": "Audit author", "country": "Egypt"}
        self.assertEqual(self.client.post("/authors/add", data=values).status_code, 302)
        row = self.rows("SELECT * FROM AUTHOR ORDER BY author_id DESC LIMIT 1")[0]
        author_id = row["author_id"]
        self.assertIsNone(row["photo_filename"])
        path = f"/authors/{author_id}/edit"
        self.assertEqual(self.client.post(path, data=values).status_code, 302)
        self.assertEqual(self.client.post(path, data={**values, "photo": (upload().stream, "one.png")}).status_code, 302)
        row = self.rows("SELECT * FROM AUTHOR WHERE author_id = %s", (author_id,))[0]
        old = self.root / "uploads/authors" / row["photo_filename"]
        self.assertTrue(old.is_file())
        self.assertEqual(self.client.post(path, data=values).status_code, 302)
        self.assertTrue(old.is_file())
        updated = {**values, "name": "Edited audit author", "country": "Morocco"}
        self.assertEqual(self.client.post(path, data={**updated, "photo": (upload().stream, "two.png")}).status_code, 302)
        self.assertFalse(old.exists())
        row = self.rows("SELECT * FROM AUTHOR WHERE author_id = %s", (author_id,))[0]
        self.assertEqual((row["name"], row["country"]), ("Edited audit author", "Morocco"))
        page = self.client.get("/authors/")
        self.assertIn(b"Edited audit author", page.data)
        self.assertIn(b"Morocco", page.data)
        self.assertEqual(self.client.post(f"/authors/{author_id}/delete", data={"csrf_token": "token"}).status_code, 302)
        self.assertFalse(self.rows("SELECT * FROM AUTHOR WHERE author_id = %s", (author_id,)))
        self.assertFalse((self.root / "uploads/authors" / row["photo_filename"]).exists())
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_country_migration_preserves_existing_catalog(self):
        before_authors = self.rows("SELECT author_id, name, photo_filename FROM AUTHOR ORDER BY author_id")
        before_books = self.rows("SELECT * FROM BOOK ORDER BY book_id")
        with self.app.app_context(), get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE AUTHOR DROP COLUMN country")
                script = (Path(__file__).resolve().parents[1] / "database/add_author_country.sql").read_text(encoding="utf-8")
                script = re.sub(r"--[^\n]*", "", script)
                script = re.sub(r"\blibrary\b", self.database, script)
                for statement in script.split(";"):
                    if statement.strip():
                        cursor.execute(statement)
                with self.assertRaises(pymysql.OperationalError) as rejected:
                    cursor.execute("INSERT INTO AUTHOR(name) VALUES ('Country required')")
                self.assertEqual(rejected.exception.args[0], 1364)
        self.assertEqual(self.rows("SELECT author_id, name, photo_filename FROM AUTHOR ORDER BY author_id"), before_authors)
        self.assertEqual(self.rows("SELECT * FROM BOOK ORDER BY book_id"), before_books)
        self.assertTrue(all(row["country"] == "Unknown" for row in self.rows("SELECT country FROM AUTHOR")))

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

    def test_real_author_delete_cleans_target_assets_and_preserves_other_author(self):
        with self.app.app_context():
            target_photo = save_image(upload(), "authors")
            other_photo = save_image(upload(), "authors")
            target_covers = [save_image(upload(), "books") for _ in range(2)]
            other_cover = save_image(upload(), "books")

        target_books = self.rows(
            "SELECT book_id FROM BOOK WHERE author_id = %s ORDER BY book_id", (1,))
        other_books = self.rows(
            "SELECT book_id FROM BOOK WHERE author_id = %s ORDER BY book_id", (2,))
        self.assertGreaterEqual(len(target_books), 2)
        self.assertGreaterEqual(len(other_books), 1)

        with self.app.app_context(), get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("UPDATE AUTHOR SET photo_filename = %s WHERE author_id = %s",
                               (target_photo, 1))
                cursor.execute("UPDATE AUTHOR SET photo_filename = %s WHERE author_id = %s",
                               (other_photo, 2))
                for book, cover in zip(target_books[:2], target_covers):
                    cursor.execute("UPDATE BOOK SET cover_filename = %s WHERE book_id = %s",
                                   (cover, book["book_id"]))
                cursor.execute("UPDATE BOOK SET cover_filename = %s WHERE book_id = %s",
                               (other_cover, other_books[0]["book_id"]))
            connection.commit()

        response = self.client.post("/authors/1/delete", data={"csrf_token": "token"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.rows("SELECT author_id FROM AUTHOR WHERE author_id = %s", (1,)))
        self.assertEqual(len(self.rows("SELECT book_id FROM BOOK WHERE author_id = %s", (1,))), 0)
        self.assertEqual(len(self.rows("SELECT book_id FROM BOOK WHERE author_id = %s", (2,))),
                         len(other_books))
        self.assertEqual(self.rows("SELECT photo_filename FROM AUTHOR WHERE author_id = %s", (2,))[0]
                         ["photo_filename"], other_photo)
        self.assertEqual(self.rows("SELECT cover_filename FROM BOOK WHERE book_id = %s",
                                   (other_books[0]["book_id"],))[0]["cover_filename"], other_cover)

        self.assertFalse((self.root / "uploads/authors" / target_photo).exists())
        self.assertFalse((self.root / "uploads/books" / target_covers[0]).exists())
        self.assertFalse((self.root / "uploads/books" / target_covers[1]).exists())
        self.assertTrue((self.root / "uploads/authors" / other_photo).is_file())
        self.assertTrue((self.root / "uploads/books" / other_cover).is_file())
