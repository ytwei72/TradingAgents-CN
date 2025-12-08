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


# 步骤显示名称映射
STEP_DISPLAY_NAMES = {
    # 准备阶段
    "environment_validation": "环境验证",
    "params_validation": "参数验证", 
    "datasource_init": "数据源初始化",
    "tools_init": "工具初始化",
    "graph_config": "图配置",
    "data_collection": "数据收集",
    # 分析师阶段
    "market_analyst": "市场分析师",
    "market": "市场分析师",
    "fundamentals_analyst": "基本面分析师",
    "fundamentals": "基本面分析师",
    "news_analyst": "新闻分析师",
    "news": "新闻分析师",
    "social_media_analyst": "社交媒体分析师",
    "social": "社交媒体分析师",
    "risk_analyst": "风险控制分析师",
    "risk": "风险控制分析师",
    # 研究团队
    "bull": "看多分析师",
    "bear": "看空分析师",
    "manager": "研究经理",
    # 交易决策
    "trader": "交易员",
    # 风险评估
    "risky": "激进风险评估",
    "safe": "保守风险评估",
    "neutral": "中性风险评估",
    "judge": "风险裁决",
}


class PlannedStep(BaseModel):
    step_index: int
    step_name: str
    display_name: str
    phase: str
    status: str = "pending"
    round: Optional[int] = None
    role: Optional[str] = None


class PlannedStepsResponse(BaseModel):
    total_steps: int
    steps: List[PlannedStep]


@router.get("/{analysis_id}/planned_steps", response_model=PlannedStepsResponse)
async def get_planned_steps(analysis_id: str):
    """获取任务计划执行的所有步骤
    
    在任务启动时或启动前，返回该任务预计执行的所有步骤列表。
    步骤顺序：准备阶段 -> 分析师阶段 -> 研究团队 -> 交易决策 -> 风险评估
    
    Args:
        analysis_id: 分析任务 ID
        
    Returns:
        计划步骤列表，包含总步骤数和每个步骤的详细信息
    """
    task_manager = get_task_manager()
    task_status = task_manager.get_task_status(analysis_id)
    
    if not task_status:
        raise HTTPException(status_code=404, detail="Analysis ID not found")
    
    # 获取任务参数中的分析师列表
    params = task_status.get('params', {})
    analysts = params.get('analysts', [])
    
    steps = []
    step_index = 1
    
    # 1. 准备阶段 (6步)
    preparation_steps = [
        "environment_validation",
        "params_validation",
        "datasource_init",
        "tools_init",
        "graph_config",
        "data_collection",
    ]
    for step_name in preparation_steps:
        steps.append(PlannedStep(
            step_index=step_index,
            step_name=step_name,
            display_name=STEP_DISPLAY_NAMES.get(step_name, step_name),
            phase="preparation",
            status="pending"
        ))
        step_index += 1
    
    # 2. 分析师阶段
    # 将简短的分析师名称映射到完整名称
    analyst_mapping = {
        "market": "market_analyst",
        "fundamentals": "fundamentals_analyst",
        "news": "news_analyst",
        "social": "social_media_analyst",
        "risk": "risk_analyst",
    }
    for analyst in analysts:
        full_name = analyst_mapping.get(analyst, analyst)
        steps.append(PlannedStep(
            step_index=step_index,
            step_name=full_name,
            display_name=STEP_DISPLAY_NAMES.get(analyst, STEP_DISPLAY_NAMES.get(full_name, analyst)),
            phase="analyst",
            status="pending"
        ))
        step_index += 1
    
    # 3. 研究团队辩论阶段
    research_roles = ["bull", "bear", "manager"]
    for role in research_roles:
        steps.append(PlannedStep(
            step_index=step_index,
            step_name=f"{role}_debate",
            display_name=f"{STEP_DISPLAY_NAMES.get(role, role)}辩论",
            phase="debate",
            status="pending",
            round=1,
            role=role
        ))
        step_index += 1
    
    # 4. 交易决策阶段
    steps.append(PlannedStep(
        step_index=step_index,
        step_name="trader",
        display_name=STEP_DISPLAY_NAMES.get("trader", "交易员"),
        phase="trading",
        status="pending"
    ))
    step_index += 1
    
    # 5. 风险评估阶段
    risk_roles = ["risky", "safe", "neutral", "judge"]
    for role in risk_roles:
        steps.append(PlannedStep(
            step_index=step_index,
            step_name=f"{role}_assessment",
            display_name=STEP_DISPLAY_NAMES.get(role, role),
            phase="risk_assessment",
            status="pending"
        ))
        step_index += 1
    
    return PlannedStepsResponse(
        total_steps=len(steps),
        steps=steps
    )
