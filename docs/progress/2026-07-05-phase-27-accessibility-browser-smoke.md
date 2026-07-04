# Phase 27 手动浏览器 smoke 和可访问性回归收口

## 阶段目标

- 只读复查 `docs/browser-smoke.md`、`scripts/check-browser-smoke-env.sh`、近期 Phase 21-26 的可访问性改动和现有验证边界。
- 将 `/login`、`/chats`、`/chat/<peer>`、`/downloads`、`/diagnostics` 的关键可访问性检查加入手动浏览器 smoke 清单。
- 不引入 Playwright、npm 依赖、浏览器安装脚本或真实账号数据。
- 保持自动化基线仍为 `unittest`、`node tests/frontend_smoke.js`、诊断脚本和 `git diff --check`。
- 不读取或提交 `Download/`、`Pictures/`、`data/`、`.session` 和任何真实 Token。

## 完成内容

- `docs/browser-smoke.md`：
  - 在当前结论中记录 Phase 27 继续不引入 Playwright、Puppeteer、Selenium、浏览器安装脚本或真实账号数据。
  - 新增全局反馈和确认检查，覆盖顶部状态、toast、自定义确认弹窗焦点和键盘行为。
  - 扩充登录页检查，覆盖标题区域、表单标签、敏感字段脱敏和操作分组。
  - 新增会话列表页检查，覆盖标题、刷新、搜索、会话项、类型和未读徽标。
  - 新增聊天页检查，覆盖消息列表、操作栏、文字/文件发送区、加载/错误状态和发送后行为。
  - 扩充下载页检查，覆盖刷新/加载按钮、列表状态、分页状态和确认边界。
  - 扩充媒体查看器检查，覆盖标题/索引、图标按钮用途和焦点循环。
- `scripts/check-browser-smoke-env.sh`：
  - 只读复核，脚本仍只检查本机命令和 Node 模块，不安装依赖，不读取运行数据。
- `Telegram_Web开发.md` 同步 Phase 27 记录。

## 主代理工作

- 按 Phase 26 交接启动 Phase 27，确认工作区干净、最近提交和 Git 身份。
- 只读梳理浏览器 smoke 文档、环境检查脚本、Phase 21-26 进度/交接和模板/JS 中的 ARIA 改动。
- 仅补充手动浏览器 smoke 文档和阶段文档，不改运行逻辑。
- 补充验证和提交。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段为文档收口，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `docs/browser-smoke.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-27-accessibility-browser-smoke.md`
- `docs/handoff/2026-07-05-phase-27-to-phase-28.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：axe-core、Playwright accessibility snapshot、Puppeteer、Selenium。
- 结论：本阶段不新增外部依赖。
- 原因：
  - 当前目标是手动 smoke 清单收口，不是建立新浏览器自动化栈。
  - 当前环境仍缺少浏览器自动化条件。
  - 引入浏览器自动化需要新增 npm 元数据、锁文件、浏览器安装说明和可选验证边界，应单独开阶段。

## 验证结果

- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `sh -n scripts/diagnose-runtime.sh`：通过
- `sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=0`
- `TELEGRAM_WEB_HOST=0.0.0.0 sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=1`，warning 为未设置环境变量 Web Token
- `TELEGRAM_WEB_DIAGNOSTICS_URL=http://127.0.0.1:9/api/diagnostics sh scripts/diagnose-runtime.sh`：通过，HTTP 探测失败按 warning 处理
- `sh scripts/check-browser-smoke-env.sh`：通过；输出自动化浏览器 smoke 当前不可用，使用手动清单
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，56 个测试
- `git diff --check`：通过

## 风险和遗留

- 未执行真实浏览器或屏幕阅读器人工 smoke。
- 本阶段只是收口手动清单，不能替代真实浏览器或辅助技术验证。
- 自动浏览器 smoke 仍未引入；后续若引入，需要单独新增 npm 元数据、锁文件和浏览器安装/缓存说明。

## Git

- 提交：提交信息 `phase27: document accessibility browser smoke`；精确 hash 以 `git log -1 --oneline` 为准。
