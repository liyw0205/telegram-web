# Phase 9 下载页前端状态 smoke

## 阶段目标

- 扩展 `tests/frontend_smoke.js`，覆盖下载页任务和文件列表关键状态。
- 不引入构建链、npm 依赖或真实浏览器依赖。
- 保持前端测试可在当前 Termux/Node 环境直接运行。

## 完成内容

- 扩展前端 smoke harness：
  - 增加通用 mock DOM 元素状态。
  - 增加 `downloadTaskList`、`downloadFileList`、`downloadFileStatus`、`downloadFileMore` 元素。
  - 增加按路径前缀返回 API 数据或错误的 `routes` mock。
- 新增下载任务覆盖：
  - 运行中任务渲染暂停按钮和“取消”。
  - 终态任务渲染“移除记录”。
  - `/api/tasks` 错误会显示到任务列表。
- 新增下载文件覆盖：
  - 首次加载请求 `limit=30&offset=0`。
  - 图片、视频和普通文件卡片渲染。
  - `has_more=true` 时显示“加载更多”。
  - 下一页请求使用上次 offset。
  - 下一页后状态文案更新为 `已显示 3 / 3`，并隐藏分页按钮。
  - 已有第一页时，下一页错误走 toast，不清空已有文件列表。
- README 和开发方案同步更新测试覆盖说明。

## 主代理工作

- 按 Phase 8 交接启动 Phase 9，确认工作区干净、最近提交和 Git 身份。
- 只读梳理下载页前端函数和现有 smoke harness。
- 扩展 `tests/frontend_smoke.js`，没有修改业务前端代码。
- 更新 README、开发方案、进度和交接文档。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段改动集中，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `tests/frontend_smoke.js`
- `README.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-9-downloads-frontend-smoke.md`
- `docs/handoff/2026-07-05-phase-9-to-phase-10.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：Playwright、Jest/Vitest、jsdom。
- 结论：本阶段继续不新增依赖。
- 原因：本阶段目标仍是函数级前端状态验证，Node 内置 `vm` 和 mock DOM 足够；引入真实浏览器或测试框架会扩大安装和维护成本，后续可单独开阶段处理。

## 验证结果

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，48 个测试
- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `git diff --check`：通过

## 风险和遗留

- 仍是 mock 浏览器环境，不验证真实布局、真实事件冒泡、媒体加载、剪贴板权限或 Socket.IO。
- 下载页 smoke 依赖当前 HTML 字符串结构，前端样式或文案调整时需要同步测试。
- 前端业务代码仍是单个 `static/js/app.js`，没有模块化拆分。

## Git

- 提交：提交信息 `phase9: extend downloads frontend smoke`；精确 hash 以 `git log -1 --oneline` 为准。
