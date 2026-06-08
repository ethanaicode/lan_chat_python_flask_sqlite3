# Python 版本的超简易本地局域网聊天室

## 简介

这是一个基于 Python 的简易本地局域网聊天室，使用 Flask 框架和 SQLite 数据库。它允许用户在本地网络中创建聊天室，并与其他用户进行实时聊天。

## 功能

- 创建聊天室
- 加入聊天室
- 发送消息
- 查看历史消息

## 安装

1. 确保你的 Python 环境中已经安装了 Flask 和 SQLite。
2. 克隆或下载本项目到本地。
3. 在项目根目录下运行 `pip install -r requirements.txt` 安装依赖。

## 使用

启动服务：

```bash
python app.py
```

默认监听 `0.0.0.0:8902`，局域网设备可访问。

## 超级管理员能力（无账号系统）

后端已内置超级管理员判断：

- 来自服务器本机的请求（例如 `127.0.0.1`、`::1`、或本机网卡地址）会被视为超级管理员。
- 也可配置共享令牌 `ADMIN_TOKEN`，用于远程管理员调用。

设置令牌示例：

```bash
export ADMIN_TOKEN='your-strong-token'
python app.py
```

### 管理接口：清空聊天记录

`POST /api/admin/purge`

- 清空全部消息：请求体 `{}`
- 仅清空某个房间：请求体 `{"room":"general"}`

调用示例：

```bash
curl -X POST http://127.0.0.1:8902/api/admin/purge \
	-H 'Content-Type: application/json' \
	-d '{}'
```

远程调用（带令牌）：

```bash
curl -X POST http://<server-ip>:8902/api/admin/purge \
	-H 'Content-Type: application/json' \
	-H 'X-Admin-Token: your-strong-token' \
	-d '{}'
```

前端页面已增加管理员按钮（标题同一行，左标题右按钮）：

- `删当前房间`：删除当前房间消息
- `删全部`：删除所有房间消息

按钮显示规则：

- 前端会请求 `GET /api/admin/status`。
- `is_admin=true` 时显示管理按钮；否则隐藏。