# Phase 10 前端 smoke 可维护性

## 阶段目标

- 整理 `tests/frontend_smoke.js` 中重复的 API mock 和 DOM 断言。
- 覆盖 `api()` 的错误 ID 复制行为和 401 跳转行为。
- 覆盖 `loadLoginPage()` 配置脱敏占位符逻辑。
- 不引入 npm、Playwright、Jest、Vitest 或 jsdom。

## 完成内容

- 新增 `apiSuccess()`、`apiFailure()` 和 `routeResponse()`，让 mock API 可以统一返回成功、失败、状态码和异常。
- 新增 `registerElements()`，集中注册登录页和下载页需要的 mock DOM 元素。
- 新增 `textOf()`、`htmlOf()`、`expectHtmlIncludes()`，减少测试中重复读取 `innerHTML` 和 `textContent`。
- 新增 `api()` 覆盖：
  - 后端返回 `error_id` 时，前端错误消息包含错误 ID。
  - 后端返回 `error_id` 时，前端尝试复制错误 ID 到剪贴板。
  - 401 响应会跳转到 `/auth?next=...` 并抛出 `需要 Web Token`。
- 新增 `loadLoginPage()` 覆盖：
  - 已保存 `api_hash`、代理凭据、`.session`、StringSession 和 Web Token 时，输入值保持空，placeholder 展示“已保存，留空沿用/不修改”语义。
  - 普通配置字段仍填入页面控件。
- 简化下载文件下一页错误测试，不再手写整段 `fetch` 覆盖。
- README 和开发方案同步更新 smoke 覆盖范围。

## 主代理工作

- 先完成并提交 Phase 9 收尾，恢复 `docs/handoff/LATEST.md`。
- 按 Phase 9 交接启动 Phase 10，确认最近提交和工作区状态。
- 只修改前端 smoke 测试与文档，没有修改业务前端代码。
- 运行完整回归并记录结果。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段改动集中，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `tests/frontend_smoke.js`
- `README.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-10-frontend-smoke-maintainability.md`
- `docs/handoff/2026-07-05-phase-10-to-phase-11.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：Playwright、Jest/Vitest、jsdom。
- 结论：本阶段继续不新增依赖。
- 原因：目标是维护现有纯 Node smoke 边界并补关键行为覆盖；Node 内置 `vm`、`assert` 和轻量 mock 已足够，新增测试框架会扩大安装成本和阶段范围。

## 验证结果

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，48 个测试
- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `git diff --check`：通过

## 风险和遗留

- 仍未执行真实浏览器点击回归；当前是 mock 浏览器环境。
- 前端 smoke 不验证 CSS 布局、真实事件冒泡、真实 Socket.IO 连接、媒体加载和浏览器剪贴板权限差异。
- 原生 `confirm()` 仍未替换为自定义可访问确认组件。
- 下载页 smoke 仍和当前 HTML 字符串结构耦合。

## Git

- 提交：提交信息 `phase10: improve frontend smoke coverage`；精确 hash 以 `git log -1 --oneline` 为准。
