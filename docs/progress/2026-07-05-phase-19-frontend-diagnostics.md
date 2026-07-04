# Phase 19 前端只读诊断入口

## 阶段目标

- 新增受现有 Web Token 保护的 `/diagnostics` 页面。
- 页面只展示 `/api/diagnostics` 的脱敏状态，不展示 secret、Token、手机号、代理原文、StringSession、`.session` 路径或本地绝对路径。
- 前端只按白名单渲染布尔、枚举和数值状态，忽略接口响应中可能出现的额外字段。
- 补充纯 Node smoke 覆盖诊断页渲染和错误状态。
- 不引入前端构建链，不触碰运行数据和凭据。

## 完成内容

- 新增 `GET /diagnostics` 页面路由，复用现有 `before_request` Web Token 鉴权。
- 新增 `templates/diagnostics.html`：
  - 展示配置、访问、运行和目录四组只读状态。
  - 提供手动刷新按钮。
- 底部导航新增“诊断”入口，并将移动端导航改为四列。
- `static/js/app.js` 新增诊断页渲染 helper：
  - 只读取固定白名单字段。
  - 将 Web Token 来源、session 类型、监听范围等显示为枚举。
  - 将 secret 是否保存、目录是否存在等显示为布尔状态。
  - 不渲染 raw host、路径、Token、手机号、代理原文或 session 内容。
- `static/css/app.css` 增加诊断页列表、摘要、状态颜色和移动端布局。
- `tests/frontend_smoke.js` 新增诊断分组：
  - 覆盖正常诊断状态渲染。
  - 向 mock API 注入 secret 字段，确认 UI 不渲染这些字段。
  - 覆盖诊断接口失败时摘要和 toast。
- `tests/test_core.py` 扩展页面路由和 Web Token 保护断言。
- README、运行 runbook 和开发方案同步更新。

## 主代理工作

- 按 Phase 18 交接启动 Phase 19，确认当前 HEAD、工作区改动和 Git 身份。
- 复查已有 `/api/diagnostics` 脱敏边界和前端 smoke harness。
- 收敛前端展示范围，避免显示 raw host、路径或任何非白名单字段。
- 补齐测试、文档、验证和提交。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段改动集中在模板、原生 JS/CSS、测试和文档，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `app.py`
- `templates/base.html`
- `templates/diagnostics.html`
- `static/js/app.js`
- `static/css/app.css`
- `tests/test_core.py`
- `tests/frontend_smoke.js`
- `README.md`
- `docs/runtime-runbook.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-19-frontend-diagnostics.md`
- `docs/handoff/2026-07-05-phase-19-to-phase-20.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：前端组件库、状态面板库、独立监控 UI。
- 结论：本阶段不新增外部依赖。
- 原因：
  - 当前目标是一个小型只读页面，现有 Jinja、原生 JS/CSS 和 `/api/diagnostics` 已足够。
  - 引入 npm 或组件库会改变当前无构建链前端形态，收益不足。
  - 诊断状态需要严格白名单渲染，自定义少量 helper 更容易控制脱敏边界。

## 验证结果

- `sh -n scripts/diagnose-runtime.sh`：通过
- `sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=0`
- `TELEGRAM_WEB_HOST=0.0.0.0 sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=1`，warning 为未设置环境变量 Web Token
- `TELEGRAM_WEB_DIAGNOSTICS_URL=http://127.0.0.1:9/api/diagnostics sh scripts/diagnose-runtime.sh`：通过，HTTP 探测失败按 warning 处理
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，50 个测试
- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `git diff --check`：通过

## 风险和遗留

- `/diagnostics` 只展示脱敏运行状态，不替代真实日志、真实浏览器 smoke 或 Telegram 登录回归。
- 诊断页依赖 `/api/diagnostics`；如果 Web Token 失效或接口不可达，页面只显示错误摘要和 toast。
- 纯 Node smoke 覆盖了渲染逻辑和脱敏边界，但未验证真实浏览器布局。
- 诊断脚本可选 HTTP 探测仍只使用环境变量中的 Token，不读取 `data/config.json`。

## Git

- 提交：提交信息 `phase19: add frontend diagnostics page`；精确 hash 以 `git log -1 --oneline` 为准。
