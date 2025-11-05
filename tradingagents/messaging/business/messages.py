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

