import sys
from tempfile import TemporaryDirectory
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
            "web_token": "token-secret",
        }
        public = webapp.public_config(cfg)
        self.assertEqual(public["api_id"], 123)
        self.assertEqual(public["api_hash"], "")
        self.assertEqual(public["session_file"], "")
        self.assertEqual(public["string_session"], "")
        self.assertEqual(public["web_token"], "")
        self.assertTrue(public["api_hash_saved"])
        self.assertTrue(public["session_file_saved"])
        self.assertTrue(public["string_session_saved"])
        self.assertTrue(public["web_token_saved"])

        cfg["proxy"] = "socks5://user:pass@127.0.0.1:1080"
        public = webapp.public_config(cfg)
        self.assertEqual(public["proxy"], "")
        self.assertTrue(public["proxy_saved"])
        self.assertTrue(public["proxy_redacted"])

    def test_run_host_and_port_defaults_and_env(self):
        with patch.dict(webapp.os.environ, {}, clear=True):
            self.assertEqual(webapp.run_host(), "127.0.0.1")
            self.assertEqual(webapp.run_port(), 5000)
        with patch.dict(webapp.os.environ, {"TELEGRAM_WEB_HOST": "0.0.0.0", "TELEGRAM_WEB_PORT": "8080"}, clear=True):
            self.assertEqual(webapp.run_host(), "0.0.0.0")
            self.assertEqual(webapp.run_port(), 8080)

    def test_normalize_config_patch_validates_fields(self):
        cfg = webapp.normalize_config_patch({
            "api_id": "123",
            "api_hash": "abcdefabcdefabcdefabcdefabcdefab",
            "phone": "+1234567890",
            "download_threads": "32",
            "cache_limit_mb": "512",
            "session_type": "file",
            "session_file": "custom.session",
            "proxy": "socks5://127.0.0.1:1080",
            "web_token": "12345678",
        }, webapp.DEFAULT_CONFIG)
        self.assertEqual(cfg["api_id"], 123)
        self.assertEqual(cfg["api_hash"], "abcdefabcdefabcdefabcdefabcdefab")
        self.assertEqual(cfg["phone"], "+1234567890")
        self.assertEqual(cfg["download_threads"], 32)
        self.assertEqual(cfg["cache_limit_mb"], 512)
        self.assertEqual(cfg["session_file"], str((webapp.DATA_DIR / "custom").resolve()))
        self.assertEqual(cfg["proxy"], "socks5://127.0.0.1:1080")
        self.assertEqual(cfg["web_token"], "12345678")

        with self.assertRaises(webapp.ApiError):
            webapp.normalize_config_patch({"api_id": 0}, webapp.DEFAULT_CONFIG)
        with self.assertRaises(webapp.ApiError):
            webapp.normalize_config_patch({"api_hash": "not-a-hash"}, webapp.DEFAULT_CONFIG)
        with self.assertRaises(webapp.ApiError):
            webapp.normalize_config_patch({"phone": "abc"}, webapp.DEFAULT_CONFIG)
        with self.assertRaises(webapp.ApiError):
            webapp.normalize_config_patch({"proxy": "socks5://127.0.0.1:1080/path"}, webapp.DEFAULT_CONFIG)
        with self.assertRaises(webapp.ApiError):
            webapp.normalize_config_patch({"download_threads": 0}, webapp.DEFAULT_CONFIG)
        with self.assertRaises(webapp.ApiError):
            webapp.normalize_config_patch({"cache_limit_mb": 64}, webapp.DEFAULT_CONFIG)
        with self.assertRaises(webapp.ApiError):
            webapp.normalize_config_patch({"session_type": "bad"}, webapp.DEFAULT_CONFIG)
        with self.assertRaises(webapp.ApiError):
            webapp.normalize_config_patch({"session_file": str(ROOT / "outside")}, webapp.DEFAULT_CONFIG)
        with self.assertRaises(webapp.ApiError):
            webapp.normalize_config_patch({"web_token": "short"}, webapp.DEFAULT_CONFIG)
        with self.assertRaises(webapp.ApiError):
            webapp.normalize_config_patch({"session_type": "string"}, webapp.DEFAULT_CONFIG)

    def test_safe_bind_requires_token_for_external_host(self):
        with patch.dict(webapp.os.environ, {}, clear=True):
            with patch.object(webapp, "load_config", return_value={**webapp.DEFAULT_CONFIG, "web_token": ""}):
                webapp.ensure_safe_bind("127.0.0.1")
                with self.assertRaises(RuntimeError):
                    webapp.ensure_safe_bind("0.0.0.0")
        with patch.dict(webapp.os.environ, {"TELEGRAM_WEB_TOKEN": "12345678"}, clear=True):
            webapp.ensure_safe_bind("0.0.0.0")


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


class WebAuthTest(unittest.TestCase):
    def setUp(self):
        self.client = webapp.app.test_client()

    def test_api_requires_token_when_configured(self):
        with patch.dict(webapp.os.environ, {"TELEGRAM_WEB_TOKEN": "12345678"}, clear=True):
            response = self.client.get("/api/tasks")
            self.assertEqual(response.status_code, 401)
            self.assertFalse(response.get_json()["success"])

            response = self.client.get("/api/tasks", headers={"X-Web-Telegram-Token": "12345678"})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.get_json()["success"])

    def test_login_and_static_are_public_token_entrypoints(self):
        with patch.dict(webapp.os.environ, {"TELEGRAM_WEB_TOKEN": "12345678"}, clear=True):
            response = self.client.get("/login")
            self.assertEqual(response.status_code, 200)

            response = self.client.get("/static/css/app.css")
            self.addCleanup(response.close)
            self.assertEqual(response.status_code, 200)

            response = self.client.get("/chats")
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.headers["Location"].startswith("/auth?"))

    def test_file_route_requires_token_when_configured(self):
        sample = webapp.DOWNLOAD_DIR / "unit-test-auth.txt"
        sample.write_text("secret", "utf-8")
        self.addCleanup(sample.unlink, missing_ok=True)
        with patch.dict(webapp.os.environ, {"TELEGRAM_WEB_TOKEN": "12345678"}, clear=True):
            response = self.client.get("/download-file/unit-test-auth.txt")
            self.assertEqual(response.status_code, 401)

            response = self.client.get("/download-file/unit-test-auth.txt?token=12345678", buffered=True)
            self.addCleanup(response.close)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b"secret")

    def test_auth_form_sets_cookie(self):
        with patch.dict(webapp.os.environ, {"TELEGRAM_WEB_TOKEN": "12345678"}, clear=True):
            response = self.client.post("/auth", data={"token": "bad", "next": "/chats"})
            self.assertEqual(response.status_code, 200)
            self.assertIn("Token", response.get_data(as_text=True))

            response = self.client.post("/auth", data={"token": "12345678", "next": "/chats"})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers["Location"], "/chats")
            self.assertIn(webapp.AUTH_COOKIE, response.headers.get("Set-Cookie", ""))

    def test_query_token_sets_cookie(self):
        with patch.dict(webapp.os.environ, {"TELEGRAM_WEB_TOKEN": "12345678"}, clear=True):
            response = self.client.get("/login?token=12345678")
            self.assertEqual(response.status_code, 200)
            self.assertIn(webapp.AUTH_COOKIE, response.headers.get("Set-Cookie", ""))

    def test_config_save_sets_token_cookie_and_redacts_response(self):
        with TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "config.json"
            with patch.object(webapp, "CONFIG_FILE", config_file), patch.object(webapp.tg, "reload_config", lambda: None):
                response = self.client.post("/api/config", json={"web_token": "12345678"})
                self.assertEqual(response.status_code, 200)
                data = response.get_json()["data"]
                self.assertEqual(data["web_token"], "")
                self.assertTrue(data["web_token_saved"])
                self.assertIn(webapp.AUTH_COOKIE, response.headers.get("Set-Cookie", ""))

                response = self.client.post("/api/config", json={"download_threads": 0}, headers={"X-Web-Telegram-Token": "12345678"})
                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.get_json()["success"])

    def test_socketio_requires_token_when_configured(self):
        with patch.dict(webapp.os.environ, {"TELEGRAM_WEB_TOKEN": "12345678"}, clear=True):
            client = webapp.socketio.test_client(webapp.app)
            self.assertFalse(client.is_connected())

            client = webapp.socketio.test_client(webapp.app, auth={"token": "12345678"})
            self.assertTrue(client.is_connected())
            client.disconnect()


if __name__ == "__main__":
    unittest.main()
