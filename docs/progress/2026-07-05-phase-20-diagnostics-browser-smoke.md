# Phase 20 诊断页浏览器 smoke 清单

## 阶段目标

- 重新确认当前 shell 是否具备真实浏览器自动化 smoke 条件。
- 将 `/diagnostics` 加入 `docs/browser-smoke.md` 的手动浏览器检查路径。
- 明确诊断页在浏览器中应检查的脱敏、鉴权、刷新、错误和移动端布局边界。
- 不引入 npm、Playwright、Puppeteer、Selenium 或浏览器安装步骤。
- 不读取或提交 `data/`、`Download/`、`Pictures/`、`.session` 和任何真实 Token。

## 完成内容

- 运行 `sh scripts/check-browser-smoke-env.sh` 复核环境：
  - Node/npm/npx 可用。
  - Playwright Node 模块缺失。
  - `chromium`、`chromium-browser`、`google-chrome`、`google-chrome-stable`、`firefox` 命令缺失。
  - 结论：当前 shell 仍不具备自动化真实浏览器 smoke 条件。
- 更新 `docs/browser-smoke.md`：
  - 在当前结论中追加 Phase 20 复核结果。
  - 基础页面清单加入 `/diagnostics`。
  - 新增“诊断页”手动检查项。
  - 明确诊断页只应显示摘要、布尔、枚举和数值状态。
  - 明确不得显示原始 host、URL、Token、本地路径、手机号、代理原文、代理凭据、StringSession 或 `.session` 内容。
  - 移动端视口清单加入 `/diagnostics` 和诊断列表遮挡检查。
- 更新 `Telegram_Web开发.md` 的 Phase 20 记录。

## 主代理工作

- 按 Phase 19 交接启动 Phase 20，确认工作区干净、最近提交和 Git 身份。
- 只读梳理 `docs/browser-smoke.md`、`scripts/check-browser-smoke-env.sh`、README、运行 runbook 和既有 smoke 说明。
- 根据环境复核结果决定不新增浏览器自动化依赖。
- 补齐手动浏览器 smoke 清单、验证和交接文档。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段只涉及文档和验证，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `docs/browser-smoke.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-20-diagnostics-browser-smoke.md`
- `docs/handoff/2026-07-05-phase-20-to-phase-21.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：Playwright、Puppeteer、Selenium。
- 结论：本阶段不新增外部依赖。
- 原因：
  - 当前 shell 缺少 Playwright Node 模块和可调用浏览器命令。
  - 本阶段目标是补齐 `/diagnostics` 的真实浏览器手动检查边界，不是搭建新测试栈。
  - 引入浏览器自动化需要新增 `package.json`、锁文件、浏览器安装说明和可选验证边界，超出本阶段最小目标。

## 验证结果

- `sh scripts/check-browser-smoke-env.sh`：通过；输出自动化浏览器 smoke 当前不可用，使用手动清单
- `sh -n scripts/diagnose-runtime.sh`：通过
- `sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=0`
- `TELEGRAM_WEB_HOST=0.0.0.0 sh scripts/diagnose-runtime.sh`：通过，`failures=0 warnings=1`，warning 为未设置环境变量 Web Token
- `TELEGRAM_WEB_DIAGNOSTICS_URL=http://127.0.0.1:9/api/diagnostics sh scripts/diagnose-runtime.sh`：通过，HTTP 探测失败按 warning 处理
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，50 个测试
- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `git diff --check`：通过

## 风险和遗留

- 未执行真实浏览器人工验证；本阶段只补齐手动清单并记录当前自动化条件不足。
- 真实浏览器 smoke 仍依赖用户在具备浏览器的设备上按文档执行。
- 后续若引入 Playwright，需要单独新增 npm 项目元数据、锁文件、浏览器安装边界和可选验证脚本。

## Git

- 提交：提交信息 `phase20: document diagnostics browser smoke`；精确 hash 以 `git log -1 --oneline` 为准。
