# NanoBot Web 界面

这是一个简单的 Web 界面，用于与 NanoBot AI 助手进行交互。

## 功能特性

- ✅ 左侧会话列表：显示所有历史会话
- ✅ 新建会话：一键创建新的对话
- ✅ 消息发送：支持文本输入和发送
- ✅ 会话管理：查看、删除会话
- ✅ 实时响应：流畅的聊天体验

## 快速开始

### 1. 启动 NanoBot 服务器

```bash
cd /Users/lianghaoyun/project/nanobot
python -m nanobot.server.app
```

服务器将在 `http://localhost:5088` 启动

### 2. 访问 Web 界面

在浏览器中打开：
```
http://localhost:5088
```

或者直接打开 `frontend/index.html` 文件

### 3. 开始使用

- 点击左上角的 **"+ 新建会话"** 按钮创建新对话
- 在输入框中输入消息，按 Enter 发送
- 左侧会话列表可以查看和切换历史会话
- 点击会话右侧的删除图标可以删除会话

## 技术栈

- 纯 HTML + CSS + JavaScript
- 无需任何构建工具或依赖
- 响应式设计，支持现代浏览器

## API 端点

Web 界面使用以下 API：

- `GET /api/sessions` - 获取会话列表
- `GET /api/sessions/<session_id>` - 获取会话历史
- `DELETE /api/sessions/<session_id>` - 删除会话
- `POST /api/agent/chat` - 发送消息

## 注意事项

1. 确保 NanoBot 服务器正在运行
2. 确保 API 端口 5088 未被占用
3. 如果遇到跨域问题，请使用服务器提供的 Web 界面

## 自定义配置

如果需要修改 API 地址，编辑 `frontend/index.html` 中的：

```javascript
const API_BASE = 'http://localhost:5088/api';
```

修改为您的实际 API 地址。
