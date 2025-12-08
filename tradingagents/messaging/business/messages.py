"""
业务消息格式定义
"""

from dataclasses import dataclass, field
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
    PAUSED = "paused"
    COMPLETE = "complete"
    ERROR = "error"


class NodeStatus(Enum):
    """任务节点状态"""
    START = "start"
    PAUSED = "paused"
    TOOL_CALLING = "tool_calling"  # 工具调用中（不触发步骤完成）
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
    module_name: Optional[str] = None  # 任务节点名称（英文ID识别）
    node_status: Optional[str] = None  # 任务节点状态（start/paused/complete/error）


@dataclass
class TaskStatusMessage:
    """任务状态消息"""
    analysis_id: str
    status: TaskStatus
    message: str
    timestamp: float


@dataclass
class ModuleEventMessage:
    """模块事件消息"""
    analysis_id: str
    module_name: str
    event: ModuleEvent
    stock_symbol: Optional[str] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = field(default_factory=dict)

