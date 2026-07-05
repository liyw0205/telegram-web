# Web Telegram

基于 **Flask + Telethon** 的 Telegram Web 管理与聊天界面。

## 功能

- 手机号登录 / 2FA
- 会话列表（本地搜索名称、用户名、peer 和 ID）
- 聊天消息浏览
- 媒体预览与下载任务（缩略图优先，查看器支持键盘切换、关闭和焦点循环）
- 下载任务管理（暂停 / 恢复 / 取消 / 移除记录）
- StringSession / `.session` 导入导出（导出需一次性令牌）
- 敏感操作自定义确认弹窗（含键盘焦点循环）
- 只读脱敏诊断页面和诊断 API（白名单状态渲染）
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

`tests/frontend_smoke.js` 使用纯 Node mock 浏览器环境，按确认弹窗、媒体查看器、聊天消息、会话列表、登录页/API、session/任务确认、下载页和诊断页分组覆盖前端自定义敏感确认弹窗、键盘焦点循环、媒体查看器键盘交互、焦点恢复和焦点循环、聊天刷新/更早加载和发送忙碌保护、会话搜索和会话项语义、一次性 session 导出令牌请求链、Session 导入刷新等待和忙碌保护、API 错误 ID 展示和复制尝试、401 跳转、登录页脱敏配置占位符、未保存配置输入提示、配置保存和发送验证码 payload 边界、登录页操作忙碌保护、后端中文错误 toast、任务删除确认、下载任务轮询边界、下载任务渲染、下载文件分页忙碌保护、诊断页脱敏渲染和错误提示，不需要真实 Telegram 登录或浏览器。

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

- `api_id`：1 到 2147483647 的数字；登录页提供数字输入提示。
- `api_hash`：32 位十六进制字符串；已保存时留空沿用当前值，登录页不会回显已保存值。
- 手机号：可带 `+`，数字长度 5 到 20。
- 代理（可选）：仅支持 `socks4://` 或 `socks5://`，host 必填，端口默认 1080 且必须在 1 到 65535 之间，不能包含 path、query 或 fragment；含凭据代理不会回显原文。
- Session 类型：`file` 或 `string`；选择 `string` 时需要已保存或本次填写有效 StringSession。
- Session 文件名：只接受 `data/` 目录内文件名，可带或不带 `.session` 后缀。
- 下载线程数：1 到 128。
- 缓存上限（MB）：128 到 10240。
- Web Token：8 到 256 字符，不能包含空白字符；已保存时留空不修改。

JSON API 的 POST 请求必须使用 JSON 对象；Content-Type 不匹配或数组/字符串等非对象请求会返回 `请求体必须是 JSON 对象`，语法错误会返回 `请求体必须是有效 JSON`。分页参数错误会返回字段名和范围，例如 `limit 必须在 1..100 之间`。

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
- 使用代理时请确保 SOCKS4/5 代理可用
- 会话列表一次加载最近 120 个会话，搜索只在已加载结果中按名称、用户名、peer 或 ID 过滤；没有匹配时显示“没有匹配的会话”
- 媒体缓存会按上限自动清理
- 聊天页会优先加载媒体缩略图，不自动下载原文件；点击媒体预览会按需准备缓存，未就绪时显示“媒体正在准备，稍后重试打开”
- 聊天页刷新消息和加载更早消息会互斥；文字或文件发送中重复触发会显示中文忙碌提示，发送失败会保留输入内容和文件选择
- 聊天页媒体下载按钮会创建后台下载任务，可在下载页查看进度，不会在当前页直接保存文件
- 终态下载/预览任务会记录到 `data/task-history.json`，重启后可继续在下载页看到最近历史
- 下载页会分页列出 `Download/` 和 `Pictures/` 中已完成文件，并跳过 `.part` 临时文件
- `/api/dialogs` 的 `limit` 范围为 `1..500`，`/api/messages` 的 `limit` 范围为 `1..200` 且 `offset_id` 范围为 `0..9223372036854775807`，`/api/download-files` 的 `limit` 范围为 `1..100` 且 `offset` 范围为 `0..100000`
- 下载、图片和媒体缓存文件支持单段 `Range: bytes=...`；非法、多段或越界 Range 返回 416，非 `bytes` Range 会被忽略并按普通 200 响应
- 暂停和恢复任务会直接执行；取消活跃任务或移除终态记录前会弹出确认，重复触发同一任务操作会显示中文忙碌提示，移除记录不会删除已下载文件
- `data/`、`Download/`、`Pictures/` 和 `.session` 文件是本地运行数据，不要提交到 Git
- 当前登录页开放手机号登录、验证码、2FA、StringSession 导入导出和 `.session` 文件导入导出
- 敏感配置字段已保存时会显示脱敏占位符；`api_hash`、含凭据代理、StringSession、`.session` 文件名和 Web Token 留空会沿用已保存值
- 顶部状态只显示 Telegram 连接/授权摘要或 Web Token 验证提示；底部导航标记当前页面，不加载额外数据
- Session 文件名只接受 `data/` 目录内文件名，可填写 `telegram` 或 `telegram.session`，实际存储文件会使用 `.session` 后缀
- StringSession 导出会先弹出确认，成功后填入登录页文本框并尝试复制到剪贴板
- `.session` 文件导入会重置当前客户端并切换到导入会话；导出会打开一次性令牌下载链接
- Session 导出前会弹出确认，并使用 60 秒一次性导出令牌；令牌使用后立即失效
- 对外开放前必须设置强 Web Token，并只在可信网络中使用
- 诊断页只显示配置、访问、运行和目录状态；摘要使用“Web Token 状态 · Token 来源 · 监听范围 · 端口 N”，不显示原始 host、Token、路径或 secret

## 日志和错误 ID

- API 内部错误会返回 `error_id`；前端会在提示中展示错误 ID，支持剪贴板时提示“已尝试复制”。
- 前台运行时可在服务端终端日志中搜索：`internal api error <error_id>`。
- API 或页面提示“需要 Web Token，请先验证”时，会跳转或引导到 `/auth` 输入 Web Token。
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
