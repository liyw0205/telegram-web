# Phase 34 全局导航和错误反馈文案边界复核

## 阶段目标

- 只读复查 `templates/base.html`、`static/js/app.js` 中顶部连接状态、刷新按钮、底部导航、toast、`api()` 错误 ID 展示/复制、401 跳转和 Web Token 鉴权提示相关文案，及 `README.md`、`docs/browser-smoke.md`、`docs/runtime-runbook.md` 和相关测试。
- 确认全局状态、导航、toast、确认弹窗、错误 ID、剪贴板复制失败容忍、`/auth` 跳转和 Web Token 提示的页面文案、文档和测试描述一致。
- 如发现页面提示、按钮标签、README、runbook 或手动 smoke 清单与实际行为不一致，优先做小范围文案/文档/断言修正。
- 不改变鉴权逻辑、Socket.IO 行为、API 错误包装结构、剪贴板权限处理或导航目标。
- 不引入新依赖，不读取或提交 `Download/`、`Pictures/`、`data/`、`.session` 和任何真实 Token。

## 完成内容

- `templates/base.html`：
  - 顶部初始状态从“状态检查中...”改为“Telegram 状态检查中...”。
  - 顶部刷新按钮补充 `type="button"`，可访问名称改为“刷新 Telegram 连接状态”。
  - 底部导航补充 `aria-label="主导航"`，各入口补充明确可访问名称，当前页补充 `aria-current="page"`。
  - 底部导航图标标记为装饰内容，避免重复朗读。
- `templates/auth.html`：
  - 访问验证页补充标题关联、Web Token 表单标题关联、Token 输入框 label 绑定和错误 `role="alert"`。
- `static/js/app.js`：
  - 401 前端提示从“需要 Web Token”改为“需要 Web Token，请先验证”，仍跳转 `/auth?next=...`。
  - API 错误包含 `error_id` 时，支持剪贴板的环境会在提示中追加“已尝试复制”。
  - 顶部状态文案统一为“Telegram 已登录：...”、“Telegram 已连接，未授权”、“Telegram 未连接”；状态接口错误时展示可操作错误文案。
- `app.py`：
  - API 401 Web Token 错误文案同步为“需要 Web Token，请先验证”。
- `README.md`：
  - 前端 smoke 描述同步为错误 ID 展示和复制尝试。
  - 注意事项补充顶部状态和底部导航边界。
  - 日志和错误 ID 章节补充 Web Token 验证提示与错误 ID 复制提示。
- `docs/browser-smoke.md`：
  - 全局反馈清单补充顶部状态取值、刷新按钮名称、主导航当前项、错误 ID 复制提示。
  - 新增 Web Token 验证页手动 smoke 清单。
- `docs/runtime-runbook.md`：
  - 新增“全局导航和错误反馈边界”章节，记录顶部状态、底部导航、Web Token 验证页、401 提示、错误 ID 和 toast 边界。
  - 常见故障中的 Web Token API 错误文案同步。
- `tests/test_core.py` 和 `tests/frontend_smoke.js`：
  - 同步全局模板、Web Token 验证页、API 401、错误 ID、顶部状态文案断言。
  - 新增后端静态测试覆盖 `/auth` Web Token 表单语义。
- 鉴权判断、Socket.IO 鉴权、API 错误包装结构、剪贴板权限处理和导航目标未修改。

## 主代理工作

- 按 Phase 33 交接启动 Phase 34，确认工作区、最近提交、远端同步和 Git 身份。
- 只读梳理全局模板、Web Token 验证页、前端 API/状态/toast 逻辑、后端 Web Token 401、README、browser smoke、runbook 和相关测试。
- 发现全局刷新按钮缺少 `type="button"`、底部导航缺少主导航/当前项语义、401 文案不够明确、错误 ID 提示未说明复制尝试、顶部状态缺少 Telegram 上下文后，限定做文案、模板语义、文档和断言修正。
- 补充阶段进度、交接文档、验证、提交和推送。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段为全局导航/错误反馈文案和文档一致性复核，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `app.py`
- `templates/base.html`
- `templates/auth.html`
- `static/js/app.js`
- `tests/test_core.py`
- `tests/frontend_smoke.js`
- `README.md`
- `docs/browser-smoke.md`
- `docs/runtime-runbook.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-34-global-feedback-copy.md`
- `docs/handoff/2026-07-05-phase-34-to-phase-35.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：无。
- 结论：本阶段不需要新增外部依赖。
- 原因：目标是现有全局文案、模板语义、文档和测试断言一致性，不涉及新鉴权方案、toast 组件或导航框架。

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
- 本阶段只改全局文案、模板语义、文档和断言，未改变 Web Token 判断、Socket.IO 鉴权、导航目标或错误包装结构。
- 错误 ID 复制仍取决于浏览器剪贴板权限；复制失败不会阻断页面操作。
- 顶部状态仍只展示摘要，不替代日志、诊断页或 Telegram 登录回归。

## Git

- 提交：提交信息 `phase34: align global feedback copy`；精确 hash 以 `git log -1 --oneline` 为准。
