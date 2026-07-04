# Phase 11 敏感操作确认弹窗

## 阶段目标

- 用轻量自定义确认组件替换原生 `confirm()`。
- 覆盖退出登录、session 导入导出、任务取消/移除等敏感操作入口。
- 补充纯 Node smoke，覆盖确认、取消、Esc 关闭和并发确认边界。
- 评估当前 Termux 环境是否适合引入真实浏览器 smoke。

## 完成内容

- 在 `templates/base.html` 增加全局确认弹窗结构：
  - `role="dialog"`、`aria-modal="true"`、`aria-labelledby`、`aria-describedby`。
  - 默认取消按钮和确认按钮。
- 在 `static/css/app.css` 增加确认弹窗样式：
  - 桌面居中显示。
  - 移动端贴近底部显示，避开底部导航区域。
- 在 `static/js/app.js` 将 `confirmSensitive()` 改为 Promise 式自定义确认：
  - 弹窗缺失时回退原生 `confirm()`。
  - 确认按钮返回 `true`。
  - 取消按钮、点击遮罩、按 Esc 返回 `false`。
  - 新确认打开时自动取消旧的未完成确认，避免并发悬挂。
  - 打开时默认聚焦取消按钮，关闭后尝试恢复原焦点。
- 敏感操作入口统一 `await confirmSensitive(...)`：
  - `logoutTelegram()`
  - `importStringSession()`
  - `exportStringSession()`
  - `importSessionFile()`
  - `exportSessionFile()`
  - `taskDelete()`
- 扩展 `tests/frontend_smoke.js`：
  - mock DOM 支持 `classList`、`hidden`、元素事件、document 事件和 focus。
  - 覆盖取消按钮、确认按钮、Esc 关闭和并发确认。
  - 既有 StringSession 导出、`.session` 导出和任务删除确认测试改为驱动自定义弹窗。
- README 和开发方案同步更新自定义确认与 smoke 覆盖范围。

## 主代理工作

- 按 Phase 10 交接启动 Phase 11，确认工作区干净和最近提交。
- 只读梳理所有 `confirmSensitive()` 调用点、基础模板和现有 smoke harness。
- 采用现有 Jinja + 原生 JS/CSS 风格实现，没有引入构建链或外部前端依赖。
- 本地评估真实浏览器 smoke 条件并记录结论。
- 运行完整回归并记录结果。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段改动集中，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `templates/base.html`
- `static/css/app.css`
- `static/js/app.js`
- `tests/frontend_smoke.js`
- `README.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-11-sensitive-confirm-dialog.md`
- `docs/handoff/2026-07-05-phase-11-to-phase-12.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：HTML `<dialog>`、SweetAlert2、Micromodal、Playwright。
- 结论：确认弹窗本阶段不新增依赖，使用项目内轻量实现；真实浏览器 smoke 暂不引入 Playwright。
- 原因：
  - 当前只是单一确认流程，原生 DOM + 少量 CSS 足够。
  - 外部弹窗库会增加依赖、样式接管和验证面。
  - `<dialog>` 可用但需要额外 polyfill/样式兼容判断；当前 overlay 更贴合现有 mock smoke。
  - 本地 Node/npm 可用，但未安装 Playwright，也没有可直接调用的 Chromium/Chrome。
- 本地评估命令：
  - `node -v`：`v24.15.0`
  - `npm -v`：`11.17.0`
  - `node -e "try{console.log(require.resolve('playwright'))}catch(e){process.exit(1)}"`：未安装
  - `command -v chromium || command -v chromium-browser || command -v google-chrome || command -v playwright || true`：无输出

## 验证结果

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，48 个测试
- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `git diff --check`：通过

## 风险和遗留

- 仍未执行真实浏览器点击回归；当前是 mock 浏览器环境。
- 目前确认弹窗没有完整 focus trap，只做默认取消聚焦、Esc 关闭和关闭后焦点恢复。
- 前端 smoke 不验证 CSS 布局、真实事件冒泡、真实 Socket.IO 连接、媒体加载和浏览器剪贴板权限差异。
- 没有 systemd、Termux service、容器化或日志轮转脚本。

## Git

- 提交：提交信息 `phase11: add custom sensitive confirm`；精确 hash 以 `git log -1 --oneline` 为准。
