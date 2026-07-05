# Phase 37 登录页配置输入提示和错误展示边界

## 阶段目标

- 复核登录页配置输入控件、placeholder、隐藏辅助说明和轻量 HTML 提示属性是否与 Phase 35 后端边界一致。
- 复核 `loadLoginPage()`、`loginConfigPayload()`、`saveLoginConfig()`、`startLogin()` 的错误展示和 payload 边界。
- 小范围修正文案、测试和文档，不改变登录流程、后端配置规则、session 迁移、鉴权逻辑、Telethon 行为或依赖。
- 不读取或提交 `Download/`、`Pictures/`、`data/`、`.session`、Token 或真实 Telegram 凭据。

## 完成内容

- `templates/login.html`：
  - 为 `api_id`、手机号、下载线程和缓存上限补充 `aria-describedby` 与隐藏辅助说明。
  - 为 `api_id`、`api_hash`、手机号补充低风险 `pattern` / `inputmode` / `spellcheck` 提示属性。
  - 扩展代理说明，明确端口范围和拒绝 path/query/fragment。
- `tests/test_core.py`：
  - 更新登录页静态语义断言，覆盖新增提示属性和隐藏说明。
- `tests/frontend_smoke.js`：
  - 增加配置保存 payload 覆盖，确认保存配置会携带 Web Token。
  - 增加发送验证码 payload 覆盖，确认登录启动不会携带 Web Token。
  - 增加后端中文配置错误 toast 覆盖。
- `README.md`、`docs/runtime-runbook.md`、`docs/browser-smoke.md`：
  - 同步登录页提示属性、脱敏占位符、payload smoke 和手动 browser smoke 说明。
- `Telegram_Web开发.md`：
  - 当前基线更新为 Phase 37。
  - 增加 Phase 37 摘要，并把下一阶段建议切到 Phase 38。

## 主代理工作

- 按 Phase 36 交接启动 Phase 37，读取主开发文档、最新交接、登录模板、前端 JS、后端校验和测试。
- 对比后端配置边界和登录页提示，限定改动在模板提示、文档和测试覆盖。
- 发现 `saveLoginConfig()` 调用 `loadLoginPage()` 但不等待的现有异步行为后，前端 smoke 不假设保存后表单已立即重载，只验证当前实际行为和 Web Token 边界。
- 跑自动化验证并记录结果。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段范围较窄，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `templates/login.html`
- `tests/test_core.py`
- `tests/frontend_smoke.js`
- `README.md`
- `docs/runtime-runbook.md`
- `docs/browser-smoke.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-06-phase-37-login-input-errors.md`
- `docs/handoff/2026-07-06-phase-37-to-phase-38.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：无。
- 结论：本阶段不需要新增外部依赖。
- 原因：目标是登录页原生 HTML 提示、原生 JS smoke 和文档对齐；现有 Flask/Jinja/原生 JS/Node smoke 足够覆盖。

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
- HTML `pattern` 等提示属性只作为前端提示，后端仍是最终校验来源。
- 自动浏览器 smoke 仍未引入；当前环境检查仍显示缺少 Playwright 模块和常见浏览器命令。

## Git

- 提交：提交信息 `phase37: align login input guidance`；精确 hash 以 `git log -1 --oneline` 为准。
