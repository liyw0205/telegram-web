# Phase 12 确认弹窗焦点边界

## 阶段目标

- 给自定义确认弹窗补轻量 focus trap，避免键盘 Tab 跳到背景页面。
- 补充纯 Node smoke 覆盖 Tab / Shift+Tab 焦点循环。
- 梳理媒体查看器和 composer 面板的键盘交互边界。
- 不引入 Playwright、npm 构建链或外部焦点管理依赖。

## 完成内容

- 在 `static/js/app.js` 增加 `getConfirmFocusables()`。
- 扩展 `handleConfirmKeydown()`：
  - 保留 Esc 关闭确认弹窗。
  - Tab 在最后一个确认按钮上回到第一个按钮。
  - Shift+Tab 在第一个确认按钮上回到最后一个按钮。
  - 如果当前焦点在弹窗外，Tab 会把焦点拉回弹窗内。
  - 如果没有可聚焦元素，阻止默认 Tab 行为。
- 扩展 `tests/frontend_smoke.js`：
  - mock DOM 元素的 `focus()` 现在会更新 `document.activeElement`。
  - `pressDocumentKey()` 支持 `shiftKey`。
  - 新增确认弹窗焦点循环 smoke，覆盖 Tab、Shift+Tab 和弹窗外焦点回拉。
  - 既有确认、取消、Esc、并发确认和敏感操作请求链 smoke 保持通过。
- README 和开发方案同步更新 smoke 覆盖范围。
- 梳理其他浮层：
  - `mediaViewer` 目前有关闭、上一项、下一项和下载按钮，但没有全局 Esc 关闭和焦点恢复。
  - `composer-panel` 是页面内联展开区域，不是遮罩式浮层；优先级低于媒体查看器。
  - 本阶段只收紧确认弹窗，避免把媒体查看器行为和确认弹窗混在同一个阶段。

## 主代理工作

- 按 Phase 11 交接启动 Phase 12，确认工作区干净和最近提交。
- 只读梳理确认弹窗、媒体查看器和 composer 面板的键盘相关入口。
- 小范围修改 `static/js/app.js` 和 `tests/frontend_smoke.js`。
- 运行完整回归并记录结果。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段改动集中，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `static/js/app.js`
- `tests/frontend_smoke.js`
- `README.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-12-confirm-focus-trap.md`
- `docs/handoff/2026-07-05-phase-12-to-phase-13.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：`focus-trap`、`tabbable`、Micromodal、原生 `<dialog>`。
- 结论：本阶段不新增依赖。
- 原因：
  - 当前确认弹窗只有两个按钮，焦点循环边界很小。
  - 引入焦点库会扩大依赖和测试面，不符合本阶段的小步收紧目标。
  - 原生 `<dialog>` 仍需要样式和兼容性重新评估，超出本阶段边界。

## 验证结果

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，48 个测试
- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `git diff --check`：通过

## 风险和遗留

- 仍未执行真实浏览器点击回归；当前是 mock 浏览器环境。
- Focus trap 当前基于确认弹窗内两个按钮；如果后续弹窗增加输入框或链接，需要扩展 `getConfirmFocusables()`。
- 媒体查看器还没有全局 Esc 关闭、焦点恢复或焦点循环。
- 前端 smoke 不验证 CSS 布局、真实事件冒泡、真实 Socket.IO 连接、媒体加载和浏览器剪贴板权限差异。

## Git

- 提交：提交信息 `phase12: trap confirm dialog focus`；精确 hash 以 `git log -1 --oneline` 为准。
