# 消息机制使用指南

## 快速开始

### 1. 启用消息模式

编辑 `config/message_config.json`，将 `enabled` 设置为 `true`：

```json
{
    "enabled": true,
    "message_engine": {
        "type": "memory"
    }
}
```

或者通过环境变量启用：

```bash
export MESSAGE_MODE_ENABLED=true
```

### 2. 选择消息引擎

#### 内存引擎（默认，用于开发测试）

```json
{
    "message_engine": {
        "type": "memory"
    }
}
```

#### MQTT引擎（生产环境推荐）

```json
{
    "message_engine": {
        "type": "mqtt",
        "mqtt": {
            "host": "localhost",
            "port": 1883,
            "client_id": "tradingagents"
        }
    }
}
```

#### Redis Pub/Sub引擎

```json
{
    "message_engine": {
        "type": "redis",
        "redis": {
            "host": "localhost",
            "port": 6379,
            "db": 0
        }
    }
}
```

### 3. 使用消息装饰器

在分析节点中使用消息装饰器替代日志装饰器：

```python
from tradingagents.messaging.decorators import message_analysis_module

@message_analysis_module("market_analyst")
def market_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    # 分析逻辑
    pass
```

**注意**：如果消息模式未启用，装饰器会自动回退到日志模式，保持向后兼容。

## 兼容性说明

### 双模式运行

系统支持双模式运行：
- **消息模式**：当 `MESSAGE_MODE_ENABLED=true` 时，使用消息机制
- **日志模式**：当消息模式未启用时，使用日志关键字识别（原有方式）

### 迁移策略

1. **第一阶段**：保持消息模式关闭，所有代码继续使用日志模式
2. **第二阶段**：在测试环境启用消息模式，验证功能正常
3. **第三阶段**：逐步将装饰器替换为消息装饰器
4. **第四阶段**：生产环境启用消息模式

## 消息类型

### 任务进度消息 (TASK_PROGRESS)

包含任务的当前进度信息：
- `analysis_id`: 分析ID
- `current_step`: 当前步骤
- `total_steps`: 总步骤数
- `progress_percentage`: 进度百分比
- `current_step_name`: 当前步骤名称
- `current_step_description`: 当前步骤描述
- `elapsed_time`: 已用时间
- `remaining_time`: 剩余时间
- `last_message`: 最后一条消息

### 任务状态消息 (TASK_STATUS)

包含任务状态变更：
- `analysis_id`: 分析ID
- `status`: 状态（running/paused/completed/failed/stopped）
- `message`: 状态消息
- `timestamp`: 时间戳

### 模块事件消息 (MODULE_START/COMPLETE/ERROR)

包含模块执行事件：
- `analysis_id`: 分析ID
- `module_name`: 模块名称
- `event`: 事件类型（start/complete/error）
- `stock_symbol`: 股票代码（可选）
- `duration`: 执行时长（complete事件）
- `error_message`: 错误消息（error事件）

## 性能优化

### 消息批量处理

对于高频消息，可以考虑批量处理：

```python
# 批量发送进度更新
progress_handler.get_producer().publish_progress(...)
```

### 消息确认机制

MQTT和Redis都支持消息确认，确保消息不会丢失：
- MQTT: QoS=1（至少一次传递）
- Redis: Pub/Sub（尽力传递）

## 故障排查

### 消息未收到

1. 检查消息模式是否启用
2. 检查消息引擎连接状态
3. 检查主题订阅是否正确
4. 查看日志文件中的错误信息

### 消息丢失

1. 使用MQTT QoS=1或更高
2. 检查网络连接稳定性
3. 实现消息重试机制

### 性能问题

1. 使用内存引擎进行开发测试
2. 生产环境使用MQTT或Redis
3. 考虑消息批量处理

## 示例代码

### 完整示例

```python
from tradingagents.messaging.config import get_progress_handler, is_message_mode_enabled
from tradingagents.messaging.business.messages import TaskStatus

# 检查消息模式是否启用
if is_message_mode_enabled():
    # 获取进度处理器
    progress_handler = get_progress_handler()
    
    # 注册跟踪器
    progress_handler.register_tracker(analysis_id, tracker)
    
    # 发送状态消息
    producer = progress_handler.get_producer()
    producer.publish_status(analysis_id, TaskStatus.RUNNING, "任务开始")
```

## 注意事项

1. **消息格式版本化**：消息格式变更时需要保持向前兼容
2. **错误处理**：消息发送失败不应该影响主业务流程
3. **资源清理**：任务完成后记得注销跟踪器
4. **线程安全**：消息处理是线程安全的，但注意回调函数的线程安全

