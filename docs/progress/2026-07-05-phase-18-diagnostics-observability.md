# Phase 18 后端诊断可观测性

## 阶段目标

- 新增只返回脱敏状态的诊断能力。
- 复用现有配置脱敏规则，不返回 `api_hash`、StringSession、`.session` 内容、Web Token、代理凭据或导出令牌。
- 给 `scripts/diagnose-runtime.sh` 增加可选 HTTP 探测。
- 补充测试，确认诊断 helper 和 API 输出不泄露 secret。
- 不触碰真实 `data/`、`Download/`、`Pictures/` 和凭据内容。

## 完成内容

- 新增 `diagnostics_snapshot()`：
  - 复用 `public_config()` 的 saved/redacted 标记。
  - 返回配置文件是否存在。
  - 返回 `api_id`、`api_hash`、手机号、代理、session、StringSession、Web Token 是否已配置或保存。
  - 返回 `session_type`、下载线程数、缓存上限。
  - 返回 Web Token 是否启用，以及来源为 `environment`、`config` 或 `none`。
  - 返回当前 host、port、port 是否有效、是否 loopback。
  - 返回运行目录和任务历史文件是否存在。
  - 不返回任何 secret 原文或本地 session 路径。
- 新增 `GET /api/diagnostics`：
  - 走现有 `/api/` Web Token 鉴权。
  - 成功时返回脱敏诊断状态。
- 扩展 `scripts/diagnose-runtime.sh`：
  - 支持设置 `TELEGRAM_WEB_DIAGNOSTICS_URL` 探测运行中的 `/api/diagnostics`。
  - 如果环境变量中有 `TELEGRAM_WEB_TOKEN` 或 `WEB_TELEGRAM_TOKEN`，脚本会通过 header 发送 Token。
  - 脚本只输出 HTTP 状态和脱敏布尔/枚举摘要，不打印 Token 或完整 URL。
  - 探测失败作为 warning，不让本地预检整体失败。
- 扩展单元测试：
  - `diagnostics_snapshot()` 不泄露 secret。
  - `/api/diagnostics` 不泄露 secret。
  - Web Token 启用时 `/api/diagnostics` 仍受保护。
- README、运行 runbook 和开发方案同步更新。

## 主代理工作

- 按 Phase 17 交接启动 Phase 18，确认工作区干净、最近提交和 Git 身份。
- 只读梳理 `/api/config`、`/api/status`、`public_config()`、Web Token 鉴权和现有测试结构。
- 实现脱敏诊断 helper 和 API。
- 扩展诊断脚本可选 HTTP 探测。
- 补充单元测试和文档。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段涉及 `app.py`、测试、脚本和文档，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `app.py`
- `tests/test_core.py`
- `scripts/diagnose-runtime.sh`
- `README.md`
- `docs/runtime-runbook.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-18-diagnostics-observability.md`
- `docs/handoff/2026-07-05-phase-18-to-phase-19.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：Prometheus exporter、healthcheck 蓝图库、Sentry/OpenTelemetry。
- 结论：本阶段不新增外部可观测性依赖。
- 原因：
  - 当前目标是本地脱敏诊断状态，不是指标采集、分布式追踪或错误上报。
  - 引入外部可观测性栈会扩大部署、网络和凭据边界。
  - 现有 Flask API、测试客户端和 shell 脚本足够覆盖本阶段目标。

## 验证结果

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest tests.test_core.CoreHelpersTest.test_diagnostics_snapshot_redacts_secret_values tests.test_core.FlaskBoundaryTest.test_diagnostics_api_returns_only_redacted_state tests.test_core.WebAuthTest.test_api_requires_token_when_configured -v`：通过，3 个测试
- `TELEGRAM_WEB_DIAGNOSTICS_URL=http://127.0.0.1:9/api/diagnostics sh scripts/diagnose-runtime.sh`：通过，HTTP 探测失败按 warning 处理
- `sh -n scripts/diagnose-runtime.sh`：通过
- `sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=0`
- `TELEGRAM_WEB_HOST=0.0.0.0 sh scripts/diagnose-runtime.sh`：通过，输出未设置 Token 环境变量的 warning
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，50 个测试
- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `git diff --check`：通过

## 风险和遗留

- `/api/diagnostics` 只返回脱敏状态，不替代真实日志、浏览器回归或 Telegram 登录回归。
- 诊断脚本可选 HTTP 探测只能使用环境变量中的 Token；如果服务只使用 `data/config.json` 中的 Token，脚本不会读取该文件。
- 未新增前端诊断页面，当前需要通过 API 或脚本查看诊断状态。
- 本阶段没有修改 Telegram 客户端业务流程。

## Git

- 提交：提交信息 `phase18: add redacted diagnostics endpoint`；精确 hash 以 `git log -1 --oneline` 为准。
