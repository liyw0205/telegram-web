# Phase 16 真实浏览器 smoke 边界

## 阶段目标

- 只读确认当前环境是否具备真实浏览器自动化 smoke 条件。
- 如果条件不足，不强制安装依赖，不引入 Playwright、Puppeteer、Selenium 或 npm 构建链。
- 产出可重复执行的环境检查脚本。
- 固化手动浏览器 smoke 清单，覆盖 `/login` 基本渲染、自定义确认弹窗键盘路径、下载页、媒体查看器和移动端视口。
- 保持纯 Node smoke 作为必跑自动化基线。

## 完成内容

- 新增 `scripts/check-browser-smoke-env.sh`：
  - 检查 `node`、`npm`、`npx`。
  - 检查 Node 侧 `playwright` 模块。
  - 检查 `chromium`、`chromium-browser`、`google-chrome`、`google-chrome-stable`、`firefox`。
  - 不安装依赖，不读取运行数据。
  - 自动浏览器条件不足时返回成功并提示使用手动清单。
- 新增 `docs/browser-smoke.md`：
  - 记录当前环境结论。
  - 列出必跑自动化基线命令。
  - 提供手动浏览器 smoke 步骤。
  - 明确后续引入 Playwright 的边界。
- README 增加可选真实浏览器 smoke 说明。
- `Telegram_Web开发.md` 增加新脚本、文档路径和 Phase 16 更新记录。

## 环境检查结论

- 仓库当前没有 `package.json`、锁文件、Playwright 配置或浏览器 smoke 脚本。
- `node`、`npm`、`npx` 可用。
- `playwright` 命令不可用。
- Node 侧 `playwright` 模块不可用。
- 未发现可直接调用的 `chromium`、`chromium-browser`、`google-chrome`、`google-chrome-stable` 或 `firefox` 命令。
- 结论：本阶段不具备自动真实浏览器 smoke 条件，不引入新依赖。

## 主代理工作

- 按 Phase 15 交接启动 Phase 16，确认工作区干净、最近提交和 Git 身份。
- 检查仓库是否已有 npm/Playwright/browser smoke 配置。
- 检查当前 shell 中浏览器和 Playwright 可用性。
- 新增环境检查脚本和手动验证文档。
- 更新 README、开发方案、进度和交接文档。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段修改范围集中在脚本和文档，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `scripts/check-browser-smoke-env.sh`
- `docs/browser-smoke.md`
- `README.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-16-browser-smoke-boundary.md`
- `docs/handoff/2026-07-05-phase-16-to-phase-17.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：Playwright、Puppeteer、Selenium。
- 结论：本阶段不新增依赖。
- 原因：
  - 当前环境没有可用浏览器命令，也没有 Playwright 模块。
  - 仓库没有 npm 包管理基线，贸然加入会扩大安装、锁文件和部署维护面。
  - 当前目标是确认可行性和固定验证边界，而不是建立完整浏览器自动化体系。
  - 后续若引入 Playwright，应作为独立阶段新增 `package.json`、锁文件、npm 脚本和最小 `/login` smoke。

## 验证结果

- `sh scripts/check-browser-smoke-env.sh`：通过，输出当前 shell 不具备自动浏览器 smoke 条件
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，48 个测试
- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `git diff --check`：通过

## 风险和遗留

- 仍未执行自动真实浏览器点击回归；当前 shell 缺少必要浏览器/Playwright 条件。
- 手动 smoke 清单需要操作者实际打开浏览器执行，无法替代自动化回归。
- 后续引入 Playwright 时需要新增 npm 依赖管理和可复现浏览器安装方式。
- 本阶段没有修改业务前后端行为。

## Git

- 提交：提交信息 `phase16: document browser smoke boundary`；精确 hash 以 `git log -1 --oneline` 为准。
