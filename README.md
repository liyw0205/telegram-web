# Web Telegram

基于 **Flask + Telethon** 的 Telegram Web 管理与聊天界面。

## 功能

- 手机号登录 / 2FA
- 会话列表
- 聊天消息浏览
- 媒体预览与下载（查看器支持键盘切换、关闭和焦点循环）
- 下载任务管理（暂停 / 删除）
- StringSession / `.session` 导入导出（导出需一次性令牌）
- 敏感操作自定义确认弹窗（含键盘焦点循环）
- 只读脱敏诊断页面和诊断 API
- 缓存自动清理
- Markdown 消息渲染

## 技术栈

- Python
- Flask
- Flask-SocketIO
- Telethon
- HTML / CSS / JavaScript

## 安装

```bash
pip install -r requirements.txt
```

## 验证

推荐先做运行环境预检：

```bash
sh -n scripts/diagnose-runtime.sh
sh scripts/diagnose-runtime.sh
```

再运行自动化回归：

```bash
PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py
PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v
node --check static/js/app.js
node --check tests/frontend_smoke.js
node tests/frontend_smoke.js
git diff --check
```

`tests/frontend_smoke.js` 使用纯 Node mock 浏览器环境，按确认弹窗、媒体查看器、聊天消息、会话列表、登录页/API、session/任务确认、下载页和诊断页分组覆盖前端自定义敏感确认弹窗、键盘焦点循环、媒体查看器键盘交互、焦点恢复和焦点循环、聊天加载/发送状态、会话搜索和会话项语义、一次性 session 导出令牌请求链、API 错误 ID 复制、401 跳转、登录页脱敏配置占位符、任务删除确认、下载任务渲染、下载文件分页、诊断页脱敏渲染和错误提示，不需要真实 Telegram 登录或浏览器。

真实浏览器 smoke 目前作为可选手动验证：先运行 `sh scripts/check-browser-smoke-env.sh` 查看本机是否具备自动化条件，再按 `docs/browser-smoke.md` 执行页面和键盘交互清单。该检查脚本只报告命令和 Node 模块可用性，不安装依赖，不读取运行数据。

服务启动后可用以下命令对脱敏诊断接口做可选 HTTP 探测：

```bash
TELEGRAM_WEB_DIAGNOSTICS_URL=http://127.0.0.1:5000/api/diagnostics sh scripts/diagnose-runtime.sh
```

诊断脚本只检查仓库文件、命令、依赖导入、语法、前端语法和启动环境变量形状，不读取 `data/config.json`，也不会打印 Web Token、StringSession、`.session`、代理凭据或 Telegram API 凭据。若 Web Token 只保存在 `data/config.json`，脚本不会读取该 Token，HTTP 探测可能提示鉴权失败或探测失败；详细排障流程见 `docs/runtime-runbook.md`。

服务启动后可打开 `/diagnostics` 查看只读诊断页，也可访问 `GET /api/diagnostics` 查看脱敏运行状态。诊断页只渲染白名单布尔、枚举和数值状态；接口只返回配置是否存在、secret 是否已保存、Token 来源、host/port 和运行目录状态，不返回 `api_hash`、StringSession、`.session` 内容、Web Token 或代理凭据。

## 运行

```bash
python app.py
```

Termux 或本机 shell 可使用仓库内脚本：

```bash
sh scripts/run-termux.sh
```

默认访问：

```bash
http://127.0.0.1:5000
```

默认仅监听 `127.0.0.1`。如已在本机 `/login` 保存 Web Token，确需对局域网开放时可显式设置：

```bash
TELEGRAM_WEB_HOST=0.0.0.0 TELEGRAM_WEB_PORT=5000 python app.py
```

对外监听必须已有 Web Token，否则服务会拒绝启动。更推荐用环境变量提供 Token：

```bash
TELEGRAM_WEB_HOST=0.0.0.0 TELEGRAM_WEB_PORT=5000 TELEGRAM_WEB_TOKEN=your-strong-token python app.py
```

也可以先在本机打开 `/login`，保存 `Web Token` 后再对外监听。Token 来源优先级为 `TELEGRAM_WEB_TOKEN`、`WEB_TELEGRAM_TOKEN`、`data/config.json` 中保存的 `web_token`；对外访问推荐使用环境变量。设置 Token 后，页面、API、媒体缓存和下载文件都会要求通过 `/auth` 验证。

## 配置

登录页需要填写：

- `api_id`
- `api_hash`
- 手机号
- 代理（可选）
- 下载线程数
- 缓存上限（MB）

## 目录结构

```text
.
├── app.py
├── requirements.txt
├── templates/
├── static/
├── data/       # 运行配置和媒体缓存，已忽略提交
├── Download/   # 下载文件，已忽略提交
└── Pictures/   # 下载图片，已忽略提交
```

## 注意

- 需要有效的 Telegram API ID / Hash
- 首次登录需要验证码
- 使用代理时请确保 SOCKS5 可用
- 媒体缓存会按上限自动清理
- 终态下载/预览任务会记录到 `data/task-history.json`，重启后可继续在下载页看到最近历史
- `data/`、`Download/`、`Pictures/` 和 `.session` 文件是本地运行数据，不要提交到 Git
- 当前登录页开放手机号登录、验证码、2FA、StringSession 导入导出和 `.session` 文件导入导出
- Session 导出前会弹出确认，并使用 60 秒一次性导出令牌；令牌使用后立即失效
- 对外开放前必须设置强 Web Token，并只在可信网络中使用

## 日志和错误 ID

- API 内部错误会返回 `error_id`，前端会在提示中展示并尝试复制到剪贴板。
- 前台运行时可在服务端终端日志中搜索：`internal api error <error_id>`。
- 使用 `tmux` 时先执行 `tmux attach -t telegram-web` 回到运行窗口，再按错误 ID 检索当前终端缓冲或用户自己的日志文件。
- 可用 `TELEGRAM_WEB_DIAGNOSTICS_URL=http://127.0.0.1:5000/api/diagnostics sh scripts/diagnose-runtime.sh` 对运行中的脱敏诊断接口做可选 HTTP 探测。

## 部署和备份

- 推荐先在本机 `127.0.0.1` 完成登录，再按需设置 `TELEGRAM_WEB_TOKEN` 对外访问。
- Termux 后台运行可使用 `tmux`、`screen` 或用户自己的进程管理方式，环境变量仍按上文设置。
- 例如：先执行 `tmux new -s telegram-web`，再运行 `sh scripts/run-termux.sh`；退出查看时用 `tmux attach -t telegram-web`。
- 需要备份时复制 `data/config.json` 和当前 session 存储文件；默认文件 session 为 `data/telegram.session`，自定义或导入后以登录页的 Session 文件名为准。
- `data/config.json` 可能包含 `api_hash`、手机号、代理、StringSession 和 Web Token，备份文件应离线保存，不要提交到 Git。
- 如果使用 StringSession，可在登录页导出文本后离线保存；如果使用文件 session，备份对应的 `data/*.session` 文件。
- 如需保留任务历史，可一并备份 `data/task-history.json`。
- 恢复时先安装依赖，再放回 `data/config.json` 和 session 文件，或通过登录页导入 StringSession / `.session` 文件；如果启用了 Web Token，先通过 `/auth` 验证，再确认 `/api/status` 授权状态正常。
- 反向代理只转发到本机监听地址；不要让未设置 Web Token 的服务直接暴露到外部网络。

## 说明

本项目仅用于个人 Telegram 数据管理与浏览。
