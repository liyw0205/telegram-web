# Phase 42 聊天发送区操作状态和失败回退边界

## 阶段目标

- 复核 `sendText()`、`sendFile()`、`loadMessages()` 和“更早”加载在连续点击/失败回退下的状态。
- 复核文字/文件发送失败后输入区、文件选择、`aria-busy` 和面板显示是否保持一致。
- 限定在原生 JS、前端 smoke 和文档内做小范围修正，不改变消息 API、媒体准备/下载 API、鉴权逻辑、Telethon 行为或依赖。

## 完成内容

- `static/js/app.js`：
  - 新增消息刷新和更早加载的前端忙碌状态，重复触发会复用当前请求并显示中文提示。
  - `loadMessages()` 进行中重复刷新或点击“更早”会显示“消息正在刷新，请稍候”。
  - `loadOlderMessages()` 进行中重复触发会显示“更早消息正在加载，请稍候”。
  - `sendText()` 发送中重复触发会显示“文字消息正在发送，请稍候”，不重复提交。
  - `sendFile()` 发送中重复触发会显示“媒体或文件正在发送，请稍候”，不重复提交。
  - 文字或文件发送失败后保留输入内容、文件选择、说明文字和面板显示状态，`aria-busy` 恢复。
- `tests/frontend_smoke.js`：
  - 新增文字消息发送中重复触发和失败保留草稿的 smoke。
  - 新增文件发送中重复触发和失败保留文件选择/说明文字的 smoke。
  - 新增消息刷新和更早加载互斥、重复触发只发起一个请求的 smoke。
- `README.md`、`docs/browser-smoke.md`、`Telegram_Web开发.md`：
  - 同步聊天刷新/更早加载、发送忙碌保护和 Phase 42 基线。

## 主代理工作

- 按 Phase 41 交接启动 Phase 42，确认工作区干净和最近提交。
- 复核聊天页消息刷新、加载更早、发送文字、发送文件和现有前端 smoke。
- 实现聊天页请求忙碌保护和发送失败回退。
- 扩展前端 smoke，覆盖重复触发、失败保留输入和 `aria-busy` 恢复。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段范围集中在聊天页原生 JS 和 smoke，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `static/js/app.js`
- `tests/frontend_smoke.js`
- `README.md`
- `docs/browser-smoke.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-06-phase-42-chat-busy-state.md`
- `docs/handoff/2026-07-06-phase-42-to-phase-43.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：无。
- 结论：本阶段不需要新增外部依赖。
- 原因：目标是前端请求状态串行化和 smoke 覆盖，现有原生 JS 与 Node smoke 足够处理。

## 验证结果

- `sh -n scripts/diagnose-runtime.sh`：通过
- `sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=0`
- `TELEGRAM_WEB_HOST=0.0.0.0 sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=1`，warning 为未设置环境变量 Web Token
- `TELEGRAM_WEB_DIAGNOSTICS_URL=http://127.0.0.1:9/api/diagnostics sh scripts/diagnose-runtime.sh`：通过，HTTP 探测失败按 warning 处理
- `sh scripts/check-browser-smoke-env.sh`：通过；输出自动化浏览器 smoke 当前不可用，使用手动清单
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，57 个测试
- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `rg -n "api_hash|StringSession|\\.session|Bearer\\s+[A-Za-z0-9._-]{16,}|sk-[A-Za-z0-9]|password\\s*[:=]" .`：通过；仅命中文档、字段名和测试假数据，未发现真实凭据
- `git diff --check`：通过
- `git diff --cached --check`：通过

## 风险和遗留

- 未执行真实浏览器或屏幕阅读器人工 smoke。
- 自动浏览器 smoke 仍未引入；当前环境缺少 Playwright 模块和常见浏览器命令。
- 本阶段没有改变后端消息发送、媒体准备、下载任务或 Telethon 行为，只收口前端状态竞态。
- 媒体查看器准备和下载任务触发的连续点击/失败回退仍建议下阶段复核。

## Git

- 提交：提交信息 `phase42: stabilize chat busy states`；精确 hash 以 `git log -1 --oneline` 为准。
