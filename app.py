import asyncio
import json
import mimetypes
import os
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse, unquote, quote

import socks
from flask import Flask, request, jsonify, render_template, redirect, send_from_directory, Response, abort
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
}
CONFIG_FIELDS = ["api_id", "api_hash", "phone", "proxy", "session_type", "session_file", "string_session", "download_threads", "cache_limit_mb"]

app = Flask(__name__)
app.config["SECRET_KEY"] = "web-telegram-flask"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


class ApiError(ValueError):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.code = code


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
    cfg["download_threads"] = max(1, min(128, int(cfg.get("download_threads") or 16)))
    cfg["cache_limit_mb"] = max(128, min(10240, int(cfg.get("cache_limit_mb") or 1024)))
    return cfg


def save_config(cfg):
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
    proxy_type = socks.SOCKS5 if scheme == "socks5" else socks.SOCKS4
    return (proxy_type, u.hostname, int(u.port or 1080), True, unquote(u.username) if u.username else None, unquote(u.password) if u.password else None)


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


def public_config(cfg):
    data = dict(cfg)
    data["api_hash_saved"] = bool(data.get("api_hash"))
    data["session_file_saved"] = bool(data.get("session_file"))
    data["string_session_saved"] = bool(data.get("string_session"))
    data["api_hash"] = ""
    data["session_file"] = ""
    data["string_session"] = ""
    return data


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
    def __init__(self):
        self.lock = threading.Lock()
        self.tasks = {}
    def create(self, kind, meta=None):
        task_id = uuid.uuid4().hex
        with self.lock:
            self.tasks[task_id] = {"id": task_id, "kind": kind, "status": "queued", "progress": 0, "downloaded": 0, "total": 0, "speed": 0, "file": "", "url": "", "path": "", "mime": "", "error": "", "created_at": time.time(), "updated_at": time.time(), "meta": meta or {}}
        return task_id
    def update(self, task_id, **patch):
        with self.lock:
            if task_id not in self.tasks: return
            self.tasks[task_id].update(patch)
            self.tasks[task_id]["updated_at"] = time.time()
    def get(self, task_id):
        with self.lock:
            return dict(self.tasks.get(task_id) or {})
    def list(self):
        with self.lock:
            return [dict(v) for v in self.tasks.values()]
    def delete(self, task_id):
        with self.lock:
            self.tasks.pop(task_id, None)


tasks = TaskStore()
task_controls = {}


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

    async def status(self):
        client = await self.ensure_client()
        authorized = await client.is_user_authorized()
        me = None
        if authorized:
            user = await client.get_me()
            me = {"id": user.id, "username": user.username, "first_name": user.first_name, "last_name": user.last_name, "phone": user.phone}
        return {"connected": client.is_connected(), "authorized": authorized, "me": me, "config": {"api_id": self.cfg.get("api_id"), "phone": self.cfg.get("phone"), "proxy": self.cfg.get("proxy"), "session_type": self.cfg.get("session_type"), "download_threads": self.cfg.get("download_threads"), "cache_limit_mb": self.cfg.get("cache_limit_mb")}}

    async def start_login(self, api_id, api_hash, phone, proxy, download_threads=16, cache_limit_mb=1024):
        self.cfg.update({"api_id": int(api_id), "api_hash": str(api_hash), "phone": str(phone), "proxy": str(proxy or ""), "download_threads": int(download_threads or 16), "cache_limit_mb": int(cache_limit_mb or 1024)})
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
        return {"need_password": False, "message": "登录成功"}

    async def sign_in_password(self, password):
        client = await self.ensure_client()
        await client.sign_in(password=str(password))
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
            if p.is_file():
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

        path = await client.download_media(msg, file=str(target_path), progress_callback=progress_callback)
        if not path:
            raise RuntimeError("媒体下载失败")
        p = Path(path)
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
    code = getattr(e, "code", code)
    return jsonify({"success": False, "error": str(e)}), code


def list_download_files():
    result = []
    for root, kind, url_prefix in [(DOWNLOAD_DIR, "download", "/download-file"), (PICTURES_DIR, "picture", "/pictures")]:
        rows = []
        for p in root.glob("*"):
            try:
                if p.is_symlink() or not p.is_file():
                    continue
                st = p.stat()
            except OSError:
                continue
            rows.append((p, st))
        for p, st in sorted(rows, key=lambda row: row[1].st_mtime, reverse=True):
            mime = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
            result.append({"name": p.name, "kind": kind, "size": st.st_size, "size_text": format_size(st.st_size), "mtime": int(st.st_mtime), "url": f"{url_prefix}/{quote(p.name)}", "mime": mime, "is_image": mime.startswith("image/"), "is_video": mime.startswith("video/"), "is_audio": mime.startswith("audio/")})
    return result


def send_file_range(path: Path):
    path = Path(path)
    if not path.exists() or not path.is_file():
        abort(404)
    file_size = path.stat().st_size
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    range_header = request.headers.get("Range")
    if not range_header:
        return send_from_directory(path.parent, path.name, as_attachment=False)
    try:
        byte_range = range_header.replace("bytes=", "")
        start_s, end_s = byte_range.split("-", 1)
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else file_size - 1
    except Exception:
        start, end = 0, file_size - 1
    start = max(0, start)
    end = min(file_size - 1, end)
    if start > end or start >= file_size:
        return Response(status=416, headers={"Content-Range": f"bytes */{file_size}", "Accept-Ranges": "bytes"})
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
@app.route("/login")
def page_login(): return render_template("login.html", active="login")
@app.route("/chats")
def page_chats(): return render_template("chats.html", active="chats")
@app.route("/chat/<path:peer>")
def page_chat(peer): return render_template("chat.html", active="chats", peer=unquote(peer))
@app.route("/downloads")
def page_downloads(): return render_template("downloads.html", active="downloads", files=list_download_files())

@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    try:
        if request.method == "GET":
            return ok(public_config(load_config()))
        data = request_json_object()
        cfg = load_config()
        for k in CONFIG_FIELDS:
            if k in data:
                cfg[k] = data[k]
        save_config(cfg)
        tg.reload_config()
        return ok(public_config(cfg), "配置已保存")
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
        cfg = load_config()
        api_id = data.get("api_id") or cfg.get("api_id")
        api_hash = data.get("api_hash") or cfg.get("api_hash")
        phone = data.get("phone") or cfg.get("phone")
        if not api_id or not api_hash or not phone:
            return fail("缺少 api_id / api_hash / phone", 400)
        result = tg.run(tg.start_login(api_id, api_hash, phone, data.get("proxy", cfg.get("proxy", "")), data.get("download_threads", cfg.get("download_threads", 16)), data.get("cache_limit_mb", cfg.get("cache_limit_mb", 1024))))
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
    try: return ok(tg.run(tg.dialogs(int(request.args.get("limit", 120)))))
    except Exception as e: return fail(e)

@app.route("/api/messages")
def api_messages():
    try:
        peer = request.args.get("peer", "")
        if not peer: return fail("缺少 peer", 400)
        return ok(tg.run(tg.messages(peer, int(request.args.get("limit", 80)), int(request.args.get("offset_id", 0)))))
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
                tasks.update(task_id, status="running")
                result = tg.run(tg.prepare_media(peer, msg_id, task_id=task_id))
                tasks.update(task_id, status="done", progress=100, file=result.get("file", ""), path=result.get("path", ""), url=result.get("url", ""), mime=result.get("mime", ""), downloaded=result.get("size", 0), total=result.get("size", 0))
            except Exception as e:
                tasks.update(task_id, status="error", error=str(e))
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
                tasks.update(task_id, status="running")
                result = tg.run(tg.download_media(peer, msg_id, task_id=task_id))
                tasks.update(task_id, status="done", progress=100, file=result.get("file", ""), path=result.get("path", ""), url=result.get("url", ""), mime=result.get("mime", ""), downloaded=result.get("size", 0), total=result.get("size", 0))
            except Exception as e:
                tasks.update(task_id, status="error", error=str(e))
        executor_holder.submit(job)
        return ok({"task_id": task_id}, "下载任务已创建")
    except Exception as e:
        return fail(e)

@app.route("/api/task/<task_id>", methods=["GET", "DELETE"])
def api_task(task_id):
    task = tasks.get(task_id)
    if not task: return fail("任务不存在", 404)
    if request.method == "DELETE":
        task_controls.setdefault(task_id, {"paused": False, "canceled": False})["canceled"] = True
        tasks.update(task_id, status="canceled")
        return ok({"task_id": task_id}, "已取消")
    task["downloaded_text"] = format_size(task.get("downloaded", 0))
    task["total_text"] = format_size(task.get("total", 0)) if task.get("total") else ""
    task["speed_text"] = format_size(task.get("speed", 0)) + "/s"
    return ok(task)

@app.route("/api/task/<task_id>/pause", methods=["POST"])
def api_task_pause(task_id):
    if not tasks.get(task_id): return fail("任务不存在", 404)
    task_controls.setdefault(task_id, {"paused": False, "canceled": False})["paused"] = True
    tasks.update(task_id, status="paused")
    return ok({"task_id": task_id}, "已暂停")

@app.route("/api/task/<task_id>/resume", methods=["POST"])
def api_task_resume(task_id):
    if not tasks.get(task_id): return fail("任务不存在", 404)
    task_controls.setdefault(task_id, {"paused": False, "canceled": False})["paused"] = False
    tasks.update(task_id, status="running")
    return ok({"task_id": task_id}, "已恢复")

@app.route("/api/tasks")
def api_tasks():
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
    return ok(list_download_files())

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
def ws_connect():
    socketio.emit("server_message", {"message": "connected"})

if __name__ == "__main__":
    socketio.run(app, host=run_host(), port=run_port(), debug=False, allow_unsafe_werkzeug=True)
