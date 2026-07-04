# Phase 21 诊断页可访问性语义

## 阶段目标

- 只读复查 `/diagnostics` 页面、渲染 helper 和样式的可访问性语义。
- 给诊断摘要、刷新按钮、诊断列表和动态加载/错误状态增加低风险语义。
- 不改变 `/api/diagnostics` 脱敏边界，不新增 secret、路径或 raw host 展示。
- 继续不引入前端构建链或浏览器自动化依赖。
- 补充后端页面测试和纯 Node smoke 覆盖。

## 完成内容

- `templates/diagnostics.html`：
  - 页面 section 增加 `aria-labelledby="diagnosticsTitle"`。
  - 标题增加稳定 `id`。
  - 刷新按钮增加 `aria-label` 和 `title`。
  - 摘要区域增加 `role="status"`、`aria-live="polite"`、`aria-atomic="true"` 和初始 `aria-busy="true"`。
  - 四个诊断分组增加稳定标题 `id`、`role="list"`、`aria-labelledby` 和初始 `aria-busy="true"`。
- `static/js/app.js`：
  - 新增诊断状态 helper，加载时设置 `aria-busy=true`，成功/失败时设为 `false`。
  - 成功状态给摘要增加 `ok` class，错误状态增加 `warn` class。
  - 诊断行渲染为 `role="listitem"`，并用白名单字段生成 `aria-label`。
  - 保持只渲染固定字段，不读取或展示 API 响应中的 secret 字段。
- `static/css/app.css`：
  - 增加摘要成功/错误状态样式，沿用现有绿色/黄色状态语义。
- `tests/frontend_smoke.js`：
  - 扩展 mock element 的 attribute 支持。
  - 断言成功/失败状态 class、`aria-busy=false` 和诊断行 `role="listitem"`。
- `tests/test_core.py`：
  - 新增 `/diagnostics` 页面静态可访问性语义测试。
- `Telegram_Web开发.md` 同步 Phase 21 记录。

## 主代理工作

- 按 Phase 20 交接启动 Phase 21，确认工作区干净、最近提交和 Git 身份。
- 只读复查诊断页模板、JS helper、CSS 和现有 smoke。
- 选择不引入外部可访问性库，只做小范围语义补强。
- 补充测试、文档、验证和提交。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段修改范围较小，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `templates/diagnostics.html`
- `static/js/app.js`
- `static/css/app.css`
- `tests/frontend_smoke.js`
- `tests/test_core.py`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-21-diagnostics-accessibility.md`
- `docs/handoff/2026-07-05-phase-21-to-phase-22.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：axe-core、Playwright accessibility snapshot、专用前端 a11y 测试库。
- 结论：本阶段不新增外部依赖。
- 原因：
  - 当前目标是低风险 HTML/JS 语义补强，原生 ARIA 属性和现有测试足够覆盖。
  - 当前环境仍缺少浏览器自动化条件。
  - 引入 axe/Playwright 会扩大 npm、浏览器和安装边界，超出本阶段目标。

## 验证结果

- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest tests.test_core.FlaskBoundaryTest.test_diagnostics_page_has_accessible_status_semantics tests.test_core.FlaskBoundaryTest.test_page_routes_render_without_telegram_login -v`：通过，2 个测试
- `sh -n scripts/diagnose-runtime.sh`：通过
- `sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=0`
- `TELEGRAM_WEB_HOST=0.0.0.0 sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=1`，warning 为未设置环境变量 Web Token
- `TELEGRAM_WEB_DIAGNOSTICS_URL=http://127.0.0.1:9/api/diagnostics sh scripts/diagnose-runtime.sh`：通过，HTTP 探测失败按 warning 处理
- `sh scripts/check-browser-smoke-env.sh`：通过；输出自动化浏览器 smoke 当前不可用，使用手动清单
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，51 个测试
- `git diff --check`：通过

## 风险和遗留

- 未执行真实屏幕阅读器或真实浏览器人工验证。
- 纯 Node smoke 能覆盖动态属性和 HTML 字符串，但不替代真实浏览器辅助技术行为。
- 诊断页仍只展示脱敏状态，不替代真实日志、Telegram 登录回归或运行监控。

## Git

- 提交：提交信息 `phase21: improve diagnostics accessibility`；精确 hash 以 `git log -1 --oneline` 为准。
