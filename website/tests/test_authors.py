import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pymysql

from app import create_app
from tests import TEST_CONFIG
from tests.test_images import upload


class AuthorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = create_app({**TEST_CONFIG, "SESSION_FILE_DIR": str(self.root / "sessions"),
                               "UPLOAD_ROOT": str(self.root / "uploads")})
        self.client = self.app.test_client()
        self.connection = MagicMock()
        self.connection.__enter__.return_value = self.connection
        self.cursor = self.connection.cursor.return_value.__enter__.return_value
        self.author = {"author_id": 1, "name": "Author One", "country": "Egypt", "photo_filename": None}
        self.cursor.fetchone.return_value = self.author.copy()
        self.cursor.fetchall.return_value = []
        patcher = patch("app.authors.routes.get_connection", return_value=self.connection)
        patcher.start()
        self.addCleanup(patcher.stop)
        with self.client.session_transaction() as session:
            session.update(user_id=1, name="Reader", csrf_token="token")

    def post(self, path="/authors/add", **values):
        return self.client.post(path, data={"csrf_token": "token", "name": "  Author One  ", "country": " Egypt ", **values})

    def files(self, kind):
        folder = self.root / "uploads" / kind
        return list(folder.glob("*.jpg")) if folder.exists() else []

    def test_login_csrf_and_crud_queries(self):
        for path in ("/authors/", "/authors/add", "/authors/1/edit", "/authors/1/delete"):
            self.assertEqual(self.client.post(path).status_code, 400)
        self.assertEqual(self.client.get("/authors/").status_code, 200)
        response = self.post()
        self.assertEqual(response.location, "/authors/")
        sql, params = self.cursor.execute.call_args.args
        self.assertIn("INSERT INTO AUTHOR", sql)
        self.assertEqual(params, ("Author One", "Egypt", None))

    def test_list_escapes_content_and_unknown_record_is_404(self):
        self.cursor.fetchall.return_value = [{**self.author, "name": "<script>x</script>"}]
        page = self.client.get("/authors/")
        self.assertIn(b"&lt;script&gt;x&lt;/script&gt;", page.data)
        self.assertIn(b"Egypt", page.data)
        self.assertIn(b"No photo", page.data)
        self.cursor.fetchone.return_value = None
        self.assertEqual(self.client.get("/authors/99/edit").status_code, 404)
        self.assertEqual(self.post("/authors/99/edit", photo=(upload().stream, "x.png")).status_code, 404)
        self.assertEqual(self.files("authors"), [])

    def test_validation_and_image_lifecycle(self):
        for invalid in ("", "  ", "x" * 101):
            self.assertEqual(self.post(name=invalid).status_code, 200)
        self.connection.commit.assert_not_called()
        for invalid_country in ("", "  ", "x" * 101):
            self.assertEqual(self.post(country=invalid_country).status_code, 200)
        self.assertEqual(self.post(photo=(io.BytesIO(b"bad"), "bad.png")).status_code, 200)
        self.assertEqual(self.files("authors"), [])
        self.assertEqual(self.post(photo=(upload().stream, "one.png")).status_code, 302)
        first = self.files("authors")[0]
        self.cursor.fetchone.return_value = {**self.author, "photo_filename": first.name}
        self.assertEqual(self.post("/authors/1/edit").status_code, 302)
        self.assertTrue(first.exists())
        self.assertEqual(self.post("/authors/1/edit", photo=(upload().stream, "two.png")).status_code, 302)
        self.assertFalse(first.exists())

    def test_rollback_removes_new_photo_and_keeps_old_photo(self):
        self.post(photo=(upload().stream, "one.png"))
        old = self.files("authors")[0]
        self.cursor.fetchone.return_value = {**self.author, "photo_filename": old.name}
        self.connection.commit.side_effect = pymysql.IntegrityError(1062, "private")
        with self.assertLogs(self.app.logger, level="ERROR"):
            response = self.post("/authors/1/edit", photo=(upload().stream, "two.png"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.files("authors"), [old])

    def test_author_delete_cascades_rows_and_cleans_photo_and_covers(self):
        self.cursor.fetchone.return_value = {**self.author, "photo_filename": "a" * 32 + ".jpg"}
        self.cursor.fetchall.return_value = [{"book_id": 4, "cover_filename": "b" * 32 + ".jpg"},
                                             {"book_id": 5, "cover_filename": None}]
        with patch("app.authors.routes.delete_image") as cleanup:
            response = self.post("/authors/1/delete")
        self.assertEqual(response.location, "/authors/")
        sql_calls = [call.args[0] for call in self.cursor.execute.call_args_list]
        self.assertTrue(any("SELECT book_id, cover_filename FROM BOOK" in sql for sql in sql_calls))
        self.assertTrue(any("DELETE FROM AUTHOR" in sql for sql in sql_calls))
        self.assertEqual(cleanup.call_args_list[0].args, ("a" * 32 + ".jpg", "authors"))
        self.assertEqual(cleanup.call_args_list[1].args, ("b" * 32 + ".jpg", "books"))
        self.connection.commit.assert_called_once()

    def test_media_is_authenticated_and_rejects_invalid_paths(self):
        name = "a" * 32 + ".jpg"
        folder = self.root / "uploads" / "authors"
        folder.mkdir(parents=True)
        (folder / name).write_bytes(b"jpeg")
        with self.client.get(f"/media/authors/{name}") as response:
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(self.client.get(f"/media/other/{name}").status_code, 404)
        self.assertEqual(self.client.get("/media/authors/../secret").status_code, 404)
        with self.client.session_transaction() as session:
            session.pop("user_id")
        self.assertEqual(self.client.get(f"/media/authors/{name}").location, "/login")

    def test_all_author_routes_require_login(self):
        with self.client.session_transaction() as session:
            session.pop("user_id")
        with patch("app.authors.routes.get_connection") as connect:
            for path in ("/authors/", "/authors/add", "/authors/1/edit", "/authors/1/delete"):
                self.assertEqual(self.client.get(path).location, "/login")
                if path != "/authors/":
                    self.assertEqual(self.post(path).location, "/login")
            connect.assert_not_called()

    def test_failed_author_delete_retains_photo_and_covers(self):
        self.post(photo=(upload().stream, "photo.png"))
        photo = self.files("authors")[0]
        self.cursor.fetchone.return_value = {**self.author, "photo_filename": photo.name}
        covers = ["b" * 32 + ".jpg", "c" * 32 + ".jpg"]
        folder = self.root / "uploads/books"
        folder.mkdir()
        for filename in covers:
            (folder / filename).write_bytes(b"retained cover")
        self.cursor.fetchall.return_value = [{"book_id": index, "cover_filename": filename}
                                             for index, filename in enumerate(covers)]
        def execute(sql, values=None):
            if sql.startswith("DELETE FROM AUTHOR"):
                raise pymysql.OperationalError(1205, "private SQL detail")
        self.cursor.execute.side_effect = execute
        self.connection.commit.reset_mock()
        with self.assertLogs(self.app.logger, level="ERROR"):
            response = self.post("/authors/1/delete")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"private SQL detail", response.data)
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()
        self.assertTrue(photo.is_file())
        self.assertTrue(all((folder / filename).is_file() for filename in covers))

    def test_request_size_recovery(self):
        response = self.client.post("/authors/add", data={"csrf_token": "token", "name": "Large photo",
            "photo": (io.BytesIO(b"x" * (6 * 1024 * 1024)), "too-large.jpg")},
            content_type="multipart/form-data")
        self.assertEqual(response.status_code, 413)
        self.assertIn(b"5 MiB", response.data)
        # A rejected oversized body is never parsed; close the test client's spool.
        response.request.input_stream.close()
