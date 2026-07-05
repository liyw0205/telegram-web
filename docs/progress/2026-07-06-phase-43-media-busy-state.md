# Phase 43 媒体查看器准备和下载触发状态边界

## 阶段目标

- 复核 `openMediaViewerByMessage()`、`downloadMedia()` 和查看器下载按钮在连续点击/失败回退下的状态。
- 复核媒体准备未就绪、准备失败、下载任务创建失败时 toast、焦点和查看器状态是否保持一致。
- 限定在原生 JS、前端 smoke 和文档内做小范围修正，不改变媒体准备 API、下载任务 API、鉴权逻辑、Telethon 行为或依赖。

## 完成内容

- `static/js/app.js`：
  - 新增按消息 ID 管理的 `mediaPreparePromises`，同一媒体准备中重复点击复用当前请求。
  - 媒体准备中重复触发显示“媒体正在准备，请稍候”，不会额外发起 `/api/media/prepare` 请求。
  - 媒体准备失败只显示后端错误，不打开查看器；准备 Promise 释放后可再次重试。
  - 新增按消息 ID 管理的 `mediaDownloadPromises`，同一媒体下载任务创建中重复触发复用当前请求。
  - 查看器当前媒体创建下载任务时，下载按钮设置 `aria-busy` 和 `aria-disabled`；成功或失败后恢复。
  - 下载任务创建失败只显示后端错误，查看器保持打开，按钮状态可恢复并可重试。
- `tests/frontend_smoke.js`：
  - 新增同一媒体准备重复点击只发起一次请求的 smoke。
  - 新增媒体准备失败后不打开查看器、再次点击可重试的 smoke。
  - 新增查看器下载任务创建重复触发、失败恢复按钮状态和再次重试成功的 smoke。
- `README.md`、`docs/browser-smoke.md`、`Telegram_Web开发.md`：
  - 同步媒体准备/下载任务创建忙碌保护、失败回退和 Phase 43 基线。

## 主代理工作

- 按 Phase 42 交接启动 Phase 43，确认工作区状态和最近提交。
- 复核媒体查看器打开、媒体准备、下载按钮和现有前端 smoke。
- 实现媒体准备和下载任务创建的同消息 ID 忙碌保护。
- 扩展前端 smoke，覆盖重复触发、失败回退、查看器保持打开和按钮 busy 状态恢复。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段范围集中在媒体查看器原生 JS 和 smoke，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `static/js/app.js`
- `tests/frontend_smoke.js`
- `README.md`
- `docs/browser-smoke.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-06-phase-43-media-busy-state.md`
- `docs/handoff/2026-07-06-phase-43-to-phase-44.md`
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
- 本阶段没有改变后端媒体准备、下载任务、任务队列或 Telethon 行为，只收口前端状态竞态。
- 会话列表刷新、搜索输入和失败回退仍建议下阶段复核。

## Git

- 提交：提交信息 `phase43: stabilize media busy states`；精确 hash 以 `git log -1 --oneline` 为准。
