# Phase 8 -> Phase 9 交接

## 当前完成进度

- 新增纯 Node 前端行为 smoke：`tests/frontend_smoke.js`。
- Smoke 使用 Node 内置 `vm` 和 `assert`，不引入 npm、Playwright、Jest、Vitest 或 jsdom。
- 覆盖敏感操作确认：
  - 取消导出 StringSession 不发后端请求。
  - 确认导出 StringSession 会先请求 `/api/session/export-token`，再请求带 `export_token` 的 `/api/session/string`。
  - 确认导出 `.session` 会打开带 `export_token` 和当前 Web Token 的下载 URL。
  - 取消任务删除不请求后端，确认后发送 `DELETE /api/task/<id>`。
- README 增加完整验证命令。
- 开发方案增加 `tests/frontend_smoke.js` 路径说明和前端行为验证命令。

## 本阶段提交

- commit：提交信息 `phase8: add frontend smoke test`；精确 hash 以 `git log -1 --oneline` 为准。
- 主要文件：
  - `tests/frontend_smoke.js`
  - `README.md`
  - `Telegram_Web开发.md`
  - `docs/progress/2026-07-05-phase-8-frontend-smoke.md`
  - `docs/handoff/2026-07-05-phase-8-to-phase-9.md`
  - `docs/handoff/LATEST.md`

## 已验证

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，48 个测试
- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `git diff --check`：通过

## 未完成/风险

- 仍未执行真实浏览器点击回归；当前是 mock 浏览器环境。
- 前端 smoke 不验证 CSS 布局、真实 Socket.IO 连接、媒体加载和浏览器权限差异。
- 原生 `confirm()` 仍未替换为自定义可访问确认组件。
- 没有 systemd、Termux service、容器化或日志轮转脚本。
- 活动下载任务仍不会恢复；重启后只保留终态历史。

## 下阶段目标

Phase 9 建议主题：**下载任务和文件列表的前端状态可测性**。

优先完成：

- 扩展 `tests/frontend_smoke.js`，覆盖下载页任务渲染、分页状态、API 错误 toast 和下载文件列表渲染。
- 考虑把少量纯函数从 `static/js/app.js` 拆成更易测试的局部函数，但避免引入构建链。
- 如环境允许，再评估 Playwright 最小真实浏览器 smoke。
- 可选：统一前端 toast/confirm 的可测试接口，减少直接依赖浏览器全局函数。

## 建议子代理拆分

- Explorer：只读梳理 `static/js/app.js` 中适合 smoke 覆盖的纯函数和 DOM 依赖点。
- Worker：扩展 `tests/frontend_smoke.js`，必要时小幅调整前端函数以便测试。
- Verifier：运行 py_compile、单元测试、Node smoke、`git diff --check`，确认无运行数据进入提交。

## 续会启动步骤

1. 阅读 `Telegram_Web开发.md`。
2. 阅读本文。
3. 运行 `git status --short` 和 `git log --oneline -5`。
4. 确认 Git 身份仍为 `liyw0205 <2650115317@qq.com>`。
5. 按“下阶段目标”启动 Phase 9。
6. 阶段结束前更新新的 `docs/progress/`、`docs/handoff/` 和 `docs/handoff/LATEST.md`，然后提交 Git。
