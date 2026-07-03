# Phase 0 -> Phase 1 交接

最新交接文件：`docs/handoff/2026-07-04-phase-0-to-phase-1.md`

## 当前完成进度

- 已为 `telegram-web` 建立主开发文档 `Telegram_Web开发.md`。
- 已建立阶段进度目录 `docs/progress/` 和交接目录 `docs/handoff/`。
- 已明确后续开发采用多阶段、多会话方式，每阶段使用主代理 + 子代理协作。
- 已明确每阶段结束必须更新进度/交接文档、运行验证并创建 Git 提交。
- 已明确如果 GitHub、npm 或 PyPI 上有成熟开源方案，应优先复用，不从头实现通用能力。

## 本阶段提交

- commit：本阶段收尾提交，提交信息 `docs: add telegram web development plan`；精确 hash 以 `git log -1 --oneline` 为准。
- 主要文件：
  - `Telegram_Web开发.md`
  - `docs/progress/2026-07-04-phase-0-docs.md`
  - `docs/handoff/2026-07-04-phase-0-to-phase-1.md`
  - `docs/handoff/LATEST.md`

## 已验证

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `git diff --check`：通过
- `git status --short`：提交前仅显示本阶段新增文档

## 未完成/风险

- 仓库缺少 `.gitignore`，运行 `app.py` 后可能生成 `data/`、`Download/`、`Pictures/` 等不应提交的目录。
- 仓库缺少自动化测试，后续修改只能依赖语法检查和手动验证，回归风险较高。
- `templates/config.html`、`templates/data.html`、`templates/media_view.html` 当前是否仍需保留，需要 Phase 1 做只读确认后再处理。
- README 中 StringSession / `.session` 导入导出说明需要与 `app.py` 当前实现校对，避免文档承诺超过实际功能。
- 真实新会话启动依赖外部环境；若没有自动调度器，请由用户发送“继续 telegram-web”恢复。

## 下阶段目标

Phase 1 建议主题：**基线整理和安全边界**。

优先完成：

- 新增 `.gitignore`，覆盖 `data/`、`Download/`、`Pictures/`、session、缓存、上传临时文件、`__pycache__` 等。
- 建立最小测试骨架，优先覆盖纯函数：`safe_filename()`、`format_size()`、`parse_proxy()`、路径/文件列表安全逻辑。
- 梳理 `send_file_range()`、`serve_download_file()`、`serve_picture()`、`serve_media_cache()` 的路径穿越边界。
- 检查 API JSON 请求体错误处理是否会把无效请求变成 500。
- 更新 README 或开发文档中与实际行为不一致的说明，重点校对 StringSession / `.session` 导入导出。

## 建议子代理拆分

- Explorer：只读梳理 `app.py` 路由、路径拼接、运行数据目录和潜在测试点。
- Worker：负责 `.gitignore` 和最小测试文件，避免同时大改 `app.py`。
- Verifier：运行 `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`、新增测试、`git diff --check`，并复查没有运行数据进入提交。

## 续会启动步骤

1. 阅读 `Telegram_Web开发.md`。
2. 阅读本文和 `docs/progress/2026-07-04-phase-0-docs.md`。
3. 运行 `git status --short` 和 `git log --oneline -5`。
4. 按“下阶段目标”启动 Phase 1。
5. 阶段结束前更新新的 `docs/progress/`、`docs/handoff/` 和 `docs/handoff/LATEST.md`，然后提交 Git。
