"""
WebSocket连接管理器
"""

from typing import List, Dict, Any
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger('websocket_manager')

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """建立连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket客户端已连接，当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket客户端已断开，当前连接数: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """广播消息给所有连接的客户端"""
        if not self.active_connections:
            return
            
        # 序列化消息
        try:
            if isinstance(message, str):
                message_str = message
            else:
                message_str = json.dumps(message, ensure_ascii=False)
        except Exception as e:
            logger.error(f"消息序列化失败: {e}")
            return

        # 广播
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.warning(f"发送消息失败，移除连接: {e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(connection)

# 全局实例
manager = ConnectionManager()
