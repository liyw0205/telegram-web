# 运行诊断和服务化边界

## 目标

本文记录本项目在 Termux 或本机单进程形态下的启动、访问、日志观察和常见故障排查方式。当前仓库不内置 systemd unit、Termux service、容器编排或日志轮转配置；这些应由使用者在自己的运行环境中维护。

## 验证入口总览

- 自动化基线：运行 `py_compile`、后端 `unittest`、`node --check`、纯 Node 前端 smoke 和 `git diff --check`，命令见本文末尾“必跑回归”。
- 运行预检：运行 `sh -n scripts/diagnose-runtime.sh` 和 `sh scripts/diagnose-runtime.sh`，检查仓库文件、命令、依赖导入、语法和启动环境变量形状。
- 运行中探测：服务启动后可设置 `TELEGRAM_WEB_DIAGNOSTICS_URL=http://127.0.0.1:5000/api/diagnostics` 再运行诊断脚本，对脱敏诊断接口做可选 HTTP 探测。
- 浏览器 smoke：先运行 `sh scripts/check-browser-smoke-env.sh` 记录本机自动化能力，再按 `docs/browser-smoke.md` 执行手动页面和键盘交互清单。

## 安全预检

运行诊断脚本：

```sh
sh scripts/diagnose-runtime.sh
```

脚本只检查仓库文件、命令、Python 依赖导入、语法、前端语法和启动环境变量形状，不读取 `data/config.json`，不打印 Token、StringSession、`.session`、代理凭据或 Telegram API 凭据。

服务已启动时，可选探测脱敏诊断接口：

```sh
TELEGRAM_WEB_DIAGNOSTICS_URL=http://127.0.0.1:5000/api/diagnostics sh scripts/diagnose-runtime.sh
```

如果服务使用 `TELEGRAM_WEB_TOKEN` 或 `WEB_TELEGRAM_TOKEN` 环境变量，脚本会通过 header 发送 Token，但不会打印 Token 或完整 URL。如果服务只使用保存在 `data/config.json` 中的 Web Token，脚本不会读取该文件，HTTP 探测会提示鉴权失败或探测失败。

如需确认真实浏览器自动化条件：

```sh
sh scripts/check-browser-smoke-env.sh
```

## 启动

本机默认启动：

```sh
sh scripts/run-termux.sh
```

等价关键环境变量：

```sh
TELEGRAM_WEB_HOST=127.0.0.1
TELEGRAM_WEB_PORT=5000
PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache"
```

直接启动：

```sh
PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python app.py
```

访问地址：

```text
http://127.0.0.1:5000
```

## Web Token 和访问

默认监听 `127.0.0.1`，仅本机访问。对外监听时必须先有有效 Web Token；推荐用环境变量提供：

```sh
TELEGRAM_WEB_HOST=0.0.0.0 TELEGRAM_WEB_TOKEN='replace-with-strong-token' sh scripts/run-termux.sh
```

`TELEGRAM_WEB_TOKEN` 优先于 `WEB_TELEGRAM_TOKEN` 和本地配置中的 `web_token`。推荐对外访问时使用环境变量，不依赖保存在 `data/config.json` 中的 Token。

浏览器访问受保护页面时会跳到 `/auth`。也可以先访问：

```text
http://127.0.0.1:5000/auth
```

API 调用可使用以下任一方式传递 Token：

```sh
curl -H "Authorization: Bearer $TELEGRAM_WEB_TOKEN" http://127.0.0.1:5000/api/status
curl -H "X-Web-Telegram-Token: $TELEGRAM_WEB_TOKEN" http://127.0.0.1:5000/api/status
```

不要把带真实 Token 的完整 URL、Cookie 或命令历史提交到仓库。

## 登录和 Session 操作

登录页保存配置时，已保存的敏感字段会显示脱敏占位符。留空规则：

- `api_hash` 留空：沿用已保存的 `api_hash`。
- 含凭据代理留空：沿用已保存的代理。
- Session 文件名留空：沿用已保存的 `.session` 文件。
- StringSession 留空：沿用已保存的 StringSession。
- Web Token 留空：不修改已保存的 Web Token。

Session 文件名只接受 `data/` 目录内的文件名，可填写 `telegram` 或 `telegram.session`；系统保存配置时会去掉 `.session` 后缀，实际存储文件仍为对应的 `data/*.session`。

Session 迁移操作：

- 导入 StringSession 或 `.session` 文件前会弹出确认；确认后当前客户端会重置并切换到导入的会话。
- 导出 StringSession 前会弹出确认；成功后文本会填入登录页 StringSession 文本框，并尝试复制到剪贴板。
- 导出 `.session` 文件前会弹出确认；确认后会创建一次性导出令牌并打开下载链接。
- 一次性导出令牌有效期为 60 秒，且使用后立即失效。

## 脱敏诊断接口

浏览器可打开只读诊断页：

```text
http://127.0.0.1:5000/diagnostics
```

该页面复用 `/api/diagnostics`，只渲染白名单布尔、枚举和数值状态，不展示 secret、Token、代理原文、手机号、StringSession、`.session` 路径或本地绝对路径。启用 Web Token 时，页面和接口一样会先经过 `/auth`。

运行中可访问：

```sh
curl -H "X-Web-Telegram-Token: $TELEGRAM_WEB_TOKEN" http://127.0.0.1:5000/api/diagnostics
```

返回内容只包含状态和布尔值：

- 配置文件是否已存在。
- `api_id`、`api_hash`、手机号、代理、StringSession、`.session` 文件、Web Token 是否已配置或已保存。
- 代理是否包含凭据，仅返回 `proxy_redacted`，不返回代理原文。
- 当前 `session_type`、下载线程数、缓存上限。
- Web Token 是否启用，以及来源是环境变量、配置文件还是未启用。
- 当前 host、port、是否 loopback。
- 运行目录和任务历史文件是否存在。

该接口不返回 `api_hash`、手机号原文、代理 URL、代理用户名/密码、StringSession、`.session` 文件路径或内容、Web Token、Cookie 或导出令牌。

## 日志

前台运行时，Flask、Socket.IO 和应用错误日志会输出在当前终端。

推荐用 `tmux` 或 `screen` 保持会话：

```sh
tmux new -s telegram-web
sh scripts/run-termux.sh
```

重新进入：

```sh
tmux attach -t telegram-web
```

如果需要保存日志，建议写到仓库外：

```sh
mkdir -p "$HOME/telegram-web-logs"
sh scripts/run-termux.sh 2>&1 | tee -a "$HOME/telegram-web-logs/server.log"
```

API 内部错误会返回 `error_id`。服务端日志中对应格式：

```text
internal api error <error_id>
```

检索示例：

```sh
grep 'internal api error err-id-here' "$HOME/telegram-web-logs/server.log"
```

## 聊天页发送和媒体边界

聊天页包含文字发送、媒体/文件发送、消息浏览、媒体预览和下载任务入口。

发送边界：

- 文字发送使用 `/api/send`，输入为空时前端不发请求；成功后追加消息并收起文字发送区。
- 文件发送使用 `/api/send-file`，必须选择文件；说明文字可选。成功后清空文件选择和说明文字，追加消息并收起媒体/文件发送区。
- 文字消息按安全 Markdown 渲染，不执行原始 HTML。
- “更早”按钮会按当前最早消息 ID 加载旧消息；没有更早消息时显示 toast，不清空当前消息列表。

媒体预览边界：

- 消息列表优先请求 `/api/media/thumb` 加载缩略图；这一步只拉取缩略图，不自动下载原文件。
- 缩略图不可用时显示文件占位或“无预览”。
- 点击媒体缩略图会调用 `/api/media/prepare` 按需准备查看器缓存；如果缓存尚未就绪，前端显示“媒体正在准备，稍后重试打开”。
- 查看器打开后显示媒体标题和索引，支持左右方向键切换、`Esc` 关闭和焦点循环。

媒体下载边界：

- 消息内下载图标和查看器下载按钮都会调用 `/api/download-media` 创建后台下载任务。
- 下载任务创建成功后显示“下载任务已创建，可在下载页查看进度”。
- 照片下载到 `Pictures/`，其他媒体或文件下载到 `Download/`；进度、暂停、恢复、取消和终态记录在下载页管理。

## 下载页任务和文件边界

下载页包含两类列表：

- 任务列表：显示当前下载/预览任务和最近终态任务历史。
- 已下载文件：分页显示 `Download/` 和 `Pictures/` 下的完成文件。

任务操作边界：

- 运行中任务可暂停，已暂停任务可恢复；这两类操作直接执行，不弹确认。
- 排队中、运行中或已暂停任务点击“取消任务”会先弹出确认；确认后任务记录会移除，并向后台任务发送取消信号。
- 已完成、失败或已取消任务点击“移除记录”会先弹出确认；确认后只移除任务记录，不删除 `Download/` 或 `Pictures/` 中的文件。
- 终态下载/预览任务会写入 `data/task-history.json`，用于重启后在下载页继续显示最近历史；运行中任务不会持久化。

已下载文件边界：

- 文件列表按 `Download/` 和 `Pictures/` 的文件修改时间全局排序并分页加载。
- `.part` 临时文件和符号链接不会出现在已下载文件列表。
- 加载第一页失败时会在文件列表区域显示错误；加载后续页失败时保留已有文件并显示 toast，内部错误会带可检索的错误 ID。

## 常见故障

- 缺少依赖：运行 `pip install -r requirements.txt`，再执行 `sh scripts/diagnose-runtime.sh`。
- 端口占用：设置新端口，例如 `TELEGRAM_WEB_PORT=5001 sh scripts/run-termux.sh`。
- 对外监听启动失败：非本机监听必须设置 `TELEGRAM_WEB_TOKEN`，或先在本机 `/login` 保存 Web Token。
- 页面跳到 `/auth`：服务启用了 Web Token；输入 Token 后会写入本地 Cookie。
- API 返回 `需要 Web Token`：请求缺少有效 Token；使用 `/auth`、`Authorization` header 或 `X-Web-Telegram-Token` header。
- `/api/diagnostics` 探测失败：确认服务正在运行；如启用了 Web Token，优先用 `TELEGRAM_WEB_TOKEN` 环境变量启动，或手动通过 header 访问。
- API 返回 `Telegram 未登录`：先打开 `/login` 完成手机号、验证码和 2FA 登录，或导入 StringSession / `.session`。
- 代理错误：仅支持 `socks4://` 或 `socks5://`，不能带 path、query 或 fragment。
- 下载页没有历史：只有终态下载/预览任务会写入 `data/task-history.json`，运行中任务不会持久化。
- 前端提示内部错误并显示错误 ID：在服务端日志中搜索 `internal api error <error_id>`。

## 备份和恢复

需要备份的核心运行数据：

- `data/config.json`：包含 Telegram API 配置、手机号、代理配置、session 类型、下载配置，可能包含 StringSession 和 Web Token。
- 当前文件 session：默认是 `data/telegram.session`；自定义或导入后以登录页的 Session 文件名为准，实际文件仍应位于 `data/` 下并以 `.session` 结尾。
- `data/task-history.json`：可选，只用于恢复下载页最近终态任务历史。
- `Download/` 和 `Pictures/`：可选，只用于保留已经下载的文件。

备份文件不要提交到 Git，也不要放入公开日志或 issue。`data/config.json`、StringSession、`.session`、Web Token 和代理凭据都应按账号凭据处理。

推荐恢复流程：

1. 安装依赖并保持默认本机监听：`pip install -r requirements.txt`，然后 `sh scripts/run-termux.sh`。
2. 放回 `data/config.json` 和对应的 `data/*.session` 文件，或打开 `/login` 导入 StringSession / `.session` 文件。
3. 如果配置中启用了 Web Token，先通过 `/auth` 输入 Token；如果对外监听，优先改用 `TELEGRAM_WEB_TOKEN` 环境变量启动。
4. 打开 `/api/status` 或页面顶部状态，确认 Telegram 授权状态正常。
5. 如恢复 `data/task-history.json`、`Download/` 或 `Pictures/`，确认下载页只显示预期的历史和文件。

## 服务化边界

当前仓库只提供单进程启动脚本，不提交通用 systemd、Termux service 或容器配置，原因是：

- 运行目录包含本地 Telegram session、下载文件和缓存，服务化策略需要用户按设备和备份方案决定。
- Web Token、代理和 session 配置不能硬编码进仓库模板。
- Termux、Linux 服务器和桌面系统的后台策略差异较大，强行提供统一守护配置容易误导。

推荐策略：

- Termux：优先使用 `tmux` 或 `screen`。
- Linux 服务器：自行创建 systemd unit，工作目录指向仓库，环境变量通过本机私有 env 文件注入。
- 反向代理：只转发到本机监听地址，并始终启用 Web Token。

## 必跑回归

```sh
PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -m py_compile app.py
PYTHONPYCACHEPREFIX="${TMPDIR:-$HOME/.cache}/telegram-web-pycache" python -Wd -m unittest discover -v
node --check static/js/app.js
node --check tests/frontend_smoke.js
node tests/frontend_smoke.js
git diff --check
```
