# Phase 32 聊天页发送和媒体操作文案边界复核

## 阶段目标

- 只读复查 `templates/chat.html`、`static/js/app.js` 中聊天发送、媒体预览、媒体下载、图库查看器相关文案，及 `README.md`、`docs/browser-smoke.md`、`docs/runtime-runbook.md` 和聊天/媒体相关测试。
- 确认文字发送、文件发送、媒体预览、缩略图加载、下载任务创建、图库打开/关闭/下载、加载更早消息和错误 ID 提示的页面文案、文档和测试描述一致。
- 如发现页面提示、按钮标签、确认/状态文案、README、runbook 或手动 smoke 清单与实际行为不一致，优先做小范围文案/文档/断言修正。
- 不改变 Telegram 发送流程、媒体缓存/下载流程、图库交互逻辑、Range 响应或任务状态机。
- 不引入新依赖，不读取或提交 `Download/`、`Pictures/`、`data/`、`.session` 和任何真实 Token。

## 完成内容

- `templates/chat.html`：
  - 媒体查看器下载按钮的可访问名称从“下载当前媒体”改为“创建当前媒体下载任务”，与实际后台任务行为一致。
- `static/js/app.js`：
  - 消息内媒体下载图标的可访问名称改为“创建媒体 <id> 下载任务”，并补充 `title="创建下载任务"`。
  - 单媒体查看器默认标题从英文 `media <id>` 改为中文 `媒体 #<id>`。
  - 媒体准备未就绪 toast 改为“媒体正在准备，稍后重试打开”。
  - 媒体下载任务创建成功 toast 改为“下载任务已创建，可在下载页查看进度”。
- `README.md`：
  - 功能列表将“媒体预览与下载”收紧为“媒体预览与下载任务”。
  - 注意事项补充聊天页优先加载缩略图、不自动下载原文件、媒体预览按需准备缓存、媒体下载按钮创建后台下载任务。
- `docs/browser-smoke.md`：
  - 聊天页清单补充缩略图/文件占位、按需准备缓存、未就绪 toast 和下载任务创建 toast。
  - 媒体查看器清单将下载按钮描述为“创建当前媒体下载任务”，并说明不会直接保存文件到当前浏览器页面。
- `docs/runtime-runbook.md`：
  - 新增“聊天页发送和媒体边界”章节，记录文字发送、文件发送、Markdown 渲染、加载更早消息、缩略图加载、媒体准备、查看器和媒体下载任务边界。
- `tests/test_core.py` 和 `tests/frontend_smoke.js`：
  - 同步媒体查看器下载按钮可访问名称断言。
  - 新增纯 Node smoke 覆盖媒体准备未就绪 toast、中文查看器标题和媒体下载任务创建 toast/请求体。
- Telegram 发送流程、媒体缓存/下载流程、图库交互逻辑、Range 响应和任务状态机未修改。

## 主代理工作

- 按 Phase 31 交接启动 Phase 32，确认工作区、最近提交、远端同步和 Git 身份。
- 只读梳理聊天模板、前端聊天/媒体逻辑、后端发送/媒体接口、README、browser smoke、runbook 和相关测试。
- 发现媒体下载按钮实际是创建后台下载任务、单媒体查看器标题仍用英文 `media <id>`、未就绪/创建任务 toast 与文档不够一致后，限定做文案/文档/断言修正。
- 补充阶段进度、交接文档、验证、提交和推送。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段为聊天/媒体文案和文档一致性复核，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `templates/chat.html`
- `static/js/app.js`
- `tests/test_core.py`
- `tests/frontend_smoke.js`
- `README.md`
- `docs/browser-smoke.md`
- `docs/runtime-runbook.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-32-chat-media-copy.md`
- `docs/handoff/2026-07-05-phase-32-to-phase-33.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：无。
- 结论：本阶段不需要新增外部依赖。
- 原因：目标是现有聊天/媒体文案、文档和测试断言一致性，不涉及新聊天能力或测试框架。

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
- 本阶段只改聊天/媒体文案、文档和断言，未改变发送、媒体准备或下载任务行为。
- 媒体准备和下载仍依赖 Telegram 连接状态和后台任务检查点；未就绪时需要稍后重试打开或到下载页查看任务。

## Git

- 提交：提交信息 `phase32: align chat media copy`；精确 hash 以 `git log -1 --oneline` 为准。
