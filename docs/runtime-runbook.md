# 运行诊断和服务化边界

## 目标

本文记录本项目在 Termux 或本机单进程形态下的启动、访问、日志观察和常见故障排查方式。当前仓库不内置 systemd unit、Termux service、容器编排或日志轮转配置；这些应由使用者在自己的运行环境中维护。

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

默认监听 `127.0.0.1`，仅本机访问。对外监听时必须先设置 Web Token：

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
