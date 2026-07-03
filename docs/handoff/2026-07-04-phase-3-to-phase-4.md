# Phase 3 -> Phase 4 交接

## 当前完成进度

- 已完成 Web Token 和配置校验基础后，继续收紧媒体预览与下载任务可靠性。
- 已新增标准化单 range 解析：
  - 支持普通 range、open-ended range、suffix range。
  - 非法 bytes range、多 range、越界 range 返回 416。
  - 非 bytes range 忽略并返回普通 200。
- 已补普通文件响应的 `Accept-Ranges: bytes`。
- 已强化任务状态：
  - 终态 `done/error/canceled` 默认不可被覆盖。
  - 后台任务通过 `task_finish()` / `task_fail()` 收尾。
  - queued/running 任务在进入下载前和下载收尾前检查取消标记。
  - pause/resume 拒绝终态任务。
  - `/api/tasks` 会清理过期终态任务和控制表。
- 已改用 `.part` 临时文件下载，成功后原子替换；取消/失败会清理临时文件。
- 缓存命中和下载文件列表会跳过 `.part` 文件。
- 下载页操作后立即刷新，按钮文案区分“取消”和“移除记录”。
- 测试扩展到 32 个用例。

## 本阶段提交

- commit：本阶段收尾提交，提交信息 `phase3: harden range and task lifecycle`；精确 hash 以 `git log -1 --oneline` 为准。
- 主要文件：
  - `app.py`
  - `static/js/app.js`
  - `tests/test_core.py`
  - `Telegram_Web开发.md`
  - `docs/progress/2026-07-04-phase-3-media-tasks.md`
  - `docs/handoff/2026-07-04-phase-3-to-phase-4.md`
  - `docs/handoff/LATEST.md`

## 已验证

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，32 个测试
- `git diff --check`：通过

## 未完成/风险

- `fail(e)` 仍可能向客户端暴露内部异常字符串；下阶段应引入内部日志和用户可见错误分层。
- 下载页仍全量轮询任务和文件；大量文件时需要分页、limit 或后端按需加载。
- 暂停下载仍依赖回调里的短 sleep；长期应改成不会阻塞 Telegram 客户端事件循环的控制模型。
- 删除任务记录会保留运行中任务的取消信号；这是当前设计，用于让后台回调尽快退出。
- StringSession 新登录后仍未自动持久化，`.session` 导入/导出 UI 也未实现。
- 尚未做真实浏览器手动回归；本阶段验证集中在后端单元测试和前端代码路径审查。

## 下阶段目标

Phase 4 建议主题：**前端交互和移动端体验**。

优先完成：

- 下载页文件列表分页或最近 N 项限制，避免每 1.2 秒全量扫描/渲染。
- 聊天页媒体预览、下载按钮、任务状态提示更清晰。
- 移动端聊天输入区、文件发送区和下载页卡片布局检查，避免小屏误触或文字溢出。
- 错误响应分层：用户输入错误返回明确消息，内部异常返回通用文案并保留服务端日志。
- 评估是否引入成熟轻量前端组件或仅延续原生 JS；如引入 npm，必须同步构建/部署文档。

## 建议子代理拆分

- Explorer：只读梳理 `static/js/app.js`、`static/css/app.css`、`templates/chat.html`、`templates/downloads.html` 的移动端交互、下载页轮询和错误提示路径。
- Worker：实现下载页分页/limit、错误响应分层和前端按钮/状态提示，写范围限定在 `app.py`、`static/js/app.js`、`static/css/app.css`、相关模板和测试。
- Verifier：运行 py_compile、`python -Wd -m unittest discover -v`、`git diff --check`，并用浏览器或 Flask test client 验证主要页面不报错。

## 续会启动步骤

1. 阅读 `Telegram_Web开发.md`。
2. 阅读本文。
3. 运行 `git status --short` 和 `git log --oneline -5`。
4. 确认当前仓库 Git 身份仍为 `liyw0205 <2650115317@qq.com>`。
5. 按“下阶段目标”启动 Phase 4。
6. 阶段结束前更新新的 `docs/progress/`、`docs/handoff/` 和 `docs/handoff/LATEST.md`，然后提交 Git。
