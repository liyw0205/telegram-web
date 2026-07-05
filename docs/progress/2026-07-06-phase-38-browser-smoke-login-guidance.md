# Phase 38 浏览器 smoke 条件和登录页提示回归

## 阶段目标

- 复核当前环境是否具备真实浏览器自动化 smoke 条件。
- 按 Phase 37 交接收口登录页输入提示、脱敏占位符和 smoke 覆盖边界。
- 如仍缺 Playwright/浏览器命令，不引入新依赖，只更新手动 smoke 结论和阶段文档。
- 不改变登录流程、配置保存规则、session 导入导出、鉴权逻辑、Telethon 行为或新增依赖。

## 完成内容

- `scripts/check-browser-smoke-env.sh` 复核结果不变：
  - Node/npm/npx 可用。
  - Playwright Node 模块缺失。
  - 常见浏览器命令 `chromium`、`chromium-browser`、`google-chrome`、`google-chrome-stable`、`firefox` 缺失。
  - 本阶段不引入 Playwright、Puppeteer、Selenium、浏览器安装脚本或 npm 构建链。
- `static/js/app.js`：
  - 修正 `loadLoginPage()` 在未保存 `api_hash` 时的运行时 placeholder，从旧的 `api_hash` 对齐为 `32 位十六进制字符串`。
- `tests/frontend_smoke.js`：
  - 新增未保存配置输入提示 smoke，覆盖 `api_hash`、代理、Session 文件名、StringSession 和 Web Token 默认提示。
- `README.md`、`docs/browser-smoke.md`、`Telegram_Web开发.md`：
  - 同步未保存配置输入提示覆盖和 Phase 38 浏览器 smoke 条件结论。
  - 主开发文档基线更新为 Phase 38，并将下一阶段建议切到 Phase 39。

## 主代理工作

- 按 Phase 37 交接启动 Phase 38，确认工作区干净、最近提交、Git 身份和浏览器 smoke 环境。
- 只读复查 `docs/browser-smoke.md`、登录页模板、`loadLoginPage()` 和前端 smoke。
- 发现模板默认 `api_hash` placeholder 已是 `32 位十六进制字符串`，但 `loadLoginPage()` 未保存配置时会覆盖成旧文案 `api_hash`。
- 做小范围 JS 修正和 smoke 覆盖，不改后端 API、配置规则或登录流程。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段范围较窄，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `static/js/app.js`
- `tests/frontend_smoke.js`
- `README.md`
- `docs/browser-smoke.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-06-phase-38-browser-smoke-login-guidance.md`
- `docs/handoff/2026-07-06-phase-38-to-phase-39.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：Playwright、Puppeteer、Selenium。
- 结论：本阶段不引入。
- 原因：当前环境缺少 Playwright 模块和常见浏览器命令；阶段目标是复核条件和收口登录页提示，不需要新增浏览器自动化依赖或构建链。

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

- 未执行真实浏览器或屏幕阅读器人工 smoke；当前环境仍不具备自动化浏览器 smoke 条件。
- HTML `pattern` 和 placeholder 仍只是提示，最终校验以后端中文错误为准。
- `saveLoginConfig()` 保存成功后会触发 `loadLoginPage()` 但不等待，连续点击和状态反馈边界建议 Phase 39 继续复核。

## Git

- 提交：提交信息 `phase38: document browser smoke boundary`；精确 hash 以 `git log -1 --oneline` 为准。
