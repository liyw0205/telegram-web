# Phase 4 前端交互和移动端体验

## 阶段目标

- 下载页文件列表改为分页加载，避免页面和轮询路径反复全量扫描 `Download/` 与 `Pictures/`。
- 下载页高频刷新只覆盖任务状态，文件列表改为显式刷新和加载更多。
- API 错误响应分层：用户可修正错误返回明确消息，内部异常返回通用文案并记录服务端日志。
- 小幅收紧移动端下载卡片和聊天输入区布局。
- 扩展自动化测试覆盖分页 API、分页参数校验和内部异常隐藏。

## 完成内容

- `GET /downloads` 首屏不再调用 `list_download_files()`。
- `GET /api/download-files` 新增 `limit` / `offset` 参数：
  - 默认 `limit=30`。
  - `limit` 限制在 `1..100`。
  - `offset` 限制在 `0..100000`。
  - 返回 `{items,total,limit,offset,has_more}`。
- `list_download_files()` 支持全局按 mtime 排序、分页切片和 total 返回，并继续跳过 symlink 与 `.part` 文件。
- 下载页前端：
  - 初始化和手动刷新时加载第一页文件。
  - 任务列表仍 1.2 秒刷新。
  - 文件列表不再 1.2 秒轮询。
  - 增加文件统计和“加载更多”按钮。
- 错误响应：
  - `ApiError`、显式 4xx 和少量可操作运行错误继续返回明确消息。
  - 未分类内部异常返回 `内部错误，请查看服务端日志` 和 `error_id`。
  - 服务端日志记录内部异常栈。
- 查询参数校验：
  - `/api/dialogs?limit=...`
  - `/api/messages?limit=...&offset_id=...`
  - `/api/download-files?limit=...&offset=...`
- 移动端样式：
  - 下载卡片在窄屏变成两列，打开按钮换行显示。
  - 聊天页和面板圆角、间距在窄屏收紧。
  - 输入区按钮在窄屏稳定三列。
- 测试从 32 个扩展到 36 个。

## 主代理工作

- 按 Phase 3 -> Phase 4 交接文档启动。
- 读取 `Telegram_Web开发.md`、`docs/handoff/LATEST.md`、现有实现和测试。
- 实现下载文件分页、前端加载更多、错误响应分层和移动端样式微调。
- 补充单元测试并运行验证。

## 子代理协作

- 子代理：未使用。
- 任务：本阶段改动集中且文件少，主代理直接完成。
- 输出：无。
- 采纳情况：无。

## 改动文件

- `app.py`
- `static/js/app.js`
- `static/css/app.css`
- `templates/downloads.html`
- `tests/test_core.py`
- `Telegram_Web开发.md`
- `docs/progress/2026-07-04-phase-4-frontend-mobile.md`
- `docs/handoff/2026-07-04-phase-4-to-phase-5.md`
- `docs/handoff/LATEST.md`

## 开源复用评估

- 候选：前端分页组件、数据表组件、后端分页库。
- 结论：本阶段不新增依赖。
- 原因：项目当前是 Jinja + 原生 JS/CSS，分页只涉及简单 limit/offset 和一个加载更多按钮；引入 npm 或后端分页库会增加构建和部署成本，收益不足。

## 验证结果

- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py`：通过
- `PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v`：通过，36 个测试
- `git diff --check`：通过

## 风险和遗留

- 尚未做真实浏览器手动回归；本阶段以前端静态路径审查和 Flask test client 为主。
- 下载任务仍未持久化，服务重启后内存任务记录会丢失。
- 暂停下载仍依赖回调里的短 sleep，长期应改成不会阻塞 Telegram 客户端事件循环的控制模型。
- StringSession 新登录后仍未自动持久化，`.session` 导入/导出 UI 也未实现。
- 文件列表分页仍需要扫描目录以计算 total；相比全量返回和全量渲染已有改善，但超大目录可继续优化为索引或游标。

## Git

- 提交信息：`phase4: improve downloads pagination and errors`
