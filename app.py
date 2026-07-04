import asyncio
import json
import mimetypes
import os
import re
import secrets
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse, unquote, quote

import socks
from flask import Flask, request, jsonify, render_template, redirect, send_from_directory, send_file, Response, abort, make_response
from flask_socketio import SocketIO
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession
from werkzeug.exceptions import BadRequest

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DOWNLOAD_DIR = BASE_DIR / "Download"
PICTURES_DIR = BASE_DIR / "Pictures"
CACHE_DIR = DATA_DIR / "media-cache"
UPLOAD_DIR = DATA_DIR / "uploads"

for p in [DATA_DIR, DOWNLOAD_DIR, PICTURES_DIR, CACHE_DIR, UPLOAD_DIR]:
    p.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = DATA_DIR / "config.json"
TASK_HISTORY_FILE = DATA_DIR / "task-history.json"

DEFAULT_CONFIG = {
    "api_id": 0,
    "api_hash": "",
    "phone": "",
    "proxy": "",
    "session_type": "file",
    "session_file": str(DATA_DIR / "telegram"),
    "string_session": "",
    "download_threads": 16,
    "cache_limit_mb": 1024,
    "web_token": "",
}
CONFIG_FIELDS = ["api_id", "api_hash", "phone", "proxy", "session_type", "session_file", "string_session", "download_threads", "cache_limit_mb", "web_token"]
SECRET_CONFIG_FIELDS = ["api_hash", "session_file", "string_session", "web_token"]
AUTH_COOKIE = "telegram_web_token"

app = Flask(__name__)
app.config["SECRET_KEY"] = "web-telegram-flask"
socketio = SocketIO(app, async_mode="threading")


class ApiError(ValueError):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.code = code


INTERNAL_ERROR_MESSAGE = "内部错误，请查看服务端日志"
PUBLIC_RUNTIME_ERRORS = {
    "Telegram 未登录",
    "该消息没有媒体",
    "媒体下载失败",
    "任务已取消",
}


def load_config():
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        data = json.loads(CONFIG_FILE.read_text("utf-8"))
    except Exception:
        data = {}
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(data)
    cfg["download_threads"] = coerce_int_range(cfg.get("download_threads"), 16, 1, 128, "download_threads", strict=False)
    cfg["cache_limit_mb"] = coerce_int_range(cfg.get("cache_limit_mb"), 1024, 128, 10240, "cache_limit_mb", strict=False)
    cfg["api_id"] = coerce_int_range(cfg.get("api_id"), 0, 0, 2**31 - 1, "api_id", strict=False)
    if cfg.get("session_type") not in ("file", "string"):
        cfg["session_type"] = "file"
    return cfg


def save_config(cfg):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")


def safe_filename(name):
    name = str(name or "file").strip()
    for ch in '\\/:*?"<>|':
        name = name.replace(ch, "_")
    return name or "file"


def format_size(num):
    num = float(num or 0)
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while num >= 1024 and i < len(units) - 1:
        num /= 1024
        i += 1
    return f"{int(num)} {units[i]}" if i == 0 else f"{num:.2f} {units[i]}"


def parse_proxy(proxy_url):
    proxy_url = str(proxy_url or "").strip()
    if not proxy_url:
        return None
    u = urlparse(proxy_url)
    scheme = u.scheme.lower()
    if scheme not in ("socks5", "socks4"):
        raise ValueError("仅支持 socks4/socks5")
    if not u.hostname:
        raise ValueError("代理地址缺少 host")
    if u.path not in ("", "/") or u.query or u.fragment:
        raise ValueError("代理地址不能包含 path/query/fragment")
    port = int(u.port or 1080)
    if port < 1 or port > 65535:
        raise ValueError("代理端口必须在 1..65535 之间")
    proxy_type = socks.SOCKS5 if scheme == "socks5" else socks.SOCKS4
    return (proxy_type, u.hostname, port, True, unquote(u.username) if u.username else None, unquote(u.password) if u.password else None)


def coerce_int_range(value, default, min_value, max_value, field, strict=True):
    try:
        number = int(value)
    except Exception:
        if strict:
            raise ApiError(f"{field} 必须是数字")
        number = int(default)
    if number < min_value or number > max_value:
        if strict:
            raise ApiError(f"{field} 必须在 {min_value}..{max_value} 之间")
        number = int(default)
    return number


def request_json_object():
    if not request.is_json:
        raise ApiError("请求体必须是 JSON 对象")
    try:
        data = request.get_json(silent=False)
    except BadRequest:
        raise ApiError("请求体必须是有效 JSON")
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ApiError("请求体必须是 JSON 对象")
    return data


def query_int_arg(name, default, min_value, max_value):
    value = request.args.get(name)
    if value in (None, ""):
        return int(default)
    return coerce_int_range(value, default, min_value, max_value, name)


def public_config(cfg):
    data = dict(cfg)
    for field in SECRET_CONFIG_FIELDS:
        data[f"{field}_saved"] = bool(data.get(field))
        data[field] = ""
    data["proxy_saved"] = bool(data.get("proxy"))
    data["proxy_redacted"] = proxy_has_credentials(data.get("proxy", ""))
    data["proxy"] = public_proxy(data.get("proxy", ""))
    return data


def proxy_has_credentials(proxy_url):
    try:
        parsed = urlparse(str(proxy_url or "").strip())
    except Exception:
        return False
    return bool(parsed.username or parsed.password)


def public_proxy(proxy_url):
    proxy_url = str(proxy_url or "").strip()
    if not proxy_url:
        return ""
    try:
        parsed = urlparse(proxy_url)
    except Exception:
        return ""
    if parsed.username or parsed.password:
        return ""
    return proxy_url


def normalize_session_file(value):
    raw = str(value or "").strip()
    if not raw:
        return str(DATA_DIR / "telegram")
    path = Path(raw)
    if path.is_absolute() or path.name != raw or ".." in path.parts:
        raise ApiError("session_file 只能是 data 目录内的文件名")
    if path.suffix and path.suffix != ".session":
        raise ApiError("session_file 仅支持 .session 后缀")
    name = safe_filename(path.stem if path.suffix == ".session" else path.name)
    if name in ("", ".", ".."):
        raise ApiError("session_file 文件名无效")
    return str((DATA_DIR / name).resolve())


def normalize_web_token(value):
    token = str(value or "").strip()
    if not token:
        return ""
    if len(token) < 8 or len(token) > 256:
        raise ApiError("web_token 长度必须在 8..256 之间")
    if any(ch.isspace() for ch in token):
        raise ApiError("web_token 不能包含空白字符")
    return token


def normalize_api_hash(value):
    text = str(value or "").strip()
    if not text:
        return ""
    if not re.fullmatch(r"[0-9a-fA-F]{32}", text):
        raise ApiError("api_hash 必须是 32 位十六进制字符串")
    return text.lower()


def normalize_phone(value):
    text = str(value or "").strip()
    if not text:
        return ""
    if not re.fullmatch(r"\+?[0-9]{5,20}", text):
        raise ApiError("phone 格式无效")
    return text


def normalize_string_session(value):
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        StringSession(text)
    except Exception:
        raise ApiError("string_session 格式无效")
    return text


def normalize_proxy_url(value):
    proxy = str(value or "").strip()
    if not proxy:
        return ""
    parsed = urlparse(proxy)
    try:
        parse_proxy(proxy)
    except ValueError as e:
        raise ApiError(str(e))
    auth = ""
    if parsed.username:
        auth = quote(unquote(parsed.username), safe="")
        if parsed.password is not None:
            auth += ":" + quote(unquote(parsed.password), safe="")
        auth += "@"
    port = parsed.port or 1080
    return f"{parsed.scheme.lower()}://{auth}{parsed.hostname}:{port}"


def normalize_config_patch(data, base=None, require_string_session=True):
    cfg = dict(DEFAULT_CONFIG)
    if base:
        cfg.update(base)
    for key in CONFIG_FIELDS:
        if key not in data:
            continue
        value = data[key]
        if key == "api_id":
            cfg[key] = coerce_int_range(value, 0, 1, 2**31 - 1, key)
        elif key == "download_threads":
            cfg[key] = coerce_int_range(value, 16, 1, 128, key)
        elif key == "cache_limit_mb":
            cfg[key] = coerce_int_range(value, 1024, 128, 10240, key)
        elif key == "session_type":
            session_type = str(value or "file").strip()
            if session_type not in ("file", "string"):
                raise ApiError("session_type 仅支持 file/string")
            cfg[key] = session_type
        elif key == "session_file":
            cfg[key] = normalize_session_file(value)
        elif key == "proxy":
            cfg[key] = normalize_proxy_url(value)
        elif key == "web_token":
            cfg[key] = normalize_web_token(value)
        elif key == "api_hash":
            next_value = normalize_api_hash(value)
            if next_value:
                cfg[key] = next_value
        elif key == "phone":
            cfg[key] = normalize_phone(value)
        elif key == "string_session":
            next_value = normalize_string_session(value)
            if next_value:
                cfg[key] = next_value
        else:
            cfg[key] = str(value or "").strip()
    if require_string_session and cfg.get("session_type") == "string" and not cfg.get("string_session"):
        raise ApiError("session_type=string 需要 string_session")
    return cfg


def session_file_path(cfg=None):
    cfg = cfg or load_config()
    return Path(cfg.get("session_file") or str(DATA_DIR / "telegram")).resolve()


def session_storage_path(cfg=None):
    base = session_file_path(cfg)
    return base if base.suffix == ".session" else base.with_suffix(".session")


def session_upload_paths(filename):
    raw = str(filename or "telegram.session").strip() or "telegram.session"
    if not raw.endswith(".session"):
        raw += ".session"
    config_path = Path(normalize_session_file(raw))
    return config_path, session_storage_path({"session_file": str(config_path)})


def copy_session_file_upload(upload_file):
    if not upload_file or not upload_file.filename:
        raise ApiError("缺少 .session 文件")
    config_path, target = session_upload_paths(upload_file.filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".upload")
    upload_file.save(tmp)
    try:
        if not tmp.exists() or tmp.stat().st_size <= 0:
            raise ApiError(".session 文件为空")
        tmp.replace(target)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return config_path, target


def save_string_session_value(value, base=None):
    text = normalize_string_session(value)
    if not text:
        raise ApiError("string_session 不能为空")
    cfg = normalize_config_patch({"session_type": "string", "string_session": text}, base or load_config())
    save_config(cfg)
    return cfg


def resolve_under(base_dir, filename):
    base = Path(base_dir).resolve()
    name = str(filename or "").strip()
    if not name:
        return None
    candidate = (base / name).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        return None
    return candidate


def run_host():
    return os.environ.get("TELEGRAM_WEB_HOST") or os.environ.get("HOST") or "127.0.0.1"


def run_port():
    return int(os.environ.get("TELEGRAM_WEB_PORT") or os.environ.get("PORT") or "5000")


def ensure_safe_bind(host):
    if not is_loopback_host(host) and not current_web_token():
        raise RuntimeError("对外监听必须先设置 TELEGRAM_WEB_TOKEN 或配置 web_token")


def is_loopback_host(host):
    return str(host or "").strip().lower() in ("127.0.0.1", "localhost", "::1")


def current_web_token():
    return (os.environ.get("TELEGRAM_WEB_TOKEN") or os.environ.get("WEB_TELEGRAM_TOKEN") or str(load_config().get("web_token") or "")).strip()


def request_token():
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    token = (
        request.headers.get("X-Web-Telegram-Token")
        or request.headers.get("X-Web-Token")
        or request.args.get("token")
        or request.cookies.get(AUTH_COOKIE)
        or ""
    ).strip()
    if token:
        return token
    if request.path == "/auth":
        return request.form.get("token", "").strip()
    return ""


def token_matches(value):
    token = current_web_token()
    return bool(token and value and secrets.compare_digest(str(value), token))


def web_auth_required():
    return bool(current_web_token())


def web_authorized():
    return not web_auth_required() or token_matches(request_token())


def safe_next_url(value):
    target = str(value or "").strip()
    if not target or not target.startswith("/") or target.startswith("//"):
        return "/"
    return target


def unauthorized_response():
    if request.path.startswith("/api/"):
        return fail(ApiError("需要 Web Token", 401))
    if request.path.startswith(("/download-file/", "/pictures/", "/media-cache/")):
        abort(401)
    return redirect("/auth?next=" + quote(request.full_path if request.query_string else request.path, safe=""))


@app.before_request
def require_web_auth():
    path = request.path or ""
    if path.startswith("/static/") or path.startswith("/socket.io/") or path in ("/auth", "/login", "/favicon.ico"):
        return None
    if not web_authorized():
        return unauthorized_response()
    return None


@app.after_request
def remember_query_token(resp):
    token = request.args.get("token", "")
    if token_matches(token):
        resp.set_cookie(AUTH_COOKIE, current_web_token(), httponly=True, samesite="Lax")
    return resp


def peer_raw_id(peer_id):
    if not peer_id:
        return ""
    return str(getattr(peer_id, "channel_id", "") or getattr(peer_id, "chat_id", "") or getattr(peer_id, "user_id", "") or "")


def media_type_of(msg):
    if not msg:
        return ""
    if msg.photo: return "photo"
    if msg.video: return "video"
    if msg.audio: return "audio"
    if msg.voice: return "voice"
    if msg.gif: return "gif"
    if msg.sticker: return "sticker"
    if msg.document: return "document"
    if msg.media: return "media"
    return ""


def file_info_of(msg):
    name, size, mime = "", 0, ""
    try:
        if msg.file:
            name = msg.file.name or ""
            size = msg.file.size or 0
            mime = msg.file.mime_type or ""
    except Exception:
        pass
    return name, size, mime


def message_to_json(msg):
    if not msg:
        return None
    file_name, file_size, mime = file_info_of(msg)
    mt = media_type_of(msg)
    grouped_id = getattr(msg, "grouped_id", None)
    if grouped_id is not None:
        grouped_id = str(grouped_id)
    return {
        "id": msg.id,
        "peer_id": peer_raw_id(msg.peer_id),
        "date": msg.date.isoformat() if msg.date else "",
        "sender_id": str(msg.sender_id or ""),
        "text": msg.message or "",
        "out": bool(msg.out),
        "has_media": bool(msg.media),
        "media_type": mt,
        "file_name": file_name,
        "file_size": file_size,
        "file_size_text": format_size(file_size),
        "mime": mime,
        "grouped_id": grouped_id,
    }


def dialog_to_json(dialog):
    entity = dialog.entity
    username = getattr(entity, "username", "") or ""
    title = getattr(entity, "title", "") or ""
    first_name = getattr(entity, "first_name", "") or ""
    last_name = getattr(entity, "last_name", "") or ""
    name = title or " ".join([first_name, last_name]).strip() or username or str(dialog.id)
    peer = username or str(dialog.id)
    return {
        "id": dialog.id,
        "peer": peer,
        "peer_url": quote(peer, safe=""),
        "name": name,
        "username": username,
        "is_user": dialog.is_user,
        "is_group": dialog.is_group,
        "is_channel": dialog.is_channel,
        "unread_count": dialog.unread_count,
    }


def cache_cleanup(limit_mb):
    limit = int(limit_mb) * 1024 * 1024
    files = [p for p in CACHE_DIR.glob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    if total <= limit:
        return
    files.sort(key=lambda x: x.stat().st_mtime)
    for p in files:
        if total <= limit:
            break
        try:
            total -= p.stat().st_size
            p.unlink(missing_ok=True)
        except Exception:
            pass


class TaskStore:
    def __init__(self, history_file=None, load_history=False):
        self.lock = threading.Lock()
        self.tasks = {}
        self.terminal_statuses = {"done", "error", "canceled"}
        self.history_file = Path(history_file) if history_file else None
        if load_history and self.history_file:
            self.load_history()

    def sanitize_for_history(self, task):
        error = "任务失败" if task.get("error") else ""
        return {
            "id": str(task.get("id") or ""),
            "kind": str(task.get("kind") or ""),
            "status": str(task.get("status") or ""),
            "progress": int(task.get("progress") or 0),
            "downloaded": int(task.get("downloaded") or 0),
            "total": int(task.get("total") or 0),
            "speed": 0,
            "file": Path(str(task.get("file") or "")).name,
            "url": str(task.get("url") or ""),
            "path": "",
            "mime": str(task.get("mime") or ""),
            "error": error,
            "created_at": float(task.get("created_at") or time.time()),
            "updated_at": float(task.get("updated_at") or task.get("created_at") or time.time()),
            "meta": {},
        }

    def load_history(self):
        if not self.history_file:
            return
        try:
            rows = json.loads(self.history_file.read_text("utf-8"))
        except Exception:
            return
        if not isinstance(rows, list):
            return
        with self.lock:
            for row in rows:
                if not isinstance(row, dict):
                    continue
                if row.get("status") not in self.terminal_statuses:
                    continue
                task_id = str(row.get("id") or "")
                if not task_id:
                    continue
                self.tasks[task_id] = self.sanitize_for_history(row)

    def save_history(self, max_items=200):
        if not self.history_file:
            return
        with self.lock:
            rows = [
                self.sanitize_for_history(task)
                for task in self.tasks.values()
                if task.get("status") in self.terminal_statuses
            ]
        rows.sort(key=lambda task: task.get("updated_at", 0), reverse=True)
        rows = rows[:max_items]
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            self.history_file.write_text(json.dumps(rows, ensure_ascii=False, indent=2), "utf-8")
        except Exception:
            app.logger.exception("failed to save task history")

    def create(self, kind, meta=None):
        task_id = uuid.uuid4().hex
        with self.lock:
            self.tasks[task_id] = {"id": task_id, "kind": kind, "status": "queued", "progress": 0, "downloaded": 0, "total": 0, "speed": 0, "file": "", "url": "", "path": "", "mime": "", "error": "", "created_at": time.time(), "updated_at": time.time(), "meta": meta or {}}
        return task_id
    def update(self, task_id, force=False, **patch):
        persist = False
        with self.lock:
            if task_id not in self.tasks: return
            current = self.tasks[task_id].get("status")
            next_status = patch.get("status")
            if current in self.terminal_statuses and not force:
                return
            if current == "canceled" and next_status != "canceled" and not force:
                return
            self.tasks[task_id].update(patch)
            self.tasks[task_id]["updated_at"] = time.time()
            persist = self.tasks[task_id].get("status") in self.terminal_statuses
        if persist:
            self.save_history()
    def get(self, task_id):
        with self.lock:
            return dict(self.tasks.get(task_id) or {})
    def list(self):
        with self.lock:
            return [dict(v) for v in self.tasks.values()]
    def delete(self, task_id):
        persist = False
        with self.lock:
            task = self.tasks.pop(task_id, None)
            persist = bool(task and task.get("status") in self.terminal_statuses)
        if persist:
            self.save_history()
    def cleanup(self, max_age=3600, max_items=200):
        now = time.time()
        changed = False
        with self.lock:
            removable = [
                (task_id, task)
                for task_id, task in self.tasks.items()
                if task.get("status") in self.terminal_statuses and now - float(task.get("updated_at") or task.get("created_at") or now) > max_age
            ]
            for task_id, _task in removable:
                self.tasks.pop(task_id, None)
                task_controls.pop(task_id, None)
                changed = True
            if len(self.tasks) > max_items:
                overflow = sorted(self.tasks.items(), key=lambda item: item[1].get("updated_at", 0))[:len(self.tasks) - max_items]
                for task_id, task in overflow:
                    if task.get("status") in self.terminal_statuses:
                        self.tasks.pop(task_id, None)
                        task_controls.pop(task_id, None)
                        changed = True
        if changed:
            self.save_history()


tasks = TaskStore(history_file=TASK_HISTORY_FILE, load_history=True)
task_controls = {}


def task_is_canceled(task_id):
    return bool(task_controls.get(task_id, {}).get("canceled") or tasks.get(task_id).get("status") == "canceled")


def task_finish(task_id, result):
    if task_is_canceled(task_id):
        tasks.update(task_id, status="canceled", force=True)
        task_controls.pop(task_id, None)
        return
    tasks.update(
        task_id,
        status="done",
        progress=100,
        file=result.get("file", ""),
        path=result.get("path", ""),
        url=result.get("url", ""),
        mime=result.get("mime", ""),
        downloaded=result.get("size", 0),
        total=result.get("size", 0),
        speed=0,
    )
    task_controls.pop(task_id, None)


def task_fail(task_id, exc):
    if task_is_canceled(task_id) or str(exc) == "任务已取消":
        tasks.update(task_id, status="canceled", error="", force=True)
        task_controls.pop(task_id, None)
        return
    tasks.update(task_id, status="error", error=str(exc), speed=0)
    task_controls.pop(task_id, None)


class ExecutorHolder:
    def __init__(self):
        self.max_workers = int(load_config().get("download_threads") or 16)
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
    def reload(self):
        next_workers = max(1, min(128, int(load_config().get("download_threads") or 16)))
        if next_workers == self.max_workers:
            return
        old = self.executor
        self.max_workers = next_workers
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        old.shutdown(wait=False, cancel_futures=False)
    def submit(self, fn, *args, **kwargs):
        return self.executor.submit(fn, *args, **kwargs)


executor_holder = ExecutorHolder()


class TelegramService:
    def __init__(self):
        self.cfg = load_config()
        self.client = None
        self.login_phone = ""
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result()

    def reload_config(self):
        self.cfg = load_config()
        executor_holder.reload()
        cache_cleanup(self.cfg.get("cache_limit_mb", 1024))

    def persist_string_session_if_needed(self):
        if self.cfg.get("session_type") != "string" or not self.client:
            return False
        value = self.client.session.save()
        if not value:
            return False
        self.cfg = save_string_session_value(value, self.cfg)
        return True

    def create_client(self):
        api_id = int(self.cfg.get("api_id") or 0)
        api_hash = str(self.cfg.get("api_hash") or "")
        if not api_id or not api_hash:
            raise RuntimeError("请先配置 api_id / api_hash")
        proxy = parse_proxy(self.cfg.get("proxy", ""))
        if self.cfg.get("session_type") == "string":
            session = StringSession(str(self.cfg.get("string_session") or ""))
        else:
            session = self.cfg.get("session_file") or str(DATA_DIR / "telegram")
        client = TelegramClient(session, api_id, api_hash, proxy=proxy, connection_retries=2, request_retries=2, retry_delay=2, timeout=20)

        @client.on(events.NewMessage)
        async def on_new_message(event):
            try:
                socketio.emit("new_message", message_to_json(event.message))
            except Exception:
                pass
        return client

    async def ensure_client(self):
        if self.client and self.client.is_connected():
            return self.client
        if self.client:
            try: await self.client.disconnect()
            except Exception: pass
        self.client = self.create_client()
        await self.client.connect()
        return self.client

    async def reconnect(self):
        if self.client:
            try: await self.client.disconnect()
            except Exception: pass
        self.client = None
        return await self.ensure_client()

    async def reset_client(self):
        if self.client:
            try: await self.client.disconnect()
            except Exception: pass
        self.client = None
        return {"message": "客户端已重置"}

    async def status(self):
        client = await self.ensure_client()
        authorized = await client.is_user_authorized()
        me = None
        if authorized:
            user = await client.get_me()
            me = {"id": user.id, "username": user.username, "first_name": user.first_name, "last_name": user.last_name, "phone": user.phone}
        return {"connected": client.is_connected(), "authorized": authorized, "me": me, "config": {"api_id": self.cfg.get("api_id"), "phone": self.cfg.get("phone"), "proxy": self.cfg.get("proxy"), "session_type": self.cfg.get("session_type"), "download_threads": self.cfg.get("download_threads"), "cache_limit_mb": self.cfg.get("cache_limit_mb")}}

    async def start_login(self, api_id, api_hash, phone, proxy, session_type="file", session_file="", string_session="", download_threads=16, cache_limit_mb=1024):
        self.cfg = normalize_config_patch({
            "api_id": api_id,
            "api_hash": api_hash,
            "phone": phone,
            "proxy": proxy,
            "session_type": session_type,
            "session_file": session_file,
            "string_session": string_session,
            "download_threads": download_threads,
            "cache_limit_mb": cache_limit_mb,
        }, self.cfg, require_string_session=False)
        save_config(self.cfg)
        self.reload_config()
        await self.reconnect()
        client = await self.ensure_client()
        if await client.is_user_authorized():
            return {"message": "当前账号已登录，无需发送验证码"}
        await client.send_code_request(str(phone))
        self.login_phone = str(phone)
        return {"message": "验证码已发送"}

    async def sign_in_code(self, code):
        client = await self.ensure_client()
        phone = self.login_phone or self.cfg.get("phone")
        if not phone:
            raise RuntimeError("缺少手机号")
        try:
            await client.sign_in(phone=phone, code=str(code))
        except SessionPasswordNeededError:
            return {"need_password": True, "message": "需要两步验证密码"}
        self.persist_string_session_if_needed()
        return {"need_password": False, "message": "登录成功"}

    async def sign_in_password(self, password):
        client = await self.ensure_client()
        await client.sign_in(password=str(password))
        self.persist_string_session_if_needed()
        return {"message": "两步验证通过，登录成功"}

    async def logout(self):
        if self.client:
            await self.client.log_out()
            await self.client.disconnect()
            self.client = None
        return {"message": "已退出登录"}

    async def dialogs(self, limit=100):
        client = await self.ensure_client()
        if not await client.is_user_authorized():
            raise RuntimeError("Telegram 未登录")
        result = []
        async for dialog in client.iter_dialogs(limit=int(limit)):
            result.append(dialog_to_json(dialog))
        return result

    async def messages(self, peer, limit=40, offset_id=0):
        client = await self.ensure_client()
        if not await client.is_user_authorized():
            raise RuntimeError("Telegram 未登录")
        entity = await client.get_entity(peer)
        result = []
        async for msg in client.iter_messages(entity, limit=int(limit), offset_id=int(offset_id or 0)):
            row = message_to_json(msg)
            if row: result.append(row)
        result.reverse()
        return result

    async def send_text(self, peer, text):
        client = await self.ensure_client()
        if not await client.is_user_authorized():
            raise RuntimeError("Telegram 未登录")
        entity = await client.get_entity(peer)
        msg = await client.send_message(entity, str(text))
        return message_to_json(msg)

    async def send_file(self, peer, file_path, caption=""):
        client = await self.ensure_client()
        if not await client.is_user_authorized():
            raise RuntimeError("Telegram 未登录")
        entity = await client.get_entity(peer)
        msg = await client.send_file(entity, file_path, caption=caption or "")
        return message_to_json(msg)

    async def get_msg(self, peer, msg_id):
        client = await self.ensure_client()
        if not await client.is_user_authorized():
            raise RuntimeError("Telegram 未登录")
        entity = await client.get_entity(peer)
        return await client.get_messages(entity, ids=int(msg_id))

    def cache_key(self, peer, msg_id):
        return f"{safe_filename(str(peer))}_{int(msg_id)}"

    def find_cached_media(self, peer, msg_id):
        key = self.cache_key(peer, msg_id)
        for p in CACHE_DIR.glob(f"{key}_*"):
            if p.is_file() and not p.name.endswith(".part") and p.stat().st_size > 0:
                return p
        return None

    async def get_media_thumb(self, peer, msg_id):
        client = await self.ensure_client()
        if not await client.is_user_authorized():
            raise RuntimeError("Telegram 未登录")
    
        msg = await self.get_msg(peer, msg_id)
        if not msg or not msg.media:
            raise RuntimeError("该消息没有媒体")
    
        key = self.cache_key(peer, msg_id)
        # 固定扩展，避免每次变名
        thumb_path = CACHE_DIR / f"{key}_thumb.jpg"
    
        # 1) 先命中本地缓存
        if thumb_path.exists() and thumb_path.stat().st_size > 0:
            return {
                "ready": True,
                "cached": True,
                "url": f"/media-cache/{quote(thumb_path.name)}",
                "mime": "image/jpeg",
                "size": thumb_path.stat().st_size,
                "size_text": format_size(thumb_path.stat().st_size),
            }
    
        # 2) 没命中才向 Telegram 拉 thumb（不是原文件）
        path = await client.download_media(msg, file=str(thumb_path), thumb=-1)
        if not path:
            return {"ready": False, "no_thumb": True}
    
        p = Path(path)
        if not p.exists() or p.stat().st_size <= 0:
            return {"ready": False, "no_thumb": True}
    
        cache_cleanup(self.cfg.get("cache_limit_mb", 1024))
    
        return {
            "ready": True,
            "cached": False,
            "url": f"/media-cache/{quote(p.name)}",
            "mime": "image/jpeg",
            "size": p.stat().st_size,
            "size_text": format_size(p.stat().st_size),
        }

    async def prepare_media(self, peer, msg_id, task_id=None, target_dir=None):
        client = await self.ensure_client()
        if not await client.is_user_authorized():
            raise RuntimeError("Telegram 未登录")
        msg = await self.get_msg(peer, msg_id)
        if not msg or not msg.media:
            raise RuntimeError("该消息没有媒体")
        file_name, total_size, mime0 = file_info_of(msg)
        media_type = media_type_of(msg)
        target_dir = target_dir or CACHE_DIR
        key = self.cache_key(peer, msg_id)
        if file_name:
            filename = f"{key}_{safe_filename(file_name)}"
        else:
            ext = mimetypes.guess_extension(mime0 or "") or (".jpg" if media_type == "photo" else ".mp4" if media_type == "video" else ".bin")
            filename = f"{key}_{media_type}{ext}"
        target_path = target_dir / filename
        if target_path.exists() and target_path.stat().st_size > 0:
            mime = mimetypes.guess_type(str(target_path))[0] or mime0 or "application/octet-stream"
            url = f"/media-cache/{quote(target_path.name)}" if target_dir == CACHE_DIR else f"/pictures/{quote(target_path.name)}" if target_dir == PICTURES_DIR else f"/download-file/{quote(target_path.name)}"
            return {"ready": True, "file": target_path.name, "path": str(target_path), "url": url, "mime": mime, "size": target_path.stat().st_size, "size_text": format_size(target_path.stat().st_size)}
        if task_id and task_is_canceled(task_id):
            raise RuntimeError("任务已取消")
        last_bytes = 0
        last_time = time.time()

        def progress_callback(current, total):
            nonlocal last_bytes, last_time
            if not task_id:
                return
            ctl = task_controls.get(task_id, {})
            if ctl.get("canceled"):
                raise RuntimeError("任务已取消")
            while ctl.get("paused"):
                tasks.update(task_id, status="paused")
                time.sleep(0.2)
                ctl = task_controls.get(task_id, {})
                if ctl.get("canceled"):
                    raise RuntimeError("任务已取消")
            now = time.time()
            delta_t = max(0.001, now - last_time)
            delta_b = max(0, int(current) - int(last_bytes))
            speed = int(delta_b / delta_t)
            last_bytes = int(current)
            last_time = now
            total = int(total or total_size or 0)
            progress = int((int(current) / total) * 100) if total > 0 else 0
            tasks.update(task_id, status="running", downloaded=int(current), total=total, progress=max(0, min(100, progress)), speed=speed)

        partial_path = target_path.with_name(target_path.name + ".part")
        downloaded_path = None
        try:
            partial_path.unlink(missing_ok=True)
            path = await client.download_media(msg, file=str(partial_path), progress_callback=progress_callback)
            if not path:
                raise RuntimeError("媒体下载失败")
            downloaded_path = Path(path)
            if not downloaded_path.exists() or downloaded_path.stat().st_size <= 0:
                raise RuntimeError("媒体下载失败")
            if task_id and task_is_canceled(task_id):
                raise RuntimeError("任务已取消")
            downloaded_path.replace(target_path)
        except Exception:
            for leftover in (partial_path, downloaded_path):
                if leftover:
                    try:
                        Path(leftover).unlink(missing_ok=True)
                    except OSError:
                        pass
            raise
        p = target_path
        mime = mimetypes.guess_type(str(p))[0] or mime0 or "application/octet-stream"
        size = p.stat().st_size
        url = f"/media-cache/{quote(p.name)}" if target_dir == CACHE_DIR else f"/pictures/{quote(p.name)}" if target_dir == PICTURES_DIR else f"/download-file/{quote(p.name)}"
        if task_id:
            tasks.update(task_id, status="done", progress=100, downloaded=size, total=size, speed=0, file=p.name, path=str(p), url=url, mime=mime)
        cache_cleanup(self.cfg.get("cache_limit_mb", 1024))
        return {"ready": True, "file": p.name, "path": str(p), "url": url, "mime": mime, "size": size, "size_text": format_size(size)}

    async def download_media(self, peer, msg_id, task_id=None):
        msg = await self.get_msg(peer, msg_id)
        if not msg or not msg.media:
            raise RuntimeError("该消息没有媒体")
        mt = media_type_of(msg)
        target_dir = PICTURES_DIR if mt == "photo" else DOWNLOAD_DIR
        return await self.prepare_media(peer, msg_id, task_id=task_id, target_dir=target_dir)


tg = TelegramService()


def ok(data=None, message="ok"):
    return jsonify({"success": True, "message": message, "data": data})


def fail(e, code=500):
    if not isinstance(e, BaseException):
        return jsonify({"success": False, "error": str(e)}), code
    code = getattr(e, "code", code)
    if isinstance(e, ApiError) or code < 500:
        return jsonify({"success": False, "error": str(e)}), code
    if isinstance(e, RuntimeError) and str(e) in PUBLIC_RUNTIME_ERRORS:
        return jsonify({"success": False, "error": str(e)}), 400
    error_id = uuid.uuid4().hex[:12]
    app.logger.error("internal api error %s", error_id, exc_info=(type(e), e, e.__traceback__))
    return jsonify({"success": False, "error": INTERNAL_ERROR_MESSAGE, "error_id": error_id}), 500


def list_download_files(limit=None, offset=0, include_total=False):
    entries = []
    for root, kind, url_prefix in [(DOWNLOAD_DIR, "download", "/download-file"), (PICTURES_DIR, "picture", "/pictures")]:
        for p in root.glob("*"):
            try:
                if p.is_symlink() or not p.is_file() or p.name.endswith(".part"):
                    continue
                st = p.stat()
            except OSError:
                continue
            entries.append((p, st, kind, url_prefix))
    entries.sort(key=lambda row: row[1].st_mtime, reverse=True)
    total = len(entries)
    offset = max(0, int(offset or 0))
    if limit is not None:
        limit = max(0, int(limit))
        entries = entries[offset:offset + limit]
    elif offset:
        entries = entries[offset:]
    result = []
    for p, st, kind, url_prefix in entries:
        mime = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        result.append({"name": p.name, "kind": kind, "size": st.st_size, "size_text": format_size(st.st_size), "mtime": int(st.st_mtime), "url": f"{url_prefix}/{quote(p.name)}", "mime": mime, "is_image": mime.startswith("image/"), "is_video": mime.startswith("video/"), "is_audio": mime.startswith("audio/")})
    if include_total:
        return result, total
    return result


def parse_range_header(range_header, file_size):
    if not range_header:
        return None
    text = str(range_header).strip()
    if not text.startswith("bytes="):
        return None
    spec = text[6:].strip()
    if "," in spec:
        return "invalid"
    if "-" not in spec:
        return "invalid"
    start_s, end_s = spec.split("-", 1)
    start_s, end_s = start_s.strip(), end_s.strip()
    try:
        if start_s == "":
            suffix_len = int(end_s)
            if suffix_len <= 0:
                return "invalid"
            if file_size <= 0:
                return "invalid"
            start = max(0, file_size - suffix_len)
            end = file_size - 1
        else:
            start = int(start_s)
            if start < 0:
                return "invalid"
            end = int(end_s) if end_s else file_size - 1
            if end < start:
                return "invalid"
            if start >= file_size:
                return "unsatisfiable"
            end = min(end, file_size - 1)
    except Exception:
        return "invalid"
    return (start, end)


def send_file_range(path: Path):
    path = Path(path)
    if not path.exists() or not path.is_file():
        abort(404)
    file_size = path.stat().st_size
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    range_header = request.headers.get("Range")
    parsed_range = parse_range_header(range_header, file_size)
    if parsed_range is None:
        response = send_from_directory(path.parent, path.name, as_attachment=False, conditional=not bool(range_header))
        response.headers.setdefault("Accept-Ranges", "bytes")
        return response
    if parsed_range in ("invalid", "unsatisfiable"):
        return Response(status=416, headers={"Content-Range": f"bytes */{file_size}", "Accept-Ranges": "bytes"})
    start, end = parsed_range
    length = end - start + 1
    def generate():
        with path.open("rb") as f:
            f.seek(start)
            remain = length
            while remain > 0:
                chunk = f.read(min(1024 * 1024, remain))
                if not chunk: break
                remain -= len(chunk)
                yield chunk
    return Response(generate(), status=206, headers={"Content-Range": f"bytes {start}-{end}/{file_size}", "Accept-Ranges": "bytes", "Content-Length": str(length), "Content-Type": mime})


@app.route("/")
def home(): return redirect("/chats")
@app.route("/auth", methods=["GET", "POST"])
def page_auth():
    next_url = safe_next_url(request.values.get("next") or "/")
    if not web_auth_required():
        return redirect(next_url)
    error = ""
    if request.method == "POST":
        token = request.form.get("token", "")
        if token_matches(token):
            resp = make_response(redirect(next_url))
            resp.set_cookie(AUTH_COOKIE, current_web_token(), httponly=True, samesite="Lax")
            return resp
        error = "Token 不正确"
    return render_template("auth.html", active="", next_url=next_url, error=error)


def socket_authorized(auth=None):
    if not web_auth_required():
        return True
    token = ""
    if isinstance(auth, dict):
        token = str(auth.get("token") or auth.get("web_token") or "").strip()
    return token_matches(token) or token_matches(request.args.get("token", "")) or token_matches(request.cookies.get(AUTH_COOKIE, ""))
@app.route("/login")
def page_login(): return render_template("login.html", active="login")
@app.route("/chats")
def page_chats(): return render_template("chats.html", active="chats")
@app.route("/chat/<path:peer>")
def page_chat(peer): return render_template("chat.html", active="chats", peer=unquote(peer))
@app.route("/downloads")
def page_downloads(): return render_template("downloads.html", active="downloads")

@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    try:
        if request.method == "GET":
            return ok(public_config(load_config()))
        data = request_json_object()
        cfg = normalize_config_patch(data, load_config(), require_string_session=False)
        save_config(cfg)
        tg.reload_config()
        resp = ok(public_config(cfg), "配置已保存")
        if "web_token" in data:
            if cfg.get("web_token"):
                resp.set_cookie(AUTH_COOKIE, cfg["web_token"], httponly=True, samesite="Lax")
            else:
                resp.delete_cookie(AUTH_COOKIE)
        return resp
    except Exception as e:
        return fail(e)


@app.route("/api/session/string", methods=["GET", "POST"])
def api_session_string():
    try:
        if request.method == "GET":
            cfg = load_config()
            value = str(cfg.get("string_session") or "")
            if not value and tg.client:
                value = tg.client.session.save() or ""
            if not value:
                raise ApiError("当前没有可导出的 StringSession", 404)
            return ok({"string_session": value})
        data = request_json_object()
        cfg = save_string_session_value(data.get("string_session", ""))
        tg.reload_config()
        tg.run(tg.reset_client())
        return ok(public_config(cfg), "StringSession 已导入")
    except Exception as e:
        return fail(e)


@app.route("/api/session/file", methods=["GET", "POST"])
def api_session_file():
    try:
        if request.method == "GET":
            path = session_storage_path()
            if not path.exists() or not path.is_file():
                raise ApiError("当前没有可导出的 .session 文件", 404)
            return send_file(path, as_attachment=True, download_name=path.name, mimetype="application/octet-stream")
        config_path, stored_path = copy_session_file_upload(request.files.get("file"))
        cfg = normalize_config_patch({"session_type": "file", "session_file": stored_path.name}, load_config())
        cfg["session_file"] = str(config_path)
        save_config(cfg)
        tg.reload_config()
        tg.run(tg.reset_client())
        return ok({"session_file_saved": True, "file": stored_path.name}, ".session 文件已导入")
    except Exception as e:
        return fail(e)

@app.route("/api/status")
def api_status():
    try: return ok(tg.run(tg.status()))
    except Exception as e: return fail(e)

@app.route("/api/login/start", methods=["POST"])
def api_login_start():
    try:
        data = request_json_object()
        current_cfg = load_config()
        cfg = normalize_config_patch({
            "api_id": data.get("api_id") or current_cfg.get("api_id"),
            "api_hash": data.get("api_hash") or current_cfg.get("api_hash"),
            "phone": data.get("phone") or current_cfg.get("phone"),
            "proxy": data.get("proxy", current_cfg.get("proxy", "")),
            "session_type": data.get("session_type", current_cfg.get("session_type", "file")),
            "string_session": data.get("string_session", current_cfg.get("string_session", "")),
            "session_file": data.get("session_file", current_cfg.get("session_file", "telegram")),
            "download_threads": data.get("download_threads", current_cfg.get("download_threads", 16)),
            "cache_limit_mb": data.get("cache_limit_mb", current_cfg.get("cache_limit_mb", 1024)),
        }, current_cfg, require_string_session=False)
        api_id = data.get("api_id") or cfg.get("api_id")
        api_hash = data.get("api_hash") or cfg.get("api_hash")
        phone = data.get("phone") or cfg.get("phone")
        if not api_id or not api_hash or not phone:
            return fail("缺少 api_id / api_hash / phone", 400)
        result = tg.run(tg.start_login(api_id, api_hash, phone, cfg.get("proxy", ""), cfg.get("session_type", "file"), cfg.get("session_file", ""), cfg.get("string_session", ""), cfg.get("download_threads", 16), cfg.get("cache_limit_mb", 1024)))
        return ok(result, result.get("message", "ok"))
    except Exception as e:
        return fail(e)

@app.route("/api/login/code", methods=["POST"])
def api_login_code():
    try:
        code = request_json_object().get("code")
        if not code: return fail("缺少验证码", 400)
        result = tg.run(tg.sign_in_code(code))
        return ok(result, result.get("message", "ok"))
    except Exception as e:
        return fail(e)

@app.route("/api/login/password", methods=["POST"])
def api_login_password():
    try:
        password = request_json_object().get("password")
        if not password: return fail("缺少两步验证密码", 400)
        return ok(tg.run(tg.sign_in_password(password)), "登录成功")
    except Exception as e:
        return fail(e)

@app.route("/api/logout", methods=["POST"])
def api_logout():
    try: return ok(tg.run(tg.logout()), "已退出登录")
    except Exception as e: return fail(e)

@app.route("/api/dialogs")
def api_dialogs():
    try:
        limit = query_int_arg("limit", 120, 1, 500)
        return ok(tg.run(tg.dialogs(limit)))
    except Exception as e: return fail(e)

@app.route("/api/messages")
def api_messages():
    try:
        peer = request.args.get("peer", "")
        if not peer: return fail("缺少 peer", 400)
        limit = query_int_arg("limit", 80, 1, 200)
        offset_id = query_int_arg("offset_id", 0, 0, 2**63 - 1)
        return ok(tg.run(tg.messages(peer, limit, offset_id)))
    except Exception as e:
        return fail(e)

@app.route("/api/send", methods=["POST"])
def api_send():
    try:
        data = request_json_object()
        if not data.get("peer") or not data.get("text"):
            return fail("缺少 peer / text", 400)
        return ok(tg.run(tg.send_text(data["peer"], data["text"])), "消息已发送")
    except Exception as e:
        return fail(e)

@app.route("/api/send-file", methods=["POST"])
def api_send_file():
    try:
        peer = request.form.get("peer", "")
        caption = request.form.get("caption", "")
        if not peer: return fail("缺少 peer", 400)
        if "file" not in request.files: return fail("缺少文件", 400)
        f = request.files["file"]
        tmp = UPLOAD_DIR / safe_filename(f.filename or "upload.bin")
        f.save(tmp)
        msg = tg.run(tg.send_file(peer, str(tmp), caption))
        try: tmp.unlink()
        except Exception: pass
        return ok(msg, "文件已发送")
    except Exception as e:
        return fail(e)

@app.route("/api/media/thumb", methods=["POST"])
def api_media_thumb():
    try:
        data = request_json_object()
        if not data.get("peer") or not data.get("msg_id"):
            return fail("缺少 peer / msg_id", 400)
        return ok(tg.run(tg.get_media_thumb(data["peer"], data["msg_id"])))
    except Exception as e:
        return fail(e)

@app.route("/api/media/prepare", methods=["POST"])
def api_media_prepare():
    try:
        data = request_json_object()
        peer, msg_id = data.get("peer"), data.get("msg_id")
        if not peer or not msg_id: return fail("缺少 peer / msg_id", 400)
        cached = tg.find_cached_media(peer, msg_id)
        if cached:
            mime = mimetypes.guess_type(str(cached))[0] or "application/octet-stream"
            return ok({"ready": True, "url": f"/media-cache/{quote(cached.name)}", "file": cached.name, "mime": mime, "size": cached.stat().st_size, "size_text": format_size(cached.stat().st_size)})
        task_id = tasks.create("prepare_media", {"peer": peer, "msg_id": msg_id})
        task_controls[task_id] = {"paused": False, "canceled": False}
        def job():
            try:
                if task_is_canceled(task_id):
                    raise RuntimeError("任务已取消")
                tasks.update(task_id, status="running")
                if task_is_canceled(task_id):
                    raise RuntimeError("任务已取消")
                result = tg.run(tg.prepare_media(peer, msg_id, task_id=task_id))
                task_finish(task_id, result)
            except Exception as e:
                task_fail(task_id, e)
        executor_holder.submit(job)
        return ok({"ready": False, "task_id": task_id})
    except Exception as e:
        return fail(e)

@app.route("/api/download-media", methods=["POST"])
def api_download_media():
    try:
        data = request_json_object()
        peer, msg_id = data.get("peer"), data.get("msg_id")
        if not peer or not msg_id: return fail("缺少 peer / msg_id", 400)
        task_id = tasks.create("download_media", {"peer": peer, "msg_id": msg_id})
        task_controls[task_id] = {"paused": False, "canceled": False}
        def job():
            try:
                if task_is_canceled(task_id):
                    raise RuntimeError("任务已取消")
                tasks.update(task_id, status="running")
                if task_is_canceled(task_id):
                    raise RuntimeError("任务已取消")
                result = tg.run(tg.download_media(peer, msg_id, task_id=task_id))
                task_finish(task_id, result)
            except Exception as e:
                task_fail(task_id, e)
        executor_holder.submit(job)
        return ok({"task_id": task_id}, "下载任务已创建")
    except Exception as e:
        return fail(e)

@app.route("/api/task/<task_id>", methods=["GET", "DELETE"])
def api_task(task_id):
    task = tasks.get(task_id)
    if not task: return fail("任务不存在", 404)
    if request.method == "DELETE":
        if task.get("status") in tasks.terminal_statuses:
            task_controls.pop(task_id, None)
        else:
            task_controls.setdefault(task_id, {"paused": False, "canceled": False})["canceled"] = True
        tasks.delete(task_id)
        return ok({"task_id": task_id}, "已删除")
    task["downloaded_text"] = format_size(task.get("downloaded", 0))
    task["total_text"] = format_size(task.get("total", 0)) if task.get("total") else ""
    task["speed_text"] = format_size(task.get("speed", 0)) + "/s"
    return ok(task)

@app.route("/api/task/<task_id>/pause", methods=["POST"])
def api_task_pause(task_id):
    task = tasks.get(task_id)
    if not task: return fail("任务不存在", 404)
    if task.get("status") in tasks.terminal_statuses:
        return fail("任务已结束", 400)
    task_controls.setdefault(task_id, {"paused": False, "canceled": False})["paused"] = True
    tasks.update(task_id, status="paused")
    return ok({"task_id": task_id}, "已暂停")

@app.route("/api/task/<task_id>/resume", methods=["POST"])
def api_task_resume(task_id):
    task = tasks.get(task_id)
    if not task: return fail("任务不存在", 404)
    if task.get("status") in tasks.terminal_statuses:
        return fail("任务已结束", 400)
    task_controls.setdefault(task_id, {"paused": False, "canceled": False})["paused"] = False
    tasks.update(task_id, status="running")
    return ok({"task_id": task_id}, "已恢复")

@app.route("/api/tasks")
def api_tasks():
    tasks.cleanup(max_age=7 * 24 * 3600, max_items=200)
    result = []
    for task in tasks.list():
        task["downloaded_text"] = format_size(task.get("downloaded", 0))
        task["total_text"] = format_size(task.get("total", 0)) if task.get("total") else ""
        task["speed_text"] = format_size(task.get("speed", 0)) + "/s"
        result.append(task)
    result.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return ok(result)

@app.route("/api/download-files")
def api_download_files():
    try:
        limit = query_int_arg("limit", 30, 1, 100)
        offset = query_int_arg("offset", 0, 0, 100000)
        items, total = list_download_files(limit=limit, offset=offset, include_total=True)
        return ok({"items": items, "total": total, "limit": limit, "offset": offset, "has_more": offset + len(items) < total})
    except Exception as e:
        return fail(e)

@app.route("/download-file/<path:filename>")
def serve_download_file(filename):
    path = resolve_under(DOWNLOAD_DIR, filename)
    if not path:
        abort(404)
    return send_file_range(path)
@app.route("/pictures/<path:filename>")
def serve_picture(filename):
    path = resolve_under(PICTURES_DIR, filename)
    if not path:
        abort(404)
    return send_file_range(path)
@app.route("/media-cache/<path:filename>")
def serve_media_cache(filename):
    path = resolve_under(CACHE_DIR, filename)
    if not path:
        abort(404)
    resp = send_file_range(path)
    # 7天强缓存
    resp.headers["Cache-Control"] = "public, max-age=604800, immutable"
    return resp

@socketio.on("connect")
def ws_connect(auth=None):
    if not socket_authorized(auth):
        return False
    socketio.emit("server_message", {"message": "connected"})

if __name__ == "__main__":
    host = run_host()
    ensure_safe_bind(host)
    socketio.run(app, host=host, port=run_port(), debug=False, allow_unsafe_werkzeug=True)
