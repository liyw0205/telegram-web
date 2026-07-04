# Phase 13 媒体查看器键盘交互

## 阶段目标

- 给媒体查看器增加打开前焦点记录、关闭后焦点恢复。
- 增加 Esc 关闭媒体查看器。
- 增加左右方向键切换媒体。
- 补充纯 Node smoke 覆盖，不引入真实浏览器依赖。

## 完成内容

- 在 `static/js/app.js` 增加媒体查看器状态：
  - `galleryLastFocus`
  - `galleryKeydownBound`
  - `galleryEventsBound`
- `bindGalleryEvents()` 增加重复绑定保护，避免重复初始化时叠加按钮事件。
- 新增 `handleGalleryKeydown()`：
  - Esc 关闭媒体查看器。
  - ArrowLeft 切到上一项。
  - ArrowRight 切到下一项。
  - 如果敏感确认弹窗打开，媒体查看器键盘处理会让位，避免 Esc 同时关闭确认框和查看器。
- `openGallery()`：
  - 首次打开时记录 `document.activeElement`。
  - 显示查看器并绑定 document keydown。
  - 渲染当前媒体后聚焦关闭按钮。
- `closeGallery()`：
  - 隐藏查看器。
  - 解绑 document keydown。
  - 尝试恢复打开前焦点。
- 扩展 `tests/frontend_smoke.js`：
  - 增加媒体查看器相关 mock DOM 元素。
  - 覆盖打开后聚焦关闭按钮。
  - 覆盖 ArrowRight / ArrowLeft 更新标题、索引和渲染内容。
  - 覆盖 Esc 关闭并恢复触发元素焦点。
  - 覆盖敏感确认弹窗打开时，查看器忽略方向键和 Esc。
- README 和开发方案同步更新测试覆盖说明。

## 主代理工作

- 按 Phase 12 交接启动 Phase 13，确认工作区干净和最近提交。
- 只读梳理 `openGallery()`、`closeGallery()`、`moveGallery()`、`bindGalleryEvents()` 和媒体查看器模板。
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
- `docs/progress/2026-07-05-phase-13-gallery-keyboard.md`
- `docs/handoff/2026-07-05-phase-13-to-phase-14.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：PhotoSwipe、Viewer.js、GLightbox、Micromodal。
- 结论：本阶段不新增依赖。
- 原因：
  - 当前项目已有自定义媒体查看器，只缺少少量键盘和焦点行为。
  - 引入图库库会扩大样式、资源加载和真实浏览器验证范围。
  - 本阶段目标是收紧现有行为，不迁移媒体查看器实现。

## 验证结果

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，48 个测试
- `node --check static/js/app.js`：通过
- `node --check tests/frontend_smoke.js`：通过
- `node tests/frontend_smoke.js`：通过，输出 `frontend smoke passed`
- `git diff --check`：通过

## 风险和遗留

- 仍未执行真实浏览器点击回归；当前是 mock 浏览器环境。
- 媒体查看器尚未实现完整 focus trap；本阶段只做打开后聚焦关闭按钮、关闭后恢复焦点和键盘切换。
- 前端 smoke 不验证 CSS 布局、真实事件冒泡、真实 Socket.IO 连接、媒体加载和浏览器剪贴板权限差异。
- composer 面板仍是内联展开区域，没有额外键盘关闭行为。

## Git

- 提交：提交信息 `phase13: add gallery keyboard controls`；精确 hash 以 `git log -1 --oneline` 为准。
