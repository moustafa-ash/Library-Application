"""Run the shared UI checks with Node and an existing Playwright installation."""

import os
from pathlib import Path
import subprocess
import tempfile
import threading
import sys

from werkzeug.serving import make_server

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from tests import TEST_CONFIG


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as directory:
        app = create_app({**TEST_CONFIG, "SESSION_FILE_DIR": directory})
        server = make_server("127.0.0.1", 0, app)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            result = subprocess.run([
                os.environ.get("NODE_BINARY", "node"),
                str(Path(__file__).with_name("browser.test.js")),
                f"http://127.0.0.1:{server.server_port}",
            ])
        finally:
            server.shutdown()
            server.server_close()
        raise SystemExit(result.returncode)
