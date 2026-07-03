# Phase 2 登录、session 和访问控制可靠性

## 阶段目标

- 为页面、API、文件路由和 Socket.IO 增加最小 Web Token 访问控制。
- 为配置保存增加字段级校验和归一化，避免坏配置落盘。
- 明确 StringSession / `.session` 当前边界。
- 删除未启用历史模板，避免悬空 JS 函数和误启用页面。
- 扩展测试覆盖访问控制、配置校验、Socket.IO 和 session 文件边界。

## 完成内容

- 新增 Web Token 鉴权：
  - 支持 `Authorization: Bearer ...`、`X-Web-Telegram-Token`、`X-Web-Token`、`?token=` 和 HttpOnly Cookie。
  - `/auth` 页面可输入 Token 并写入 `SameSite=Lax` Cookie。
  - `/login?token=...` 可作为 Token 入口并写入 Cookie。
  - `/api/*`、`/chats`、`/chat/<peer>`、`/downloads`、文件路由和媒体缓存路由在配置 Token 后都会受保护。
  - `/static/*`、`/socket.io/*`、`/auth`、`/login`、`/favicon.ico` 放行；Socket.IO 连接事件自行校验 Token。
- 对外监听安全检查：
  - 默认仍监听 `127.0.0.1`。
  - `TELEGRAM_WEB_HOST=0.0.0.0` 时必须设置 `TELEGRAM_WEB_TOKEN` 或配置 `web_token`，否则启动失败。
  - Socket.IO 移除任意 Origin 放行。
- 配置字段校验：
  - `api_id` 必须是 32-bit 正整数。
  - `api_hash` 必须是 32 位十六进制字符串；空值表示沿用已保存值。
  - `phone` 校验为可选 `+` 加数字。
  - `proxy` 只允许 `socks4://` / `socks5://`，host 必填，端口 `1..65535`，拒绝 path/query/fragment，并归一化保存。
  - `session_type` 只允许 `file` / `string`。
  - `session_file` 只允许 `data/` 下安全文件名，保存时去掉 `.session` 后缀。
  - `string_session` 非空时用 `StringSession()` 做格式校验；`session_type=string` 时必须已有或新提供。
  - `download_threads` 限制为 `1..128`，`cache_limit_mb` 限制为 `128..10240`。
  - `web_token` 长度限制为 `8..256` 且不能包含空白字符。
- `/api/config` 响应继续脱敏 `api_hash`、`session_file`、`string_session`、`web_token`；含凭据代理不回显原文，只返回 `proxy_saved/proxy_redacted` 标记。
- 登录页新增“保存配置”按钮和 Web Token 输入框，空敏感字段不会清空已保存值。
- 删除未启用历史模板：
  - `templates/config.html`
  - `templates/data.html`
  - `templates/media_view.html`
- README 增加 Web Token 和对外监听说明。
- 测试扩展到 23 个用例。

## 主代理工作

- 按 Phase 1 交接文档启动 Phase 2。
- 读取现有路由、前端 API 封装、登录模板和测试。
- 实现鉴权、配置校验、前端保存配置和文档更新。
- 删除悬空历史模板。

## 子代理协作

- 子代理：Explorer `McClintock`
- 任务：只读梳理 Web Token 鉴权、配置校验、StringSession / `.session` 边界和历史模板取舍。
- 输出：建议保护所有页面/API/文件路由，放行 `/login`、静态资源和 Socket.IO 客户端脚本；Socket.IO 连接事件也要校验 Token；配置保存前必须统一校验；`data.html/media_view.html` 更适合删除。
- 采纳情况：已实现 HTTP + Socket.IO Token 鉴权、同源 Socket.IO、配置字段校验、登录页 Token 入口，删除 `config.html/data.html/media_view.html`；StringSession 导出持久化留后续阶段。

## 改动文件

- `README.md`
- `Telegram_Web开发.md`
- `app.py`
- `static/js/app.js`
- `templates/auth.html`
- `templates/login.html`
- `templates/config.html`（删除）
- `templates/data.html`（删除）
- `templates/media_view.html`（删除）
- `tests/test_core.py`
- `docs/progress/2026-07-04-phase-2-auth-config.md`
- `docs/handoff/2026-07-04-phase-2-to-phase-3.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：Flask-Login、Flask-HTTPAuth、Flask-WTF。
- 结论：本阶段不引入。
- 原因：当前只需要单 Token 访问控制和轻量配置校验，引入用户系统或表单框架会扩大部署与迁移成本；后续如需要多用户、权限或 CSRF 表单保护，再评估成熟扩展。

## 验证结果

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，23 个测试
- `git diff --check`：通过
- 悬空模板/JS 搜索：代码中无 `exportStringSession()`、`initMediaViewPage()`、`loadConfigPage()`、`saveConfigPage()` 悬空引用

## 风险和遗留

- Web Token 可以保存在本地 `data/config.json`；对更高安全要求的部署应优先使用 `TELEGRAM_WEB_TOKEN` 环境变量。
- 使用 `session_type=string` 新登录后，当前代码还不会自动把 `client.session.save()` 写回配置，重启后可能需要手动保存 StringSession。
- 还没有 `.session` 文件上传/下载导入导出 UI。
- Range 解析仍为轻量实现，未完整支持 RFC 多 Range 和 suffix range 语义。
- `fail(e)` 仍可能把部分内部异常字符串返回给客户端，后续应分层处理用户错误和内部错误。

## Git

- 提交信息：`phase2: add web token auth and config validation`
