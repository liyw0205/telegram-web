# Phase 35 配置校验和 API 参数错误文案边界复核

## 阶段目标

- 只读复查 `app.py` 中配置保存、分页参数、Range 请求、session 文件名、代理解析、下载线程/缓存上限和 JSON 请求错误相关文案，及 `README.md`、`docs/runtime-runbook.md`、`docs/browser-smoke.md` 和相关测试。
- 确认 `api_id`、`api_hash`、手机号、代理、Session 文件名、Web Token、下载线程、缓存上限、分页参数、Range 请求和 JSON 请求错误的后端文案、前端提示、文档和测试描述一致。
- 如发现页面提示、API 错误、README、runbook 或测试断言与实际行为不一致，优先做小范围文案、文档或断言修正。
- 不改变文件路径约束、分页逻辑、Range 策略、鉴权逻辑或 Telethon 行为；只修复已确认的代理端口错误文案收敛问题。
- 不引入新依赖，不读取或提交 `Download/`、`Pictures/`、`data/`、`.session` 和任何真实 Token。

## 完成内容

- `app.py`：
  - 新增 `proxy_port_or_default()`，让代理端口非数字、0 或超过 65535 时统一返回“代理端口必须在 1..65535 之间”。
  - 保持 SOCKS4/SOCKS5、host、path/query/fragment、默认端口 1080 和凭据归一化规则不变。
- `templates/login.html`：
  - 代理字段标签从“SOCKS5 代理”改为“SOCKS4/5 代理”。
  - 代理隐藏说明补充 `socks4://` / `socks5://`、host、默认端口和留空沿用边界。
- `tests/test_core.py`：
  - 补充代理默认端口和非法端口中文错误断言。
  - 将配置校验错误、JSON 请求错误和分页参数错误改为精确文案断言。
  - 登录页静态测试同步 SOCKS4/5 代理标签和说明。
- `README.md`：
  - 配置章节补齐 `api_id`、`api_hash`、手机号、代理、session、下载线程、缓存上限和 Web Token 的范围。
  - 补充 JSON POST、分页参数和 Range 响应边界。
- `docs/runtime-runbook.md`：
  - 新增“配置校验和 API 参数错误”章节，记录配置、JSON、分页和 Range 边界。
  - 常见故障中的代理错误补齐 host 和端口范围。
- `docs/browser-smoke.md`：
  - 登录页手动 smoke 同步 SOCKS4/5 标签。
  - 补充配置错误和下载文件 API 参数错误的中文提示检查。
- `Telegram_Web开发.md`：
  - 配置白名单补齐 `web_token`。
  - 增加配置/API 参数错误边界摘要和 Phase 35 阶段记录。

## 主代理工作

- 按 Phase 34 交接启动 Phase 35，确认工作区、最近提交、远端同步和 Git 身份。
- 只读梳理配置标准化、代理解析、JSON 请求、分页参数、Range 请求、登录页、README、runbook、browser smoke 和相关测试。
- 发现代理端口非数字/越界可能透出 `urlparse` 英文错误，且端口 0 会被旧的 `or 1080` 写法误当默认端口，限定修复为既有中文错误文案。
- 同步文档和测试断言，避免扩大配置规则、分页、Range、鉴权或 Telethon 行为。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段为配置/API 参数错误文案和边界一致性复核，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `app.py`
- `templates/login.html`
- `tests/test_core.py`
- `README.md`
- `docs/browser-smoke.md`
- `docs/runtime-runbook.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-35-config-api-errors.md`
- `docs/handoff/2026-07-05-phase-35-to-phase-36.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：无新增依赖；继续使用标准库 `urllib.parse` 和现有 `PySocks` 类型映射。
- 结论：本阶段不需要新增外部依赖。
- 原因：目标是已有配置/API 参数错误文案一致性和一个小范围代理端口错误收敛问题，标准库解析和现有测试足够覆盖。

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
- `git diff --check`：通过
- `git diff --cached --check`：通过

## 风险和遗留

- 未执行真实浏览器或屏幕阅读器人工 smoke。
- 代理端口 0 现在按文档和原有范围检查拒绝；这是对既有范围校验的错误收敛，不改变代理协议或默认端口规则。
- 本阶段未新增前端本地表单校验；错误仍由后端统一返回，前端 toast 展示。
- 文件 Range 策略仍是单段范围支持，不扩展多 Range。

## Git

- 提交：提交信息 `phase35: align config api error copy`；精确 hash 以 `git log -1 --oneline` 为准。
