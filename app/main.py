"""
TradingAgents API 主应用
"""

import os
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph

load_dotenv()

app = FastAPI(
    title="TradingAgents API",
    description="API for TradingAgents stock analysis",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {"message": "TradingAgents API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
