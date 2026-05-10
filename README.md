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

默认访问：

```bash
http://127.0.0.1:5000
```

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
├── data/
├── Download/
└── Pictures/
```

## 注意

- 需要有效的 Telegram API ID / Hash
- 首次登录需要验证码
- 使用代理时请确保 SOCKS5 可用
- 媒体缓存会按上限自动清理

## 说明

本项目仅用于个人 Telegram 数据管理与浏览。
