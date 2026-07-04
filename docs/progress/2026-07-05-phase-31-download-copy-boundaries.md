# Phase 31 下载页任务操作文案和边界一致性复核

## 阶段目标

- 只读复查 `templates/downloads.html`、`static/js/app.js` 中下载任务/文件相关文案、`README.md`、`docs/browser-smoke.md`、`docs/runtime-runbook.md` 和下载相关测试。
- 确认暂停、恢复、取消、移除、终态任务历史、分页加载、`.part` 临时文件跳过和错误 ID 提示的页面文案、文档和测试描述一致。
- 如发现页面提示、确认弹窗、README、runbook 或手动 smoke 清单与实际行为不一致，优先做小范围文案/文档/断言修正。
- 不改变下载任务状态机、文件枚举、分页 API、Range 响应或缓存清理逻辑。
- 不引入新依赖，不读取或提交 `Download/`、`Pictures/`、`data/`、`.session` 和任何真实 Token。

## 完成内容

- `templates/downloads.html`：
  - 下载页说明改为“支持暂停、恢复、取消任务、移除终态记录和分页查看文件”，补齐终态记录移除边界。
- `static/js/app.js`：
  - 下载/预览任务确认文案区分活跃任务和终态记录：
    - 活跃任务：确认取消后移除任务记录，并向后台任务发送取消信号。
    - 终态任务：确认移除后只移除记录，不删除已下载文件。
  - 任务卡片将内部枚举显示为中文文案：
    - `download_media` -> `下载原文件`
    - `prepare_media` -> `准备预览`
    - `queued/running/paused/done/error/canceled` -> 中文状态
  - 活跃任务按钮文案改为“取消任务”，终态任务保留“移除记录”。
  - 动态任务按钮补充 `type="button"`，避免后续嵌入表单时出现默认提交行为。
- `README.md`：
  - 功能列表补充下载任务支持暂停、恢复、取消和移除记录。
  - 注意事项补充下载页分页列出 `Download/` 和 `Pictures/` 完成文件、跳过 `.part` 临时文件、暂停/恢复直接执行、取消/移除需确认且移除记录不删除文件。
- `docs/browser-smoke.md`：
  - 修正下载页手动 smoke：暂停/恢复直接执行；取消活跃任务或移除终态记录才弹确认。
  - 补充取消确认后不应发起请求、移除记录不删除已下载文件、已下载列表不显示 `.part` 临时文件。
- `docs/runtime-runbook.md`：
  - 新增“下载页任务和文件边界”章节，记录任务列表、文件列表、操作边界、终态历史、分页排序、`.part`/符号链接跳过和错误 ID 提示。
- `tests/test_core.py` 和 `tests/frontend_smoke.js`：
  - 同步下载页标题说明、确认文案、中文任务种类/状态和“取消任务”按钮断言。
- 下载任务状态机、文件枚举、分页 API、Range 响应和缓存清理逻辑未修改。

## 主代理工作

- 按 Phase 30 交接启动 Phase 31，确认工作区、最近提交、远端同步和 Git 身份。
- 只读梳理下载页模板、前端下载任务渲染、后端任务状态、文件枚举、README、browser smoke、runbook 和相关测试。
- 发现手动 smoke 将暂停/恢复误写为需确认，README 对下载操作边界过简，页面仍暴露内部任务枚举后，限定做文案/文档/断言修正。
- 补充阶段进度、交接文档、验证、提交和推送。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段为下载文案和文档一致性复核，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `templates/downloads.html`
- `static/js/app.js`
- `tests/test_core.py`
- `tests/frontend_smoke.js`
- `README.md`
- `docs/browser-smoke.md`
- `docs/runtime-runbook.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-31-download-copy-boundaries.md`
- `docs/handoff/2026-07-05-phase-31-to-phase-32.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：无。
- 结论：本阶段不需要新增外部依赖。
- 原因：目标是现有下载页文案、文档和测试断言一致性，不涉及新下载能力或测试框架。

## 验证结果

- `sh -n scripts/diagnose-runtime.sh`：通过
- `sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=0`
- `TELEGRAM_WEB_HOST=0.0.0.0 sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=1`，warning 为未设置环境变量 Web Token
- `TELEGRAM_WEB_DIAGNOSTICS_URL=http://127.0.0.1:9/api/diagnostics sh scripts/diagnose-runtime.sh`：通过，HTTP 探测失败按 warning 处理
- `sh scripts/check-browser-smoke-env.sh`：通过；输出自动化浏览器 smoke 当前不可用，使用手动清单
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，56 个测试
- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `git diff --check`：通过
- `git diff --cached --check`：通过

## 风险和遗留

- 未执行真实浏览器或屏幕阅读器人工 smoke。
- 本阶段只改下载页文案、文档和断言，未改变下载状态机或文件枚举行为。
- 取消活跃任务会立即移除前端任务记录并向后台发送取消信号；后台任务实际停止仍取决于下载/预览流程中的取消检查点。

## Git

- 提交：提交信息 `phase31: align download task copy`；精确 hash 以 `git log -1 --oneline` 为准。
