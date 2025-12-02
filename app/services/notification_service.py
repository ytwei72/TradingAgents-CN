"""
通知服务层
负责通知的发送和管理（简化版）
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from tradingagents.utils.logging_manager import get_logger

logger = get_logger('notification_service')


class NotificationService:
    """通知服务类（简化版）"""
    
    def __init__(self):
        # 使用内存存储通知（后续可扩展到MongoDB/Redis）
        self.notifications: Dict[str, Dict[str, Any]] = {}
        
    def send_notification(
        self,
        notification_type: str,
        message: str,
        analysis_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        发送通知
        
        Args:
            notification_type: 通知类型
            message: 通知消息
            analysis_id: 关联的分析ID
            metadata: 额外元数据
            
        Returns:
            通知信息字典
        """
        try:
            # 生成通知ID
            notification_id = str(uuid.uuid4())
            timestamp = datetime.now()
            
            # 创建通知记录
            notification = {
                'notification_id': notification_id,
                'type': notification_type,
                'message': message,
                'analysis_id': analysis_id,
                'metadata': metadata or {},
                'timestamp': timestamp.isoformat(),
                'status': 'sent',
                'created_at': timestamp
            }
            
            # 保存到内存
            self.notifications[notification_id] = notification
            
            logger.info(f"通知已发送: {notification_id} - {notification_type}: {message}")
            
            return notification
            
        except Exception as e:
            logger.error(f"发送通知失败: {e}", exc_info=True)
            raise Exception(f"发送通知失败: {str(e)}")
    
    def get_notification(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """获取单个通知"""
        return self.notifications.get(notification_id)
    
    def get_notifications(
        self,
        analysis_id: Optional[str] = None,
        notification_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取通知列表
        
        Args:
            analysis_id: 筛选特定分析ID的通知
            notification_type: 筛选特定类型的通知
            limit: 返回数量限制
            
        Returns:
            通知列表
        """
        notifications = list(self.notifications.values())
        
        # 筛选
        if analysis_id:
            notifications = [n for n in notifications if n.get('analysis_id') == analysis_id]
        
        if notification_type:
            notifications = [n for n in notifications if n.get('type') == notification_type]
        
        # 按时间倒序排序
        notifications.sort(key=lambda x: x['created_at'], reverse=True)
        
        # 限制数量
        return notifications[:limit]
    
    def clear_notifications(self, older_than_hours: int = 24):
        """清理旧通知"""
        try:
            now = datetime.now()
            to_delete = []
            
            for notification_id, notification in self.notifications.items():
                created_at = notification['created_at']
                age_hours = (now - created_at).total_seconds() / 3600
                
                if age_hours > older_than_hours:
                    to_delete.append(notification_id)
            
            for notification_id in to_delete:
                del self.notifications[notification_id]
            
            if to_delete:
                logger.info(f"已清理 {len(to_delete)} 个旧通知")
                
        except Exception as e:
            logger.error(f"清理通知失败: {e}")


# 创建全局服务实例
notification_service = NotificationService()
