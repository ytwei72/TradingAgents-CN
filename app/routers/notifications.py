"""
通知路由模块
提供通知发送接口
"""

from fastapi import APIRouter, HTTPException

from app.schemas.notification import NotificationRequest, NotificationResponse
from app.services.notification_service import notification_service
from tradingagents.utils.logging_manager import get_logger

router = APIRouter()
logger = get_logger('notifications_router')


@router.post("/notifications", response_model=NotificationResponse)
async def send_notification(request: NotificationRequest):
    """
    发送通知
    
    - **type**: 通知类型（analysis_complete/analysis_failed/error_alert/system_message/custom）
    - **analysis_id**: 关联的分析ID（可选）
    - **message**: 通知消息内容
    - **metadata**: 额外的元数据（可选）
    
    注意：当前版本为简化版，仅记录通知，不支持实时推送。
    """
    try:
        # 发送通知
        logger.info(f"发送通知: type={request.type}, message={request.message}")
        
        notification = notification_service.send_notification(
            notification_type=request.type,
            message=request.message,
            analysis_id=request.analysis_id,
            metadata=request.metadata
        )
        
        return NotificationResponse(
            notification_id=notification['notification_id'],
            status=notification['status'],
            timestamp=notification['timestamp'],
            message="通知已发送"
        )
        
    except Exception as e:
        logger.error(f"发送通知失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"发送通知失败: {str(e)}"
        )


@router.get("/notifications/{notification_id}")
async def get_notification(notification_id: str):
    """
    获取单个通知详情
    
    - **notification_id**: 通知ID
    """
    try:
        notification = notification_service.get_notification(notification_id)
        
        if not notification:
            raise HTTPException(
                status_code=404,
                detail=f"通知不存在: {notification_id}"
            )
        
        return notification
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取通知失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取通知失败: {str(e)}"
        )


@router.get("/notifications")
async def list_notifications(
    analysis_id: str = None,
    notification_type: str = None,
    limit: int = 100
):
    """
    获取通知列表
    
    - **analysis_id**: 筛选特定分析ID的通知（可选）
    - **notification_type**: 筛选特定类型的通知（可选）
    - **limit**: 返回数量限制（默认100）
    """
    try:
        notifications = notification_service.get_notifications(
            analysis_id=analysis_id,
            notification_type=notification_type,
            limit=limit
        )
        
        return {
            "total": len(notifications),
            "notifications": notifications
        }
        
    except Exception as e:
        logger.error(f"获取通知列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取通知列表失败: {str(e)}"
        )
