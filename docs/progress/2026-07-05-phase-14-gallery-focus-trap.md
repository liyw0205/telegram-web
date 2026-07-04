# Phase 14 媒体查看器焦点边界

## 阶段目标

- 给媒体查看器补最小 focus trap。
- 覆盖查看器内部关闭、下载、上一项、下一项四个按钮的 Tab / Shift+Tab 循环。
- 评估点击遮罩关闭是否适合本阶段。
- 继续保持无构建链、无真实浏览器依赖。

## 完成内容

- 在 `static/js/app.js` 增加 `getGalleryFocusables()`：
  - 焦点范围包含 `viewerClose`、`viewerDownload`、`viewerPrev`、`viewerNext`。
  - 忽略缺失、禁用或不可聚焦元素。
- 扩展 `handleGalleryKeydown()`：
  - 保留 Esc、ArrowLeft、ArrowRight 行为。
  - Tab 从最后一个查看器按钮循环到第一个按钮。
  - Shift+Tab 从第一个按钮循环到最后一个按钮。
  - 如果当前焦点在查看器外，Tab 会拉回查看器内。
  - 如果没有可聚焦元素，阻止默认 Tab 行为。
- 扩展 `tests/frontend_smoke.js`：
  - 新增媒体查看器焦点循环 smoke。
  - 覆盖 Tab、Shift+Tab 和查看器外焦点回拉。
  - 验证关闭按钮点击仍能关闭查看器。
- README 和开发方案同步更新测试覆盖说明。
- 点击遮罩关闭评估：
  - 本阶段暂不实现。
  - 原因：当前查看器主体可承载图片、视频、音频和文件链接，移动端触摸区域较大；引入遮罩点击关闭容易造成误触，且需要真实浏览器验证触摸事件边界。

## 主代理工作

- 按 Phase 13 交接启动 Phase 14，确认工作区干净和最近提交。
- 只读梳理媒体查看器可聚焦元素和当前键盘处理。
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
- `docs/progress/2026-07-05-phase-14-gallery-focus-trap.md`
- `docs/handoff/2026-07-05-phase-14-to-phase-15.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：`focus-trap`、`tabbable`、PhotoSwipe、Viewer.js。
- 结论：本阶段不新增依赖。
- 原因：
  - 当前查看器焦点范围只有四个按钮，小范围原生实现足够。
  - 引入焦点管理库或图库库会扩大依赖、样式和验证面。
  - 本阶段目标是补齐现有查看器焦点边界，不迁移查看器。

## 验证结果

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，48 个测试
- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `git diff --check`：通过

## 风险和遗留

- 仍未执行真实浏览器点击回归；当前是 mock 浏览器环境。
- 媒体查看器 focus trap 当前只覆盖四个固定按钮；如果后续查看器增加更多控件，需要更新 `getGalleryFocusables()`。
- 点击遮罩关闭暂未实现，避免移动端误触。
- 前端 smoke 不验证 CSS 布局、真实事件冒泡、真实 Socket.IO 连接、媒体加载和浏览器剪贴板权限差异。

## Git

- 提交：提交信息 `phase14: trap gallery focus`；精确 hash 以 `git log -1 --oneline` 为准。
