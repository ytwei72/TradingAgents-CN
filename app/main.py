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
from app.routers import health

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
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include health router
app.include_router(health.router, prefix="/api", tags=["health"])

class AnalysisRequest(BaseModel):
    symbol: str
    trade_date: Optional[str] = None

class AnalysisResponse(BaseModel):
    decision: str
    full_report: str

@app.post("/api/analysis", response_model=AnalysisResponse)
async def analyze_stock(request: AnalysisRequest):
    """Run stock analysis using agents"""
    symbol = request.symbol.upper()
    trade_date = request.trade_date or datetime.now().strftime("%Y-%m-%d")

    try:
        config = DEFAULT_CONFIG.copy()
        # Update with env vars if needed
        config["llm_provider"] = os.getenv("LLM_PROVIDER", "openai")
        config["deep_think_llm"] = os.getenv("DEEP_THINK_LLM", "gpt-4o-mini")
        config["quick_think_llm"] = os.getenv("QUICK_THINK_LLM", "gpt-4o-mini")

        graph = TradingAgentsGraph(config=config, debug=False)
        final_state, processed_signal = graph.propagate(symbol, trade_date)

        return {
            "decision": str(processed_signal),
            "full_report": str(final_state.get("final_trade_decision", "No decision available"))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
