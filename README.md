# Web Telegram

基于 **Flask + Telethon** 的 Telegram Web 管理与聊天界面。

## 功能

- 手机号登录 / 2FA
- 会话列表
- 聊天消息浏览
- 媒体预览与下载
- 下载任务管理（暂停 / 删除）
- StringSession / `.session` 配置支持
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
- `data/`、`Download/`、`Pictures/` 和 `.session` 文件是本地运行数据，不要提交到 Git
- 当前登录页开放手机号登录、验证码和 2FA；StringSession / `.session` 可通过配置字段使用，独立导入导出页面尚未启用
- 对外开放前必须设置强 Web Token，并只在可信网络中使用

## 说明

本项目仅用于个人 Telegram 数据管理与浏览。
