"""
WebSocket路由模块
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import manager
import logging

router = APIRouter()
logger = logging.getLogger('websocket_router')

@router.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket通知端点
    客户端连接此端点以接收实时通知
    """
    await manager.connect(websocket)
    try:
        while True:
            # 保持连接活跃，接收客户端消息（虽然主要用于单向推送）
            # 可以在这里处理客户端的心跳或其他指令
            data = await websocket.receive_text()
            # 简单的回显或处理
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket连接异常: {e}")
        manager.disconnect(websocket)
