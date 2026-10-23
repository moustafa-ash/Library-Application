import io
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pymysql
from flask import send_from_directory

from app import create_app
from tests import TEST_CONFIG
from tests.test_images import upload


class BookTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.app = create_app({**TEST_CONFIG, "SESSION_FILE_DIR": str(self.root / "sessions"),
                               "UPLOAD_ROOT": str(self.root / "uploads")})
        self.client = self.app.test_client()
        self.connection = MagicMock()
        self.connection.__enter__.return_value = self.connection
        self.cursor = self.connection.cursor.return_value.__enter__.return_value
        self.book = {"book_id": 1, "title": "Test book", "price": Decimal("12.50"),
                     "author_id": 1, "cover_filename": None}
        self.cursor.fetchone.return_value = self.book.copy()
        self.cursor.fetchall.return_value = [{"author_id": 1, "name": "Author"}]
        self.connect = patch("app.books.routes.get_connection", return_value=self.connection).start()
        self.addCleanup(patch.stopall)
        with self.client.session_transaction() as session:
            session.update(user_id=1, name="Reader", csrf_token="token")

    def post(self, path="/books/add", **values):
        return self.client.post(path, data={"csrf_token": "token", "title": " Test book ",
            "price": "12.50", "author_id": "1", **values})

    def files(self):
        return list((self.root / "uploads/books").glob("*.jpg"))

    def test_routes_require_login_and_writes_require_csrf(self):
        for path in ("/books/", "/books/add", "/books/1/edit", "/books/1/delete"):
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path).status_code, 400)
        self.connect.assert_not_called()
        with self.client.session_transaction() as session:
            session.pop("user_id")
        for path in ("/books/", "/books/add", "/books/1/edit", "/books/1/delete"):
            self.assertEqual(self.client.get(path).location, "/login")
            if path != "/books/":
                self.assertEqual(self.client.post(path, data={"csrf_token": "token"}).location, "/login")
        self.connect.assert_not_called()

    def test_list_escapes_values_and_delete_get_does_not_write(self):
        self.cursor.fetchall.return_value = [{**self.book, "title": "<script>bad</script>"}]
        response = self.client.get("/books/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Author ID", response.data)
        self.assertIn(b"&lt;script&gt;bad&lt;/script&gt;", response.data)
        self.assertIn(b"No cover", response.data)
        self.assertEqual(self.client.get("/books/1/delete").status_code, 200)
        self.connection.commit.assert_not_called()

    def test_create_uses_parameters_and_commit(self):
        response = self.post(title=" ' OR 1=1 -- ")
        self.assertEqual(response.location, "/books/")
        sql, params = self.cursor.execute.call_args.args
        self.assertIn("INSERT INTO BOOK", sql)
        self.assertNotIn("OR 1=1", sql)
        self.assertEqual(params, ("' OR 1=1 --", Decimal("12.50"), 1, None))
        self.connection.commit.assert_called_once()

    def test_validation_preserves_text_and_never_writes(self):
        for field, value in [("title", " "), ("title", "x" * 256), ("price", "NaN"),
            ("price", "Infinity"), ("price", "-1"), ("price", "1.001"), ("price", "100000000"),
            ("price", "bad"), ("price", ""), ("author_id", "0"), ("author_id", "bad")]:
            with self.subTest(field=field, value=value):
                response = self.post(**{field: value})
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'role="alert"', response.data)
        self.connection.commit.assert_not_called()
        self.cursor.fetchone.return_value = None
        response = self.post(cover=(upload().stream, "test.png"))
        self.assertIn(b"existing author", response.data)
        self.assertEqual(self.files(), [])

    def test_unknown_ids_do_not_save_images(self):
        self.cursor.fetchone.return_value = None
        for path in ("/books/999/edit", "/books/999/delete"):
            self.assertEqual(self.client.get(path).status_code, 404)
            self.assertEqual(self.post(path, cover=(upload().stream, "test.png")).status_code, 404)
        self.assertEqual(self.files(), [])
        self.connection.commit.assert_not_called()

    def test_cover_create_retain_replace_delete(self):
        self.assertEqual(self.post(cover=(upload().stream, "test.png")).status_code, 302)
        old = self.files()[0]
        self.cursor.fetchone.return_value = {**self.book, "cover_filename": old.name}
        self.assertEqual(self.post("/books/1/edit").status_code, 302)
        self.assertTrue(old.exists())
        self.assertEqual(self.cursor.execute.call_args.args[1][-2], old.name)
        self.assertEqual(self.post("/books/1/edit", cover=(upload().stream, "new.png")).status_code, 302)
        self.assertFalse(old.exists())
        new = self.files()[0]
        self.cursor.fetchone.return_value = {**self.book, "cover_filename": new.name}
        self.assertEqual(self.post("/books/1/delete").status_code, 302)
        self.assertEqual(self.files(), [])

    def test_bad_upload_and_disk_failure_prevent_insert(self):
        response = self.post(cover=(io.BytesIO(b"bad"), "test.png"))
        self.assertIn(b"image", response.data)
        with patch("app.books.routes.save_image", side_effect=OSError("private disk detail")), self.assertLogs(self.app.logger, level="ERROR"):
            response = self.post(cover=(upload().stream, "test.png"))
        self.assertNotIn(b"private disk detail", response.data)
        self.connection.commit.assert_not_called()

    def test_rollback_removes_new_file_and_retains_old(self):
        self.post(cover=(upload().stream, "test.png"))
        old = self.files()[0]
        self.cursor.fetchone.return_value = {**self.book, "cover_filename": old.name}
        self.connection.commit.side_effect = pymysql.IntegrityError(1452, "private SQL detail")
        for path in ("/books/add", "/books/1/edit", "/books/1/delete"):
            with self.subTest(path=path), self.assertLogs(self.app.logger, level="ERROR"):
                response = self.post(path, cover=(upload().stream, "test.png"))
                self.assertEqual(response.status_code, 200)
                self.assertNotIn(b"private SQL detail", response.data)
                self.assertEqual(self.files(), [old])
        self.assertEqual(self.connection.rollback.call_count, 3)

    def test_foreign_key_race_cleans_saved_cover(self):
        def execute(sql, values=None):
            if sql.startswith("INSERT INTO BOOK"):
                raise pymysql.IntegrityError(1452, "author removed concurrently")
        self.cursor.execute.side_effect = execute
        with self.assertLogs(self.app.logger, level="ERROR"):
            response = self.post(cover=(upload().stream, "test.png"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.files(), [])
        self.connection.commit.assert_not_called()
        self.connection.rollback.assert_called_once()

    def test_cleanup_failure_does_not_reverse_commit(self):
        self.cursor.fetchone.return_value = {**self.book, "cover_filename": "a" * 32 + ".jpg"}
        with patch("app.books.routes.delete_image", side_effect=OSError("disk")), self.assertLogs(self.app.logger, level="ERROR"):
            self.assertEqual(self.post("/books/1/delete").status_code, 302)
        self.connection.commit.assert_called_once()
        self.connection.rollback.assert_not_called()

    def test_disconnected_rollback_still_removes_new_cover(self):
        self.connection.commit.side_effect = pymysql.OperationalError(2013, "lost connection")
        self.connection.rollback.side_effect = pymysql.OperationalError(2006, "server gone")
        with self.assertLogs(self.app.logger, level="ERROR"):
            response = self.post(cover=(upload().stream, "test.png"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.files(), [])

    def test_database_unavailable_is_safe(self):
        self.connect.side_effect = pymysql.OperationalError(1049, "private SQL detail")
        with self.assertLogs(self.app.logger, level="ERROR"):
            response = self.client.get("/books/")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"private SQL detail", response.data)

    def test_form_query_failure_is_safe(self):
        self.cursor.execute.side_effect = pymysql.OperationalError(1146, "private missing table")
        for path in ("/books/add", "/books/1/edit"):
            with self.subTest(path=path), self.assertLogs(self.app.logger, level="ERROR"):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 503)
                self.assertNotIn(b"private missing table", response.data)

    def test_preview_endpoint_is_optional(self):
        self.post(cover=(upload().stream, "test.png"))
        name = self.files()[0].name
        self.cursor.fetchone.return_value = {**self.book, "cover_filename": name}
        self.assertIn(b"Cover preview awaiting media integration", self.client.get("/books/1/edit").data)
        # Test-only endpoint; production media remains Ibrahim's responsibility.
        app = create_app({**TEST_CONFIG, "SESSION_FILE_DIR": str(self.root / "sessions2")})
        app.add_url_rule("/media/<kind>/<filename>", "media.image",
            lambda kind, filename: send_from_directory(self.root / "uploads" / kind, filename))
        client = app.test_client()
        with client.session_transaction() as session:
            session["user_id"] = 1
        response = client.get("/books/1/edit")
        self.assertIn(f'/media/books/{name}'.encode(), response.data)
        with client.get(f"/media/books/{name}") as image_response:
            self.assertEqual(image_response.mimetype, "image/jpeg")
