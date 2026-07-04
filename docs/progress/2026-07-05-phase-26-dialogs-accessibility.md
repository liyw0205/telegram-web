# Phase 26 会话列表页可访问性

## 阶段目标

- 只读复查 `templates/chats.html`、`loadDialogs()`、`renderDialogs()`、`filterDialogs()` 和会话列表 CSS。
- 给会话页标题、搜索框、刷新按钮、会话列表、空/错误状态和未读徽标增加低风险可访问性语义。
- 不改变 `/api/dialogs` 请求、会话跳转 URL、过滤逻辑、未读计数展示或 Socket.IO 行为。
- 不读取或提交 `Download/`、`Pictures/`、`data/`、`.session` 和任何真实 Token。
- 补充后端页面测试和纯 Node smoke，继续不引入前端构建链或浏览器自动化依赖。

## 完成内容

- `templates/chats.html`：
  - 会话页主区域增加标题关联。
  - 刷新按钮增加 `type="button"`、`aria-label` 和 `title`。
  - 搜索容器增加 `role="search"` 和可访问名称。
  - 搜索输入改为 `type="search"`，增加 `aria-label`、`aria-controls` 和 `autocomplete="off"`。
  - 会话列表增加 `role="list"`、标题关联、`aria-live` 和初始 `aria-busy`。
- `static/js/app.js`：
  - `loadDialogs()` 请求期间动态维护会话列表 `aria-busy`。
  - 加载、空状态和错误状态作为列表项渲染。
  - 新增会话类型和会话可访问名称 helper。
  - 动态会话项增加 `role="listitem"` 和包含名称、类型、用户名、未读数的 `aria-label`。
  - 未读徽标增加按数量区分的可访问名称。
  - `/api/dialogs?limit=120` 请求、跳转 URL 和过滤条件未改变。
- `tests/frontend_smoke.js`：
  - mock DOM 注册会话列表和搜索输入。
  - 新增会话列表 smoke，覆盖 `aria-busy=false`、动态列表项语义、跳转 URL 和未读徽标标签。
- `tests/test_core.py`：
  - 新增会话页静态可访问性语义测试。
- `Telegram_Web开发.md` 同步 Phase 26 记录和前端 smoke 覆盖说明。

## 主代理工作

- 按 Phase 25 交接启动 Phase 26，确认工作区干净、最近提交和 Git 身份。
- 只读梳理会话列表模板、会话列表 JS helper、现有 smoke 和 CSS。
- 保持 `/api/dialogs` 请求、会话跳转 URL、过滤逻辑、未读计数展示和 Socket.IO 行为不变。
- 补充测试、文档、验证和提交。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段修改范围较小，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `templates/chats.html`
- `static/js/app.js`
- `tests/frontend_smoke.js`
- `tests/test_core.py`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-26-dialogs-accessibility.md`
- `docs/handoff/2026-07-05-phase-26-to-phase-27.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：axe-core、Playwright accessibility snapshot、现成列表/搜索组件。
- 结论：本阶段不新增外部依赖。
- 原因：
  - 当前目标是原生 HTML/ARIA 语义补强，现有模板和纯 Node smoke 足够覆盖。
  - 当前环境仍缺少浏览器自动化条件。
  - 引入列表组件会改动会话项结构和现有过滤/跳转边界，超出本阶段低风险目标。

## 验证结果

- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest tests.test_core.FlaskBoundaryTest.test_chats_page_has_accessible_dialog_list_semantics tests.test_core.FlaskBoundaryTest.test_page_routes_render_without_telegram_login -v`：通过，2 个测试
- `sh -n scripts/diagnose-runtime.sh`：通过
- `sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=0`
- `TELEGRAM_WEB_HOST=0.0.0.0 sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=1`，warning 为未设置环境变量 Web Token
- `TELEGRAM_WEB_DIAGNOSTICS_URL=http://127.0.0.1:9/api/diagnostics sh scripts/diagnose-runtime.sh`：通过，HTTP 探测失败按 warning 处理
- `sh scripts/check-browser-smoke-env.sh`：通过；输出自动化浏览器 smoke 当前不可用，使用手动清单
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，56 个测试
- `git diff --check`：通过

## 风险和遗留

- 未执行真实浏览器或屏幕阅读器人工 smoke。
- 会话列表页可访问性仍以静态 HTML 测试和纯 Node mock 为主。
- 本阶段没有调整搜索过滤策略、会话排序、跳转 URL、未读计数来源或 Socket.IO 行为。

## Git

- 提交：提交信息 `phase26: improve dialogs accessibility`；精确 hash 以 `git log -1 --oneline` 为准。
