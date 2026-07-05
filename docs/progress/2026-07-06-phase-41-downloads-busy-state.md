# Phase 41 下载页任务轮询和文件分页状态边界

## 阶段目标

- 复核 `loadDownloadTasks()`、`taskDelete()`、`loadDownloadFiles()` 和“加载更多”在连续点击/失败回退下的状态。
- 复核下载页 `aria-busy`、空状态、错误 toast 和分页按钮显示是否一致。
- 限定在原生 JS、前端 smoke 和文档内做小范围修正，不改变下载 API、任务队列、文件服务、鉴权逻辑、Telethon 行为或依赖。

## 完成内容

- `static/js/app.js`：
  - 新增下载任务轮询进行中状态，避免重复任务列表请求互相覆盖。
  - 新增同一任务操作忙碌保护，暂停、恢复、取消和移除重复触发时显示“任务正在处理，请稍候”。
  - 任务操作会等待已有轮询结束后再强制刷新任务；取消或移除后同步刷新文件列表。
  - 任务轮询结果如果在任务操作期间返回，会丢弃旧结果，避免删除后短暂渲染旧任务。
  - 文件分页加载中重复触发会复用当前请求，并显示“文件列表正在加载，请稍候”。
  - 文件刷新重置时会清空旧分页状态，失败后列表显示错误且 busy 状态恢复。
- `tests/frontend_smoke.js`：
  - 新增任务删除与正在进行的轮询交错时最终渲染删除后状态的 smoke。
  - 新增同一任务重复操作忙碌提示 smoke。
  - 新增加载更多重复点击只发起一个分页请求、按钮 loading 状态和中文 toast 的 smoke。
  - 新增文件刷新失败清理旧分页状态和恢复 `aria-busy` 的 smoke。
- `README.md`、`docs/browser-smoke.md`、`Telegram_Web开发.md`：
  - 同步下载页任务操作、文件分页忙碌保护和 Phase 41 基线。

## 主代理工作

- 按 Phase 40 交接启动 Phase 41，确认工作区干净和最近提交。
- 复核下载页任务轮询、任务操作、文件分页函数和现有前端 smoke。
- 实现下载任务操作与轮询交错保护、文件分页重复触发提示和刷新失败状态清理。
- 扩展前端 smoke，覆盖任务、分页、失败回退和 busy 状态。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段范围集中在下载页原生 JS 和 smoke，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `static/js/app.js`
- `tests/frontend_smoke.js`
- `README.md`
- `docs/browser-smoke.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-06-phase-41-downloads-busy-state.md`
- `docs/handoff/2026-07-06-phase-41-to-phase-42.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：无。
- 结论：本阶段不需要新增外部依赖。
- 原因：目标是前端状态串行化、轮询边界和 smoke 覆盖，现有原生 JS 与 Node smoke 足够处理。

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
- 本阶段没有改变后端任务队列、文件服务或 Telethon 行为，只收口前端状态竞态。
- 聊天发送区、消息刷新和更早加载的连续点击/失败回退仍建议下阶段复核。

## Git

- 提交：提交信息 `phase41: stabilize downloads busy states`；精确 hash 以 `git log -1 --oneline` 为准。
