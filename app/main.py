"""
TradingAgents API 主应用
"""

import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
# 这样可以直接运行 python app/main.py
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
import time
import os
from contextlib import asynccontextmanager

from datetime import datetime
from typing import Optional
from pydantic import BaseModel

import asyncio

from app.core.config import settings
from app.core.startup_validator import validate_startup_config
from app.routers import health, analysis, reports, notifications, websocket
from app.services.websocket_manager import manager as ws_manager

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.messaging.config import get_message_handler, is_message_mode_enabled
from tradingagents.messaging.engine.websocket_engine import WebSocketEngine

# 在模块级别配置日志，确保在 uvicorn 启动时就生效
# 降低 watchfiles 的日志级别，减少开发模式下的噪音
logging.getLogger("watchfiles.main").setLevel(logging.WARNING)
logging.getLogger("watchfiles").setLevel(logging.WARNING)


async def lifespan(app: FastAPI):
    # Startup
    validate_startup_config()
    logging.basicConfig(level=settings.LOG_LEVEL)
    
    # 注册WebSocket广播回调
    if is_message_mode_enabled():
        handler = get_message_handler()
        if handler and isinstance(handler.engine, WebSocketEngine):
            # 获取当前运行的事件循环（主线程循环）
            main_loop = asyncio.get_running_loop()
            
            # 定义同步包装器，使用捕获的主线程循环
            def broadcast_wrapper(message):
                try:
                    # 使用 run_coroutine_threadsafe 将协程提交到主线程循环
                    asyncio.run_coroutine_threadsafe(ws_manager.broadcast(message), main_loop)
                except Exception as e:
                    logging.error(f"WebSocket广播回调异常: {e}")
            
            handler.engine.set_broadcast_callback(broadcast_wrapper)
            logging.info("已注册WebSocket广播回调到消息引擎")
            
    yield
    # Shutdown

app = FastAPI(
    title="TradingAgents API",
    description="API for TradingAgents stock analysis",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# TrustedHost middleware (from reference, conditional)
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS + ["http://localhost:5173"], # Add Vue dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(notifications.router, prefix="/api", tags=["notifications"])
app.include_router(websocket.router, tags=["websocket"])

@app.get("/")
async def root():
    return {
        "name": "TradingAgents-CN API",
        "version": "0.1.0",
        "status": "healthy",
        "docs_url": "/docs" if settings.DEBUG else None
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
