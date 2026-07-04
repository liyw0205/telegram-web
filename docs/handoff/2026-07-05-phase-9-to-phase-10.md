# Phase 9 -> Phase 10 交接

## 当前完成进度

- 扩展 `tests/frontend_smoke.js`，覆盖下载页任务和文件列表状态。
- Smoke harness 现在支持 mock DOM 元素状态和按路径前缀返回 API 数据或错误。
- 新增覆盖：
  - 下载任务列表渲染运行中和终态任务。
  - 运行中任务显示“暂停”和“取消”。
  - 终态任务显示“移除记录”。
  - `/api/tasks` 错误显示在任务列表。
  - 下载文件首次分页、下一页分页、状态文案和“加载更多”按钮显示/隐藏。
  - 已有文件列表时下一页错误走 toast，不清空现有列表。
- README 和开发方案同步更新了前端 smoke 覆盖范围。

## 本阶段提交

- commit：提交信息 `phase9: extend downloads frontend smoke`；精确 hash 以 `git log -1 --oneline` 为准。
- 主要文件：
  - `tests/frontend_smoke.js`
  - `README.md`
  - `Telegram_Web开发.md`
  - `docs/progress/2026-07-05-phase-9-downloads-frontend-smoke.md`
  - `docs/handoff/2026-07-05-phase-9-to-phase-10.md`
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
- 下载页 smoke 和当前 HTML 字符串结构耦合，后续 UI 文案调整需要同步测试。
- 原生 `confirm()` 仍未替换为自定义可访问确认组件。
- 没有 systemd、Termux service、容器化或日志轮转脚本。

## 下阶段目标

Phase 10 建议主题：**前端 smoke 可维护性和轻量测试边界**。

优先完成：

- 将 `tests/frontend_smoke.js` 中重复的 API mock 和 DOM 断言整理得更清晰，避免测试脚本继续线性膨胀。
- 覆盖 `api()` 的错误 ID 复制行为和 401 跳转行为。
- 覆盖 `loadLoginPage()` 配置脱敏占位符逻辑。
- 可选：把少量纯渲染函数的输出断言集中，仍不引入构建链。
- 如环境允许，单独评估真实浏览器 smoke，不和本阶段 mock 测试混在一起。

## 建议子代理拆分

- Explorer：只读梳理 `api()`、`loadLoginPage()`、toast/error ID 和配置脱敏的前端行为。
- Worker：重整 `tests/frontend_smoke.js` 的 helper，并新增 API 错误/登录页配置 smoke。
- Verifier：运行 py_compile、单元测试、Node smoke、`git diff --check`，确认无运行数据进入提交。

## 续会启动步骤

1. 阅读 `Telegram_Web开发.md`。
2. 阅读本文。
3. 运行 `git status --short` 和 `git log --oneline -5`。
4. 确认 Git 身份仍为 `liyw0205 <2650115317@qq.com>`。
5. 按“下阶段目标”启动 Phase 10。
6. 阶段结束前更新新的 `docs/progress/`、`docs/handoff/` 和 `docs/handoff/LATEST.md`，然后提交 Git。
