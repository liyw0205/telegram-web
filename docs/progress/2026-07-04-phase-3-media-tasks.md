# Phase 3 媒体预览和下载任务可靠性

## 阶段目标

- 标准化文件 Range 请求处理，覆盖普通 range、open-ended range、suffix range、非法 range 和多 range 拒绝策略。
- 收紧下载/预览任务状态流，避免取消任务被后台回调覆盖成 done/error。
- 避免取消或失败后的半截媒体文件进入缓存命中和下载文件列表。
- 让下载页任务操作反馈更明确。
- 扩展自动化测试覆盖 Range、任务状态、任务清理和 `.part` 文件边界。

## 完成内容

- 新增 `parse_range_header()`：
  - 支持 `bytes=1-3`、`bytes=3-`、`bytes=-2`、超长 suffix 裁剪。
  - `bytes=99-100` 返回 416，并带 `Content-Range: bytes */size`。
  - 非法 range 和多 range 统一返回 416。
  - 非 `bytes=` range 忽略并返回普通 200，同时声明 `Accept-Ranges: bytes`。
- 强化 `send_file_range()`：
  - 单 range 返回 206 和准确 `Content-Range` / `Content-Length`。
  - 普通 200 响应也补充 `Accept-Ranges: bytes`。
- 强化任务生命周期：
  - `TaskStore` 增加终态保护，`done/error/canceled` 不会被普通更新覆盖。
  - 增加 `force=True` 兜底处理取消竞态。
  - 增加 `task_is_canceled()`、`task_finish()`、`task_fail()`，后台任务统一通过 helper 收尾。
  - queued 任务在真正进入 Telegram 下载前会先检查取消标记。
  - pause/resume 会拒绝终态任务，避免污染 `task_controls`。
  - `/api/tasks` 调用 `TaskStore.cleanup()` 清理过期终态任务和控制表。
- 强化媒体文件写入：
  - `prepare_media()` 下载到 `.part` 临时文件，成功后原子替换为目标文件。
  - 取消/失败会删除 `.part` 残留。
  - 缓存命中和下载文件列表会跳过 `.part` 文件。
- 前端下载页：
  - 暂停/恢复/删除操作成功后立即刷新任务或文件列表。
  - 活动任务按钮显示“取消”，终态任务按钮显示“移除记录”。
- 测试从 23 个扩展到 32 个。

## 主代理工作

- 按 Phase 2 交接文档启动 Phase 3。
- 读取 `app.py`、`static/js/app.js`、`tests/test_core.py` 和最新交接文档。
- 整合已有 Phase 3 未提交改动，补齐 `.part` 下载、Range 策略、任务状态测试和前端刷新。
- 运行编译、单元测试和 diff 空白检查。

## 子代理协作

- 子代理：Explorer `James`
- 任务：只读梳理 `send_file_range()`、任务状态流、`task_controls` 和前端下载页轮询。
- 输出：建议明确单 range 策略，补 `Accept-Ranges`，使用 `.part` 避免半截文件污染缓存，终态任务拒绝 pause/resume，任务清理接入 `/api/tasks`，前端区分“取消”和“移除记录”。
- 采纳情况：已采纳 Range 策略、`Accept-Ranges`、`.part` 临时文件、终态保护、任务清理、前端按钮文案和刷新；下载页分页、非阻塞暂停模型、错误响应分层留后续阶段。

## 改动文件

- `app.py`
- `static/js/app.js`
- `tests/test_core.py`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-04-phase-3-media-tasks.md`
- `docs/handoff/2026-07-04-phase-3-to-phase-4.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：Flask/Werkzeug 现有文件发送能力、第三方 Range/下载任务库。
- 结论：本阶段不新增 GitHub/npm/PyPI 依赖。
- 原因：项目已依赖 Flask/Werkzeug，现有能力可承担普通文件响应；本阶段只需要固定单 range 策略、补测试和收紧任务状态，引入额外下载任务框架会扩大集成面。后续若做断点续传队列、分页、持久任务或前端播放器，再重新评估成熟方案。

## 验证结果

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，32 个测试
- `git diff --check`：通过

## 风险和遗留

- `fail(e)` 仍会把部分内部异常字符串返回给客户端，后续需要区分用户错误和内部错误。
- 暂停逻辑仍在 Telethon 下载回调里用短 sleep，会阻塞当前下载回调；长期应改成更清晰的非阻塞任务控制。
- 下载页仍每 1.2 秒全量拉取任务和文件；文件多时需要分页或 limit。
- 删除任务当前语义是：从任务列表移除记录，同时为运行中后台任务保留取消信号。
- `session_type=string` 新登录后仍未自动持久化新的 StringSession。

## Git

- 提交信息：`phase3: harden range and task lifecycle`
