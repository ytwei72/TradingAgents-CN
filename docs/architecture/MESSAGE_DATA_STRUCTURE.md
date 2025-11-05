# 消息机制数据结构说明

## 概述

消息机制使用结构化消息传递，所有消息都遵循统一的数据结构。本文档详细描述了各种消息类型的数据结构。

## 消息包装结构

所有消息在传输时都会被包装在统一的消息容器中：

```json
{
    "type": "消息类型枚举值",
    "timestamp": 1234567890.123,
    "payload": {
        // 具体消息数据
    }
}
```

### 包装字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `type` | `string` | 消息类型，使用 `MessageType` 枚举值 | `"task.progress"` |
| `timestamp` | `float` | 消息时间戳（Unix时间戳，秒） | `1704067200.123` |
| `payload` | `object` | 消息负载，包含具体的业务数据 | 见下方各消息类型说明 |

## 消息类型枚举

### MessageType

```python
class MessageType(Enum):
    TASK_PROGRESS = "task.progress"      # 任务进度消息
    TASK_STATUS = "task.status"         # 任务状态消息
    MODULE_START = "module.start"        # 模块开始消息
    MODULE_COMPLETE = "module.complete"  # 模块完成消息
    MODULE_ERROR = "module.error"        # 模块错误消息
    STEP_UPDATE = "step.update"          # 步骤更新消息（预留）
```

## 1. 任务进度消息 (TASK_PROGRESS)

### 消息类型
`task.progress`

### 主题格式
```
task/progress/{analysis_id}
```

### Payload 结构

```json
{
    "analysis_id": "string",
    "current_step": 0,
    "total_steps": 12,
    "progress_percentage": 45.5,
    "current_step_name": "📈 市场分析师",
    "current_step_description": "技术面分析：K线形态、均线系统、价格趋势...",
    "elapsed_time": 120.5,
    "remaining_time": 150.0,
    "last_message": "正在获取市场数据..."
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `analysis_id` | `string` | 是 | 分析任务ID，唯一标识一个分析任务 | `"analysis_20250101_001"` |
| `current_step` | `integer` | 是 | 当前步骤索引（从0开始） | `5` |
| `total_steps` | `integer` | 是 | 总步骤数 | `12` |
| `progress_percentage` | `float` | 是 | 进度百分比（0.0-100.0） | `45.5` |
| `current_step_name` | `string` | 是 | 当前步骤名称（带emoji） | `"📈 市场分析师"` |
| `current_step_description` | `string` | 是 | 当前步骤描述 | `"技术面分析：K线形态..."` |
| `elapsed_time` | `float` | 是 | 已用时间（秒，排除暂停时间） | `120.5` |
| `remaining_time` | `float` | 是 | 预估剩余时间（秒） | `150.0` |
| `last_message` | `string` | 是 | 最后一条消息 | `"正在获取市场数据..."` |

### 数据类定义

```python
@dataclass
class TaskProgressMessage:
    analysis_id: str
    current_step: int
    total_steps: int
    progress_percentage: float
    current_step_name: str
    current_step_description: str
    elapsed_time: float
    remaining_time: float
    last_message: str
```

### 示例

```json
{
    "type": "task.progress",
    "timestamp": 1704067200.123,
    "payload": {
        "analysis_id": "analysis_20250101_001",
        "current_step": 5,
        "total_steps": 12,
        "progress_percentage": 45.5,
        "current_step_name": "📈 市场分析师",
        "current_step_description": "技术面分析：K线形态、均线系统、价格趋势",
        "elapsed_time": 120.5,
        "remaining_time": 150.0,
        "last_message": "正在获取市场数据..."
    }
}
```

## 2. 任务状态消息 (TASK_STATUS)

### 消息类型
`task.status`

### 主题格式
```
task/status/{analysis_id}
```

### Payload 结构

```json
{
    "analysis_id": "string",
    "status": "running",
    "message": "任务已开始",
    "timestamp": 1704067200.123
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `analysis_id` | `string` | 是 | 分析任务ID | `"analysis_20250101_001"` |
| `status` | `string` | 是 | 任务状态枚举值 | `"running"` |
| `message` | `string` | 是 | 状态消息描述 | `"任务已开始"` |
| `timestamp` | `float` | 是 | 状态变更时间戳 | `1704067200.123` |

### 任务状态枚举 (TaskStatus)

| 值 | 说明 | 使用场景 |
|----|------|----------|
| `pending` | 待处理 | 任务已创建但未开始 |
| `running` | 运行中 | 任务正在执行 |
| `paused` | 已暂停 | 任务被暂停 |
| `completed` | 已完成 | 任务成功完成 |
| `failed` | 失败 | 任务执行失败 |
| `stopped` | 已停止 | 任务被手动停止 |

### 数据类定义

```python
@dataclass
class TaskStatusMessage:
    analysis_id: str
    status: TaskStatus
    message: str
    timestamp: float
```

### 示例

```json
{
    "type": "task.status",
    "timestamp": 1704067200.123,
    "payload": {
        "analysis_id": "analysis_20250101_001",
        "status": "completed",
        "message": "分析完成",
        "timestamp": 1704067200.123
    }
}
```

## 3. 模块开始消息 (MODULE_START)

### 消息类型
`module.start`

### 主题格式
```
module/start/{analysis_id}
```

### Payload 结构

```json
{
    "analysis_id": "string",
    "module_name": "market_analyst",
    "stock_symbol": "AAPL",
    "event": "start",
    "function_name": "market_analysis",
    "args_count": 1,
    "kwargs_keys": ["state"]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `analysis_id` | `string` | 是 | 分析任务ID | `"analysis_20250101_001"` |
| `module_name` | `string` | 是 | 模块名称 | `"market_analyst"` |
| `stock_symbol` | `string` | 否 | 股票代码 | `"AAPL"` |
| `event` | `string` | 是 | 事件类型，固定为 `"start"` | `"start"` |
| `function_name` | `string` | 否 | 函数名称（额外数据） | `"market_analysis"` |
| `args_count` | `integer` | 否 | 参数数量（额外数据） | `1` |
| `kwargs_keys` | `array` | 否 | 关键字参数列表（额外数据） | `["state"]` |

### 模块名称列表

| 模块名称 | 说明 |
|----------|------|
| `market_analyst` | 市场分析师 |
| `fundamentals_analyst` | 基本面分析师 |
| `technical_analyst` | 技术分析师 |
| `sentiment_analyst` | 情绪分析师 |
| `news_analyst` | 新闻分析师 |
| `social_media_analyst` | 社交媒体分析师 |
| `risk_analyst` | 风险分析师 |
| `bull_researcher` | 看涨研究员 |
| `bear_researcher` | 看跌研究员 |
| `research_manager` | 研究经理 |
| `trader` | 交易员 |
| `risky_analyst` | 激进风险分析师 |
| `safe_analyst` | 保守风险分析师 |
| `neutral_analyst` | 中性风险分析师 |
| `risk_manager` | 风险经理 |
| `graph_signal_processing` | 信号处理 |

### 示例

```json
{
    "type": "module.start",
    "timestamp": 1704067200.123,
    "payload": {
        "analysis_id": "analysis_20250101_001",
        "module_name": "market_analyst",
        "stock_symbol": "AAPL",
        "event": "start",
        "function_name": "market_analysis",
        "args_count": 1,
        "kwargs_keys": ["state"]
    }
}
```

## 4. 模块完成消息 (MODULE_COMPLETE)

### 消息类型
`module.complete`

### 主题格式
```
module/complete/{analysis_id}
```

### Payload 结构

```json
{
    "analysis_id": "string",
    "module_name": "market_analyst",
    "stock_symbol": "AAPL",
    "event": "complete",
    "duration": 5.23,
    "function_name": "market_analysis",
    "result_length": 1024
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `analysis_id` | `string` | 是 | 分析任务ID | `"analysis_20250101_001"` |
| `module_name` | `string` | 是 | 模块名称 | `"market_analyst"` |
| `stock_symbol` | `string` | 否 | 股票代码 | `"AAPL"` |
| `event` | `string` | 是 | 事件类型，固定为 `"complete"` | `"complete"` |
| `duration` | `float` | 是 | 执行时长（秒） | `5.23` |
| `function_name` | `string` | 否 | 函数名称（额外数据） | `"market_analysis"` |
| `result_length` | `integer` | 否 | 结果长度（额外数据） | `1024` |

### 示例

```json
{
    "type": "module.complete",
    "timestamp": 1704067205.456,
    "payload": {
        "analysis_id": "analysis_20250101_001",
        "module_name": "market_analyst",
        "stock_symbol": "AAPL",
        "event": "complete",
        "duration": 5.23,
        "function_name": "market_analysis",
        "result_length": 1024
    }
}
```

## 5. 模块错误消息 (MODULE_ERROR)

### 消息类型
`module.error`

### 主题格式
```
module/error/{analysis_id}
```

### Payload 结构

```json
{
    "analysis_id": "string",
    "module_name": "market_analyst",
    "stock_symbol": "AAPL",
    "event": "error",
    "error_message": "数据获取失败: Connection timeout"
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `analysis_id` | `string` | 是 | 分析任务ID | `"analysis_20250101_001"` |
| `module_name` | `string` | 是 | 模块名称 | `"market_analyst"` |
| `stock_symbol` | `string` | 否 | 股票代码 | `"AAPL"` |
| `event` | `string` | 是 | 事件类型，固定为 `"error"` | `"error"` |
| `error_message` | `string` | 是 | 错误消息 | `"数据获取失败: Connection timeout"` |

### 示例

```json
{
    "type": "module.error",
    "timestamp": 1704067205.456,
    "payload": {
        "analysis_id": "analysis_20250101_001",
        "module_name": "market_analyst",
        "stock_symbol": "AAPL",
        "event": "error",
        "error_message": "数据获取失败: Connection timeout"
    }
}
```

## 模块事件枚举 (ModuleEvent)

```python
class ModuleEvent(Enum):
    START = "start"      # 模块开始
    COMPLETE = "complete"  # 模块完成
    ERROR = "error"      # 模块错误
```

## 消息流转示例

### 完整的分析任务消息流

```
1. 模块开始
   ↓
   MODULE_START: market_analyst
   
2. 模块执行中
   ↓
   TASK_PROGRESS: progress_percentage = 10%
   TASK_PROGRESS: progress_percentage = 15%
   ...
   
3. 模块完成
   ↓
   MODULE_COMPLETE: market_analyst, duration = 5.23s
   
4. 下一个模块开始
   ↓
   MODULE_START: fundamentals_analyst
   ...
   
5. 任务完成
   ↓
   TASK_STATUS: status = "completed"
```

## 消息序列化

所有消息在传输前会被序列化为JSON格式：

```python
import json

# 序列化
message_json = json.dumps(message, ensure_ascii=False)

# 反序列化
message = json.loads(message_json)
```

## 主题命名规范

### 主题格式

```
{message_type}/{analysis_id}
```

其中 `message_type` 使用点号分隔，转换为斜杠分隔：
- `task.progress` → `task/progress`
- `module.start` → `module/start`

### 示例主题

```
task/progress/analysis_20250101_001
task/status/analysis_20250101_001
module/start/analysis_20250101_001
module/complete/analysis_20250101_001
module/error/analysis_20250101_001
```

## 数据验证

### 必填字段验证

所有消息类型都有必填字段，缺失必填字段会导致消息发送失败。

### 类型验证

- `analysis_id`: 必须是字符串
- `current_step`, `total_steps`: 必须是整数，且 `current_step >= 0`, `total_steps > 0`
- `progress_percentage`: 必须是浮点数，范围 `0.0-100.0`
- `duration`, `elapsed_time`, `remaining_time`: 必须是浮点数，单位：秒
- `timestamp`: 必须是浮点数，Unix时间戳

## 扩展性

### 添加新消息类型

1. 在 `MessageType` 枚举中添加新类型
2. 定义新的数据类（可选）
3. 在 `TaskMessageProducer` 中添加发布方法
4. 在 `TaskMessageConsumer` 中添加处理逻辑

### 添加额外字段

可以通过 `**extra` 参数传递额外字段，这些字段会被包含在消息的 `payload` 中。

## 总结

消息机制使用统一的数据结构，包含：
- **消息包装**：`type` + `timestamp` + `payload`
- **业务数据**：根据消息类型的不同，`payload` 包含不同的字段
- **类型安全**：使用 dataclass 和枚举确保类型安全
- **易于扩展**：支持额外字段和新的消息类型

所有消息都遵循这个结构，确保系统的一致性和可维护性。

