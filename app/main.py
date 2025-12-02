"""
TradingAgents API 主应用
"""

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
from app.routers import health, analysis, reports, notifications

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph

async def lifespan(app: FastAPI):
    # Startup
    validate_startup_config()
    logging.basicConfig(level=settings.LOG_LEVEL)
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
