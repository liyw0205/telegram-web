# Telegram Web 开发方案

> **当前产品基线**：Web Telegram，Flask + Flask-SocketIO + Telethon 的个人 Telegram Web 管理与聊天界面。
> **仓库**：`telegram-web`，当前 HEAD 以 `git log -1 --oneline` 为准。
> **本文**：`telegram-web/Telegram_Web开发.md`，长期开发方案和阶段会话协作规则。
> **运行形态**：单进程 Python Web 服务，后端负责 Telegram 客户端、下载任务、媒体缓存和 Socket.IO 推送；前端为 Jinja 模板 + 原生 JavaScript/CSS。
> **最低回归规则**：每阶段至少跑 `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py` 和 `git diff --check`；涉及行为修改时补充对应手动或自动验证。

## 当前结论

本项目当前定位是 **个人 Telegram 数据浏览、聊天、媒体预览和下载管理工具**。它不是 Telegram Bot，也不是独立前端 SPA；核心入口是 `app.py` 中的 Flask 路由和 `TelegramService` 封装的 Telethon 客户端。

一句话目标：在不泄露 Telegram API 凭据和本地会话数据的前提下，持续提高登录、会话浏览、消息收发、媒体预览、断点/任务下载、配置持久化和移动端 Web 体验的稳定性。

## 当前主线

后续开发围绕四个问题展开：

| 问题 | 目标 |
|------|------|
| 登录和会话怎么更稳？ | API ID/Hash、手机号、代理、2FA、StringSession 和 `.session` 文件流程可恢复、可解释 |
| 媒体怎么更可靠？ | 缩略图、预览、下载任务、Range 响应、缓存清理和大文件处理边界清晰 |
| 前端怎么更顺手？ | 会话列表、聊天流、图库、发送文件、任务管理和移动端布局减少误操作 |
| 开发怎么可续接？ | 每阶段独立目标、主代理+子代理协作、进度/交接文档、验证结果和 Git 提交可追溯 |

## 固定边界

- **不提交真实 Telegram 凭据和会话**：`api_id`、`api_hash`、手机号、代理账号、StringSession、`.session`、Cookie、Token 只能存在于运行配置或本地数据目录，不能进入仓库文档示例以外的真实内容。
- **不提交运行数据**：`data/`、`Download/`、`Pictures/`、`media-cache/`、`uploads/` 和临时下载文件属于运行态数据。
- **不扩大到无关账户或目录**：开发默认只处理本仓库、运行进程、本项目创建的数据目录和用户明确提供的测试数据。
- **不绕过 Telegram 授权流程**：登录、验证码、2FA、退出登录和 session 导入导出必须保持可审计，不写隐藏式自动登录逻辑。
- **不把前端无计划改成大型构建链**：当前是模板 + 原生 JS/CSS；只有在阶段目标明确、收益足够、验证和部署方式同步更新时，才引入 npm/Vite/React 等构建链。
- **优先复用成熟开源方案**：如果 GitHub、npm 或 PyPI 上存在维护活跃、许可证兼容、集成成本合理的成熟方案，优先依赖或适配，不从头实现同类基础能力。
- **每阶段都要可回滚**：小步提交，避免无关重构；生成文件、缓存和凭据不进入提交。
- **阶段结束必须提交 Git**：每个阶段完成后更新进度和交接文档，跑验证，创建一次非交互式 Git 提交。

## 工作区结构

| 路径 | 作用 |
|------|------|
| `app.py` | Flask 应用、Telethon 客户端、配置、任务队列、下载和媒体缓存逻辑 |
| `requirements.txt` | Python 运行依赖：`flask`、`flask-socketio`、`telethon`、`pysocks`、`python-socketio` |
| `templates/base.html` | 页面基础布局、顶部状态、导航和脚本入口 |
| `templates/login.html` | Telegram API 配置、手机号登录、验证码和 2FA 操作入口 |
| `templates/chats.html` | 会话列表页面 |
| `templates/chat.html` | 单会话聊天页面、消息流和输入区容器 |
| `templates/downloads.html` | 下载任务和已下载文件页面 |
| `templates/diagnostics.html` | 只读脱敏诊断页面 |
| `static/js/app.js` | 前端 API 封装、Socket.IO、会话/消息/媒体/下载交互 |
| `static/css/app.css` | 全站样式和移动端布局 |
| `tests/frontend_smoke.js` | 纯 Node 前端行为 smoke，按确认弹窗、媒体查看器、登录页/API、session/任务确认、下载页和诊断页分组，在 mock 浏览器环境验证自定义敏感确认、键盘焦点循环、媒体查看器键盘交互和焦点循环、导出令牌、API 错误、登录页配置、下载页状态和诊断页脱敏渲染 |
| `docs/browser-smoke.md` | 真实浏览器手动 smoke 验证清单和后续 Playwright 引入边界 |
| `scripts/check-browser-smoke-env.sh` | 检查当前 shell 是否具备浏览器自动化 smoke 条件，不安装依赖 |
| `docs/runtime-runbook.md` | 启动、访问、日志观察、Web Token 和常见故障排查清单 |
| `scripts/diagnose-runtime.sh` | 本机运行预检脚本，不读取运行配置和凭据 |
| `docs/progress/` | 每阶段开发进度文档 |
| `docs/handoff/` | 每阶段会话交接文档，`LATEST.md` 指向/承载最新交接内容 |

## 配置和数据路径

应用启动时会创建以下运行目录：

```text
data/
Download/
Pictures/
data/media-cache/
data/uploads/
```

关键文件和目录：

| 文件/目录 | 说明 |
|-----------|------|
| `data/config.json` | API 配置、代理、session 类型、下载线程数和缓存上限 |
| `data/task-history.json` | 终态下载/预览任务历史，最多保留最近记录，不能提交 |
| `data/telegram.session` 或自定义 session 文件 | Telethon 文件会话，不能提交 |
| `Download/` | 用户主动下载的媒体文件 |
| `Pictures/` | 图片文件服务目录 |
| `data/media-cache/` | 聊天媒体预览和临时缓存 |
| `data/uploads/` | 发送文件时的临时上传目录 |

配置加载规则：

1. `load_config()` 从 `data/config.json` 读取配置，缺失时写入默认配置。
2. `api_config()` 只允许更新白名单字段：`api_id`、`api_hash`、`phone`、`proxy`、`session_type`、`session_file`、`string_session`、`download_threads`、`cache_limit_mb`。
3. `download_threads` 被限制在 `1..128`，`cache_limit_mb` 被限制在 `128..10240`。
4. 修改配置后调用 `tg.reload_config()`，同时刷新下载线程池和媒体缓存清理。

## 功能入口

### 页面入口

| 路由 | 说明 |
|------|------|
| `GET /` | 重定向到 `/chats` |
| `GET /login` | 登录与配置页面 |
| `GET /chats` | 会话列表 |
| `GET /chat/<peer>` | 单会话消息页面 |
| `GET /downloads` | 下载任务和已下载文件 |
| `GET /diagnostics` | 只读脱敏运行诊断页面 |

### API 入口

| API | 说明 |
|-----|------|
| `GET/POST /api/config` | 读取/保存运行配置 |
| `GET /api/status` | Telegram 连接和授权状态 |
| `POST /api/login/start` | 创建客户端并发起验证码登录 |
| `POST /api/login/code` | 提交验证码 |
| `POST /api/login/password` | 提交 2FA 密码 |
| `POST /api/logout` | 退出登录 |
| `GET /api/diagnostics` | 返回脱敏运行诊断状态，不暴露 `api_hash`、StringSession、`.session` 内容、Web Token 或代理凭据 |
| `POST /api/session/export-token` | 生成 60 秒一次性 session 导出令牌，类型为 `string` 或 `file` |
| `GET/POST /api/session/string` | 导出或导入 StringSession；导出必须带一次性 `export_token` |
| `GET/POST /api/session/file` | 导出或导入 `.session` 文件；导出必须带一次性 `export_token` |
| `GET /api/dialogs` | 获取会话列表 |
| `GET /api/messages` | 获取消息列表，支持 `offset_id` 翻页 |
| `POST /api/send` | 发送文本消息 |
| `POST /api/send-file` | 上传并发送文件 |
| `POST /api/media/thumb` | 获取媒体缩略图 |
| `POST /api/media/prepare` | 准备媒体预览缓存 |
| `POST /api/download-media` | 创建下载任务 |
| `GET/DELETE /api/task/<task_id>` | 查询任务、取消运行中任务或移除任务记录 |
| `POST /api/task/<task_id>/pause` | 暂停任务 |
| `POST /api/task/<task_id>/resume` | 恢复任务 |
| `GET /api/tasks` | 下载/预览任务列表 |
| `GET /api/download-files` | 已下载文件列表 |
| `GET /download-file/<filename>` | Range 方式访问下载文件 |
| `GET /pictures/<filename>` | Range 方式访问图片目录文件 |
| `GET /media-cache/<filename>` | Range 方式访问媒体缓存 |

### Socket.IO

| 事件 | 说明 |
|------|------|
| `connect` | 服务端返回 `server_message` |
| `new_message` | Telethon 新消息事件转发给前端 |

## 开源复用策略

阶段开发前必须先判断是否已有成熟方案可复用：

| 场景 | 优先方向 |
|------|----------|
| Telegram API | 优先延续 `Telethon`，除非阶段明确证明需要替换 |
| Web 框架和实时事件 | 优先延续 `Flask` / `Flask-SocketIO`，避免无目标迁移 |
| Markdown/富文本 | 优先评估成熟、安全的解析库，不继续扩展脆弱正则 |
| 大文件下载/断点续传 | 优先评估成熟库或标准协议实现，再决定是否保留自研任务控制 |
| 前端组件/图标/交互 | 若引入 npm 构建链，优先使用维护活跃、体积可控的成熟组件 |
| 测试工具 | Python 后端优先 `pytest` 或标准库 `unittest`；前端行为可评估 Playwright |

复用前必须记录：

- 项目地址或包名。
- 许可证是否兼容。
- 最近维护状态和社区活跃度。
- 替代当前自研代码的边界。
- 新增依赖、配置和验证命令。
- 不采用该方案的原因。

## 分阶段会话开发制度

本项目开发必须采用多阶段、多会话方式，避免单次会话上下文过大。每个阶段只处理一个清晰目标，完成后提交 Git，并生成阶段进度和交接文档。

### 阶段编号

阶段编号使用：

```text
Phase 0, Phase 1, Phase 2, ...
```

文档路径使用：

```text
docs/progress/YYYY-MM-DD-phase-N-主题.md
docs/handoff/YYYY-MM-DD-phase-N-to-phase-N+1.md
docs/handoff/LATEST.md
```

`LATEST.md` 必须包含最新完整交接内容，或明确指向最新交接文件并保留阶段摘要。

### 每阶段启动流程

新阶段开始时，主代理必须先执行：

1. 阅读 `Telegram_Web开发.md`。
2. 阅读 `docs/handoff/LATEST.md` 和最新 `docs/progress/`。
3. 运行 `git status --short`，确认工作区是否干净。
4. 查看最近提交：`git log --oneline -5`。
5. 根据交接文档确认本阶段目标、验收标准、风险和建议子代理拆分。
6. 如目标涉及依赖或组件，先查成熟开源方案，再决定复用或实现。

### 主代理职责

- 确定阶段目标和验收边界。
- 拆分子代理任务，避免多个代理同时修改同一文件。
- 负责关键架构判断、最终编辑整合、验证和提交。
- 维护 `docs/progress/` 和 `docs/handoff/`。
- 遇到用户未授权的凭据、运行数据或无关目录时停止扩展。

### 子代理职责

子代理按任务类型使用：

| 类型 | 适用任务 | 写权限 |
|------|----------|--------|
| Explorer | 只读梳理路由、数据流、依赖、测试缺口、开源方案候选 | 不改文件 |
| Worker | 修改明确文件集合，如 `app.py`、`static/js/app.js`、测试文件 | 只改分配范围 |
| Verifier | 跑测试、审 diff、复查安全和文档一致性 | 默认不改文件 |

子代理必须收到明确边界：

- 本阶段目标。
- 允许读取/修改的路径。
- 禁止触碰的运行数据和凭据。
- 预期输出格式。
- 不回退其他代理或用户的改动。

### 阶段实施流程

1. **被动检查**：先看文件、路由、配置、日志和现有行为。
2. **目标确认**：把本阶段只做什么、不做什么写入进度文档草稿。
3. **开源复用评估**：涉及通用能力时先评估 GitHub/npm/PyPI 成熟方案。
4. **小步修改**：优先按现有 Flask/Telethon/Jinja/原生 JS 风格实现。
5. **验证**：运行最低回归；行为改动必须有可复现命令或手动步骤。
6. **文档更新**：更新阶段进度和交接文档。
7. **Git 提交**：非交互式提交，提交信息体现阶段和结果。
8. **续会准备**：最终回复给出下一阶段口令和最新交接文档路径；若外部环境支持自动新会话，则以该交接文档作为启动上下文。

说明：仓库内可以自动生成文档和 Git 提交；真正“开启新会话”取决于 Codex CLI 或外部调度器能力。若环境不支持自动启动，新会话由用户发送“继续 telegram-web”触发，但仍必须依据 `docs/handoff/LATEST.md` 继续。

## 每阶段必守验收

最低命令：

```sh
PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py
git diff --check
git status --short
```

涉及依赖时：

```sh
python -m pip check
```

涉及后端行为时，按改动范围增加：

```sh
python -m unittest discover
```

如果仓库尚无测试，阶段内新增共享逻辑或修复回归时，应优先补最小可运行测试。

涉及前端行为时，至少记录一组浏览器手动验证：

```sh
node --check static/js/app.js
node --check tests/frontend_smoke.js
node tests/frontend_smoke.js
```

有真实浏览器环境时，再记录一组手动或自动验证：

```text
打开 /login -> 检查配置加载 -> 打开 /chats -> 打开一个 /chat/<peer> -> 预览/下载媒体 -> 查看 /downloads
```

涉及服务启动时：

```sh
python app.py
```

默认访问：

```text
http://127.0.0.1:5000
```

敏感信息检查：

```sh
rg -n "api_hash|StringSession|\\.session|Bearer\\s+[A-Za-z0-9._-]{16,}|sk-[A-Za-z0-9]|password\\s*[:=]" .
```

命中示例、字段名或文档说明可以保留；真实凭据必须移除。

## 进度文档模板

每阶段创建或更新：

```text
docs/progress/YYYY-MM-DD-phase-N-主题.md
```

模板：

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

## 交接文档模板

每阶段结束时创建：

```text
docs/handoff/YYYY-MM-DD-phase-N-to-phase-N+1.md
docs/handoff/LATEST.md
```

模板：

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
4. 按“下阶段目标”继续。
```

## 建议阶段路线

| 阶段 | 主题 | 目标 |
|------|------|------|
| Phase 0 | 文档和流程基线 | 建立开发方案、进度/交接文档规则并提交 |
| Phase 1 | 基线整理和安全边界 | 增加 `.gitignore`、最小测试骨架、配置/路径安全检查 |
| Phase 2 | 登录和 session 可靠性 | 梳理 `StringSession`/文件 session 导入导出、错误提示和代理校验 |
| Phase 3 | 媒体预览和下载任务 | 强化任务状态、暂停/取消语义、缓存清理和 Range 安全 |
| Phase 4 | 前端交互和移动端体验 | 优化聊天流、图库、发送文件、下载页和状态反馈 |
| Phase 5 | 部署和运维 | 补充启动脚本、环境变量、反向代理、备份恢复和发布说明 |

阶段路线不是硬性排期；每个新阶段以最新交接文档和用户目标为准。

## 搜索与验证命令

查看 Flask 路由：

```sh
rg -n "^@app\\.route|^@socketio|def api_|def page_" app.py
```

查看入口、数据路径和默认配置：

```sh
rg -n "@app.route|@socketio.on|DATA_DIR|DOWNLOAD_DIR|PICTURES_DIR|CONFIG_FILE|DEFAULT_CONFIG" app.py
```

查看 Telegram 客户端主流程：

```sh
rg -n "class TelegramService|ensure_client|start_login|sign_in|dialogs|messages|send_|download_media|prepare_media" app.py
```

查看任务状态：

```sh
rg -n "class TaskStore|task_controls|tasks\\.update|pause|resume|canceled" app.py static/js/app.js
```

查看运行数据路径：

```sh
rg -n "DATA_DIR|DOWNLOAD_DIR|PICTURES_DIR|CACHE_DIR|UPLOAD_DIR|CONFIG_FILE" app.py
```

查看前端 API 调用：

```sh
rg -n "api\\(|fetch\\(|io\\(|/api/|socket|downloadMedia|prepareMedia|send" static/js/app.js templates
```

## 开工口令

- “继续 telegram-web” -> 先读 `Telegram_Web开发.md` 和 `docs/handoff/LATEST.md`，再执行最新交接目标。
- “进入 Phase N” -> 按对应阶段交接文档启动，主代理先拆分子代理任务。
- “只做当前阶段收尾” -> 只更新进度/交接文档、跑验证、提交 Git，不开启新功能。
- “评估开源方案” -> 子代理先查候选，主代理决定复用边界并记录在进度文档。

## 最后更新

2026-07-04：建立 telegram-web 本地开发方案，明确项目定位、固定边界、路由/API、数据路径、开源复用策略、分阶段多会话机制、主代理+子代理协作、进度/交接文档模板和阶段验收命令。

2026-07-04：Phase 1 建立安全基线，新增 `.gitignore` 和最小单测，收紧 JSON 请求体、文件路径边界、配置响应脱敏和默认本机监听。

2026-07-04：Phase 2 增加 Web Token 访问控制、配置字段保存前校验、Socket.IO 鉴权和登录页配置保存入口，并删除未启用历史模板。

2026-07-04：Phase 3 强化媒体 Range 响应、任务终态保护、取消竞态处理、`.part` 临时下载和下载页任务操作反馈，测试扩展到 32 个。

2026-07-04：Phase 4 优化下载页分页加载和任务/文件刷新节奏，增加内部错误通用响应与 `error_id`，小幅收紧移动端下载卡片和聊天输入布局，测试扩展到 36 个。

2026-07-04：Phase 5 补充 StringSession 和 `.session` 文件导入导出，StringSession 登录成功后自动持久化，并完善 README 中部署、备份和恢复说明。

2026-07-04：Phase 6 增加终态任务历史持久化到 `data/task-history.json`，重启后恢复最近任务历史；前端内部错误提示展示 `error_id` 并尝试复制，新增 Termux/本机启动脚本。

2026-07-05：Phase 7 为 StringSession 和 `.session` 导出增加 60 秒一次性导出令牌，统一退出登录、导入/导出 session、取消/移除任务的前端确认语义，并补充错误 ID 日志检索说明。

2026-07-05：Phase 8 增加纯 Node 前端行为 smoke 测试，不引入 Playwright/npm 依赖，覆盖确认取消不发请求、确认后申请一次性导出令牌、文件导出 URL 和任务删除确认。

2026-07-05：Phase 9 扩展前端 smoke 覆盖下载任务渲染、任务接口错误、下载文件分页、分页按钮状态和下一页错误 toast，继续保持无前端构建链。

2026-07-05：Phase 10 重整前端 smoke harness，补充 `api()` 错误 ID 复制、401 跳转和 `loadLoginPage()` 脱敏配置占位符覆盖，继续不引入前端测试依赖。

2026-07-05：Phase 11 用轻量自定义确认弹窗替换敏感操作的原生 `confirm()`，覆盖确认、取消、Esc 关闭和并发确认边界；本地评估真实浏览器 smoke 条件后暂不引入 Playwright。

2026-07-05：Phase 12 为自定义确认弹窗增加轻量 focus trap，覆盖 Tab、Shift+Tab 和弹窗外焦点回拉；媒体查看器和 composer 键盘交互作为后续独立阶段处理。

2026-07-05：Phase 13 为媒体查看器增加打开前焦点记录、关闭后焦点恢复、Esc 关闭和左右方向键切换，并补充纯 Node smoke 覆盖。

2026-07-05：Phase 14 为媒体查看器增加最小 focus trap，覆盖关闭、下载、上一项、下一项按钮的 Tab / Shift+Tab 循环；点击遮罩关闭暂不引入，避免移动端误触行为变化。

2026-07-05：Phase 15 重组纯 Node 前端 smoke，抽出元素 ID、焦点和键盘断言 helper，并按确认弹窗、媒体查看器、登录/API、session/任务确认和下载页分组执行，保持无前端测试依赖。

2026-07-05：Phase 16 评估真实浏览器 smoke 条件，新增环境检查脚本和手动浏览器 smoke 清单；当前环境缺少 Playwright/浏览器命令，因此不引入新 npm 依赖。

2026-07-05：Phase 17 补充运行诊断脚本和运行排障 runbook，覆盖启动环境、Web Token、日志、常见故障和服务化边界；不新增守护进程依赖。

2026-07-05：Phase 18 新增 `/api/diagnostics` 脱敏诊断状态接口，并让运行诊断脚本支持可选 HTTP 探测；测试扩展到 50 个，覆盖诊断输出不泄露 secret。

2026-07-05：Phase 19 新增 `/diagnostics` 只读诊断页面和底部导航入口，前端只按白名单渲染布尔、枚举和数值状态，并补充纯 Node smoke 覆盖诊断页脱敏渲染和错误状态。

2026-07-05：Phase 20 复核真实浏览器 smoke 条件仍不足以引入自动化浏览器测试，将 `/diagnostics` 加入手动浏览器 smoke 清单，并记录继续不引入 npm/Playwright 依赖的边界。

2026-07-05：Phase 21 为 `/diagnostics` 增加标题关联、刷新按钮标签、live status、列表语义、动态 `aria-busy` 和成功/错误状态 class，并补充后端页面语义测试和纯 Node smoke 断言。

2026-07-05：Phase 22 为 `/login` 配置表单补充显式 label 绑定、区域标题关联、敏感字段隐藏说明、操作按钮分组和按钮类型，并新增登录页静态可访问性测试。

2026-07-05：Phase 23 为顶部连接状态、刷新按钮和 toast 容器补充 live/status 语义，`refreshStatus()` 增加动态 `aria-busy`，并补充全局反馈静态测试和纯 Node smoke。

2026-07-05：Phase 24 为下载页任务列表、文件列表、分页状态和刷新/加载按钮补充可访问性语义，下载刷新流程增加动态 `aria-busy`/`aria-disabled`，并补充下载页静态测试和纯 Node smoke。
