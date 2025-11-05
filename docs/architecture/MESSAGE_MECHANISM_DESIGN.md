# TradingAgents 消息机制设计方案

## 1. 概述

### 1.1 背景

当前 TradingAgents 项目使用日志输出和关键字识别来更新任务状态，存在以下问题：

- **耦合度高**：状态更新依赖日志格式，格式变化会导致状态检测失效
- **不易扩展**：添加新步骤需要修改大量关键字匹配逻辑
- **性能问题**：需要解析字符串并匹配大量关键字，效率低
- **维护困难**：关键字匹配逻辑复杂，容易出错，难以调试

### 1.2 目标

设计一个基于消息机制的架构，实现：

- ✅ **解耦**：状态更新与日志系统解耦，通过结构化消息传递
- ✅ **可扩展**：支持新业务类型消息，无需修改核心逻辑
- ✅ **高性能**：直接传递结构化数据，无需字符串解析
- ✅ **易维护**：清晰的接口定义和消息规范
- ✅ **可切换**：支持多种消息引擎（MQTT、Redis Pub/Sub、RabbitMQ等）

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        应用层 (Application Layer)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ 分析节点      │  │ 任务管理器    │  │ 进度跟踪器    │          │
│  │ (Analysts)   │  │ (TaskManager)│  │ (Tracker)    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                  │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
          ┌──────────────────▼──────────────────┐
          │     消息业务层 (Business Layer)       │
          │  ┌────────────────────────────────┐  │
          │  │  TaskMessageProducer           │  │
          │  │  TaskMessageConsumer           │  │
          │  │  ProgressMessageHandler        │  │
          │  └────────────────────────────────┘  │
          └──────────────────┬───────────────────┘
                             │
          ┌──────────────────▼───────────────────┐
          │     消息处理层 (Handler Layer)        │
          │  ┌────────────────────────────────┐  │
          │  │  MessageHandler                │  │
          │  │  - publish()                    │  │
          │  │  - subscribe()                 │  │
          │  │  - register_handler()          │  │
          │  └────────────────────────────────┘  │
          └──────────────────┬───────────────────┘
                             │
          ┌──────────────────▼───────────────────┐
          │     消息引擎层 (Engine Layer)        │
          │  ┌──────────┐  ┌──────────┐        │
          │  │ MQTT     │  │ Redis    │        │
          │  │ Adapter  │  │ Pub/Sub  │        │
          │  └──────────┘  └──────────┘        │
          │  ┌──────────┐  ┌──────────┐        │
          │  │ RabbitMQ │  │ Memory   │        │
          │  │ Adapter  │  │ Adapter  │        │
          │  └──────────┘  └──────────┘        │
          └─────────────────────────────────────┘
```

### 2.2 层次说明

#### 2.2.1 消息引擎层 (Engine Layer)

**职责**：提供底层消息传输能力，支持多种消息中间件

**设计原则**：
- 抽象接口，支持多种实现
- 统一的消息格式
- 自动重连和错误处理
- 配置驱动，易于切换

#### 2.2.2 消息处理层 (Handler Layer)

**职责**：封装消息引擎，提供统一的消息发布/订阅接口

**核心类**：`MessageHandler`

**功能**：
- 消息发布（publish）
- 消息订阅（subscribe）
- 消息路由
- 消息序列化/反序列化
- 错误处理和重试

#### 2.2.3 消息业务层 (Business Layer)

**职责**：定义业务相关的消息类型和处理逻辑

**核心类**：
- `TaskMessageProducer`：任务消息生产者
- `TaskMessageConsumer`：任务消息消费者
- `ProgressMessageHandler`：进度消息处理器

**功能**：
- 定义业务消息格式
- 消息的生产和消费
- 业务逻辑处理
- 与现有系统集成

#### 2.2.4 应用层 (Application Layer)

**职责**：使用消息机制的业务模块

**包含模块**：
- 分析节点（Analysts）
- 任务管理器（TaskManager）
- 进度跟踪器（ProgressTracker）
- Web界面

## 3. 核心组件设计

### 3.1 消息引擎接口

```python
from abc import ABC, abstractmethod
from typing import Callable, Optional, Dict, Any

class MessageEngine(ABC):
    """消息引擎抽象基类"""
    
    @abstractmethod
    def connect(self) -> bool:
        """连接消息服务器"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass
    
    @abstractmethod
    def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """发布消息"""
        pass
    
    @abstractmethod
    def subscribe(self, topic: str, callback: Callable) -> bool:
        """订阅消息"""
        pass
    
    @abstractmethod
    def unsubscribe(self, topic: str) -> bool:
        """取消订阅"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """检查连接状态"""
        pass
```

### 3.2 MQTT 引擎实现

```python
import paho.mqtt.client as mqtt
from typing import Dict, Any, Callable

class MQTTEngine(MessageEngine):
    """MQTT 消息引擎实现"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = None
        self.callbacks: Dict[str, Callable] = {}
        
    def connect(self) -> bool:
        """连接MQTT服务器"""
        try:
            self.client = mqtt.Client(
                client_id=self.config.get('client_id', 'tradingagents'),
                clean_session=self.config.get('clean_session', True)
            )
            
            if self.config.get('username'):
                self.client.username_pw_set(
                    self.config['username'],
                    self.config.get('password')
                )
            
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect
            
            self.client.connect(
                self.config['host'],
                self.config.get('port', 1883),
                self.config.get('keepalive', 60)
            )
            
            self.client.loop_start()
            return True
        except Exception as e:
            logger.error(f"MQTT连接失败: {e}")
            return False
    
    def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """发布消息"""
        import json
        payload = json.dumps(message, ensure_ascii=False)
        result = self.client.publish(topic, payload, qos=1)
        return result.rc == mqtt.MQTT_ERR_SUCCESS
    
    def subscribe(self, topic: str, callback: Callable) -> bool:
        """订阅主题"""
        self.callbacks[topic] = callback
        result = self.client.subscribe(topic, qos=1)
        return result[0] == mqtt.MQTT_ERR_SUCCESS
    
    # ... 其他方法实现
```

### 3.3 Redis Pub/Sub 引擎实现

```python
import redis
import json
from typing import Dict, Any, Callable
import threading

class RedisPubSubEngine(MessageEngine):
    """Redis Pub/Sub 消息引擎实现"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = None
        self.pubsub = None
        self.callbacks: Dict[str, Callable] = {}
        self.subscribe_thread = None
        self.running = False
    
    def connect(self) -> bool:
        """连接Redis服务器"""
        try:
            self.client = redis.Redis(
                host=self.config.get('host', 'localhost'),
                port=self.config.get('port', 6379),
                password=self.config.get('password'),
                db=self.config.get('db', 0),
                decode_responses=True
            )
            self.client.ping()
            self.pubsub = self.client.pubsub()
            self.running = True
            return True
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            return False
    
    def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """发布消息"""
        payload = json.dumps(message, ensure_ascii=False)
        self.client.publish(topic, payload)
        return True
    
    def subscribe(self, topic: str, callback: Callable) -> bool:
        """订阅主题"""
        self.callbacks[topic] = callback
        self.pubsub.subscribe(topic)
        
        if not self.subscribe_thread or not self.subscribe_thread.is_alive():
            self.subscribe_thread = threading.Thread(
                target=self._message_loop,
                daemon=True
            )
            self.subscribe_thread.start()
        
        return True
    
    def _message_loop(self):
        """消息循环"""
        while self.running:
            try:
                message = self.pubsub.get_message(timeout=1.0)
                if message and message['type'] == 'message':
                    topic = message['channel']
                    data = json.loads(message['data'])
                    if topic in self.callbacks:
                        self.callbacks[topic](topic, data)
            except Exception as e:
                logger.error(f"消息处理错误: {e}")
```

### 3.4 内存引擎实现（用于测试和开发）

```python
from typing import Dict, Any, Callable
from collections import defaultdict
import threading

class MemoryEngine(MessageEngine):
    """内存消息引擎实现（用于测试和开发）"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.subscribers: Dict[str, list] = defaultdict(list)
        self.lock = threading.Lock()
        self.connected = False
    
    def connect(self) -> bool:
        """连接（内存模式无需真实连接）"""
        self.connected = True
        return True
    
    def publish(self, topic: str, message: Dict[str, Any]) -> bool:
        """发布消息"""
        with self.lock:
            for callback in self.subscribers.get(topic, []):
                try:
                    callback(topic, message)
                except Exception as e:
                    logger.error(f"回调执行错误: {e}")
        return True
    
    def subscribe(self, topic: str, callback: Callable) -> bool:
        """订阅主题"""
        with self.lock:
            self.subscribers[topic].append(callback)
        return True
```

### 3.5 消息处理器

```python
from typing import Dict, Any, Callable, Optional
from enum import Enum

class MessageType(Enum):
    """消息类型枚举"""
    TASK_PROGRESS = "task.progress"
    TASK_STATUS = "task.status"
    MODULE_START = "module.start"
    MODULE_COMPLETE = "module.complete"
    MODULE_ERROR = "module.error"
    STEP_UPDATE = "step.update"

class MessageHandler:
    """消息处理器 - 统一的消息发布/订阅接口"""
    
    def __init__(self, engine: MessageEngine):
        self.engine = engine
        self.handlers: Dict[str, list] = {}
    
    def initialize(self) -> bool:
        """初始化消息处理器"""
        return self.engine.connect()
    
    def publish(self, message_type: MessageType, payload: Dict[str, Any]) -> bool:
        """发布消息"""
        topic = self._get_topic(message_type, payload)
        message = {
            'type': message_type.value,
            'timestamp': time.time(),
            'payload': payload
        }
        return self.engine.publish(topic, message)
    
    def subscribe(self, message_type: MessageType, 
                  handler: Callable[[Dict[str, Any]], None],
                  topic_filter: Optional[str] = None) -> bool:
        """订阅消息"""
        topic = self._get_topic(message_type, {'*': '*'}) if not topic_filter else topic_filter
        
        def callback(topic_received: str, message: Dict[str, Any]):
            # 验证消息类型
            if message.get('type') == message_type.value:
                try:
                    handler(message['payload'])
                except Exception as e:
                    logger.error(f"消息处理错误: {e}")
        
        return self.engine.subscribe(topic, callback)
    
    def _get_topic(self, message_type: MessageType, payload: Dict[str, Any]) -> str:
        """生成主题名称"""
        # 根据消息类型和负载生成主题
        # 例如: task/progress/{analysis_id}
        if 'analysis_id' in payload:
            return f"{message_type.value.replace('.', '/')}/{payload['analysis_id']}"
        return message_type.value.replace('.', '/')
```

## 4. 业务层设计

### 4.1 消息数据结构说明

#### 4.1.1 消息包装结构

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

**包装字段说明**：

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `type` | `string` | 消息类型，使用 `MessageType` 枚举值 | `"task.progress"` |
| `timestamp` | `float` | 消息时间戳（Unix时间戳，秒） | `1704067200.123` |
| `payload` | `object` | 消息负载，包含具体的业务数据 | 见下方各消息类型说明 |

#### 4.1.2 消息类型枚举

```python
class MessageType(Enum):
    TASK_PROGRESS = "task.progress"      # 任务进度消息
    TASK_STATUS = "task.status"         # 任务状态消息
    MODULE_START = "module.start"        # 模块开始消息
    MODULE_COMPLETE = "module.complete"  # 模块完成消息
    MODULE_ERROR = "module.error"        # 模块错误消息
    STEP_UPDATE = "step.update"          # 步骤更新消息（预留）
```

#### 4.1.3 主题命名规范

消息主题格式：`{message_type}/{analysis_id}`

其中 `message_type` 使用点号分隔，转换为斜杠分隔：
- `task.progress` → `task/progress`
- `module.start` → `module/start`

示例主题：
- `task/progress/analysis_20250101_001`
- `task/status/analysis_20250101_001`
- `module/start/analysis_20250101_001`
- `module/complete/analysis_20250101_001`
- `module/error/analysis_20250101_001`

### 4.2 任务消息格式

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

class ModuleEvent(Enum):
    """模块事件类型"""
    START = "start"
    COMPLETE = "complete"
    ERROR = "error"

@dataclass
class TaskProgressMessage:
    """任务进度消息"""
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

**完整消息示例**：

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

**字段详细说明**：

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

@dataclass
class TaskStatusMessage:
    """任务状态消息"""
    analysis_id: str
    status: TaskStatus
    message: str
    timestamp: float
```

**完整消息示例**：

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

**字段详细说明**：

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `analysis_id` | `string` | 是 | 分析任务ID | `"analysis_20250101_001"` |
| `status` | `string` | 是 | 任务状态枚举值 | `"running"` |
| `message` | `string` | 是 | 状态消息描述 | `"任务已开始"` |
| `timestamp` | `float` | 是 | 状态变更时间戳 | `1704067200.123` |

**任务状态枚举值说明**：

| 值 | 说明 | 使用场景 |
|----|------|----------|
| `pending` | 待处理 | 任务已创建但未开始 |
| `running` | 运行中 | 任务正在执行 |
| `paused` | 已暂停 | 任务被暂停 |
| `completed` | 已完成 | 任务成功完成 |
| `failed` | 失败 | 任务执行失败 |
| `stopped` | 已停止 | 任务被手动停止 |

@dataclass
class ModuleEventMessage:
    """模块事件消息"""
    analysis_id: str
    module_name: str
    event: ModuleEvent
    stock_symbol: Optional[str] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
```

**模块开始消息示例 (MODULE_START)**：

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

**模块完成消息示例 (MODULE_COMPLETE)**：

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

**模块错误消息示例 (MODULE_ERROR)**：

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

**模块名称列表**：

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

**模块事件消息字段说明**：

| 字段 | 类型 | 必填 | 说明 | 适用事件 |
|------|------|------|------|----------|
| `analysis_id` | `string` | 是 | 分析任务ID | 所有 |
| `module_name` | `string` | 是 | 模块名称 | 所有 |
| `stock_symbol` | `string` | 否 | 股票代码 | 所有 |
| `event` | `string` | 是 | 事件类型（start/complete/error） | 所有 |
| `duration` | `float` | 是 | 执行时长（秒） | complete |
| `error_message` | `string` | 是 | 错误消息 | error |
| `function_name` | `string` | 否 | 函数名称（额外数据） | start/complete |
| `result_length` | `integer` | 否 | 结果长度（额外数据） | complete |

**消息流转示例**：

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

### 4.2 任务消息生产者

```python
class TaskMessageProducer:
    """任务消息生产者"""
    
    def __init__(self, message_handler: MessageHandler):
        self.handler = message_handler
    
    def publish_progress(self, progress_data: TaskProgressMessage):
        """发布进度消息"""
        payload = {
            'analysis_id': progress_data.analysis_id,
            'current_step': progress_data.current_step,
            'total_steps': progress_data.total_steps,
            'progress_percentage': progress_data.progress_percentage,
            'current_step_name': progress_data.current_step_name,
            'current_step_description': progress_data.current_step_description,
            'elapsed_time': progress_data.elapsed_time,
            'remaining_time': progress_data.remaining_time,
            'last_message': progress_data.last_message
        }
        self.handler.publish(MessageType.TASK_PROGRESS, payload)
    
    def publish_status(self, analysis_id: str, status: TaskStatus, message: str):
        """发布状态消息"""
        payload = {
            'analysis_id': analysis_id,
            'status': status.value,
            'message': message,
            'timestamp': time.time()
        }
        self.handler.publish(MessageType.TASK_STATUS, payload)
    
    def publish_module_start(self, analysis_id: str, module_name: str, 
                            stock_symbol: Optional[str] = None, **extra):
        """发布模块开始消息"""
        payload = {
            'analysis_id': analysis_id,
            'module_name': module_name,
            'stock_symbol': stock_symbol,
            'event': ModuleEvent.START.value,
            **extra
        }
        self.handler.publish(MessageType.MODULE_START, payload)
    
    def publish_module_complete(self, analysis_id: str, module_name: str,
                               duration: float, stock_symbol: Optional[str] = None,
                               **extra):
        """发布模块完成消息"""
        payload = {
            'analysis_id': analysis_id,
            'module_name': module_name,
            'stock_symbol': stock_symbol,
            'event': ModuleEvent.COMPLETE.value,
            'duration': duration,
            **extra
        }
        self.handler.publish(MessageType.MODULE_COMPLETE, payload)
    
    def publish_module_error(self, analysis_id: str, module_name: str,
                            error_message: str, stock_symbol: Optional[str] = None):
        """发布模块错误消息"""
        payload = {
            'analysis_id': analysis_id,
            'module_name': module_name,
            'stock_symbol': stock_symbol,
            'event': ModuleEvent.ERROR.value,
            'error_message': error_message
        }
        self.handler.publish(MessageType.MODULE_ERROR, payload)
```

### 4.3 任务消息消费者

```python
class TaskMessageConsumer:
    """任务消息消费者"""
    
    def __init__(self, message_handler: MessageHandler):
        self.handler = message_handler
        self.progress_trackers: Dict[str, 'AsyncProgressTracker'] = {}
    
    def register_tracker(self, analysis_id: str, tracker: 'AsyncProgressTracker'):
        """注册进度跟踪器"""
        self.progress_trackers[analysis_id] = tracker
        
        # 订阅该分析ID的所有消息
        self._subscribe_to_analysis(analysis_id)
    
    def unregister_tracker(self, analysis_id: str):
        """注销进度跟踪器"""
        if analysis_id in self.progress_trackers:
            del self.progress_trackers[analysis_id]
    
    def _subscribe_to_analysis(self, analysis_id: str):
        """订阅分析相关的消息"""
        # 订阅进度消息
        self.handler.subscribe(
            MessageType.TASK_PROGRESS,
            lambda payload: self._handle_progress(analysis_id, payload),
            topic_filter=f"task/progress/{analysis_id}"
        )
        
        # 订阅模块事件消息
        for msg_type in [MessageType.MODULE_START, MessageType.MODULE_COMPLETE, 
                        MessageType.MODULE_ERROR]:
            self.handler.subscribe(
                msg_type,
                lambda payload, mt=msg_type: self._handle_module_event(
                    analysis_id, mt, payload
                ),
                topic_filter=f"{mt.value.replace('.', '/')}/{analysis_id}"
            )
    
    def _handle_progress(self, analysis_id: str, payload: Dict[str, Any]):
        """处理进度消息"""
        if analysis_id in self.progress_trackers:
            tracker = self.progress_trackers[analysis_id]
            # 更新跟踪器（不再需要关键字匹配）
            tracker.update_progress_from_message(payload)
    
    def _handle_module_event(self, analysis_id: str, message_type: MessageType,
                           payload: Dict[str, Any]):
        """处理模块事件消息"""
        if analysis_id in self.progress_trackers:
            tracker = self.progress_trackers[analysis_id]
            
            if message_type == MessageType.MODULE_START:
                tracker.handle_module_start(payload)
            elif message_type == MessageType.MODULE_COMPLETE:
                tracker.handle_module_complete(payload)
            elif message_type == MessageType.MODULE_ERROR:
                tracker.handle_module_error(payload)
```

### 4.4 进度消息处理器

```python
class ProgressMessageHandler:
    """进度消息处理器 - 集成到现有的进度跟踪系统"""
    
    def __init__(self, message_handler: MessageHandler):
        self.handler = message_handler
        self.consumer = TaskMessageConsumer(message_handler)
        self.producer = TaskMessageProducer(message_handler)
    
    def initialize(self):
        """初始化处理器"""
        # 订阅全局任务消息
        self.handler.subscribe(
            MessageType.TASK_STATUS,
            self._handle_task_status
        )
    
    def register_tracker(self, analysis_id: str, tracker: 'AsyncProgressTracker'):
        """注册跟踪器"""
        self.consumer.register_tracker(analysis_id, tracker)
    
    def _handle_task_status(self, payload: Dict[str, Any]):
        """处理任务状态消息"""
        # 可以在这里添加全局状态处理逻辑
        pass
```

## 5. 集成方案

### 5.1 替换日志装饰器

**当前代码**：
```python
@log_analysis_module("market_analyst")
def market_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    # 分析逻辑
    pass
```

**新代码**：
```python
@message_analysis_module("market_analyst")
def market_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    # 分析逻辑
    pass
```

**装饰器实现**：
```python
def message_analysis_module(module_name: str):
    """消息版分析模块装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取分析ID和股票代码
            analysis_id = _extract_analysis_id(*args, **kwargs)
            stock_symbol = _extract_stock_symbol(*args, **kwargs)
            
            # 获取消息生产者（可以通过依赖注入或全局获取）
            producer = get_message_producer()
            
            # 发送模块开始消息
            producer.publish_module_start(
                analysis_id, module_name, stock_symbol
            )
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # 发送模块完成消息
                producer.publish_module_complete(
                    analysis_id, module_name, duration, stock_symbol
                )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                # 发送模块错误消息
                producer.publish_module_error(
                    analysis_id, module_name, str(e), stock_symbol
                )
                raise
        
        return wrapper
    return decorator
```

### 5.2 更新进度跟踪器

**修改 `AsyncProgressTracker`**：

```python
class AsyncProgressTracker:
    """异步进度跟踪器 - 支持消息机制"""
    
    def __init__(self, analysis_id: str, ...):
        # ... 现有初始化代码 ...
        
        # 获取消息生产者
        self.message_producer = get_message_producer()
    
    def update_progress_from_message(self, message: Dict[str, Any]):
        """从消息更新进度（替代关键字匹配）"""
        # 直接使用消息中的结构化数据
        self.current_step = message.get('current_step', self.current_step)
        self.progress_data.update({
            'current_step': message.get('current_step'),
            'progress_percentage': message.get('progress_percentage'),
            'current_step_name': message.get('current_step_name'),
            'current_step_description': message.get('current_step_description'),
            'elapsed_time': message.get('elapsed_time'),
            'remaining_time': message.get('remaining_time'),
            'last_message': message.get('last_message'),
        })
        self._save_progress()
    
    def handle_module_start(self, message: Dict[str, Any]):
        """处理模块开始消息"""
        module_name = message['module_name']
        step = self._find_step_by_module_name(module_name)
        if step is not None:
            self.current_step = step
            self._update_progress_data()
            self._save_progress()
            
            # 发送进度消息
            self.message_producer.publish_progress(
                TaskProgressMessage(
                    analysis_id=self.analysis_id,
                    current_step=self.current_step,
                    total_steps=len(self.analysis_steps),
                    progress_percentage=self._calculate_weighted_progress() * 100,
                    current_step_name=self.analysis_steps[self.current_step]['name'],
                    current_step_description=self.analysis_steps[self.current_step]['description'],
                    elapsed_time=self.get_effective_elapsed_time(),
                    remaining_time=self._estimate_remaining_time(...),
                    last_message=f"开始{module_name}"
                )
            )
    
    def handle_module_complete(self, message: Dict[str, Any]):
        """处理模块完成消息"""
        # 推进到下一步
        self.current_step = min(self.current_step + 1, len(self.analysis_steps) - 1)
        self._update_progress_data()
        self._save_progress()
        
        # 发送进度消息
        self.message_producer.publish_progress(...)
    
    def _find_step_by_module_name(self, module_name: str) -> Optional[int]:
        """根据模块名称查找步骤（替代关键字匹配）"""
        # 使用映射表，而不是关键字匹配
        module_step_map = {
            'market_analyst': self._find_step_by_keyword(['市场分析']),
            'fundamentals_analyst': self._find_step_by_keyword(['基本面分析']),
            'bull_researcher': self._find_step_by_keyword(['看涨研究员']),
            # ... 其他映射
        }
        return module_step_map.get(module_name)
```

### 5.3 配置管理

**新增配置文件**：`config/message_config.json`

```json
{
    "message_engine": {
        "type": "mqtt",
        "mqtt": {
            "host": "localhost",
            "port": 1883,
            "username": null,
            "password": null,
            "client_id": "tradingagents",
            "clean_session": true,
            "keepalive": 60
        },
        "redis": {
            "host": "localhost",
            "port": 6379,
            "password": null,
            "db": 0
        },
        "memory": {
            "enabled": true
        }
    },
    "topics": {
        "task_progress": "task/progress",
        "task_status": "task/status",
        "module_start": "module/start",
        "module_complete": "module/complete",
        "module_error": "module/error"
    }
}
```

**配置加载器**：
```python
class MessageConfig:
    """消息配置管理"""
    
    @staticmethod
    def load_config() -> Dict[str, Any]:
        """加载消息配置"""
        config_path = Path("config/message_config.json")
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return MessageConfig.get_default_config()
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "message_engine": {
                "type": "memory",  # 默认使用内存引擎
                "memory": {"enabled": True}
            }
        }
    
    @staticmethod
    def create_engine(config: Dict[str, Any]) -> MessageEngine:
        """根据配置创建消息引擎"""
        engine_type = config['message_engine']['type']
        engine_config = config['message_engine'].get(engine_type, {})
        
        if engine_type == 'mqtt':
            return MQTTEngine(engine_config)
        elif engine_type == 'redis':
            return RedisPubSubEngine(engine_config)
        elif engine_type == 'memory':
            return MemoryEngine(engine_config)
        else:
            raise ValueError(f"不支持的消息引擎类型: {engine_type}")
```

## 6. 迁移计划

### 6.1 阶段一：基础设施搭建（1-2周）

1. **创建消息引擎接口和实现**
   - 实现 `MessageEngine` 接口
   - 实现 MQTT、Redis、Memory 引擎
   - 编写单元测试

2. **创建消息处理器**
   - 实现 `MessageHandler`
   - 实现消息序列化/反序列化
   - 实现错误处理和重试机制

3. **创建业务层基础组件**
   - 定义消息格式（dataclass）
   - 实现 `TaskMessageProducer`
   - 实现 `TaskMessageConsumer`

### 6.2 阶段二：核心功能迁移（2-3周）

1. **替换进度跟踪器**
   - 修改 `AsyncProgressTracker`，支持消息机制
   - 保留关键字匹配作为后备方案（兼容模式）
   - 逐步迁移到消息机制

2. **替换日志装饰器**
   - 创建 `message_analysis_module` 装饰器
   - 逐步替换现有的 `log_analysis_module` 装饰器
   - 保持向后兼容

3. **更新Web界面**
   - 修改 `backtest_page.py`，使用消息机制获取进度
   - 实现WebSocket或SSE连接，实时接收消息
   - 保持现有的轮询机制作为后备

### 6.3 阶段三：全面切换和优化（1-2周）

1. **移除关键字匹配逻辑**
   - 确认所有模块都已切换到消息机制
   - 移除 `_detect_step_from_message` 中的关键字匹配
   - 移除 `ProgressLogHandler` 中的关键字检测

2. **性能优化**
   - 优化消息序列化性能
   - 实现消息批量处理
   - 优化网络传输

3. **文档和测试**
   - 编写完整的使用文档
   - 编写集成测试
   - 更新架构文档

### 6.4 兼容性保证

**双模式运行**：
- 在迁移期间，同时支持日志模式和消息模式
- 通过配置开关控制使用哪种模式
- 逐步迁移，确保系统稳定

```python
# 配置开关
MESSAGE_MODE_ENABLED = os.getenv('MESSAGE_MODE_ENABLED', 'false').lower() == 'true'

if MESSAGE_MODE_ENABLED:
    # 使用消息机制
    producer.publish_module_start(...)
else:
    # 使用日志机制（兼容模式）
    logger.info(f"📊 [模块开始] {module_name}...")
```

## 7. 代码改动清单

### 7.1 新增文件

```
tradingagents/messaging/
├── __init__.py
├── engine/
│   ├── __init__.py
│   ├── base.py              # MessageEngine 基类
│   ├── mqtt_engine.py        # MQTT 实现
│   ├── redis_engine.py       # Redis Pub/Sub 实现
│   └── memory_engine.py      # 内存实现
├── handler/
│   ├── __init__.py
│   └── message_handler.py    # MessageHandler
├── business/
│   ├── __init__.py
│   ├── producer.py           # TaskMessageProducer
│   ├── consumer.py           # TaskMessageConsumer
│   ├── handler.py            # ProgressMessageHandler
│   └── messages.py           # 消息数据类定义
└── decorators/
    ├── __init__.py
    └── message_decorators.py # 消息装饰器
```

### 7.2 修改文件

1. **web/utils/async_progress_tracker.py**
   - 添加消息机制支持
   - 修改 `update_progress` 方法，支持消息更新
   - 添加 `update_progress_from_message` 方法
   - 添加 `handle_module_start/complete/error` 方法
   - 保留关键字匹配作为兼容模式

2. **tradingagents/utils/tool_logging.py**
   - 添加 `message_analysis_module` 装饰器
   - 保留 `log_analysis_module` 装饰器（兼容模式）
   - 添加消息发送逻辑

3. **web/utils/progress_log_handler.py**
   - 标记为废弃（deprecated）
   - 保留代码作为兼容模式
   - 添加迁移说明

4. **web/app.py**
   - 初始化消息处理器
   - 修改进度获取逻辑，支持消息模式
   - 添加WebSocket/SSE支持（可选）

5. **config/settings.json**
   - 添加消息配置项

### 7.3 配置文件

1. **config/message_config.json**（新增）
   - 消息引擎配置
   - 主题配置

2. **requirements.txt**
   - 添加 `paho-mqtt`（MQTT支持）
   - 添加 `redis`（如果还没有）

## 8. 优势分析

### 8.1 解耦性

- **现状**：状态更新依赖日志格式，耦合度高
- **改进**：通过结构化消息传递，完全解耦

### 8.2 可扩展性

- **现状**：添加新步骤需要修改大量关键字匹配逻辑
- **改进**：只需定义新的消息类型和处理逻辑

### 8.3 性能

- **现状**：字符串解析和关键字匹配，效率低
- **改进**：直接传递结构化数据，性能高

### 8.4 可维护性

- **现状**：关键字匹配逻辑复杂，难以调试
- **改进**：清晰的接口和消息规范，易于维护

### 8.5 可切换性

- **现状**：固定使用日志系统
- **改进**：支持多种消息引擎，可根据需求切换

## 9. 风险和注意事项

### 9.1 风险

1. **消息丢失**：网络问题可能导致消息丢失
   - **缓解**：使用消息确认机制（QoS）、重试机制

2. **消息顺序**：异步消息可能导致顺序问题
   - **缓解**：在消息中添加序列号，消费者端排序

3. **性能问题**：消息队列可能成为瓶颈
   - **缓解**：使用高性能引擎、批量处理、异步处理

4. **兼容性问题**：迁移期间需要保证向后兼容
   - **缓解**：双模式运行、逐步迁移

### 9.2 注意事项

1. **消息格式版本化**：确保消息格式向前兼容
2. **错误处理**：完善的错误处理和日志记录
3. **监控和告警**：监控消息队列状态
4. **测试覆盖**：充分的单元测试和集成测试

## 10. 使用指南

### 10.1 快速开始

#### 启用消息模式

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

#### 选择消息引擎

**内存引擎（默认，用于开发测试）**：

```json
{
    "message_engine": {
        "type": "memory"
    }
}
```

**MQTT引擎（生产环境推荐）**：

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

**Redis Pub/Sub引擎**：

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

#### 使用消息装饰器

在分析节点中使用消息装饰器替代日志装饰器：

```python
from tradingagents.messaging.decorators import message_analysis_module

@message_analysis_module("market_analyst")
def market_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    # 分析逻辑
    pass
```

**注意**：如果消息模式未启用，装饰器会自动回退到日志模式，保持向后兼容。

### 10.2 兼容性说明

#### 双模式运行

系统支持双模式运行：
- **消息模式**：当 `MESSAGE_MODE_ENABLED=true` 时，使用消息机制
- **日志模式**：当消息模式未启用时，使用日志关键字识别（原有方式）

#### 迁移策略

1. **第一阶段**：保持消息模式关闭，所有代码继续使用日志模式
2. **第二阶段**：在测试环境启用消息模式，验证功能正常
3. **第三阶段**：逐步将装饰器替换为消息装饰器
4. **第四阶段**：生产环境启用消息模式

### 10.3 性能优化

#### 消息批量处理

对于高频消息，可以考虑批量处理：

```python
# 批量发送进度更新
progress_handler.get_producer().publish_progress(...)
```

#### 消息确认机制

MQTT和Redis都支持消息确认，确保消息不会丢失：
- MQTT: QoS=1（至少一次传递）
- Redis: Pub/Sub（尽力传递）

### 10.4 故障排查

#### 消息未收到

1. 检查消息模式是否启用
2. 检查消息引擎连接状态
3. 检查主题订阅是否正确
4. 查看日志文件中的错误信息

#### 消息丢失

1. 使用MQTT QoS=1或更高
2. 检查网络连接稳定性
3. 实现消息重试机制

#### 性能问题

1. 使用内存引擎进行开发测试
2. 生产环境使用MQTT或Redis
3. 考虑消息批量处理

### 10.5 示例代码

#### 完整示例

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

### 10.6 注意事项

1. **消息格式版本化**：消息格式变更时需要保持向前兼容
2. **错误处理**：消息发送失败不应该影响主业务流程
3. **资源清理**：任务完成后记得注销跟踪器
4. **线程安全**：消息处理是线程安全的，但注意回调函数的线程安全

### 10.7 数据验证

#### 必填字段验证

所有消息类型都有必填字段，缺失必填字段会导致消息发送失败。

#### 类型验证

- `analysis_id`: 必须是字符串
- `current_step`, `total_steps`: 必须是整数，且 `current_step >= 0`, `total_steps > 0`
- `progress_percentage`: 必须是浮点数，范围 `0.0-100.0`
- `duration`, `elapsed_time`, `remaining_time`: 必须是浮点数，单位：秒
- `timestamp`: 必须是浮点数，Unix时间戳

### 10.8 扩展性

#### 添加新消息类型

1. 在 `MessageType` 枚举中添加新类型
2. 定义新的数据类（可选）
3. 在 `TaskMessageProducer` 中添加发布方法
4. 在 `TaskMessageConsumer` 中添加处理逻辑

#### 添加额外字段

可以通过 `**extra` 参数传递额外字段，这些字段会被包含在消息的 `payload` 中。

## 11. 总结

本设计方案提供了一个完整的消息机制架构，具有以下特点：

1. ✅ **分层设计**：清晰的层次结构，职责分明
2. ✅ **可扩展**：支持多种消息引擎，易于切换
3. ✅ **易维护**：结构化消息，清晰的接口定义
4. ✅ **向后兼容**：支持双模式运行，逐步迁移
5. ✅ **高性能**：直接传递结构化数据，无需字符串解析

通过实施本方案，可以彻底解决当前基于日志关键字识别的状态更新机制的问题，提升系统的可维护性和扩展性。

### 消息数据结构总结

消息机制使用统一的数据结构，包含：
- **消息包装**：`type` + `timestamp` + `payload`
- **业务数据**：根据消息类型的不同，`payload` 包含不同的字段
- **类型安全**：使用 dataclass 和枚举确保类型安全
- **易于扩展**：支持额外字段和新的消息类型

所有消息都遵循这个结构，确保系统的一致性和可维护性。

