"""
通知相关的数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime


class NotificationRequest(BaseModel):
    """通知请求模型"""
    type: Literal[
        "analysis_complete",
        "analysis_failed",
        "error_alert",
        "system_message",
        "custom"
    ] = Field(..., description="通知类型")
    analysis_id: Optional[str] = Field(None, description="关联的分析ID")
    message: str = Field(..., description="通知消息内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外的元数据")


class NotificationResponse(BaseModel):
    """通知响应模型"""
    notification_id: str = Field(..., description="通知ID")
    status: str = Field(..., description="发送状态：sent/failed")
    timestamp: str = Field(..., description="创建时间（ISO格式）")
    message: str = Field(..., description="状态消息")
