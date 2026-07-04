# Phase 23 顶部状态和全局反馈语义

## 阶段目标

- 只读复查 `templates/base.html`、`toast()`、`refreshStatus()` 和全局确认弹窗状态反馈。
- 给顶部状态、toast 容器和刷新按钮增加低风险状态语义。
- 不改变 API 调用、Socket.IO 连接、确认弹窗行为和导航结构。
- 不展示或提交真实 Token、Cookie、Telegram 凭据或 session 内容。
- 补充后端页面测试和纯 Node smoke，继续不引入前端构建链或浏览器自动化依赖。

## 完成内容

- `templates/base.html`：
  - 顶部连接状态 `topStatus` 增加 `role="status"`、`aria-live="polite"` 和 `aria-atomic="true"`。
  - 顶部刷新按钮增加 `aria-label` 和 `title`。
  - toast 容器增加 `role="status"`、`aria-live="polite"` 和 `aria-atomic="false"`。
  - 确认弹窗既有 `role="dialog"`、`aria-modal`、标题和描述关联保持不变。
- `static/js/app.js`：
  - `toast()` 创建的 toast item 增加 `role="status"`。
  - `refreshStatus()` 请求期间给 `topStatus` 设置 `aria-busy="true"`，成功、未连接或异常后设置为 `false`。
  - 顶部状态文案和 API 请求路径未改变。
- `tests/frontend_smoke.js`：
  - mock DOM 注册 `topStatus` 和 `toast`。
  - 新增 `refreshStatus()` smoke，覆盖顶部状态文本和动态 `aria-busy=false`。
- `tests/test_core.py`：
  - 新增 base 模板全局反馈静态语义测试。
- `Telegram_Web开发.md` 同步 Phase 23 记录。

## 主代理工作

- 按 Phase 22 交接启动 Phase 23，确认工作区干净、最近提交和 Git 身份。
- 只读梳理 base 模板、toast/status helper、确认弹窗语义和现有 smoke。
- 保持现有确认弹窗行为不变，只补顶部状态和 toast 的可访问性语义。
- 补充测试、文档、验证和提交。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段修改范围较小，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `templates/base.html`
- `static/js/app.js`
- `tests/frontend_smoke.js`
- `tests/test_core.py`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-23-global-feedback-accessibility.md`
- `docs/handoff/2026-07-05-phase-23-to-phase-24.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：axe-core、Playwright accessibility snapshot、toast/notification 组件库。
- 结论：本阶段不新增外部依赖。
- 原因：
  - 当前目标是原生 HTML/ARIA 状态语义补强，现有模板和纯 Node smoke 足够覆盖。
  - 当前环境仍缺少浏览器自动化条件。
  - 引入通知组件库会改变现有 toast 行为和样式边界，收益不足。

## 验证结果

- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest tests.test_core.FlaskBoundaryTest.test_base_template_has_global_feedback_semantics tests.test_core.FlaskBoundaryTest.test_page_routes_render_without_telegram_login -v`：通过，2 个测试
- `sh -n scripts/diagnose-runtime.sh`：通过
- `sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=0`
- `TELEGRAM_WEB_HOST=0.0.0.0 sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=1`，warning 为未设置环境变量 Web Token
- `TELEGRAM_WEB_DIAGNOSTICS_URL=http://127.0.0.1:9/api/diagnostics sh scripts/diagnose-runtime.sh`：通过，HTTP 探测失败按 warning 处理
- `sh scripts/check-browser-smoke-env.sh`：通过；输出自动化浏览器 smoke 当前不可用，使用手动清单
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，53 个测试
- `git diff --check`：通过

## 风险和遗留

- 未执行真实浏览器或屏幕阅读器人工 smoke。
- 全局反馈可访问性仍以静态 HTML 测试和纯 Node mock 为主。
- 本阶段没有做 toast 队列、持续时间或确认弹窗行为调整。

## Git

- 提交：提交信息 `phase23: improve global feedback accessibility`；精确 hash 以 `git log -1 --oneline` 为准。
