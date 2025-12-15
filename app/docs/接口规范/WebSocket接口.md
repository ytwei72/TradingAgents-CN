# WebSocket接口

## 7.1 实时通知连接

**状态**: ✅ 已完成

建立 WebSocket 连接以接收实时通知（如分析进度、系统消息）。

#### 请求

```http
WS /ws/notifications
```

#### 交互流程

1. **连接建立**: 客户端连接到 `/ws/notifications`
2. **心跳检测**: 客户端定期发送 `ping`，服务器回复 `pong`
3. **消息接收**: 服务器主动推送 JSON 格式的通知消息

#### 消息格式

**通知消息**:
```json
{
  "topic": "task/progress",
  "payload": {
    "analysis_id": "a1b2c3d4...",
    "progress_percentage": 45.5,
    "current_step": 3,
    "current_step_name": "市场分析",
    "message": "正在分析市场趋势..."
  },
  "timestamp": "2025-12-02T14:30:00"
}
```

#### 示例代码 (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/notifications');

ws.onopen = () => {
    console.log('Connected');
    // 发送心跳
    setInterval(() => ws.send('ping'), 30000);
};

ws.onmessage = (event) => {
    if (event.data === 'pong') return;
    
    const notification = JSON.parse(event.data);
    console.log('Received:', notification);
};
```

