import sys
import time
import json
from io import BytesIO
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
        parsed = webapp.parse_proxy("socks4://127.0.0.1")
        self.assertEqual(parsed[2], 1080)
        with self.assertRaises(ValueError):
            webapp.parse_proxy("http://127.0.0.1:8080")
        for proxy in ("socks5://127.0.0.1:bad", "socks5://127.0.0.1:0", "socks5://127.0.0.1:65536"):
            with self.subTest(proxy=proxy):
                with self.assertRaises(ValueError) as cm:
                    webapp.parse_proxy(proxy)
                self.assertEqual(str(cm.exception), "代理端口必须在 1..65535 之间")

    def test_resolve_under_rejects_traversal_and_absolute_paths(self):
        inside = webapp.resolve_under(webapp.DOWNLOAD_DIR, "file.txt")
        self.assertEqual(inside, (webapp.DOWNLOAD_DIR / "file.txt").resolve())
        self.assertIsNone(webapp.resolve_under(webapp.DOWNLOAD_DIR, "../app.py"))
        self.assertIsNone(webapp.resolve_under(webapp.DOWNLOAD_DIR, str((ROOT / "app.py").resolve())))

    def test_parse_range_header(self):
        self.assertIsNone(webapp.parse_range_header(None, 6))
        self.assertIsNone(webapp.parse_range_header("items=1-2", 6))
        self.assertEqual(webapp.parse_range_header("bytes=1-3", 6), (1, 3))
        self.assertEqual(webapp.parse_range_header("bytes=3-", 6), (3, 5))
        self.assertEqual(webapp.parse_range_header("bytes=-2", 6), (4, 5))
        self.assertEqual(webapp.parse_range_header("bytes=-999", 6), (0, 5))
        self.assertEqual(webapp.parse_range_header("bytes=99-100", 6), "unsatisfiable")
        self.assertEqual(webapp.parse_range_header("bytes=3-1", 6), "invalid")
        self.assertEqual(webapp.parse_range_header("bytes=1-2,3-4", 6), "invalid")

    def test_task_store_terminal_state_guard_and_cleanup(self):
        store = webapp.TaskStore()
        controls = {}
        with patch.object(webapp, "task_controls", controls):
            done_id = store.create("download_media")
            controls[done_id] = {"paused": False, "canceled": False}
            store.update(done_id, status="done", progress=100)
            store.update(done_id, status="running", progress=10)
            self.assertEqual(store.get(done_id)["status"], "done")
            self.assertEqual(store.get(done_id)["progress"], 100)

            store.update(done_id, status="canceled", force=True)
            self.assertEqual(store.get(done_id)["status"], "canceled")

            old_id = store.create("prepare_media")
            controls[old_id] = {"paused": False, "canceled": False}
            store.update(old_id, status="error", error="boom")
            with store.lock:
                store.tasks[old_id]["updated_at"] = time.time() - 7200
            active_id = store.create("download_media")
            controls[active_id] = {"paused": False, "canceled": False}

            store.cleanup(max_age=3600)
            self.assertFalse(store.get(old_id))
            self.assertNotIn(old_id, controls)
            self.assertTrue(store.get(active_id))

    def test_task_finish_and_fail_respect_canceled_tasks(self):
        store = webapp.TaskStore()
        controls = {}
        with patch.object(webapp, "tasks", store), patch.object(webapp, "task_controls", controls):
            canceled_id = store.create("download_media")
            controls[canceled_id] = {"paused": False, "canceled": True}
            webapp.task_finish(canceled_id, {"file": "x.txt", "size": 10})
            self.assertEqual(store.get(canceled_id)["status"], "canceled")
            self.assertNotIn(canceled_id, controls)

            failed_id = store.create("download_media")
            controls[failed_id] = {"paused": False, "canceled": False}
            webapp.task_fail(failed_id, RuntimeError("boom"))
            self.assertEqual(store.get(failed_id)["status"], "error")
            self.assertEqual(store.get(failed_id)["error"], "boom")
            self.assertNotIn(failed_id, controls)

    def test_task_store_persists_sanitized_terminal_history(self):
        with TemporaryDirectory() as tmp:
            history_file = Path(tmp) / "task-history.json"
            store = webapp.TaskStore(history_file=history_file)
            task_id = store.create("download_media", {"peer": "secret-peer", "msg_id": 123})
            store.update(task_id, status="done", progress=100, file="/private/path/video.mp4", path="/private/path/video.mp4", downloaded=10, total=10)

            rows = json.loads(history_file.read_text("utf-8"))
            self.assertEqual(rows[0]["id"], task_id)
            self.assertEqual(rows[0]["file"], "video.mp4")
            self.assertEqual(rows[0]["path"], "")
            self.assertEqual(rows[0]["meta"], {})
            self.assertNotIn("secret-peer", history_file.read_text("utf-8"))

            restored = webapp.TaskStore(history_file=history_file, load_history=True)
            self.assertEqual(restored.get(task_id)["status"], "done")
            self.assertEqual(restored.get(task_id)["file"], "video.mp4")

    def test_task_store_does_not_persist_active_tasks(self):
        with TemporaryDirectory() as tmp:
            history_file = Path(tmp) / "task-history.json"
            store = webapp.TaskStore(history_file=history_file)
            task_id = store.create("download_media")
            store.update(task_id, status="running", progress=20)
            self.assertFalse(history_file.exists())

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

    def test_diagnostics_snapshot_redacts_secret_values(self):
        with TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            config_file = data_dir / "config.json"
            task_history_file = data_dir / "task-history.json"
            session_file = data_dir / "account.session"
            session_file.write_bytes(b"session-bytes")
            cfg = {
                **webapp.DEFAULT_CONFIG,
                "api_id": 123,
                "api_hash": "abcdefabcdefabcdefabcdefabcdefab",
                "phone": "+1234567890",
                "proxy": "socks5://user-secret:pass-secret@127.0.0.1:1080",
                "session_type": "string",
                "session_file": str(data_dir / "account"),
                "string_session": "string-session-secret",
                "web_token": "config-token-secret",
            }
            with patch.object(webapp, "DATA_DIR", data_dir), \
                 patch.object(webapp, "CONFIG_FILE", config_file), \
                 patch.object(webapp, "TASK_HISTORY_FILE", task_history_file), \
                 patch.dict(webapp.os.environ, {"TELEGRAM_WEB_TOKEN": "env-token-secret"}, clear=True):
                webapp.save_config(cfg)
                data = webapp.diagnostics_snapshot()

        blob = json.dumps(data, ensure_ascii=False)
        for secret in ("abcdefabcdefabcdefabcdefabcdefab", "+1234567890", "user-secret", "pass-secret", "string-session-secret", "config-token-secret", "env-token-secret", "account.session"):
            self.assertNotIn(secret, blob)
        self.assertTrue(data["config"]["exists"])
        self.assertTrue(data["config"]["api_id_configured"])
        self.assertTrue(data["config"]["api_hash_saved"])
        self.assertTrue(data["config"]["phone_configured"])
        self.assertTrue(data["config"]["proxy_saved"])
        self.assertTrue(data["config"]["proxy_redacted"])
        self.assertEqual(data["config"]["session_type"], "string")
        self.assertTrue(data["config"]["session_file_saved"])
        self.assertTrue(data["config"]["session_file_exists"])
        self.assertTrue(data["config"]["string_session_saved"])
        self.assertTrue(data["web_auth"]["enabled"])
        self.assertEqual(data["web_auth"]["source"], "environment")
        self.assertTrue(data["web_auth"]["env_token_set"])
        self.assertTrue(data["web_auth"]["config_token_saved"])

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

        cases = [
            ({"api_id": 0}, "api_id 必须在 1..2147483647 之间"),
            ({"api_id": "abc"}, "api_id 必须是数字"),
            ({"api_hash": "not-a-hash"}, "api_hash 必须是 32 位十六进制字符串"),
            ({"phone": "abc"}, "phone 格式无效"),
            ({"proxy": "socks5://127.0.0.1:1080/path"}, "代理地址不能包含 path/query/fragment"),
            ({"proxy": "socks5://127.0.0.1:bad"}, "代理端口必须在 1..65535 之间"),
            ({"download_threads": 0}, "download_threads 必须在 1..128 之间"),
            ({"cache_limit_mb": 64}, "cache_limit_mb 必须在 128..10240 之间"),
            ({"session_type": "bad"}, "session_type 仅支持 file/string"),
            ({"session_file": str(ROOT / "outside")}, "session_file 只能是 data 目录内的文件名"),
            ({"session_file": "telegram.txt"}, "session_file 仅支持 .session 后缀"),
            ({"web_token": "short"}, "web_token 长度必须在 8..256 之间"),
            ({"web_token": "valid token"}, "web_token 不能包含空白字符"),
            ({"session_type": "string"}, "session_type=string 需要 string_session"),
        ]
        for patch_data, message in cases:
            with self.subTest(message=message):
                with self.assertRaises(webapp.ApiError) as cm:
                    webapp.normalize_config_patch(patch_data, webapp.DEFAULT_CONFIG)
                self.assertEqual(str(cm.exception), message)

    def test_session_file_helpers_keep_files_under_data_dir(self):
        config_path, stored_path = webapp.session_upload_paths("custom.session")
        self.assertEqual(config_path, (webapp.DATA_DIR / "custom").resolve())
        self.assertEqual(stored_path, (webapp.DATA_DIR / "custom.session").resolve())
        with self.assertRaises(webapp.ApiError):
            webapp.session_upload_paths("../outside.session")

    def test_persist_string_session_if_needed_updates_config(self):
        service = webapp.TelegramService.__new__(webapp.TelegramService)
        service.cfg = {**webapp.DEFAULT_CONFIG, "session_type": "string", "string_session": ""}
        service.client = type("Client", (), {"session": type("Session", (), {"save": lambda self: "1A"})()})()
        saved = {}
        with patch.object(webapp, "save_string_session_value", side_effect=lambda value, base=None: saved.setdefault("cfg", {**base, "string_session": value})):
            self.assertTrue(service.persist_string_session_if_needed())
        self.assertEqual(saved["cfg"]["string_session"], "1A")

    def test_safe_bind_requires_token_for_external_host(self):
        with patch.dict(webapp.os.environ, {}, clear=True):
            with patch.object(webapp, "load_config", return_value={**webapp.DEFAULT_CONFIG, "web_token": ""}):
                webapp.ensure_safe_bind("127.0.0.1")
                with self.assertRaises(RuntimeError):
                    webapp.ensure_safe_bind("0.0.0.0")
        with patch.dict(webapp.os.environ, {"TELEGRAM_WEB_TOKEN": "12345678"}, clear=True):
            webapp.ensure_safe_bind("0.0.0.0")

    def test_session_export_tokens_are_single_use_and_scoped(self):
        with patch.object(webapp, "SESSION_EXPORT_TOKEN_TTL", 1):
            webapp.session_export_tokens.clear()
            token = webapp.create_session_export_token("string")["export_token"]
            with self.assertRaises(webapp.ApiError):
                webapp.consume_session_export_token("file", token)

            token = webapp.create_session_export_token("string")["export_token"]
            webapp.consume_session_export_token("string", token)
            with self.assertRaises(webapp.ApiError):
                webapp.consume_session_export_token("string", token)

            token = webapp.create_session_export_token("file")["export_token"]
            webapp.session_export_tokens[token]["expires_at"] = time.time() - 1
            with self.assertRaises(webapp.ApiError):
                webapp.consume_session_export_token("file", token)


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
        self.assertEqual(response.get_json()["error"], "请求体必须是有效 JSON")

    def test_missing_json_content_type_returns_400(self):
        response = self.client.post("/api/send", data='{"peer":"x","text":"y"}')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])
        self.assertEqual(response.get_json()["error"], "请求体必须是 JSON 对象")

    def test_page_routes_render_without_telegram_login(self):
        for path in ("/login", "/chats", "/chat/test-peer", "/downloads", "/diagnostics"):
            response = self.client.get(path)
            self.addCleanup(response.close)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn("Web Telegram", response.get_data(as_text=True))

    def test_base_template_has_global_feedback_semantics(self):
        response = self.client.get("/login")
        self.addCleanup(response.close)
        html = response.get_data(as_text=True)
        for fragment in (
            'id="topStatus" class="app-subtitle" role="status" aria-live="polite" aria-atomic="true"',
            'type="button" onclick="refreshStatus()" aria-label="刷新 Telegram 连接状态" title="刷新 Telegram 连接状态"',
            '<nav class="bottom-nav" aria-label="主导航">',
            'href="/login" aria-label="打开登录页" aria-current="page"',
            'id="toast" role="status" aria-live="polite" aria-atomic="false"',
            'class="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirmTitle" aria-describedby="confirmMessage"',
        ):
            self.assertIn(fragment, html)

    def test_auth_page_has_accessible_token_form_semantics(self):
        with patch.dict(webapp.os.environ, {"TELEGRAM_WEB_TOKEN": "12345678"}, clear=True):
            response = self.client.get("/auth?next=/chats")
            self.addCleanup(response.close)
        html = response.get_data(as_text=True)
        for fragment in (
            '<section class="phone-card" aria-labelledby="authTitle">',
            '<h1 id="authTitle">访问验证</h1>',
            '<section class="card" aria-labelledby="authFormTitle">',
            '<h2 id="authFormTitle">Web Token</h2>',
            '<label for="authToken">Token</label>',
            'id="authToken" name="token" type="password" autocomplete="current-password" autofocus aria-label="Web Token"',
        ):
            self.assertIn(fragment, html)

    def test_chats_page_has_accessible_dialog_list_semantics(self):
        response = self.client.get("/chats")
        self.addCleanup(response.close)
        html = response.get_data(as_text=True)
        for fragment in (
            '<section class="mobile-panel" aria-labelledby="dialogsTitle">',
            '<h1 id="dialogsTitle">会话</h1>',
            'onclick="loadDialogs()" aria-label="刷新会话列表" title="刷新会话列表"',
            '<div class="search-wrap" role="search" aria-label="搜索会话">',
            'id="dialogSearch" type="search" placeholder="搜索会话、用户名、peer、ID" oninput="filterDialogs()" aria-label="搜索会话、用户名、peer 或 ID" aria-controls="dialogList" autocomplete="off"',
            'id="dialogList" class="dialog-list" role="list" aria-labelledby="dialogsTitle" aria-live="polite" aria-busy="true"',
        ):
            self.assertIn(fragment, html)

    def test_downloads_page_has_accessible_status_semantics(self):
        response = self.client.get("/downloads")
        self.addCleanup(response.close)
        html = response.get_data(as_text=True)
        for fragment in (
            '<section class="mobile-panel" aria-labelledby="downloadsTitle">',
            '<h1 id="downloadsTitle">下载</h1>',
            '支持暂停、恢复、取消任务、移除终态记录和分页查看文件',
            'onclick="loadDownloadsPage()" aria-label="刷新下载任务和文件" title="刷新下载任务和文件"',
            '<h2 class="section-title" id="downloadTaskTitle">任务</h2>',
            'id="downloadTaskList" class="download-list" role="list" aria-labelledby="downloadTaskTitle" aria-live="polite" aria-busy="true"',
            '<h2 class="section-title" id="downloadFileTitle">已下载</h2>',
            'onclick="loadDownloadFiles(true)" aria-label="刷新已下载文件"',
            'id="downloadFileStatus" class="download-summary" role="status" aria-live="polite" aria-atomic="true" aria-busy="true"',
            'id="downloadFileList" class="download-list" role="list" aria-labelledby="downloadFileTitle" aria-live="polite" aria-busy="true"',
            'id="downloadFileMore" class="small-btn gray" type="button" onclick="loadDownloadFiles(false)" aria-controls="downloadFileList" aria-label="加载更多已下载文件"',
        ):
            self.assertIn(fragment, html)

    def test_chat_page_has_accessible_message_and_composer_semantics(self):
        response = self.client.get("/chat/test-peer")
        self.addCleanup(response.close)
        html = response.get_data(as_text=True)
        for fragment in (
            '<section class="chat-page" data-peer="test-peer" aria-labelledby="chatTitle">',
            '<button class="back-btn" type="button" onclick="location.href=\'/chats\'" aria-label="返回会话列表">',
            '<div class="chat-title" id="chatTitle">test-peer</div>',
            'onclick="loadMessages()" aria-label="刷新消息" title="刷新消息"',
            'id="messageList" class="message-list" role="log" aria-label="消息列表" aria-live="polite" aria-relevant="additions text" aria-busy="true"',
            '<div class="composer-mini" role="group" aria-label="消息操作">',
            'data-composer-target="textComposer" onclick="toggleComposer(\'textComposer\')" aria-controls="textComposer" aria-expanded="false"',
            'data-composer-target="fileComposer" onclick="toggleComposer(\'fileComposer\')" aria-controls="fileComposer" aria-expanded="false"',
            'onclick="loadOlderMessages()" aria-controls="messageList" aria-label="加载更早消息"',
            'id="textComposer" class="composer-panel" role="region" aria-label="文字消息发送区" aria-hidden="true" aria-busy="false"',
            'id="messageInput" placeholder="输入消息（支持 Markdown）" aria-label="消息内容"',
            'id="fileComposer" class="composer-panel" role="region" aria-label="媒体或文件发送区" aria-hidden="true" aria-busy="false"',
            'id="sendFileInput" type="file" aria-label="选择要发送的媒体或文件"',
            'id="captionInput" placeholder="说明文字，可选" aria-label="媒体或文件说明文字" autocomplete="off"',
            'id="mediaViewer" class="media-viewer" role="dialog" aria-modal="true" aria-labelledby="viewerTitle" aria-describedby="viewerIndex"',
            'id="viewerIndex" aria-live="polite" aria-atomic="true"',
            'id="viewerDownload" class="viewer-btn" type="button" aria-label="创建当前媒体下载任务"',
            'id="viewerClose" class="viewer-btn" type="button" aria-label="关闭媒体查看器"',
            'id="viewerPrev" class="viewer-nav left" type="button" aria-label="上一项媒体"',
            'id="viewerNext" class="viewer-nav right" type="button" aria-label="下一项媒体"',
        ):
            self.assertIn(fragment, html)

    def test_diagnostics_page_has_accessible_status_semantics(self):
        response = self.client.get("/diagnostics")
        self.addCleanup(response.close)
        html = response.get_data(as_text=True)
        for fragment in (
            'aria-labelledby="diagnosticsTitle"',
            'id="diagnosticsSummary" class="diagnostics-summary" role="status" aria-live="polite" aria-atomic="true" aria-busy="true"',
            'type="button" onclick="loadDiagnosticsPage()" aria-label="刷新诊断状态" title="刷新诊断状态"',
            'id="diagnosticsConfig" class="diagnostics-list" role="list" aria-labelledby="diagnosticsConfigTitle" aria-busy="true"',
            'id="diagnosticsAuth" class="diagnostics-list" role="list" aria-labelledby="diagnosticsAuthTitle" aria-busy="true"',
            'id="diagnosticsRuntime" class="diagnostics-list" role="list" aria-labelledby="diagnosticsRuntimeTitle" aria-busy="true"',
            'id="diagnosticsPaths" class="diagnostics-list" role="list" aria-labelledby="diagnosticsPathsTitle" aria-busy="true"',
        ):
            self.assertIn(fragment, html)

    def test_login_page_has_accessible_form_semantics(self):
        response = self.client.get("/login")
        self.addCleanup(response.close)
        html = response.get_data(as_text=True)
        for fragment in (
            '<section class="phone-card" aria-labelledby="loginHeroTitle">',
            '<h1 id="loginHeroTitle">Web Telegram</h1>',
            '<section class="card" aria-labelledby="loginConfigTitle">',
            '<h2 id="loginConfigTitle">手机号登录</h2>',
            '<label for="api_id">api_id</label><input id="api_id" inputmode="numeric" autocomplete="off" aria-describedby="apiIdHelp" pattern="[0-9]*"',
            '必须是 1 到 2147483647 之间的数字。',
            '<label for="api_hash">api_hash</label><input id="api_hash" autocomplete="off" spellcheck="false" aria-describedby="apiHashHelp" pattern="[0-9a-fA-F]{32}"',
            'id="apiHashHelp" class="sr-only"',
            '必须是 32 位十六进制字符串；已保存时留空会沿用当前 api_hash。',
            '<label for="phone">手机号</label><input id="phone" inputmode="tel" autocomplete="tel" aria-describedby="phoneHelp" pattern="\\+?[0-9]{5,20}"',
            '可带加号，数字长度 5 到 20。',
            '<label for="proxy">SOCKS4/5 代理</label><input id="proxy" autocomplete="off" aria-describedby="proxyHelp"',
            '仅支持 socks4:// 或 socks5://，host 必填，端口默认 1080 且必须在 1 到 65535 之间；不能包含 path、query 或 fragment；已保存代理时留空会沿用当前代理。',
            '只填写 data 目录内文件名，可带或不带 .session 后缀；已保存时留空会沿用当前 .session 文件。',
            '<label for="string_session">StringSession</label><textarea id="string_session" autocomplete="off" spellcheck="false" aria-describedby="stringSessionHelp"',
            '<label for="download_threads">下载线程</label><input id="download_threads" type="number" min="1" max="128" inputmode="numeric" aria-describedby="downloadThreadsHelp"',
            '必须是 1 到 128 之间的数字。',
            '<label for="cache_limit_mb">缓存上限(MB)</label><input id="cache_limit_mb" type="number" min="128" max="10240" inputmode="numeric" aria-describedby="cacheLimitHelp"',
            '必须是 128 到 10240 之间的数字。',
            '<label for="web_token">Web Token</label><input id="web_token" type="password" autocomplete="new-password" aria-describedby="webTokenHelp"',
            '长度 8 到 256 字符，不能包含空白；已保存时留空不会修改 Web Token。',
            '<div class="action-grid" role="group" aria-label="登录操作">',
            '<section class="card" aria-labelledby="sessionMigrationTitle">',
            '<div class="action-grid" role="group" aria-label="StringSession 操作">',
            '<label for="sessionFileInput">.session 文件</label><input id="sessionFileInput" type="file" accept=".session" aria-describedby="sessionUploadHelp">',
            '选择需要导入的 .session 文件；导入后当前客户端会重置并切换到该会话。',
            '<div class="action-grid" role="group" aria-label=".session 文件操作">',
            '<button type="button" class="gray" onclick="saveLoginConfig()">保存配置</button>',
        ):
            self.assertIn(fragment, html)

    def test_non_object_json_returns_400(self):
        response = self.client.post("/api/send", json=[])
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])
        self.assertEqual(response.get_json()["error"], "请求体必须是 JSON 对象")

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

    def test_open_ended_and_suffix_range_requests(self):
        response = self.client.get("/download-file/unit-test-download.txt", headers={"Range": "bytes=3-"}, buffered=True)
        self.addCleanup(response.close)
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.data, b"def")
        self.assertEqual(response.headers["Content-Range"], "bytes 3-5/6")

        response = self.client.get("/download-file/unit-test-download.txt", headers={"Range": "bytes=-2"}, buffered=True)
        self.addCleanup(response.close)
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.data, b"ef")
        self.assertEqual(response.headers["Content-Range"], "bytes 4-5/6")

    def test_invalid_range_request_returns_416(self):
        response = self.client.get("/download-file/unit-test-download.txt", headers={"Range": "bytes=3-1"})
        self.assertEqual(response.status_code, 416)
        self.assertEqual(response.headers["Content-Range"], "bytes */6")

        response = self.client.get("/download-file/unit-test-download.txt", headers={"Range": "bytes=1-2,3-4"})
        self.assertEqual(response.status_code, 416)
        self.assertEqual(response.headers["Content-Range"], "bytes */6")

    def test_non_bytes_range_is_ignored(self):
        response = self.client.get("/download-file/unit-test-download.txt", headers={"Range": "items=1-2"}, buffered=True)
        self.addCleanup(response.close)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"abcdef")
        self.assertEqual(response.headers["Accept-Ranges"], "bytes")

    def test_unsatisfiable_range_request(self):
        response = self.client.get("/download-file/unit-test-download.txt", headers={"Range": "bytes=99-100"})
        self.assertEqual(response.status_code, 416)
        self.assertEqual(response.headers["Content-Range"], "bytes */6")

    def test_list_download_files_skips_partial_file(self):
        partial = webapp.DOWNLOAD_DIR / "unit-test-download.txt.part"
        partial.write_text("partial", "utf-8")
        self.addCleanup(partial.unlink, missing_ok=True)
        names = {row["name"] for row in webapp.list_download_files()}
        self.assertIn("unit-test-download.txt", names)
        self.assertNotIn("unit-test-download.txt.part", names)

    def test_download_files_api_paginates_globally(self):
        with TemporaryDirectory() as tmp:
            download_dir = Path(tmp) / "Download"
            pictures_dir = Path(tmp) / "Pictures"
            download_dir.mkdir()
            pictures_dir.mkdir()
            files = [
                (download_dir / "old.txt", 100),
                (pictures_dir / "new.jpg", 300),
                (download_dir / "middle.bin", 200),
            ]
            for path, mtime in files:
                path.write_text(path.name, "utf-8")
                webapp.os.utime(path, (mtime, mtime))
            with patch.object(webapp, "DOWNLOAD_DIR", download_dir), patch.object(webapp, "PICTURES_DIR", pictures_dir):
                rows, total = webapp.list_download_files(limit=2, offset=1, include_total=True)
                self.assertEqual(total, 3)
                self.assertEqual([row["name"] for row in rows], ["middle.bin", "old.txt"])

                response = self.client.get("/api/download-files?limit=2&offset=1")
                self.assertEqual(response.status_code, 200)
                data = response.get_json()["data"]
                self.assertEqual(data["total"], 3)
                self.assertFalse(data["has_more"])
                self.assertEqual([row["name"] for row in data["items"]], ["middle.bin", "old.txt"])

    def test_download_files_api_validates_pagination_args(self):
        cases = [
            ("/api/dialogs?limit=501", "limit 必须在 1..500 之间"),
            ("/api/messages?peer=test&limit=201", "limit 必须在 1..200 之间"),
            ("/api/messages?peer=test&offset_id=-1", "offset_id 必须在 0..9223372036854775807 之间"),
            ("/api/download-files?limit=0", "limit 必须在 1..100 之间"),
            ("/api/download-files?offset=100001", "offset 必须在 0..100000 之间"),
            ("/api/download-files?offset=abc", "offset 必须是数字"),
        ]
        for path, message in cases:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["error"], message)

    def test_internal_api_errors_are_not_exposed(self):
        with patch.object(webapp.tg, "status", new=lambda: object()), patch.object(webapp.tg, "run", side_effect=RuntimeError("secret internal path")):
            with self.assertLogs(webapp.app.logger.name, level="ERROR"):
                response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        self.assertEqual(data["error"], webapp.INTERNAL_ERROR_MESSAGE)
        self.assertIn("error_id", data)
        self.assertNotIn("secret", data["error"])

    def test_public_runtime_errors_remain_actionable(self):
        with patch.object(webapp.tg, "status", new=lambda: object()), patch.object(webapp.tg, "run", side_effect=RuntimeError("Telegram 未登录")):
            response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Telegram 未登录")

    def test_diagnostics_api_returns_only_redacted_state(self):
        with TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            config_file = data_dir / "config.json"
            cfg = {
                **webapp.DEFAULT_CONFIG,
                "api_id": 123,
                "api_hash": "abcdefabcdefabcdefabcdefabcdefab",
                "phone": "+1234567890",
                "proxy": "socks5://user-secret:pass-secret@127.0.0.1:1080",
                "session_file": str(data_dir / "telegram"),
                "string_session": "string-session-secret",
                "web_token": "config-token-secret",
            }
            with patch.object(webapp, "DATA_DIR", data_dir), patch.object(webapp, "CONFIG_FILE", config_file):
                webapp.save_config(cfg)
                response = self.client.get("/api/diagnostics", headers={"X-Web-Telegram-Token": "config-token-secret"})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()["data"]
        blob = json.dumps(data, ensure_ascii=False)
        for secret in ("abcdefabcdefabcdefabcdefabcdefab", "+1234567890", "user-secret", "pass-secret", "string-session-secret", "config-token-secret"):
            self.assertNotIn(secret, blob)
        self.assertTrue(data["config"]["api_hash_saved"])
        self.assertTrue(data["config"]["proxy_redacted"])
        self.assertTrue(data["web_auth"]["enabled"])

    def test_import_session_file_updates_config_without_connecting(self):
        with TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            config_file = data_dir / "config.json"
            def close_coro(coro):
                coro.close()
                return {"message": "ok"}
            with patch.object(webapp, "DATA_DIR", data_dir), patch.object(webapp, "CONFIG_FILE", config_file), patch.object(webapp.tg, "reload_config", lambda: None), patch.object(webapp.tg, "run", close_coro):
                response = self.client.post("/api/session/file", data={"file": (BytesIO(b"session-bytes"), "imported.session")}, content_type="multipart/form-data")
                self.assertEqual(response.status_code, 200)
                cfg = webapp.load_config()
                self.assertEqual(cfg["session_type"], "file")
                self.assertEqual(cfg["session_file"], str((data_dir / "imported").resolve()))
                self.assertEqual((data_dir / "imported.session").read_bytes(), b"session-bytes")

    def test_export_session_file_downloads_current_file(self):
        with TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            config_file = data_dir / "config.json"
            session_file = data_dir / "telegram.session"
            session_file.write_bytes(b"session-bytes")
            cfg = {**webapp.DEFAULT_CONFIG, "session_file": str((data_dir / "telegram").resolve())}
            with patch.object(webapp, "DATA_DIR", data_dir), patch.object(webapp, "CONFIG_FILE", config_file):
                webapp.save_config(cfg)
                token = self.client.post("/api/session/export-token", json={"kind": "file"}).get_json()["data"]["export_token"]
                response = self.client.get(f"/api/session/file?export_token={token}")
                self.addCleanup(response.close)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, b"session-bytes")
                self.assertIn("attachment", response.headers.get("Content-Disposition", ""))

                response = self.client.get(f"/api/session/file?export_token={token}")
                self.assertEqual(response.status_code, 403)

    def test_session_exports_require_one_time_token(self):
        with TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "config.json"
            cfg = {**webapp.DEFAULT_CONFIG, "string_session": "test-session-value"}
            with patch.object(webapp, "CONFIG_FILE", config_file):
                webapp.save_config(cfg)
                response = self.client.get("/api/session/string")
                self.assertEqual(response.status_code, 403)

                token = self.client.post("/api/session/export-token", json={"kind": "string"}).get_json()["data"]["export_token"]
                response = self.client.get(f"/api/session/string?export_token={token}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json()["data"]["string_session"], "test-session-value")

                response = self.client.get(f"/api/session/string?export_token={token}")
                self.assertEqual(response.status_code, 403)

    def test_session_export_token_rejects_invalid_kind(self):
        response = self.client.post("/api/session/export-token", json={"kind": "bad"})
        self.assertEqual(response.status_code, 400)

    def test_string_session_import_rejects_invalid_value(self):
        response = self.client.post("/api/session/string", json={"string_session": "not-a-session"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("string_session", response.get_json()["error"])

    def test_task_delete_removes_record_and_keeps_cancel_signal(self):
        store = webapp.TaskStore()
        controls = {}
        task_id = store.create("download_media")
        controls[task_id] = {"paused": False, "canceled": False}
        with patch.object(webapp, "tasks", store), patch.object(webapp, "task_controls", controls):
            response = self.client.delete(f"/api/task/{task_id}")
            self.assertEqual(response.status_code, 200)
            self.assertFalse(store.get(task_id))
            self.assertTrue(controls[task_id]["canceled"])

    def test_task_delete_terminal_record_clears_control_state(self):
        store = webapp.TaskStore()
        controls = {}
        task_id = store.create("download_media")
        controls[task_id] = {"paused": True, "canceled": False}
        store.update(task_id, status="done")
        with patch.object(webapp, "tasks", store), patch.object(webapp, "task_controls", controls):
            response = self.client.delete(f"/api/task/{task_id}")
            self.assertEqual(response.status_code, 200)
            self.assertFalse(store.get(task_id))
            self.assertNotIn(task_id, controls)

    def test_pause_rejects_terminal_task(self):
        store = webapp.TaskStore()
        controls = {}
        task_id = store.create("download_media")
        store.update(task_id, status="done")
        with patch.object(webapp, "tasks", store), patch.object(webapp, "task_controls", controls):
            response = self.client.post(f"/api/task/{task_id}/pause", json={})
            self.assertEqual(response.status_code, 400)
            self.assertFalse(response.get_json()["success"])
            self.assertNotIn(task_id, controls)

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
            self.assertEqual(response.get_json()["error"], "需要 Web Token，请先验证")

            response = self.client.get("/api/tasks", headers={"X-Web-Telegram-Token": "12345678"})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.get_json()["success"])

            response = self.client.get("/api/diagnostics")
            self.assertEqual(response.status_code, 401)
            response = self.client.get("/api/diagnostics", headers={"X-Web-Telegram-Token": "12345678"})
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

            response = self.client.get("/diagnostics")
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
