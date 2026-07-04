# Phase 29 运行文档启动和备份说明一致性复核

## 阶段目标

- 只读复查 `README.md`、`docs/runtime-runbook.md`、`scripts/run-termux.sh` 和登录/session 相关测试，确认启动、对外监听、Web Token、备份和恢复说明一致。
- 如发现 README 与 runbook 对启动命令、Token 优先级、备份对象或恢复步骤描述不一致，优先做文档修正。
- 不改变运行逻辑、API、模板、前端 JS、测试代码或脚本行为。
- 不引入新依赖，不读取或提交 `Download/`、`Pictures/`、`data/`、`.session` 和任何真实 Token。

## 完成内容

- `README.md`：
  - 将对外监听说明收紧为必须已有 Web Token，推荐用 `TELEGRAM_WEB_TOKEN` 环境变量提供。
  - 补充 Web Token 来源优先级：`TELEGRAM_WEB_TOKEN`、`WEB_TELEGRAM_TOKEN`、`data/config.json` 中的 `web_token`。
  - 明确仅在已本机保存 Web Token 后，才可只设置 `TELEGRAM_WEB_HOST=0.0.0.0` 和端口对外监听。
  - 扩充部署和备份说明，明确 `data/config.json` 的敏感性、默认文件 session 为 `data/telegram.session`、自定义 session 仍应备份对应 `data/*.session` 文件。
  - 恢复流程补充 Web Token 场景下先通过 `/auth` 验证，再确认 `/api/status`。
- `docs/runtime-runbook.md`：
  - 将 Web Token 章节改为“必须先有有效 Web Token，推荐环境变量提供”，与 README 一致。
  - 新增“备份和恢复”章节，列出 `data/config.json`、`data/*.session`、`data/task-history.json`、`Download/` 和 `Pictures/` 的备份边界。
  - 补充恢复顺序：安装依赖、默认本机监听、放回配置/session 或页面导入、Web Token 验证、确认授权状态。
- `scripts/run-termux.sh`、`app.py`、`tests/`：
  - 只读复核，未修改。
- `Telegram_Web开发.md` 同步 Phase 29 记录。

## 主代理工作

- 按 Phase 28 交接启动 Phase 29，确认工作区干净、最近提交、远端同步和 Git 身份。
- 只读梳理 README、runtime runbook、启动脚本、Web Token 优先级实现和 session 文件路径实现。
- 只修改文档以消除说明不一致，不改脚本和运行逻辑。
- 补充阶段进度、交接文档、验证、提交和推送。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段为文档一致性复核，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `README.md`
- `docs/runtime-runbook.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-29-startup-backup-docs.md`
- `docs/handoff/2026-07-05-phase-29-to-phase-30.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：无。
- 结论：本阶段不需要新增外部依赖。
- 原因：目标是现有运行文档一致性修正，不涉及新功能、测试框架或自动化浏览器能力。

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
- 本阶段只修正文档一致性，未新增启动脚本能力或备份自动化。
- 备份仍由用户自行在仓库外完成；运行数据和凭据不得提交。

## Git

- 提交：提交信息 `phase29: align startup and backup docs`；精确 hash 以 `git log -1 --oneline` 为准。
