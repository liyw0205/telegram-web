# Phase 25 聊天页消息和发送区可访问性

## 阶段目标

- 只读复查 `templates/chat.html`、消息列表、输入区、文件发送控件、图库入口和相关 JS 渲染。
- 给消息流、发送表单、附件/文件控件、发送按钮和媒体查看器增加低风险可访问性语义。
- 不改变消息 API、Socket.IO 新消息处理、媒体预览/下载流程、发送文件接口和既有键盘行为。
- 不读取或提交 `Download/`、`Pictures/`、`data/`、`.session` 和任何真实 Token。
- 补充后端页面测试和纯 Node smoke，继续不引入前端构建链或浏览器自动化依赖。

## 完成内容

- `templates/chat.html`：
  - 聊天页主区域增加标题关联。
  - 返回和刷新按钮增加 `type="button"`、可访问名称和刷新 `title`。
  - 消息列表增加 `role="log"`、`aria-live`、`aria-relevant` 和初始 `aria-busy`。
  - 消息操作栏增加 `role="group"`，文字/媒体面板按钮增加 `aria-controls` 和 `aria-expanded`。
  - 文字发送区和文件发送区增加区域语义、可访问名称、初始 `aria-hidden` 和 `aria-busy`。
  - 消息文本框、文件选择框和说明文字输入框增加可访问名称。
  - 媒体查看器增加 dialog 语义、标题/描述关联、按钮名称和索引 live status。
- `static/js/app.js`：
  - `toggleComposer()` 同步发送面板 `aria-hidden` 和按钮 `aria-expanded`。
  - `loadMessages()` 和 `loadOlderMessages()` 动态维护消息列表 `aria-busy`，空/加载/错误状态增加 status 语义。
  - 动态消息块增加 `role="article"` 和区分收发/媒体的 `aria-label`。
  - 媒体下载按钮统一通过 helper 渲染，增加 `type="button"` 和按消息 ID 区分的 `aria-label`。
  - `sendText()` 和 `sendFile()` 请求期间动态维护对应发送面板 `aria-busy`，发送后同步 `aria-hidden`。
- `tests/frontend_smoke.js`：
  - mock DOM 增加聊天页元素、基础 child 插入和 FormData append 支持。
  - 新增聊天消息 smoke，覆盖消息加载 `aria-busy=false`、动态消息 article 语义、发送后面板状态和已发送消息标签。
- `tests/test_core.py`：
  - 新增聊天页静态可访问性语义测试。
- `Telegram_Web开发.md` 同步 Phase 25 记录和前端 smoke 覆盖说明。

## 主代理工作

- 按 Phase 24 交接启动 Phase 25，确认工作区干净、最近提交和 Git 身份。
- 只读梳理聊天页模板、消息/发送 JS helper、图库入口和现有 smoke。
- 保持消息 API、Socket.IO、新消息追加、媒体预览/下载、发送文件接口和键盘行为不变。
- 补充测试、文档、验证和提交。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段修改范围较小，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `templates/chat.html`
- `static/js/app.js`
- `tests/frontend_smoke.js`
- `tests/test_core.py`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-25-chat-accessibility.md`
- `docs/handoff/2026-07-05-phase-25-to-phase-26.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：axe-core、Playwright accessibility snapshot、现成聊天组件。
- 结论：本阶段不新增外部依赖。
- 原因：
  - 当前目标是原生 HTML/ARIA 语义补强，现有模板和纯 Node smoke 足够覆盖。
  - 当前环境仍缺少浏览器自动化条件。
  - 引入聊天组件会改动消息流、媒体预览和发送区结构，超出本阶段低风险目标。

## 验证结果

- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest tests.test_core.FlaskBoundaryTest.test_chat_page_has_accessible_message_and_composer_semantics tests.test_core.FlaskBoundaryTest.test_page_routes_render_without_telegram_login -v`：通过，2 个测试
- `sh -n scripts/diagnose-runtime.sh`：通过
- `sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=0`
- `TELEGRAM_WEB_HOST=0.0.0.0 sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=1`，warning 为未设置环境变量 Web Token
- `TELEGRAM_WEB_DIAGNOSTICS_URL=http://127.0.0.1:9/api/diagnostics sh scripts/diagnose-runtime.sh`：通过，HTTP 探测失败按 warning 处理
- `sh scripts/check-browser-smoke-env.sh`：通过；输出自动化浏览器 smoke 当前不可用，使用手动清单
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，55 个测试
- `git diff --check`：通过

## 风险和遗留

- 未执行真实浏览器或屏幕阅读器人工 smoke。
- 聊天页可访问性仍以静态 HTML 测试和纯 Node mock 为主。
- 本阶段没有调整消息分页、Socket.IO 新消息策略、媒体准备流程、文件发送协议或键盘快捷键。

## Git

- 提交：提交信息 `phase25: improve chat accessibility`；精确 hash 以 `git log -1 --oneline` 为准。
