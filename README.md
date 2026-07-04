# Web Telegram

基于 **Flask + Telethon** 的 Telegram Web 管理与聊天界面。

## 功能

- 手机号登录 / 2FA
- 会话列表
- 聊天消息浏览
- 媒体预览与下载
- 下载任务管理（暂停 / 删除）
- StringSession / `.session` 导入导出
- 缓存自动清理
- Markdown 消息渲染

## 技术栈

- Python
- Flask
- Flask-SocketIO
- Telethon
- HTML / CSS / JavaScript

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python app.py
```

Termux 或本机 shell 可使用仓库内脚本：

```bash
sh scripts/run-termux.sh
```

默认访问：

```bash
http://127.0.0.1:5000
```

默认仅监听 `127.0.0.1`。如确需对局域网开放，请显式设置：

```bash
TELEGRAM_WEB_HOST=0.0.0.0 TELEGRAM_WEB_PORT=5000 python app.py
```

对外监听必须同时设置 Web Token，否则服务会拒绝启动：

```bash
TELEGRAM_WEB_HOST=0.0.0.0 TELEGRAM_WEB_TOKEN=your-strong-token python app.py
```

也可以先在本机打开 `/login`，保存 `Web Token` 后再对外监听。设置 Token 后，页面、API、媒体缓存和下载文件都会要求通过 `/auth` 验证。

## 配置

登录页需要填写：

- `api_id`
- `api_hash`
- 手机号
- 代理（可选）
- 下载线程数
- 缓存上限（MB）

## 目录结构

```text
.
├── app.py
├── requirements.txt
├── templates/
├── static/
├── data/       # 运行配置和媒体缓存，已忽略提交
├── Download/   # 下载文件，已忽略提交
└── Pictures/   # 下载图片，已忽略提交
```

## 注意

- 需要有效的 Telegram API ID / Hash
- 首次登录需要验证码
- 使用代理时请确保 SOCKS5 可用
- 媒体缓存会按上限自动清理
- 终态下载/预览任务会记录到 `data/task-history.json`，重启后可继续在下载页看到最近历史
- `data/`、`Download/`、`Pictures/` 和 `.session` 文件是本地运行数据，不要提交到 Git
- 当前登录页开放手机号登录、验证码、2FA、StringSession 导入导出和 `.session` 文件导入导出
- 对外开放前必须设置强 Web Token，并只在可信网络中使用

## 部署和备份

- 推荐先在本机 `127.0.0.1` 完成登录，再按需设置 `TELEGRAM_WEB_TOKEN` 对外访问。
- Termux 后台运行可使用 `tmux`、`screen` 或用户自己的进程管理方式，环境变量仍按上文设置。
- 例如：先执行 `tmux new -s telegram-web`，再运行 `sh scripts/run-termux.sh`；退出查看时用 `tmux attach -t telegram-web`。
- 需要备份时复制 `data/config.json` 和当前 `.session` 文件；如果使用 StringSession，可在登录页导出文本后离线保存。
- 如需保留任务历史，可一并备份 `data/task-history.json`。
- 恢复时先安装依赖，再导入 StringSession 或 `.session` 文件，确认 `/api/status` 授权状态正常。
- 反向代理只转发到本机监听地址；不要让未设置 Web Token 的服务直接暴露到外部网络。

## 说明

本项目仅用于个人 Telegram 数据管理与浏览。
