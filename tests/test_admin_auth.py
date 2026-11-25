import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

from src import app as app_module


def make_request(cookie: str | None = None) -> Request:
    headers = []
    if cookie is not None:
        headers.append((b"cookie", f"teacher_session={cookie}".encode("ascii")))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": headers,
        "server": ("testserver", 80),
        "client": ("testclient", 123),
    }
    return Request(scope)


class TeacherAuthTests(unittest.TestCase):
    def test_password_hash_authenticates_only_matching_credentials(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            credentials_file = Path(temp_dir) / "teachers.json"
            credentials_file.write_text(
                json.dumps(
                    {
                        "teachers": [
                            app_module.create_teacher_record("teacher", "correct horse")
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(app_module, "TEACHERS_FILE", credentials_file):
                self.assertTrue(
                    app_module.verify_teacher_credentials("teacher", "correct horse")
                )
                self.assertFalse(
                    app_module.verify_teacher_credentials("teacher", "wrong password")
                )
                self.assertFalse(
                    app_module.verify_teacher_credentials("unknown", "correct horse")
                )

    def test_missing_session_is_rejected(self):
        with self.assertRaises(HTTPException) as error:
            app_module.require_teacher(make_request())
        self.assertEqual(error.exception.status_code, 401)

    def test_valid_session_identifies_teacher(self):
        with patch.dict(
            app_module.teacher_sessions,
            {"valid-token": ("teacher", time.time() + 60)},
        ):
            self.assertEqual(
                app_module.require_teacher(make_request("valid-token")),
                "teacher",
            )

    def test_expired_session_is_rejected(self):
        with patch.dict(
            app_module.teacher_sessions,
            {"expired-token": ("teacher", time.time() - 1)},
        ):
            with self.assertRaises(HTTPException) as error:
                app_module.require_teacher(make_request("expired-token"))
        self.assertEqual(error.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
