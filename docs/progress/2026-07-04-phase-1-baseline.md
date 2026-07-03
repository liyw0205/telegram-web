# Phase 1 基线整理和安全边界

## 阶段目标

- 新增 `.gitignore`，避免运行数据、缓存、session 和 Python 缓存进入提交。
- 建立最小 `unittest` 测试骨架。
- 修复文件服务路径穿越边界。
- 将非法 JSON / 非对象 JSON 请求稳定返回 400。
- 校对 README 中 StringSession / `.session` 描述和当前实现的差异。

## 完成内容

- 新增 `.gitignore`，忽略 `data/`、`Download/`、`Pictures/`、`.session`、`__pycache__` 等运行产物。
- 新增 `tests/test_core.py` 和 `tests/__init__.py`，覆盖纯函数、文件路由、Range、JSON 请求体和配置脱敏。
- `app.py` 新增 `request_json_object()`，要求 JSON POST 使用 `application/json` 且请求体必须是对象。
- `app.py` 新增 `resolve_under()`，`/download-file`、`/pictures`、`/media-cache` 只允许访问对应根目录内文件。
- `send_file_range()` 对越界 Range 返回 416。
- `list_download_files()` 跳过 symlink，并在文件删除/权限变化时跳过异常项。
- `/api/config` 响应不再回传 `api_hash`、`session_file`、`string_session` 原文，只返回 `*_saved` 标记。
- 登录页在存在已保存 `api_hash` 时显示占位提示，提交空 `api_hash` 会由后端沿用已保存配置。
- 默认服务监听从 `0.0.0.0` 收紧为 `127.0.0.1`；如需对外开放，需显式设置 `TELEGRAM_WEB_HOST=0.0.0.0`。
- README 降级 StringSession / `.session` 描述为“配置支持”，并说明独立导入导出页面尚未启用。

## 主代理工作

- 按 Phase 0 交接文档启动 Phase 1。
- 设置当前仓库 Git 身份为 `liyw0205 <2650115317@qq.com>`。
- 实现安全边界修复、测试和文档更新。
- 复查未使用模板和 README 差异。

## 子代理协作

- 子代理：Explorer `Einstein`
- 任务：只读梳理 `app.py` 路由、路径拼接、JSON 请求体、配置响应、README 和未启用模板。
- 输出：指出 `/api/config` 敏感配置回传、默认 `0.0.0.0` 无鉴权暴露、`force=True` JSON 解析、Range 解析、`list_download_files()` stat 异常、README StringSession 描述不一致、`config.html/data.html/media_view.html` 未启用。
- 采纳情况：本阶段已修复配置脱敏、默认本机监听、JSON Content-Type/对象校验、路径穿越、越界 Range、symlink/stat 跳过和 README 校对；完整 Web 鉴权、配置字段严格校验和标准 Range 解析留给后续阶段。

## 改动文件

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

## 开源复用评估

- 候选：本阶段未引入 GitHub/npm/PyPI 依赖。
- 结论：使用 Python 标准库 `unittest` 和 Flask 自带 `test_client` 足够覆盖当前安全边界。
- 原因：Phase 1 是基础安全修复和测试骨架，不需要新增运行时或测试依赖。

## 验证结果

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，14 个测试
- `git diff --check`：通过
- 敏感信息检查：仅命中字段名、文档说明和代码变量，未发现真实凭据
- `git status --short --ignored`：`data/` 显示为 ignored，未进入提交

## 风险和遗留

- 显式设置 `TELEGRAM_WEB_HOST=0.0.0.0` 后，Web 页面/API/文件路由仍缺少应用层鉴权；对外暴露前必须先实现访问 Token 或登录态保护。
- `api_config()` 仍缺少完整字段类型、范围、枚举和路径校验；坏配置写入风险已部分缓解但未彻底解决。
- Range 解析仍是轻量实现，不完整支持 RFC 语义；未来可抽纯函数并补更多测试。
- `fail(e)` 仍会把非预期异常字符串返回给客户端，后续应区分用户错误和内部错误。
- `templates/config.html`、`templates/data.html`、`templates/media_view.html` 仍为未启用/历史模板，没有对应路由和 JS 函数。

## Git

- 提交信息：`phase1: add safety baseline`
