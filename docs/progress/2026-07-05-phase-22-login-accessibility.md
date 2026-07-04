# Phase 22 登录页表单可访问性

## 阶段目标

- 只读复查 `templates/login.html` 和登录页相关 JS 的表单标签、提示、错误反馈和敏感字段占位符。
- 给登录页配置表单和 Session 迁移区域增加低风险可访问性语义。
- 不改变登录、验证码、2FA、session 导入导出和 Web Token 保存流程。
- 不展示或提交真实 API hash、手机号、代理凭据、StringSession、`.session` 和 Web Token。
- 补充后端页面测试，继续不引入前端构建链或浏览器自动化依赖。

## 完成内容

- `templates/login.html`：
  - 顶部介绍区域增加 `aria-labelledby` 和稳定标题 `id`。
  - 手机号登录区域增加 `aria-labelledby` 和稳定标题 `id`。
  - 所有配置输入控件增加显式 `label for` 绑定。
  - `api_hash`、代理、Session 文件名、StringSession、Web Token 和上传 `.session` 控件增加隐藏说明，通过 `aria-describedby` 关联。
  - 手机号输入增加 `autocomplete="tel"`；敏感或配置字段使用 `autocomplete="off"`。
  - StringSession 文本框关闭 spellcheck，避免本地拼写工具处理 session 文本。
  - 登录操作、StringSession 操作和 `.session` 文件操作增加 `role="group"` 与 `aria-label`。
  - 所有操作按钮增加 `type="button"`，避免未来被表单容器包裹后触发隐式提交。
- `static/css/app.css`：
  - 新增通用 `.sr-only` 辅助类，用于隐藏但可被辅助技术读取的说明文本。
- `tests/test_core.py`：
  - 新增 `test_login_page_has_accessible_form_semantics`，覆盖登录页静态语义、隐藏说明、操作分组和按钮类型。
- `Telegram_Web开发.md` 同步 Phase 22 记录。

## 主代理工作

- 按 Phase 21 交接启动 Phase 22，确认工作区干净、最近提交和 Git 身份。
- 只读梳理登录页模板、配置加载/提交 helper 和现有 smoke。
- 选择不改 JS 登录流程，只补模板语义和 CSS 辅助类。
- 补充后端页面测试、文档、验证和提交。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段修改范围较小，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `templates/login.html`
- `static/css/app.css`
- `tests/test_core.py`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-22-login-accessibility.md`
- `docs/handoff/2026-07-05-phase-22-to-phase-23.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：axe-core、Playwright accessibility snapshot、表单校验/可访问性组件库。
- 结论：本阶段不新增外部依赖。
- 原因：
  - 当前目标是静态表单语义补强，原生 label、ARIA 和隐藏说明足够。
  - 登录流程涉及真实 Telegram 凭据和 session，自动化浏览器/a11y 工具需要额外隔离边界。
  - 当前环境仍缺少浏览器自动化条件，新增 npm 依赖会扩大阶段范围。

## 验证结果

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest tests.test_core.FlaskBoundaryTest.test_login_page_has_accessible_form_semantics tests.test_core.FlaskBoundaryTest.test_page_routes_render_without_telegram_login -v`：通过，2 个测试
- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `sh -n scripts/diagnose-runtime.sh`：通过
- `sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=0`
- `TELEGRAM_WEB_HOST=0.0.0.0 sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=1`，warning 为未设置环境变量 Web Token
- `TELEGRAM_WEB_DIAGNOSTICS_URL=http://127.0.0.1:9/api/diagnostics sh scripts/diagnose-runtime.sh`：通过，HTTP 探测失败按 warning 处理
- `sh scripts/check-browser-smoke-env.sh`：通过；输出自动化浏览器 smoke 当前不可用，使用手动清单
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，52 个测试
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `git diff --check`：通过

## 风险和遗留

- 未执行真实浏览器或屏幕阅读器人工 smoke。
- 登录页可访问性仍以静态 HTML 测试为主，不替代真实辅助技术验证。
- 本阶段没有改变登录 API、验证码、2FA、session 导入导出或 Web Token 保存行为。

## Git

- 提交：提交信息 `phase22: improve login form accessibility`；精确 hash 以 `git log -1 --oneline` 为准。
