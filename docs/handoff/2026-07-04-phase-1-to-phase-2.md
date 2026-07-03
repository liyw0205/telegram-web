# Phase 1 -> Phase 2 交接

## 当前完成进度

- Phase 1 已建立 `.gitignore` 和最小单测。
- 文件服务路由已通过 `resolve_under()` 限制在各自目录内。
- JSON POST 已统一要求 `application/json` 且请求体为对象。
- `/api/config` 已脱敏 `api_hash`、`session_file`、`string_session`。
- 默认监听已从 `0.0.0.0` 改为 `127.0.0.1`，可用 `TELEGRAM_WEB_HOST` / `TELEGRAM_WEB_PORT` 显式覆盖。
- README 已校对 StringSession / `.session` 状态，避免承诺未启用的导入导出页面。

## 本阶段提交

- commit：本阶段收尾提交，提交信息 `phase1: add safety baseline`；精确 hash 以 `git log -1 --oneline` 为准。
- 主要文件：
  - `.gitignore`
  - `README.md`
  - `app.py`
  - `static/js/app.js`
  - `tests/__init__.py`
  - `tests/test_core.py`
  - `Telegram_Web开发.md`
  - `docs/progress/2026-07-04-phase-1-baseline.md`
  - `docs/handoff/2026-07-04-phase-1-to-phase-2.md`
  - `docs/handoff/LATEST.md`

## 已验证

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，14 个测试
- `git diff --check`：通过
- 敏感信息检查：仅命中字段名、文档说明和代码变量，未发现真实凭据

## 未完成/风险

- 对外监听仍无应用层鉴权。不要在未加 Token/登录保护前把 `TELEGRAM_WEB_HOST` 设为 `0.0.0.0` 暴露到不可信网络。
- 配置保存缺少完整校验：`api_id`、`download_threads`、`cache_limit_mb`、`session_type`、`session_file`、代理 URL 需要先验证再保存。
- `StringSession` / `.session` 只在配置层支持使用；导入、导出、下载、上传和 UI 流程尚未实现。
- 未启用模板：
  - `templates/config.html` 引用 `loadConfigPage()` / `saveConfigPage()`，但无路由和 JS。
  - `templates/data.html` 引用 `exportStringSession()` 和 `cfg/data_files`，但无路由/API/JS。
  - `templates/media_view.html` 引用 `initMediaViewPage()`，但当前实际媒体查看走聊天页内嵌 viewer。
- Range 解析和 `fail(e)` 错误泄露边界仍可继续收紧。

## 下阶段目标

Phase 2 建议主题：**登录、session 和访问控制可靠性**。

优先完成：

- 增加 Web 访问 Token 或登录态保护，至少覆盖配置、聊天、媒体文件和下载文件路由。
- 为 `api_config()` 增加字段级校验和归一化，避免坏配置落盘。
- 明确并实现 StringSession / `.session` 的导入导出边界，或删除未启用模板。
- 修正/启用 `/config`、`/data`、`/media-view` 相关页面前，先补对应 API 和 JS。
- 扩展测试覆盖配置校验、Token 鉴权和 session 类型切换。

## 建议子代理拆分

- Explorer：只读梳理当前登录、session、配置字段和未启用模板的真实依赖。
- Worker：实现访问 Token/登录态保护和配置字段校验，写范围限定在 `app.py`、`static/js/app.js`、模板和测试。
- Verifier：运行 py_compile、`python -Wd -m unittest discover -v`、`git diff --check`，并复查无运行数据/真实凭据进入提交。

## 续会启动步骤

1. 阅读 `Telegram_Web开发.md`。
2. 阅读本文。
3. 运行 `git status --short` 和 `git log --oneline -5`。
4. 确认当前仓库 Git 身份仍为 `liyw0205 <2650115317@qq.com>`。
5. 按“下阶段目标”启动 Phase 2。
6. 阶段结束前更新新的 `docs/progress/`、`docs/handoff/` 和 `docs/handoff/LATEST.md`，然后提交 Git。
