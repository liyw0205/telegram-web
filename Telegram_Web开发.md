# Telegram Web 开发文档

> 当前基线：Phase 40，Session 迁移操作刷新状态和并发边界复核。实际代码版本以 `git log -1 --oneline` 为准。
> 仓库：`telegram-web`
> 应用形态：Flask + Flask-SocketIO + Telethon 的单进程个人 Telegram Web 管理界面。
> 前端形态：Jinja 模板 + 原生 JavaScript/CSS，无 npm 构建链。

## 1. 项目定位

本项目是个人 Telegram 数据浏览、聊天、媒体预览、下载任务管理和会话迁移工具。它不是 Telegram Bot，也不是独立 SPA。后端负责 Telegram 客户端、任务状态、媒体缓存、文件 Range 响应和 Socket.IO 推送；前端负责页面渲染、交互状态、可访问性语义和错误提示。

目标是在不泄露 Telegram API 凭据、本地 session、代理凭据、Web Token 和运行数据的前提下，提高以下能力：

- 登录、验证码、2FA、StringSession 和 `.session` 文件流程可恢复、可解释。
- 会话列表、消息流、媒体缩略图、媒体查看器和发送文件流程稳定。
- 下载任务、终态历史、分页文件列表、Range 响应和缓存清理边界清晰。
- 移动端页面、键盘交互、确认弹窗、错误 ID 和诊断页可持续回归。
- 每个阶段都有进度文档、交接文档、验证结果、Git 提交和远端推送。

## 2. 固定边界

- 不提交真实 Telegram 凭据和会话：`api_id`、`api_hash`、手机号、代理账号、StringSession、`.session`、Cookie、Web Token 和导出令牌只能存在于运行配置或本地运行数据中。
- 不提交运行数据：`data/`、`Download/`、`Pictures/`、`data/media-cache/`、`data/uploads/`、`.session`、`.part` 和任务历史 JSON 都属于运行态数据。
- 不扩大到无关目录或账号：默认只处理本仓库、运行进程、本项目运行目录和用户明确提供的测试数据。
- 不绕过 Telegram 授权：登录、验证码、2FA、退出登录、StringSession 导入导出和 `.session` 导入导出必须保持显式操作和可审计。
- 不无计划引入前端构建链：当前保持 Jinja + 原生 JS/CSS；只有阶段目标明确、收益足够、验证和部署方式同步更新时才引入 npm/Vite/React 等。
- 不把诊断页变成 secret 查看器：诊断页和 `/api/diagnostics` 只展示布尔、枚举和数值状态，不展示原始 secret、Token、本地绝对路径或代理原文。
- 阶段结束必须提交并推送：完成开发、验证、进度文档和交接文档后，非交互式提交，并使用 SSH 推送到 `origin/main`。

## 3. 工作区结构

| 路径 | 作用 |
|------|------|
| `app.py` | Flask 应用、Telethon 服务、配置校验、鉴权、任务队列、媒体缓存、文件服务和 Socket.IO |
| `requirements.txt` | Python 依赖：`flask`、`flask-socketio`、`telethon`、`pysocks`、`python-socketio` |
| `templates/base.html` | 全局布局、顶部状态、底部主导航、toast、确认弹窗和脚本入口 |
| `templates/auth.html` | Web Token 验证页 |
| `templates/login.html` | Telegram API 配置、手机号登录、验证码、2FA、StringSession 和 `.session` 迁移 |
| `templates/chats.html` | 会话列表页 |
| `templates/chat.html` | 单会话消息页、消息列表、发送区和媒体查看器 |
| `templates/downloads.html` | 下载任务和已下载文件页 |
| `templates/diagnostics.html` | 只读脱敏诊断页 |
| `static/js/app.js` | 前端 API 封装、Socket.IO、状态刷新、登录、会话、消息、媒体、下载和诊断交互 |
| `static/css/app.css` | 全站样式、移动端布局、卡片、弹窗、媒体查看器和下载页样式 |
| `tests/test_core.py` | 标准库 `unittest` 后端和模板静态回归 |
| `tests/frontend_smoke.js` | 纯 Node mock 浏览器 smoke，覆盖确认弹窗、媒体查看器、登录/API、会话、聊天、下载和诊断 |
| `scripts/run-termux.sh` | Termux/本机启动脚本 |
| `scripts/diagnose-runtime.sh` | 运行环境预检和可选 `/api/diagnostics` HTTP 探测 |
| `scripts/check-browser-smoke-env.sh` | 检查本机是否具备浏览器自动化 smoke 条件，不安装依赖 |
| `docs/runtime-runbook.md` | 启动、访问、Web Token、日志、诊断、配置边界、备份恢复和常见故障 |
| `docs/browser-smoke.md` | 手动真实浏览器 smoke 清单和后续 Playwright 引入边界 |
| `docs/progress/` | 每阶段进度记录 |
| `docs/handoff/` | 每阶段交接记录，`LATEST.md` 是续会入口 |

## 4. 运行数据和配置

应用启动时会创建：

```text
data/
Download/
Pictures/
data/media-cache/
data/uploads/
```

关键运行文件：

| 文件/目录 | 说明 |
|-----------|------|
| `data/config.json` | API 配置、代理、session 类型、下载线程数、缓存上限和 Web Token，可能含敏感信息 |
| `data/task-history.json` | 最近终态下载/预览任务历史 |
| `data/*.session` | Telethon 文件 session |
| `Download/` | 文档、视频、音频等下载文件 |
| `Pictures/` | 图片下载文件 |
| `data/media-cache/` | 聊天媒体查看器按需缓存 |
| `data/uploads/` | 发送文件时的临时上传目录 |

配置字段白名单：

```text
api_id
api_hash
phone
proxy
session_type
session_file
string_session
download_threads
cache_limit_mb
web_token
```

配置校验边界：

- `api_id`：`1..2147483647`。
- `api_hash`：32 位十六进制字符串；留空沿用已保存值。
- `phone`：可选 `+` 加 5 到 20 位数字。
- `proxy`：仅支持 `socks4://` 和 `socks5://`；host 必填；端口默认 1080，范围 `1..65535`；拒绝 path、query 和 fragment；含凭据代理不会回显原文。
- `session_type`：仅支持 `file` 或 `string`。
- `session_file`：只接受 `data/` 目录内文件名，可带或不带 `.session` 后缀；实际存储文件使用 `data/*.session`。
- `string_session`：必须能被 Telethon `StringSession` 解析。
- `download_threads`：`1..128`。
- `cache_limit_mb`：`128..10240`。
- `web_token`：8 到 256 字符，不能包含空白字符；留空不修改已保存 Token。

Web Token 来源优先级：

```text
TELEGRAM_WEB_TOKEN
WEB_TELEGRAM_TOKEN
data/config.json 中的 web_token
```

默认监听 `127.0.0.1`。对外监听必须已有 Web Token，否则启动拒绝。

## 5. API 和页面入口

页面路由：

| 路由 | 说明 |
|------|------|
| `GET /` | 重定向到 `/chats` |
| `GET /auth` / `POST /auth` | Web Token 验证页 |
| `GET /login` | 登录和配置页 |
| `GET /chats` | 会话列表 |
| `GET /chat/<peer>` | 单会话消息 |
| `GET /downloads` | 下载任务和已下载文件 |
| `GET /diagnostics` | 只读脱敏诊断页 |

配置、鉴权、登录和 session API：

| API | 说明 |
|-----|------|
| `GET/POST /api/config` | 读取/保存配置，响应脱敏 secret 字段 |
| `GET /api/status` | Telegram 连接和授权摘要 |
| `POST /api/login/start` | 根据配置创建客户端并发送验证码 |
| `POST /api/login/code` | 提交验证码 |
| `POST /api/login/password` | 提交两步验证密码 |
| `POST /api/logout` | 退出 Telegram 登录 |
| `GET /api/diagnostics` | 脱敏运行诊断状态 |
| `POST /api/session/export-token` | 生成 60 秒一次性导出令牌 |
| `GET/POST /api/session/string` | 导出或导入 StringSession |
| `GET/POST /api/session/file` | 导出或导入 `.session` 文件 |

会话、消息、媒体和下载 API：

| API | 说明 |
|-----|------|
| `GET /api/dialogs?limit=...` | 会话列表，`limit` 范围 `1..500` |
| `GET /api/messages?peer=...&limit=...&offset_id=...` | 消息列表，`limit` 范围 `1..200`，`offset_id` 范围 `0..9223372036854775807` |
| `POST /api/send` | 发送文本消息 |
| `POST /api/send-file` | 上传并发送文件 |
| `POST /api/media/thumb` | 获取媒体缩略图 |
| `POST /api/media/prepare` | 按需准备媒体查看器缓存 |
| `POST /api/download-media` | 创建后台下载任务 |
| `GET/DELETE /api/task/<task_id>` | 查询任务、取消活跃任务或移除记录 |
| `POST /api/task/<task_id>/pause` | 暂停任务 |
| `POST /api/task/<task_id>/resume` | 恢复任务 |
| `GET /api/tasks` | 下载/预览任务列表和终态历史 |
| `GET /api/download-files?limit=...&offset=...` | 已下载文件分页，`limit` 范围 `1..100`，`offset` 范围 `0..100000` |

文件路由：

| 路由 | 说明 |
|------|------|
| `GET /download-file/<filename>` | 访问 `Download/` 内文件 |
| `GET /pictures/<filename>` | 访问 `Pictures/` 内文件 |
| `GET /media-cache/<filename>` | 访问 `data/media-cache/` 内文件，带 7 天强缓存 |

文件访问只允许解析到对应目录内部。`.part` 文件和符号链接不会出现在已下载文件列表。文件响应支持单段 `Range: bytes=...`；非法、多段或越界 Range 返回 416 和 `Content-Range: bytes */<size>`；非 `bytes` Range 被忽略并按普通 200 响应。

Socket.IO：

| 事件 | 说明 |
|------|------|
| `connect` | 受 Web Token 鉴权保护，连接成功后服务端发送 `server_message` |
| `new_message` | Telethon 新消息事件转发给前端 |

## 6. 核心工作流

启动和访问：

1. `scripts/run-termux.sh` 或 `python app.py` 启动服务。
2. 默认监听 `127.0.0.1:5000`。
3. 如果设置 Web Token，受保护页面会跳转 `/auth?next=...`，API 缺少 Token 返回“需要 Web Token，请先验证”。
4. 对外监听需要先通过环境变量或本地配置设置 Web Token。

登录和 session：

1. `/login` 读取 `/api/config`，敏感字段只显示脱敏占位符。
2. 保存配置走 `/api/config`，发送验证码走 `/api/login/start`。
3. 验证码和 2FA 分别走 `/api/login/code` 与 `/api/login/password`。
4. StringSession 和 `.session` 导入会弹出确认，成功后重置当前客户端。
5. StringSession 和 `.session` 导出必须先申请 60 秒一次性令牌，令牌使用后立即失效。

会话和消息：

1. `/chats` 默认请求 `/api/dialogs?limit=120`。
2. 搜索只过滤前端已加载会话，字段包括名称、用户名、peer 和 ID。
3. `/chat/<peer>` 默认请求 `/api/messages?limit=80`，更早消息使用 `offset_id` 翻页。
4. 文本消息使用安全 Markdown 渲染，不执行原始 HTML。

媒体和下载：

1. 消息列表优先请求缩略图，不自动下载原文件。
2. 点击媒体预览时，前端调用 `/api/media/prepare` 按需准备缓存。
3. 媒体下载按钮调用 `/api/download-media` 创建后台任务。
4. 照片下载到 `Pictures/`，其他媒体或文件下载到 `Download/`。
5. 任务支持暂停、恢复、取消；终态记录可移除但不删除已下载文件。
6. 终态任务历史写入 `data/task-history.json`，运行中任务不持久化。

诊断和错误：

1. `/diagnostics` 只渲染 `/api/diagnostics` 的白名单状态。
2. 内部 API 错误返回通用文案和 `error_id`，前端显示错误 ID 并在支持剪贴板时尝试复制。
3. 服务端日志可搜索 `internal api error <error_id>`。
4. 诊断脚本不读取 `data/config.json`，也不会打印 Token、StringSession、`.session`、代理凭据或 Telegram API 凭据。

## 7. 前端交互基线

- 顶部状态展示 Telegram 连接/授权摘要，刷新按钮只刷新状态摘要。
- 底部导航是主导航，当前页面使用 `aria-current="page"`。
- 敏感操作使用自定义确认弹窗，支持取消、确认、Esc 关闭、Tab/Shift+Tab 焦点循环。
- 媒体查看器支持焦点恢复、Esc 关闭、左右方向键切换和焦点循环。
- 登录、会话、聊天、下载和诊断页面都有标题关联、列表语义、live region 或动态 `aria-busy`。
- 登录页配置输入提供与后端边界一致的轻量 HTML 提示和隐藏辅助说明；真正校验仍以后端中文错误为准。
- 登录页保存配置、发送验证码、提交验证码、提交 2FA、退出登录、StringSession 导入导出和 `.session` 导入导出同一时间只处理一个操作；重复触发会显示中文忙碌提示。
- StringSession 和 `.session` 导入成功后会等待配置与顶部 Telegram 状态刷新完成，再显示成功提示。
- 下载页文件分页状态和加载更多按钮保持可访问状态。
- 前端 API 错误统一通过 toast 展示；401 会跳转 `/auth?next=...`。

## 8. 测试和验证

每阶段最低回归：

```sh
PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py
git diff --check
git status --short
```

推荐完整回归：

```sh
sh -n scripts/diagnose-runtime.sh
sh scripts/diagnose-runtime.sh
TELEGRAM_WEB_HOST=0.0.0.0 sh scripts/diagnose-runtime.sh
TELEGRAM_WEB_DIAGNOSTICS_URL=http://127.0.0.1:9/api/diagnostics sh scripts/diagnose-runtime.sh
sh scripts/check-browser-smoke-env.sh
PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py
PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v
node --check static/js/app.js
node --check tests/frontend_smoke.js
node tests/frontend_smoke.js
git diff --check
git diff --cached --check
```

当前自动化基线：

- 后端单测：`tests/test_core.py`，当前 57 个测试。
- 前端 smoke：`tests/frontend_smoke.js`，输出 `frontend smoke passed`。
- 真实浏览器 smoke：仍为手动清单，见 `docs/browser-smoke.md`。
- 当前环境检查脚本会报告 Playwright 模块和常见浏览器命令是否可用，但不安装依赖。

敏感信息检查：

```sh
rg -n "api_hash|StringSession|\\.session|Bearer\\s+[A-Za-z0-9._-]{16,}|sk-[A-Za-z0-9]|password\\s*[:=]" .
```

命中字段名、示例、测试假数据和文档说明可以保留；真实凭据必须移除。

## 9. 开源复用策略

阶段开发前判断是否已有成熟方案可复用：

| 场景 | 优先方向 |
|------|----------|
| Telegram API | 继续优先使用 `Telethon` |
| Web 框架和实时事件 | 继续使用 `Flask` / `Flask-SocketIO` |
| Markdown/富文本 | 若扩展语法，优先评估成熟安全解析库 |
| 大文件下载和 Range | 现有实现满足单段 Range；复杂断点续传再评估成熟库或标准实现 |
| 前端组件 | 当前不引入构建链；如引入，必须同步 npm 元数据、锁文件和验证命令 |
| 浏览器自动化 | 满足环境和仓库脚本条件后，再评估 Playwright 或替代方案 |

采用或不采用外部方案时，需要记录：

- 项目地址或包名。
- 许可证兼容性。
- 维护状态。
- 替代现有代码的边界。
- 新增依赖和验证命令。
- 不采用的原因。

## 10. 阶段开发制度

阶段编号使用 `Phase N`。每阶段只处理一个清晰目标，完成后必须更新：

```text
docs/progress/YYYY-MM-DD-phase-N-主题.md
docs/handoff/YYYY-MM-DD-phase-N-to-phase-N+1.md
docs/handoff/LATEST.md
```

新阶段启动流程：

1. 阅读本文。
2. 阅读 `docs/handoff/LATEST.md` 和最新 `docs/progress/`。
3. 运行 `git status --short --branch`，确认工作区状态。
4. 运行 `git log --oneline -5`，确认最近提交。
5. 确认 Git 身份为 `liyw0205 <2650115317@qq.com>`。
6. 根据交接文档确认阶段目标、验收标准、风险和建议拆分。
7. 如目标涉及依赖或通用能力，先评估成熟方案。

阶段实施流程：

1. 被动检查：先看文件、路由、配置、文档、测试和现有行为。
2. 明确边界：写清本阶段做什么和不做什么。
3. 小步修改：优先沿用现有 Flask/Telethon/Jinja/原生 JS 风格。
4. 验证：运行与改动匹配的自动化和检查命令。
5. 文档：更新进度文档、交接文档和必要用户文档。
6. 提交：非交互式 `git commit`。
7. 推送：使用 SSH 推送到 `origin/main`。

常用推送命令：

```sh
GIT_SSH_COMMAND='ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new' git push origin main
```

## 11. 进度文档模板

```markdown
# Phase N 主题

## 阶段目标

- ...

## 完成内容

- ...

## 主代理工作

- ...

## 子代理协作

- 子代理：
- 任务：
- 输出：
- 采纳情况：

## 改动文件

- `path`

## 开源复用评估

- 候选：
- 结论：
- 原因：

## 验证结果

- `command`：结果

## 风险和遗留

- ...

## Git

- 提交：
```

## 12. 交接文档模板

```markdown
# Phase N -> Phase N+1 交接

## 当前完成进度

- ...

## 本阶段提交

- commit：
- 主要文件：

## 已验证

- `command`：结果

## 未完成/风险

- ...

## 下阶段目标

- ...

## 建议子代理拆分

- Explorer：
- Worker：
- Verifier：

## 续会启动步骤

1. 阅读 `Telegram_Web开发.md`。
2. 阅读本文。
3. 运行 `git status --short` 和 `git log --oneline -5`。
4. 确认 Git 身份。
5. 按“下阶段目标”继续。
```

## 13. 常用检索命令

查看 Flask 路由：

```sh
rg -n "^@app\\.route|^@socketio|def api_|def page_" app.py
```

查看配置和路径：

```sh
rg -n "DATA_DIR|DOWNLOAD_DIR|PICTURES_DIR|CACHE_DIR|UPLOAD_DIR|CONFIG_FILE|DEFAULT_CONFIG|CONFIG_FIELDS" app.py
```

查看校验和参数边界：

```sh
rg -n "normalize_|parse_proxy|query_int_arg|request_json_object|parse_range_header|send_file_range" app.py tests/test_core.py
```

查看 Telegram 主流程：

```sh
rg -n "class TelegramService|ensure_client|start_login|sign_in|dialogs|messages|send_|download_media|prepare_media" app.py
```

查看任务状态：

```sh
rg -n "class TaskStore|task_controls|tasks\\.update|pause|resume|canceled|terminal_statuses" app.py static/js/app.js
```

查看前端 API 调用：

```sh
rg -n "api\\(|fetch\\(|io\\(|/api/|socket|downloadMedia|prepareMedia|send" static/js/app.js templates
```

## 14. 阶段摘要

| 阶段 | 摘要 |
|------|------|
| Phase 0 | 建立开发方案、进度/交接文档规则和阶段验收方式 |
| Phase 1 | 建立 `.gitignore`、最小测试、JSON 请求体、文件路径、配置脱敏和默认本机监听安全基线 |
| Phase 2 | 增加 Web Token 鉴权、配置字段校验、Socket.IO 鉴权和登录页配置保存 |
| Phase 3 | 强化媒体 Range、任务终态保护、取消竞态、`.part` 临时文件和任务反馈 |
| Phase 4 | 增加下载文件分页、内部错误 `error_id` 和移动端布局收紧 |
| Phase 5 | 补充 StringSession 和 `.session` 导入导出，StringSession 登录后自动持久化 |
| Phase 6 | 增加终态任务历史、错误 ID 前端展示/复制和启动脚本 |
| Phase 7 | 为 session 导出增加 60 秒一次性令牌，统一敏感操作确认 |
| Phase 8-10 | 建立并扩展纯 Node 前端 smoke harness，覆盖确认、session、任务、下载和 API 错误 |
| Phase 11-15 | 自定义确认弹窗和媒体查看器键盘/焦点行为完善，重组前端 smoke |
| Phase 16 | 评估真实浏览器 smoke 条件，新增环境检查脚本和手动 smoke 清单 |
| Phase 17-20 | 增加运行诊断脚本、runbook、`/api/diagnostics` 和 `/diagnostics` 页面 |
| Phase 21-27 | 为诊断、登录、全局反馈、下载、聊天、会话页面补齐可访问性语义并收口到 browser smoke |
| Phase 28-29 | 同步 README/runbook 的验证、启动、对外监听、Web Token、备份和恢复说明 |
| Phase 30 | 对齐登录页、StringSession、`.session`、Web Token、一次性令牌文案和测试 |
| Phase 31 | 对齐下载任务、终态记录、分页文件、`.part`、错误 ID 和中文任务状态文案 |
| Phase 32 | 对齐聊天页发送、媒体缩略图、按需准备、下载任务和媒体查看器文案 |
| Phase 33 | 对齐会话列表搜索、无匹配空状态、诊断摘要端口和运行端口文案 |
| Phase 34 | 对齐顶部状态、主导航、Web Token 验证页、401 提示和错误 ID 复制提示 |
| Phase 35 | 对齐配置校验、JSON、分页、Range 和代理端口错误文案，收敛代理端口错误 |
| Phase 36 | 重生成主开发文档，按当前代码和文档基线重整架构、边界、验证和阶段制度 |
| Phase 37 | 对齐登录页配置输入提示、隐藏辅助说明、前端 payload smoke 和后端中文错误 toast 覆盖 |
| Phase 38 | 复核真实浏览器自动化条件，收口未保存 `api_hash` 运行时提示和 browser smoke 结论 |
| Phase 39 | 收口登录页配置保存刷新等待、数字字段字符串化和登录操作忙碌保护 |
| Phase 40 | 收口 Session 迁移导入刷新等待、导入导出忙碌保护和失败回退 smoke |

## 15. 后续建议

下一阶段建议继续 Phase 41：下载页任务轮询和文件分页状态边界复核。

优先检查：

- 复核下载任务轮询、删除/取消任务和加载更多文件的连续点击边界。
- 复核下载页 `aria-busy`、空状态、错误 toast 和分页状态在失败后是否保持一致。
- 如发现状态竞态或提示延迟，优先在原生 JS 中做小范围状态控制和 smoke 覆盖。

限制：

- 不改变下载 API、任务队列、文件服务、鉴权逻辑、Telethon 行为或新增依赖。
- 不读取或提交运行数据、session、Token 或真实 Telegram 凭据。
