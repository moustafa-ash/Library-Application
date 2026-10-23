"""Disposable MySQL book UI checks; no production login/media bypass is added."""

import os
from pathlib import Path
import subprocess
import sys
import threading

from flask import redirect, send_from_directory, session
from werkzeug.serving import make_server

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth import login_required
from tests.test_books_mysql import BookMySQLTests


if __name__ == "__main__":
    if os.environ.get("RUN_BOOK_MYSQL_TESTS") != "1":
        raise SystemExit("Set RUN_BOOK_MYSQL_TESTS=1 to use a disposable MySQL database.")
    fixture = BookMySQLTests()
    try:
        fixture.setUp()

        @fixture.app.get("/_books_test/login")
        def test_login():
            session.update(user_id=1, name="Book browser test")
            return redirect("/books/")

        @fixture.app.get("/media/<kind>/<filename>", endpoint="media.image")
        @login_required
        def test_media(kind, filename):
            # Fixture only: production safe serving and media validation belong to Ibrahim.
            return send_from_directory(fixture.root / "uploads" / kind, filename)

        server = make_server("127.0.0.1", 0, fixture.app)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            result = subprocess.run([os.environ.get("NODE_BINARY", "node"),
                str(Path(__file__).with_name("browser_books.test.js")),
                f"http://127.0.0.1:{server.server_port}"])
        finally:
            server.shutdown()
            server.server_close()
        raise SystemExit(result.returncode)
    finally:
        fixture.doCleanups()
