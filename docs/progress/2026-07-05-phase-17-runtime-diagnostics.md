# Phase 17 运行诊断和服务化边界

## 阶段目标

- 梳理启动、访问、Web Token、日志观察和常见故障排查路径。
- 补充最小运行诊断脚本，面向 Termux/本机单进程部署。
- 不新增 systemd、Termux service、容器化或日志轮转依赖。
- 不读取或提交真实 `data/`、`Download/`、`Pictures/`、session、Token 或 Telegram 凭据。
- 保持既有 py_compile、后端单测、Node smoke 和 `git diff --check` 基线。

## 完成内容

- 新增 `scripts/diagnose-runtime.sh`：
  - 检查仓库关键文件是否存在。
  - 检查 `python` 和 `node` 命令。
  - 检查有效 host、port 和 Web Token 环境变量形状。
  - 对非 loopback 监听且未设置 Token 环境变量的场景给出 warning。
  - 运行 `python -m py_compile app.py`。
  - 验证 Flask、Flask-SocketIO、Telethon、PySocks、python-socketio 运行依赖可导入。
  - 运行 `node --check static/js/app.js` 和 `node --check tests/frontend_smoke.js`。
  - 不读取 `data/config.json`，不打印 Token 或任何 Telegram 凭据。
- 新增 `docs/runtime-runbook.md`：
  - 记录安全预检命令。
  - 说明默认本机启动和直接启动方式。
  - 说明 Web Token、`/auth` 和 API Token header。
  - 说明前台、tmux 和外部日志文件观察方式。
  - 记录 `error_id` 检索方式。
  - 汇总常见故障和处理动作。
  - 明确服务化边界：仓库暂不提交 systemd/Termux service/容器配置。
- README 增加诊断脚本和 runbook 入口。
- `Telegram_Web开发.md` 增加新脚本、文档路径和 Phase 17 更新记录。

## 主代理工作

- 按 Phase 16 交接启动 Phase 17，确认工作区干净、最近提交和 Git 身份。
- 只读梳理 README、启动脚本、Web Token、host/port、错误 ID 和日志路径。
- 新增运行诊断脚本和运行排障文档。
- 验证诊断脚本默认场景和非 loopback 无环境 Token 的 warning 场景。
- 更新 README、开发方案、进度和交接文档。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段修改范围集中在脚本和文档，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `scripts/diagnose-runtime.sh`
- `docs/runtime-runbook.md`
- `README.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-17-runtime-diagnostics.md`
- `docs/handoff/2026-07-05-phase-17-to-phase-18.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：systemd unit、Termux service、supervisor、Docker/Compose、logrotate。
- 结论：本阶段不新增服务化依赖或模板。
- 原因：
  - 项目运行数据包含 Telegram session、Token、下载文件和缓存，服务化和备份策略需要用户按设备决定。
  - Termux、Linux 服务器和桌面环境差异较大，统一守护配置容易误导。
  - 本阶段目标是诊断和文档收口，轻量 shell 预检足够。

## 验证结果

- `sh -n scripts/diagnose-runtime.sh`：通过
- `sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=0`
- `TELEGRAM_WEB_HOST=0.0.0.0 sh scripts/diagnose-runtime.sh`：通过，输出未设置 Token 环境变量的 warning
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，48 个测试
- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `git diff --check`：通过

## 风险和遗留

- 诊断脚本不读取 `data/config.json`，因此无法判断配置文件中是否已保存 Web Token，只能检查环境变量。
- 仍未提供 systemd、Termux service、Docker 或日志轮转配置。
- 手动 runbook 不能替代真实浏览器或真实 Telegram 登录回归。
- 本阶段没有修改业务前后端行为。

## Git

- 提交：提交信息 `phase17: add runtime diagnostics runbook`；精确 hash 以 `git log -1 --oneline` 为准。
