from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
import datetime
import asyncio

from tradingagents.tasks import get_task_manager, TaskStatus
from tradingagents.utils.logging_manager import get_logger


router = APIRouter()
logger = get_logger("api_analysis")

class AnalysisRequest(BaseModel):
    stock_symbol: str = Field(..., description="Stock symbol (e.g., AAPL, 000001)")
    market_type: str = Field(..., description="Market type (美股, A股, 港股)")
    analysis_date: Optional[str] = Field(None, description="Analysis date (YYYY-MM-DD)")
    analysts: List[str] = Field(..., description="List of analysts to use")
    research_depth: int = Field(..., ge=1, le=5, description="Research depth (1-5)")
    include_sentiment: bool = Field(True, description="Include sentiment analysis")
    include_risk_assessment: bool = Field(True, description="Include risk assessment")
    custom_prompt: Optional[str] = Field(None, description="Custom analysis prompt")
    extra_config: Optional[Dict[str, Any]] = Field(None, description="Extra configuration parameters")

class AnalysisResponse(BaseModel):
    analysis_id: str
    status: str
    message: str



@router.post("/start", response_model=AnalysisResponse)
async def start_analysis(request: AnalysisRequest):
    task_manager = get_task_manager()
    
    task_params = {
        'stock_symbol': request.stock_symbol,
        'market_type': request.market_type,
        'analysis_date': request.analysis_date,
        'analysts': request.analysts,
        'research_depth': request.research_depth,
        'include_sentiment': request.include_sentiment,
        'include_risk_assessment': request.include_risk_assessment,
        'custom_prompt': request.custom_prompt,
        'extra_config': request.extra_config
    }
    
    analysis_id = task_manager.start_task(task_params)
    
    return {
        "analysis_id": analysis_id,
        "status": "pending",
        "message": "Analysis task started"
    }


@router.get("/{analysis_id}/status")
async def get_analysis_status(analysis_id: str):
    """获取分析任务状态（统一使用任务状态机）"""
    task_manager = get_task_manager()
    current_state = task_manager.get_task_status(analysis_id)
    
    if not current_state:
        raise HTTPException(status_code=404, detail="Analysis ID not found")
    
    return current_state

@router.get("/{analysis_id}/result")
async def get_analysis_result(analysis_id: str):
    """获取分析结果（从任务状态机读取）"""
    task_manager = get_task_manager()
    current_state = task_manager.get_task_status(analysis_id)
    if not current_state:
        raise HTTPException(status_code=404, detail="Analysis ID not found")

    status = current_state.get('status')
    if status != TaskStatus.COMPLETED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Analysis not completed. Current status: {status}",
        )

    return current_state.get('result')

@router.post("/{analysis_id}/pause", response_model=AnalysisResponse)
async def pause_analysis(analysis_id: str):
    """暂停分析任务"""
    task_manager = get_task_manager()
    
    success = task_manager.pause_task(analysis_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to pause task")
    
    return {
        "analysis_id": analysis_id,
        "status": "paused",
        "message": "Analysis task paused"
    }

@router.post("/{analysis_id}/resume", response_model=AnalysisResponse)
async def resume_analysis(analysis_id: str):
    """恢复分析任务"""
    task_manager = get_task_manager()
    
    success = task_manager.resume_task(analysis_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to resume task")
    
    return {
        "analysis_id": analysis_id,
        "status": "running",
        "message": "Analysis task resumed"
    }

@router.post("/{analysis_id}/stop", response_model=AnalysisResponse)
async def stop_analysis(analysis_id: str):
    """停止分析任务"""
    task_manager = get_task_manager()
    
    success = task_manager.stop_task(analysis_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to stop task")

    # stop_task 会自动处理任务注销
    
    return {
        "analysis_id": analysis_id,
        "status": "stopped",
        "message": "Analysis task stopped"
    }


@router.get("/{analysis_id}/current_step")
async def get_task_current_step(analysis_id: str):
    """获取任务当前步骤（从状态机获取）"""
    task_manager = get_task_manager()
    step = task_manager.get_task_current_step(analysis_id)
    
    if not step:
        raise HTTPException(status_code=404, detail="Task step not found")
    
    return step


@router.get("/{analysis_id}/history")
async def get_task_history_states(analysis_id: str):
    """获取任务历史步骤（从状态机获取）
    
    Args:
        analysis_id: 任务 ID
        
    Returns:
        完整的历史步骤列表（JSON数组）
    """
    task_manager = get_task_manager()
    history = task_manager.get_task_history(analysis_id)
    
    if not history:
        raise HTTPException(status_code=404, detail="Task history not found")
    
    return history
