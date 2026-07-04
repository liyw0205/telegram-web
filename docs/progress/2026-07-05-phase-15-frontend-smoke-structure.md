# Phase 15 前端 smoke 结构整理

## 阶段目标

- 将 `tests/frontend_smoke.js` 按确认弹窗、媒体查看器、登录页/API、session/任务确认和下载页分组。
- 保持单文件纯 Node smoke，不引入 Jest、Vitest、jsdom、Playwright 或前端构建链。
- 抽出可复用的 DOM 元素 ID、焦点断言和键盘默认行为断言 helper。
- 确保既有确认弹窗、媒体查看器、登录页/API、session 导出、任务确认和下载页覆盖不回退。

## 完成内容

- 新增元素 ID 分组常量：
  - `LOGIN_ELEMENT_IDS`
  - `DOWNLOAD_ELEMENT_IDS`
  - `CONFIRM_ELEMENT_IDS`
  - `GALLERY_ELEMENT_IDS`
  - `DEFAULT_ELEMENT_IDS`
- `createHarness()` 改为通过 `DEFAULT_ELEMENT_IDS` 统一注册默认 DOM mock 元素。
- 新增焦点和键盘断言 helper：
  - `setFocused()`
  - `setOutsideFocus()`
  - `expectFocused()`
  - `expectPreventedKeys()`
- 将确认弹窗和媒体查看器测试中重复的焦点、Tab、Shift+Tab 和 Esc 断言改为 helper 调用。
- 新增 `TEST_GROUPS` 和 `runTestGroups()`：
  - `confirm dialog`
  - `gallery viewer`
  - `api and login`
  - `session and task confirmations`
  - `downloads`
- 保持通过时输出仍为 `frontend smoke passed`。
- 失败时会在异常 message 中补充所在测试分组和测试函数名，方便后续定位。
- README 和开发方案同步补充前端 smoke 的分组说明。

## 主代理工作

- 按 Phase 14 交接启动 Phase 15，确认工作区已有 `tests/frontend_smoke.js` 的未提交半成品改动。
- 复查最新交接、进度文档、最近提交和 Git 身份。
- 在既有半成品基础上补齐 smoke 分组执行和文档更新。
- 跑前端 smoke 和完整后端回归。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段集中在一个 smoke 文件和文档维护，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `tests/frontend_smoke.js`
- `README.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-15-frontend-smoke-structure.md`
- `docs/handoff/2026-07-05-phase-15-to-phase-16.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：Jest、Vitest、jsdom、Playwright、Node 内置 `node:test`。
- 结论：本阶段不新增依赖，也不迁移到测试框架。
- 原因：
  - 本阶段目标是整理已有 smoke 的长期维护结构，不是提升浏览器真实性。
  - 现有 mock 环境已经覆盖目标路径，迁移到框架会扩大验证和部署面。
  - `node:test` 会改变当前输出和组织方式，收益小于继续保持简单单文件脚本。
  - 真实浏览器覆盖适合作为后续独立阶段评估，避免与结构调整混在一起。

## 验证结果

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，48 个测试
- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `git diff --check`：通过

## 风险和遗留

- 前端 smoke 仍是 mock 浏览器环境，不验证真实 DOM、CSS 布局、事件冒泡、媒体加载、剪贴板权限和真实 Socket.IO 连接。
- 分组结构提升了维护性，但没有新增业务覆盖路径。
- 后续如果引入真实浏览器 smoke，需要单独评估 Playwright 或浏览器环境可用性。

## Git

- 提交：提交信息 `phase15: organize frontend smoke groups`；精确 hash 以 `git log -1 --oneline` 为准。
