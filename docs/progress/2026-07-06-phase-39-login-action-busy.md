# Phase 39 登录页配置保存后刷新状态和并发边界

## 阶段目标

- 复核 `saveLoginConfig()` 保存成功后是否需要等待 `loadLoginPage()` 完成。
- 复核保存配置、发送验证码、提交验证码、提交 2FA 和退出登录的连续点击边界。
- 限定在原生 JS、前端 smoke 和文档内做小范围修正，不改变后端配置规则、登录 API、session 导入导出、鉴权逻辑、Telethon 行为或依赖。

## 完成内容

- `static/js/app.js`：
  - 新增 `withLoginAction()`，用中文忙碌提示串行化登录页操作。
  - `saveLoginConfig()` 保存成功后改为等待 `loadLoginPage()` 完成，再显示“配置已保存”。
  - `startLogin()`、`submitCode()`、`submitPassword()`、`logoutTelegram()` 统一纳入忙碌保护。
  - `loadLoginPage()` 对 `api_id`、下载线程和缓存上限显式写入字符串，避免刷新后再次读取 `.trim()` 时依赖浏览器隐式转换。
- `tests/frontend_smoke.js`：
  - mock 路由支持异步响应，用于模拟保存配置请求挂起。
  - 更新刷新后配置 payload 断言，确认保存后的表单刷新会影响后续发送验证码 payload。
  - 新增忙碌保护 smoke，确认保存配置进行中点击发送验证码不会发起 `/api/login/start`，并显示“配置正在保存，请稍候”。
- `README.md`、`docs/browser-smoke.md`、`Telegram_Web开发.md`：
  - 同步登录页操作忙碌保护和 Phase 39 基线。

## 主代理工作

- 按 Phase 38 交接启动 Phase 39，确认工作区干净、最近提交和 Git 身份。
- 复核登录页操作函数、前端 smoke harness 和已有 payload 测试。
- 实现登录页操作串行化、保存后等待刷新和数字字段字符串化。
- 扩展前端 smoke，覆盖异步保存期间重复点击和保存后刷新行为。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段范围集中在登录页原生 JS 和 smoke，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `static/js/app.js`
- `tests/frontend_smoke.js`
- `README.md`
- `docs/browser-smoke.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-06-phase-39-login-action-busy.md`
- `docs/handoff/2026-07-06-phase-39-to-phase-40.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：无。
- 结论：本阶段不需要新增外部依赖。
- 原因：目标是登录页操作状态和前端 smoke 覆盖，现有原生 JS 与 Node smoke 足够处理。

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
- 本阶段只串行化登录页登录操作；Session 迁移导入导出仍建议 Phase 40 继续复核。
- 忙碌保护不改变后端幂等性或 Telethon 行为，只减少前端重复触发。

## Git

- 提交：提交信息 `phase39: serialize login actions`；精确 hash 以 `git log -1 --oneline` 为准。
