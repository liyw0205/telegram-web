# Phase 7 敏感操作确认和浏览器回归

## 阶段目标

- 为 StringSession 和 `.session` 文件导出增加短期一次性导出令牌。
- 统一退出登录、session 导入/导出、任务取消/移除等敏感操作的前端确认语义。
- 补充错误 ID 检索说明。
- 尽量完成页面 smoke 验证，并记录当前环境限制。

## 完成内容

- 新增 `POST /api/session/export-token`。
- StringSession 和 `.session` 文件导出现在必须携带对应类型的一次性 `export_token`。
- 导出令牌有效期 60 秒，类型绑定为 `string` 或 `file`，使用后立即失效。
- 前端导出 session 时先二次确认，再申请一次性令牌，再执行导出。
- 前端导入 StringSession、导入 `.session`、退出 Telegram 登录、取消运行中任务、移除终态任务记录均增加明确确认文案。
- README 增加错误 ID 在服务端日志中的检索方式。
- 测试扩展到 48 个用例，覆盖令牌类型绑定、单次使用、过期、缺失令牌拒绝、文件导出令牌流程和页面路由 smoke。

## 主代理工作

- 按 Phase 6 交接启动 Phase 7，确认工作区干净、最近提交和 Git 身份。
- 只读梳理敏感操作入口、session 导出 API、任务删除入口、前端操作按钮和现有测试。
- 实现一次性导出令牌和前端确认。
- 更新 README、开发方案、进度和交接文档。

## 子代理协作

- 子代理：未单独启用。
- 任务：本阶段改动集中，由主代理直接完成。
- 输出：不适用。
- 采纳情况：不适用。

## 改动文件

- `app.py`
- `static/js/app.js`
- `tests/test_core.py`
- `README.md`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-05-phase-7-sensitive-confirm-smoke.md`
- `docs/handoff/2026-07-05-phase-7-to-phase-8.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：Flask-WTF/CSRF、服务端 session 存储、Playwright。
- 结论：本阶段不新增依赖。
- 原因：当前导出保护只需要进程内短期一次性令牌，`secrets` 和带锁字典足够，避免引入表单/数据库迁移。Playwright 当前环境未安装，本阶段保留为后续可选浏览器回归能力。

## 验证结果

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，48 个测试
- `node --check static/js/app.js`：通过
- `git diff --check`：通过

## 浏览器 smoke

- 本环境 `playwright` 未安装，未执行真实浏览器点击回归。
- 已通过 Flask 测试客户端覆盖 `/login`、`/chats`、`/chat/<peer>`、`/downloads` 页面渲染 smoke 和关键后端边界。
- 后续建议在具备浏览器依赖的环境补 `/login`、`/chats`、`/downloads` 的最小页面加载和确认弹窗 smoke。

## 风险和遗留

- 一次性导出令牌保存在进程内，服务重启后会失效；这是预期行为。
- 对已获得页面访问权限的人，导出仍可在确认后完成；Web Token 仍是对外访问的第一道边界。
- 前端确认使用浏览器原生 `confirm()`，没有自定义可访问性样式。
- 尚未引入 Playwright 或其它真实浏览器自动化。

## Git

- 提交：待提交，建议信息 `phase7: protect session exports`
