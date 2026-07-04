# Phase 28 README 和运行文档验证入口同步

## 阶段目标

- 只读复查 `README.md`、`docs/runtime-runbook.md`、`docs/browser-smoke.md` 和 `scripts/diagnose-runtime.sh` 的验证入口说明。
- 将当前推荐验证命令、手动浏览器 smoke 文档入口、诊断脚本边界和 Web Token 注意事项同步到用户最容易看到的文档位置。
- 不改变运行逻辑、API、模板、前端 JS、测试代码或脚本行为。
- 不引入新依赖，不读取或提交 `Download/`、`Pictures/`、`data/`、`.session` 和任何真实 Token。

## 完成内容

- `README.md`：
  - 在验证章节前置 `scripts/diagnose-runtime.sh` 语法检查和运行预检入口。
  - 保留后端、前端和 `git diff --check` 自动化回归命令。
  - 更新 `tests/frontend_smoke.js` 分组说明，补齐聊天消息和会话列表覆盖范围。
  - 明确 `scripts/check-browser-smoke-env.sh` 只报告能力，不安装依赖，不读取运行数据。
  - 增加 `TELEGRAM_WEB_DIAGNOSTICS_URL=... sh scripts/diagnose-runtime.sh` 的可选诊断接口探测入口。
  - 明确诊断脚本不读取 `data/config.json`，不打印 Web Token、StringSession、`.session`、代理凭据或 Telegram API 凭据。
- `docs/runtime-runbook.md`：
  - 新增“验证入口总览”，集中指向自动化基线、运行预检、运行中诊断接口探测和手动浏览器 smoke 清单。
- `docs/browser-smoke.md` 和 `scripts/diagnose-runtime.sh`：
  - 只读复核，未修改。
- `Telegram_Web开发.md` 同步 Phase 28 记录。

## 主代理工作

- 按 Phase 27 交接启动 Phase 28，确认工作区、最近提交和 Git 身份。
- 只读梳理 README、运行 runbook、浏览器 smoke 文档和诊断脚本边界。
- 限定修改文档，不改运行逻辑、测试代码或脚本行为。
- 补充阶段进度、交接文档、验证和提交。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段为文档同步，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `README.md`
- `docs/runtime-runbook.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-28-validation-docs.md`
- `docs/handoff/2026-07-05-phase-28-to-phase-29.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：Playwright、Puppeteer、Selenium、axe-core。
- 结论：本阶段不新增外部依赖。
- 原因：
  - 当前目标是同步文档入口，不是新增浏览器自动化能力。
  - `docs/browser-smoke.md` 已记录真实浏览器 smoke 仍为可选手动验证。
  - 引入浏览器自动化需要单独新增 npm 元数据、锁文件、安装/缓存说明和可选验证边界。

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
- 本阶段只同步文档入口，未新增自动浏览器测试。
- 诊断脚本仍不读取 `data/config.json`；如果 Web Token 只保存在配置文件，HTTP 探测仍可能鉴权失败或探测失败。

## Git

- 提交：提交信息 `phase28: sync validation documentation`；精确 hash 以 `git log -1 --oneline` 为准。
