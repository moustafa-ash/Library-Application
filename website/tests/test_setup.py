import tempfile
import unittest
from unittest.mock import patch

from app import create_app
from app.db import get_connection
from tests import TEST_CONFIG


class SharedSetupTests(unittest.TestCase):
    def test_config_validation_and_database_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "SECRET_KEY"):
                create_app({**TEST_CONFIG, "SECRET_KEY": "", "SESSION_FILE_DIR": directory})
            with self.assertRaisesRegex(ValueError, "DB_PORT"):
                create_app({**TEST_CONFIG, "DB_PORT": "invalid", "SESSION_FILE_DIR": directory})
            app = create_app({**TEST_CONFIG, "SESSION_FILE_DIR": directory})
            with app.app_context(), patch("app.db.pymysql.connect") as connect:
                get_connection()
                self.assertEqual(connect.call_args.kwargs["database"], "test_library")
                get_connection("test_registration")
                self.assertEqual(connect.call_args.kwargs["database"], "test_registration")
                self.assertEqual(connect.call_args.kwargs["charset"], "utf8mb4")
            self.assertTrue(app.config["SESSION_COOKIE_HTTPONLY"])
            self.assertEqual(app.config["SESSION_COOKIE_SAMESITE"], "Lax")

    def test_check_db_command_closes_connections(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app({**TEST_CONFIG, "SESSION_FILE_DIR": directory})
            with patch("app.db.get_connection") as connect:
                result = app.test_cli_runner().invoke(args=["check-db"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertEqual(connect.call_count, 2)
                self.assertEqual(connect.return_value.__exit__.call_count, 2)
