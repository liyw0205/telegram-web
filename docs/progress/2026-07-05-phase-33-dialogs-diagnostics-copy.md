# Phase 33 会话列表和诊断页文案边界复核

## 阶段目标

- 只读复查 `templates/chats.html`、`templates/diagnostics.html`、`static/js/app.js` 中会话列表、搜索、刷新、空状态、诊断项、脱敏字段、复制错误 ID 和 API 错误提示相关文案，及 `README.md`、`docs/browser-smoke.md`、`docs/runtime-runbook.md` 和相关测试。
- 确认会话搜索、刷新状态、未读徽标、空/错误状态、诊断页路径/配置/权限/运行状态、敏感字段脱敏和错误 ID 提示的页面文案、文档和测试描述一致。
- 如发现页面提示、按钮标签、README、runbook 或手动 smoke 清单与实际行为不一致，优先做小范围文案/文档/断言修正。
- 不改变会话加载、诊断采集、脱敏逻辑、鉴权、Socket.IO 或 API 行为。
- 不引入新依赖，不读取或提交 `Download/`、`Pictures/`、`data/`、`.session` 和任何真实 Token。

## 完成内容

- `templates/chats.html`：
  - 搜索输入占位符和可访问名称补充 `peer`，与前端实际按 `peer` 过滤保持一致。
- `static/js/app.js`：
  - 会话搜索无匹配结果时显示“没有匹配的会话”，与初始空列表“暂无会话”区分。
  - 诊断摘要端口显示从裸数字改为“端口 N”。
  - 诊断运行列表行名从英文 `Port` 改为中文“端口”。
- `templates/diagnostics.html`：
  - 诊断刷新按钮补充 `type="button"`，与其他页面按钮边界保持一致。
- `README.md`：
  - 功能列表补充会话列表本地搜索字段和诊断页白名单状态渲染说明。
  - 注意事项补充会话列表 120 条加载、前端本地过滤、搜索无匹配文案和诊断摘要格式。
- `docs/browser-smoke.md`：
  - 会话列表清单补充 `peer` 搜索、无匹配/空列表文案。
  - 诊断页清单补充“端口 N”和中文“端口”行名边界。
- `docs/runtime-runbook.md`：
  - 新增“会话列表和诊断页边界”章节，记录 `/api/dialogs?limit=120`、前端本地搜索、无匹配文案、诊断摘要、脱敏字段和错误 ID 行为。
- `tests/test_core.py` 和 `tests/frontend_smoke.js`：
  - 同步会话搜索输入、诊断刷新按钮、诊断摘要和运行端口行断言。
  - 新增纯 Node smoke 覆盖会话搜索无匹配文案。
- 会话加载、诊断采集、脱敏逻辑、鉴权、Socket.IO 和 API 行为未修改。

## 主代理工作

- 按 Phase 32 交接启动 Phase 33，确认工作区、最近提交、远端同步和 Git 身份。
- 只读梳理会话列表模板、诊断模板、前端会话/诊断逻辑、后端 `/api/dialogs` 与 `/api/diagnostics`、README、browser smoke、runbook 和相关测试。
- 发现会话搜索实际支持 `peer` 但页面提示未说明、搜索无结果复用初始空列表文案、诊断端口文案仍有英文/裸数字后，限定做文案、模板属性、文档和断言修正。
- 补充阶段进度、交接文档、验证、提交和推送。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段为会话/诊断文案和文档一致性复核，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `templates/chats.html`
- `templates/diagnostics.html`
- `static/js/app.js`
- `tests/test_core.py`
- `tests/frontend_smoke.js`
- `README.md`
- `docs/browser-smoke.md`
- `docs/runtime-runbook.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-33-dialogs-diagnostics-copy.md`
- `docs/handoff/2026-07-05-phase-33-to-phase-34.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：无。
- 结论：本阶段不需要新增外部依赖。
- 原因：目标是现有会话/诊断文案、文档和测试断言一致性，不涉及新搜索引擎、诊断框架或浏览器测试框架。

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
- 本阶段只改会话/诊断文案、模板按钮属性、文档和断言，未改变会话加载、诊断采集、脱敏、鉴权或 API 行为。
- 会话搜索仍只过滤当前已加载的最近 120 个会话，不进行服务端搜索或 Telegram 全量查询。
- 诊断页仍依赖 `/api/diagnostics` 返回的白名单状态；运行数据和 secret 仍不应提交。

## Git

- 提交：提交信息 `phase33: align dialogs diagnostics copy`；精确 hash 以 `git log -1 --oneline` 为准。
