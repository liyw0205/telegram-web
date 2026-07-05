# 浏览器 smoke 验证边界

## 当前结论

Phase 16 在当前 Termux shell 中只确认到 Node/npm/npx 可用；仓库没有 `package.json`、Playwright 配置或浏览器 smoke 脚本，本机也没有可直接调用的 `chromium`、`chromium-browser`、`google-chrome`、`google-chrome-stable`、`firefox` 或 `playwright` 命令，Node 侧也未安装 `playwright` 模块。

Phase 20 重新运行 `sh scripts/check-browser-smoke-env.sh` 后结论不变：Node/npm/npx 可用，Playwright Node 模块缺失，常见浏览器命令缺失。因此 `/diagnostics` 只加入手动浏览器 smoke 清单，不新增 npm、Playwright、Puppeteer、Selenium 或浏览器安装步骤。

Phase 27 继续复核自动化边界：当前仓库仍无 npm 浏览器测试入口，本阶段只把 Phase 21-26 的可访问性语义改动纳入手动浏览器回归清单，不引入 Playwright、Puppeteer、Selenium、浏览器安装脚本或真实账号数据。

Phase 38 再次运行 `sh scripts/check-browser-smoke-env.sh` 后结论不变：Node/npm/npx 可用，Playwright Node 模块缺失，常见浏览器命令缺失。因此本阶段只收口登录页提示的纯 Node smoke 覆盖和手动清单，不引入 Playwright、Puppeteer、Selenium、浏览器安装脚本或真实账号数据。

因此当前仍以纯 Node smoke 和后端单元测试作为必跑自动化基线；真实浏览器回归使用下面的手动清单，不在本阶段引入 Playwright、Puppeteer、Selenium 或 npm 构建链。

## 环境检查

```sh
sh scripts/check-browser-smoke-env.sh
```

该脚本只检查本机命令和 Node 模块，不安装依赖，不读取运行数据。缺少浏览器或 Playwright 时仍返回成功，方便在不同环境中记录能力状态。

## 必跑自动化基线

```sh
PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py
PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v
node --check static/js/app.js
node --check tests/frontend_smoke.js
node tests/frontend_smoke.js
git diff --check
```

## 手动浏览器 smoke

启动服务：

```sh
TELEGRAM_WEB_HOST=127.0.0.1 TELEGRAM_WEB_PORT=5000 sh scripts/run-termux.sh
```

默认访问：

```text
http://127.0.0.1:5000/login
```

基础页面：

- 打开 `/login`，页面标题、顶部状态、底部导航、手机号登录表单和 Session 迁移区域可见。
- `api_hash`、`proxy`、`.session`、`StringSession`、`Web Token` 已保存时只显示脱敏占位符，不把真实值写入输入框。
- 不登录 Telegram 的情况下，`/chats`、`/downloads`、`/diagnostics` 可打开并显示可理解的空状态、未授权状态、诊断状态或错误提示，不出现前端白屏。

全局反馈和确认：

- 顶部连接状态在刷新时有明确状态文本，如“Telegram 已登录：...”、“Telegram 已连接，未授权”、“Telegram 未连接”或“需要 Web Token，请先验证”。
- 顶部刷新按钮名称为“刷新 Telegram 连接状态”，只刷新状态摘要，不改变当前页面数据。
- 底部导航为主导航；当前页面链接有当前项标记，可进入会话、下载、诊断和登录页。
- toast 出现后不遮挡底部导航或主要操作按钮，内容可读。
- API 内部错误 toast 显示“错误 ID”；支持剪贴板时提示“已尝试复制”，复制失败不应阻断页面操作。
- 自定义确认弹窗打开后有标题、说明、取消和确认按钮，初始焦点在“取消”。
- `Tab` 和 `Shift+Tab` 在确认弹窗按钮内循环；`Esc` 关闭弹窗；关闭后页面可继续操作。

Web Token 验证页：

- 启用 Web Token 后打开受保护页面会跳转 `/auth?next=...`。
- `/auth` 显示“访问验证”和“Web Token”表单，Token 输入框有明确标签。
- 输入错误 Token 时显示“Token 不正确”；输入正确 Token 后回到 `next` 指向的页面。

登录页：

- `/login` 的介绍区域、手机号登录区域和 Session 迁移区域标题清晰。
- `api_id`、`api_hash`、手机号、SOCKS4/5 代理、Session 文件名、StringSession、下载线程、缓存上限、Web Token 和 `.session` 上传控件都有可理解标签。
- `api_id`、`api_hash`、手机号、SOCKS4/5 代理、下载线程和缓存上限的输入提示与后端范围一致；这些提示不能替代后端校验。
- 敏感字段已保存时显示脱敏占位符或“已保存”说明，不显示真实 `api_hash`、StringSession、Web Token、代理凭据或 `.session` 内容。
- “登录操作”、“StringSession 操作”和“.session 文件操作”各自成组，按钮可用键盘聚焦和触发。
- 保存配置、发送验证码、提交验证码、提交 2FA 和退出登录同一时间只处理一个操作；重复点击时显示中文忙碌提示，例如“配置正在保存，请稍候”。
- StringSession 和 `.session` 导入成功后会刷新配置与顶部 Telegram 状态；导入导出进行中重复触发会显示中文忙碌提示，例如“StringSession 正在导出，请稍候”。
- 使用测试输入触发配置错误时，页面显示后端中文错误，例如 `api_id 必须在 1..2147483647 之间`、`api_hash 必须是 32 位十六进制字符串`、`代理端口必须在 1..65535 之间`、`download_threads 必须在 1..128 之间`，不显示英文内部异常。

会话列表页：

- 打开 `/chats`，页面标题、刷新按钮、搜索框和会话列表区域可见。
- 搜索框说明可理解，可输入名称、用户名、peer 或 ID 过滤；清空搜索后列表恢复。
- 搜索无匹配结果时显示“没有匹配的会话”；未加载到任何会话时显示“暂无会话”。
- 刷新会话时列表显示加载或结果状态，不白屏。
- 会话项可用键盘聚焦并进入对应 `/chat/<peer>`；会话项能区分私聊、群组或频道。
- 有未读消息时未读徽标显示数量，且不会遮挡会话名称或元信息。

聊天页：

- 打开 `/chat/<peer>`，返回按钮、刷新按钮、消息列表、消息操作栏和发送区控件可见。
- 消息列表刷新时显示加载或空状态；失败时显示可理解错误，不白屏。
- “文字”、“媒体/文件”和“更早”按钮可用键盘聚焦和触发；打开文字或媒体发送区后对应面板出现，另一个面板收起。
- 文字输入框、文件选择框、说明文字输入框和发送按钮可用键盘操作。
- 发送文字或文件时发送区保持可理解状态；成功后追加消息，发送区收起。
- 媒体消息先显示缩略图、文件占位或“无预览”，不应自动下载原文件。
- 点击媒体缩略图会按需准备查看器缓存；如果尚未就绪，页面显示“媒体正在准备，稍后重试打开”，不白屏。
- 点击消息内下载图标会创建下载任务并显示“下载任务已创建，可在下载页查看进度”。

诊断页：

- 打开 `/diagnostics`，页面标题、刷新按钮、摘要区域和“配置 / 访问 / 运行 / 目录”四组列表可见。
- 摘要区域只显示 Web Token 是否启用、Token 来源、监听范围和“端口 N”，不显示原始 host、URL、Token 或本地路径。
- 配置列表只显示 `api_id`、`api_hash`、手机号、代理、`.session`、StringSession 等是否已配置或已保存，不显示真实 `api_hash`、手机号、代理原文、代理用户名/密码、StringSession、`.session` 路径或内容。
- 访问列表只显示 Web Token 是否启用、来源以及环境变量/配置文件是否设置，不显示 Token 原文。
- 运行和目录列表只显示“端口”、监听范围、是否需要 Token 和目录存在状态，不显示本地绝对路径。
- 点击刷新按钮后列表可重新加载；接口失败时摘要区域显示错误，页面其他区域清空且不白屏。
- 启用 Web Token 后直接访问 `/diagnostics` 会先跳转 `/auth`；验证成功后回到诊断页。

确认弹窗：

- 在 `/login` 点击“导出 StringSession”，弹出自定义确认弹窗。
- 初始焦点在“取消”按钮上。
- `Tab` 在弹窗按钮内移动，`Shift+Tab` 可反向回到前一个按钮。
- `Esc` 关闭弹窗并保持页面可继续操作。
- 重新打开后点击“取消”，弹窗关闭，页面不应跳转或下载文件。

下载页：

- 打开 `/downloads`，任务列表、已下载文件区域和加载更多按钮区域不互相遮挡。
- 顶部刷新按钮、文件刷新按钮和加载更多按钮可用键盘聚焦和触发。
- 任务列表刷新时显示加载、空状态、任务卡片或错误状态，不白屏。
- 任务卡片、文件卡片、空状态和错误状态在列表区域内保持可读。
- 已下载状态显示当前分页数量；加载更多时按钮文案显示加载中，完成后恢复或隐藏。
- 加载更多进行中重复触发只保留一个分页请求，并显示“文件列表正在加载，请稍候”。
- 暂停和恢复按钮会直接更新任务状态；取消活跃任务或移除终态记录会先弹出确认。
- 同一任务的暂停、恢复、取消或移除进行中重复触发会显示“任务正在处理，请稍候”。
- 取消确认后不应发起取消任务或移除记录请求；移除终态记录不应删除已下载文件。
- 下载页文件刷新失败时不保留旧分页数量，列表区域显示错误且 busy 状态会恢复。
- 已下载文件列表不应显示 `.part` 临时文件。
- 已下载文件 API 参数错误时提示字段和范围，例如 `limit 必须在 1..100 之间` 或 `offset 必须在 0..100000 之间`。
- 如果没有任务或文件，空状态文案保持可读。

媒体查看器：

- 登录后打开任意包含媒体的聊天，点击图片、视频或文件预览入口。
- 查看器打开后焦点进入关闭按钮。
- 查看器顶部显示媒体标题和当前索引。
- 关闭、创建当前媒体下载任务、上一项和下一项按钮都有明确用途，图标按钮不会与媒体内容重叠。
- 点击查看器下载按钮会创建后台下载任务，不会直接保存文件到当前浏览器页面。
- 左右方向键在媒体项之间切换，`Esc` 关闭查看器。
- `Tab` 和 `Shift+Tab` 在关闭、创建下载任务、上一项、下一项按钮之间循环。
- 关闭后焦点回到打开查看器前的触发元素。

移动端视口：

- 用手机浏览器或开发者工具窄屏宽度查看 `/login`、`/chats`、`/chat/<peer>`、`/downloads`、`/diagnostics`。
- 顶部栏、底部导航、聊天输入区、下载任务卡片、诊断列表和确认弹窗不互相遮挡。
- 按钮文字不溢出，关键操作按钮可点击。

## 后续 Playwright 引入边界

只有满足以下条件时再引入真实浏览器自动化：

- 仓库显式新增 `package.json`、锁文件和 `npm` 验证脚本。
- Playwright 或替代方案只覆盖不需要真实 Telegram 登录的路径，优先从 `/login` 基本渲染和确认弹窗键盘路径开始。
- 浏览器测试不得读取或提交 `data/`、`Download/`、`Pictures/`、`.session`、StringSession、Web Token 或真实 Telegram API 凭据。
- CI 或本地说明必须清楚区分“必跑纯 Node smoke”和“可选真实浏览器 smoke”。
