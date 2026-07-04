# Phase 6 -> Phase 7 交接

## 当前完成进度

- 已完成终态任务历史持久化。
- `TaskStore` 启动时会从 `data/task-history.json` 恢复 `done/error/canceled` 任务。
- 活动任务 `queued/running/paused` 不落盘、不恢复，避免重启后误导用户以为下载仍在运行。
- 落盘任务会清理 `path` 和 `meta`，只保留文件 basename、URL、大小、状态和时间。
- `/api/tasks` 默认保留 7 天内或最近 200 条终态任务。
- 前端内部错误提示会展示 `error_id`，并尝试复制到剪贴板。
- 新增 `scripts/run-termux.sh` 和 README 中的 tmux/备份说明。
- 测试扩展到 44 个用例。

## 本阶段提交

- commit：提交信息 `phase6: persist terminal task history`；精确 hash 以 `git log -1 --oneline` 为准。
- 主要文件：
  - `app.py`
  - `static/js/app.js`
  - `tests/test_core.py`
  - `README.md`
  - `Telegram_Web开发.md`
  - `scripts/run-termux.sh`
  - `docs/progress/2026-07-04-phase-6-task-history-runtime.md`
  - `docs/handoff/2026-07-04-phase-6-to-phase-7.md`
  - `docs/handoff/LATEST.md`

## 已验证

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，44 个测试
- `git diff --check`：通过

## 未完成/风险

- 活动下载任务不会恢复；重启后只能看到终态历史。
- `data/task-history.json` 属于运行数据，仍可能包含文件名和本地 URL，不能提交。
- 没有 systemd、Termux service、容器化或日志轮转脚本。
- 尚未做真实浏览器点击回归。
- Session 导出仍缺少二次确认或一次性导出令牌。

## 下阶段目标

Phase 7 建议主题：**敏感操作确认和浏览器回归**。

优先完成：

- 为 StringSession / `.session` 导出增加二次确认或短期一次性导出 token。
- 为删除任务记录、导出 session、退出登录等敏感操作统一前端确认语义。
- 用浏览器做 smoke 回归：`/login`、`/chats`、`/chat/<peer>`、`/downloads`。
- 评估是否需要 Playwright 最小页面测试。
- 补充日志路径、错误 ID 检索说明。

## 建议子代理拆分

- Explorer：只读梳理敏感操作入口、前端确认缺口和可自动化的浏览器 smoke 路径。
- Worker：实现二次确认/一次性导出 token 和前端错误 ID 操作，写范围限定在 `app.py`、前端、测试和文档。
- Verifier：运行 py_compile、单元测试、`git diff --check`，并启动服务做页面 smoke。

## 续会启动步骤

1. 阅读 `Telegram_Web开发.md`。
2. 阅读本文。
3. 运行 `git status --short` 和 `git log --oneline -5`。
4. 确认当前仓库 Git 身份仍为 `liyw0205 <2650115317@qq.com>`。
5. 按“下阶段目标”启动 Phase 7。
6. 阶段结束前更新新的 `docs/progress/`、`docs/handoff/` 和 `docs/handoff/LATEST.md`，然后提交 Git。
