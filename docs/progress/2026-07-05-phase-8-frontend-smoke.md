# Phase 8 前端 smoke 和回归基础设施

## 阶段目标

- 在不引入大型前端构建链的前提下，补一条可在当前 Termux/Node 环境直接运行的前端行为 smoke。
- 覆盖 Phase 7 遗留的敏感操作确认行为：取消确认不发请求，确认后申请一次性导出令牌。
- 记录 Playwright 取舍，给后续真实浏览器回归留接口。

## 完成内容

- 新增 `tests/frontend_smoke.js`。
- 该脚本使用 Node `vm` 加载 `static/js/app.js`，并 mock：
  - `document`
  - `window.open`
  - `location`
  - `navigator.clipboard`
  - `confirm`
  - `fetch`
  - Socket.IO `io()`
- 覆盖行为：
  - 取消导出 StringSession 时不请求 `/api/session/export-token`。
  - 确认导出 StringSession 后先请求一次性令牌，再请求带 `export_token` 的 `/api/session/string`。
  - 确认导出 `.session` 后打开带 `export_token` 和当前 Web Token 的下载 URL。
  - 取消任务删除时不请求后端，确认后发送 `DELETE /api/task/<id>`。
- README 增加统一验证命令。
- 开发方案增加 `tests/frontend_smoke.js` 说明和前端行为验证命令。

## 主代理工作

- 按 Phase 7 交接启动 Phase 8，确认工作区干净、最近提交和 Git 身份。
- 评估当前环境：Node 可用，Playwright Python 包不可用。
- 选择不新增 npm/Playwright 依赖，先落地纯 Node smoke。
- 实现 smoke 脚本并更新 README、开发方案、进度和交接文档。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段改动集中，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `tests/frontend_smoke.js`
- `README.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-8-frontend-smoke.md`
- `docs/handoff/2026-07-05-phase-8-to-phase-9.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：Playwright、Jest/Vitest、jsdom。
- 结论：本阶段不新增依赖。
- 原因：当前目标是验证少量全局函数行为，Node 内置 `vm` 和 `assert` 足够；Playwright 当前环境未安装，Jest/Vitest/jsdom 会引入 npm 依赖和配置成本，不符合当前小步回归目标。

## 验证结果

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，48 个测试
- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `git diff --check`：通过

## 风险和遗留

- `tests/frontend_smoke.js` 是 mock 浏览器环境，不等价于真实浏览器渲染和点击。
- 该脚本验证前端函数行为，不检查 CSS 布局、Socket.IO 真实连接或媒体加载。
- 后续仍建议在有浏览器依赖的环境引入 Playwright 或手动截图 smoke。

## Git

- 提交：待提交，建议信息 `phase8: add frontend smoke test`
