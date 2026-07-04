# Phase 6 任务持久化和运行管理

## 阶段目标

- 明确任务状态落盘边界，避免重启后下载页完全丢失终态历史。
- 增加轻量任务历史存储，不写入 peer、msg_id、绝对路径或其它 meta。
- 前端展示内部错误 `error_id`，并尽量复制到剪贴板。
- 补充 Termux/本机启动示例。

## 完成内容

- 新增 `data/task-history.json` 作为终态任务历史文件。
- `TaskStore` 支持：
  - 仅持久化 `done/error/canceled` 终态任务。
  - 启动时恢复历史终态任务。
  - 不持久化 `queued/running/paused` 活动任务。
  - 落盘前清理 `path`、`meta`，文件只保留 basename。
  - 错误文本落盘为通用 `任务失败`，不写入原始异常细节。
- `/api/tasks` 默认保留 7 天内或最近 200 条终态任务。
- 删除任务语义调整：
  - active 任务删除仍保留取消信号。
  - terminal 任务删除只移除记录并清理控制状态。
- 前端 API 错误包含 `error_id` 时，在提示中展示错误 ID，并尝试复制到剪贴板。
- 新增 `scripts/run-termux.sh`，可通过 `sh scripts/run-termux.sh` 启动。
- README 增加任务历史、tmux 启动和备份 `data/task-history.json` 说明。
- 测试扩展到 44 个用例。

## 主代理工作

- 按 Phase 5 交接启动 Phase 6，确认工作区干净、Git 身份正确。
- 只读梳理 `TaskStore`、任务 API、前端 API 封装和现有测试。
- 实现终态任务历史持久化、删除语义修正、错误 ID 展示和启动脚本。
- 更新 README、开发方案、进度和交接文档。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段改动集中，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `app.py`
- `static/js/app.js`
- `tests/test_core.py`
- `README.md`
- `Telegram_Web开发.md`
- `scripts/run-termux.sh`
- `docs/progress/2026-07-04-phase-6-task-history-runtime.md`
- `docs/handoff/2026-07-04-phase-6-to-phase-7.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：SQLite、任务队列库、进程管理器配置。
- 结论：本阶段不新增依赖。
- 原因：当前只需要恢复最近终态任务历史，JSON 文件足够；引入 SQLite 或任务队列会扩大迁移和运行复杂度。进程管理先提供通用 shell/tmux 启动示例。

## 验证结果

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，44 个测试
- `git diff --check`：通过

## 风险和遗留

- 活动任务不会恢复，服务重启后只保留终态历史；这是当前有意边界。
- `data/task-history.json` 仍会包含文件名和本地 URL；它属于运行数据，不应提交。
- 没有实现 systemd、Termux service 或容器化配置。
- 错误 ID 复制依赖浏览器剪贴板权限，失败时仍会显示在提示文案里。
- 尚未做真实浏览器端点击回归。

## Git

- 提交：待提交，建议信息 `phase6: persist terminal task history`
