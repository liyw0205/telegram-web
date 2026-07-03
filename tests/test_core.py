import sys
from unittest.mock import patch
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app as webapp


class CoreHelpersTest(unittest.TestCase):
    def test_safe_filename_replaces_forbidden_chars(self):
        self.assertEqual(webapp.safe_filename(' a/b:c*?"<>|.txt '), "a_b_c______.txt")
        self.assertEqual(webapp.safe_filename(""), "file")

    def test_format_size(self):
        self.assertEqual(webapp.format_size(0), "0 B")
        self.assertEqual(webapp.format_size(1024), "1.00 KB")
        self.assertEqual(webapp.format_size(1536), "1.50 KB")

    def test_parse_proxy(self):
        self.assertIsNone(webapp.parse_proxy(""))
        parsed = webapp.parse_proxy("socks5://user:pass@127.0.0.1:1081")
        self.assertEqual(parsed[1], "127.0.0.1")
        self.assertEqual(parsed[2], 1081)
        self.assertEqual(parsed[4], "user")
        self.assertEqual(parsed[5], "pass")
        with self.assertRaises(ValueError):
            webapp.parse_proxy("http://127.0.0.1:8080")

    def test_resolve_under_rejects_traversal_and_absolute_paths(self):
        inside = webapp.resolve_under(webapp.DOWNLOAD_DIR, "file.txt")
        self.assertEqual(inside, (webapp.DOWNLOAD_DIR / "file.txt").resolve())
        self.assertIsNone(webapp.resolve_under(webapp.DOWNLOAD_DIR, "../app.py"))
        self.assertIsNone(webapp.resolve_under(webapp.DOWNLOAD_DIR, str((ROOT / "app.py").resolve())))

    def test_public_config_redacts_secret_fields(self):
        cfg = {
            "api_id": 123,
            "api_hash": "secret",
            "session_file": "/private/account.session",
            "string_session": "string-secret",
        }
        public = webapp.public_config(cfg)
        self.assertEqual(public["api_id"], 123)
        self.assertEqual(public["api_hash"], "")
        self.assertEqual(public["session_file"], "")
        self.assertEqual(public["string_session"], "")
        self.assertTrue(public["api_hash_saved"])
        self.assertTrue(public["session_file_saved"])
        self.assertTrue(public["string_session_saved"])

    def test_run_host_and_port_defaults_and_env(self):
        with patch.dict(webapp.os.environ, {}, clear=True):
            self.assertEqual(webapp.run_host(), "127.0.0.1")
            self.assertEqual(webapp.run_port(), 5000)
        with patch.dict(webapp.os.environ, {"TELEGRAM_WEB_HOST": "0.0.0.0", "TELEGRAM_WEB_PORT": "8080"}, clear=True):
            self.assertEqual(webapp.run_host(), "0.0.0.0")
            self.assertEqual(webapp.run_port(), 8080)


class FlaskBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.client = webapp.app.test_client()
        self.sample = webapp.DOWNLOAD_DIR / "unit-test-download.txt"
        self.sample.write_text("abcdef", "utf-8")

    def tearDown(self):
        self.sample.unlink(missing_ok=True)

    def test_invalid_json_returns_400(self):
        response = self.client.post("/api/send", data="{", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    def test_missing_json_content_type_returns_400(self):
        response = self.client.post("/api/send", data='{"peer":"x","text":"y"}')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    def test_non_object_json_returns_400(self):
        response = self.client.post("/api/send", json=[])
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    def test_file_route_serves_inside_download_dir(self):
        response = self.client.get("/download-file/unit-test-download.txt", buffered=True)
        self.addCleanup(response.close)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"abcdef")

    def test_file_route_rejects_traversal(self):
        response = self.client.get("/download-file/..%2Fapp.py")
        self.assertEqual(response.status_code, 404)

    def test_range_request(self):
        response = self.client.get("/download-file/unit-test-download.txt", headers={"Range": "bytes=1-3"}, buffered=True)
        self.addCleanup(response.close)
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.data, b"bcd")
        self.assertEqual(response.headers["Content-Range"], "bytes 1-3/6")

    def test_unsatisfiable_range_request(self):
        response = self.client.get("/download-file/unit-test-download.txt", headers={"Range": "bytes=99-100"})
        self.assertEqual(response.status_code, 416)
        self.assertEqual(response.headers["Content-Range"], "bytes */6")

    def test_list_download_files_skips_symlink(self):
        link = webapp.DOWNLOAD_DIR / "unit-test-link.txt"
        try:
            link.symlink_to(ROOT / "app.py")
        except OSError:
            self.skipTest("symlink is not available")
        self.addCleanup(link.unlink, missing_ok=True)
        names = {row["name"] for row in webapp.list_download_files()}
        self.assertIn("unit-test-download.txt", names)
        self.assertNotIn("unit-test-link.txt", names)


if __name__ == "__main__":
    unittest.main()
