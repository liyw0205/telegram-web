# 浏览器 smoke 验证边界

## 当前结论

Phase 16 在当前 Termux shell 中只确认到 Node/npm/npx 可用；仓库没有 `package.json`、Playwright 配置或浏览器 smoke 脚本，本机也没有可直接调用的 `chromium`、`chromium-browser`、`google-chrome`、`google-chrome-stable`、`firefox` 或 `playwright` 命令，Node 侧也未安装 `playwright` 模块。

Phase 20 重新运行 `sh scripts/check-browser-smoke-env.sh` 后结论不变：Node/npm/npx 可用，Playwright Node 模块缺失，常见浏览器命令缺失。因此 `/diagnostics` 只加入手动浏览器 smoke 清单，不新增 npm、Playwright、Puppeteer、Selenium 或浏览器安装步骤。

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

诊断页：

- 打开 `/diagnostics`，页面标题、刷新按钮、摘要区域和“配置 / 访问 / 运行 / 目录”四组列表可见。
- 摘要区域只显示 Web Token 是否启用、Token 来源、监听范围和端口，不显示原始 host、URL、Token 或本地路径。
- 配置列表只显示 `api_id`、`api_hash`、手机号、代理、`.session`、StringSession 等是否已配置或已保存，不显示真实 `api_hash`、手机号、代理原文、代理用户名/密码、StringSession、`.session` 路径或内容。
- 访问列表只显示 Web Token 是否启用、来源以及环境变量/配置文件是否设置，不显示 Token 原文。
- 运行和目录列表只显示端口、监听范围、是否需要 Token 和目录存在状态，不显示本地绝对路径。
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
- 如果存在任务记录，暂停、恢复、取消或移除操作先弹出确认；取消确认后不应发起破坏性操作。
- 如果没有任务或文件，空状态文案保持可读。

媒体查看器：

- 登录后打开任意包含媒体的聊天，点击图片、视频或文件预览入口。
- 查看器打开后焦点进入关闭按钮。
- 左右方向键在媒体项之间切换，`Esc` 关闭查看器。
- `Tab` 和 `Shift+Tab` 在关闭、下载、上一项、下一项按钮之间循环。
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
