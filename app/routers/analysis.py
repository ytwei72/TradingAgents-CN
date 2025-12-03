from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
import datetime
import asyncio
from tradingagents.utils.analysis_runner import run_stock_analysis
from tradingagents.utils.task_control_manager import (
    register_task, unregister_task, pause_task, resume_task, 
    stop_task, get_task_state
)
from tradingagents.utils.logging_manager import get_logger
from tradingagents.tasks import get_task_state_machine

router = APIRouter()
logger = get_logger('api_analysis')


# In-memory store for analysis tasks (replace with database in production)
analysis_tasks = {}

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

def run_analysis_task(analysis_id: str, request: AnalysisRequest):
    """Background task wrapper for running analysis"""
    try:
        # Get state machine instance
        state_machine = get_task_state_machine()
        
        # Update task status to running
        analysis_tasks[analysis_id]['status'] = 'running'
        state_machine.update_task(analysis_id, {
            'status': 'running',
            'progress': {
                'message': '分析任务开始执行'
            }
        })
        
        # Mock progress callback for now
        def progress_callback(message, step=None, total_steps=None):
            analysis_tasks[analysis_id]['progress'].append({
                'message': message,
                'step': step,
                'total_steps': total_steps,
                'timestamp': datetime.datetime.now().isoformat()
            })
            analysis_tasks[analysis_id]['current_message'] = message
            
            # Update state machine with progress
            state_machine.update_task(analysis_id, {
                'progress': {
                    'current_step': step if step is not None else 0,
                    'total_steps': total_steps if total_steps is not None else 0,
                    'percentage': (step / total_steps * 100) if (step and total_steps) else 0,
                    'message': message
                }
            })

        # Prepare configuration
        # Note: You might need to adapt how config is passed depending on run_stock_analysis signature
        # For now, we map the request fields to the function arguments
        
        # Default LLM provider/model (should be configurable via env or request)
        llm_provider = "dashscope" # Default or from env
        llm_model = "qwen-max" # Default or from env
        
        if request.extra_config:
             llm_provider = request.extra_config.get('llm_provider', llm_provider)
             llm_model = request.extra_config.get('llm_model', llm_model)

        results = run_stock_analysis(
            stock_symbol=request.stock_symbol,
            analysis_date=request.analysis_date or datetime.date.today().strftime('%Y-%m-%d'),
            analysts=request.analysts,
            research_depth=request.research_depth,
            llm_provider=llm_provider,
            llm_model=llm_model,
            market_type=request.market_type,
            progress_callback=progress_callback,
            analysis_id=analysis_id
            # async_tracker is omitted for simplicity in this first pass, 
            # but should be integrated if full feature parity is needed
        )

        analysis_tasks[analysis_id]['status'] = 'completed'
        analysis_tasks[analysis_id]['result'] = results
        
        # Update state machine with completion
        state_machine.update_task(analysis_id, {
            'status': 'completed',
            'progress': {
                'percentage': 100.0,
                'message': '分析任务已完成'
            }
        })
        
    except asyncio.CancelledError:
        # Gracefully handle task cancellation during shutdown
        logger.info(f"Analysis task {analysis_id} was cancelled (server shutdown)")
        if analysis_id in analysis_tasks:
            analysis_tasks[analysis_id]['status'] = 'cancelled'
            analysis_tasks[analysis_id]['error'] = 'Task cancelled due to server shutdown'
            
            # Update state machine
            state_machine.update_task(analysis_id, {
                'status': 'cancelled',
                'error': 'Task cancelled due to server shutdown'
            })
        raise  # Re-raise to allow proper cleanup
    except Exception as e:
        logger.error(f"Analysis failed for {analysis_id}: {e}")
        if analysis_id in analysis_tasks:
            analysis_tasks[analysis_id]['status'] = 'failed'
            analysis_tasks[analysis_id]['error'] = str(e)
            
            # Update state machine with error
            state_machine.update_task(analysis_id, {
                'status': 'failed',
                'error': str(e)
            })

@router.post("/start", response_model=AnalysisResponse)
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    analysis_id = str(uuid.uuid4())
    
    # Register task with control manager
    register_task(analysis_id)
    
    # Create task in state machine
    state_machine = get_task_state_machine()
    task_params = {
        'task_id': analysis_id,
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
    state_machine.create_task(task_params)
    
    analysis_tasks[analysis_id] = {
        'id': analysis_id,
        'status': 'pending',
        'request': request.dict(),
        'progress': [],
        'current_message': 'Initializing...',
        'created_at': datetime.datetime.now().isoformat()
    }
    
    background_tasks.add_task(run_analysis_task, analysis_id, request)
    
    return {
        "analysis_id": analysis_id,
        "status": "pending",
        "message": "Analysis task started"
    }


@router.get("/{analysis_id}/status")
async def get_analysis_status(analysis_id: str):
    if analysis_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="Analysis ID not found")
    
    task = analysis_tasks[analysis_id]
    return {
        "analysis_id": analysis_id,
        "status": task['status'],
        "current_message": task.get('current_message'),
        "progress_log": task.get('progress')[-5:] if task.get('progress') else [], # Return last 5 logs
        "error": task.get('error')
    }

@router.get("/{analysis_id}/result")
async def get_analysis_result(analysis_id: str):
    if analysis_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="Analysis ID not found")
    
    task = analysis_tasks[analysis_id]
    if task['status'] != 'completed':
        raise HTTPException(status_code=400, detail=f"Analysis not completed. Current status: {task['status']}")
        
    return task.get('result')

@router.post("/{analysis_id}/pause", response_model=AnalysisResponse)
async def pause_analysis(analysis_id: str):
    """暂停分析任务"""
    if analysis_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="Analysis ID not found")
    
    success = pause_task(analysis_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to pause task")
    
    # Update task status in memory
    analysis_tasks[analysis_id]['status'] = 'paused'
    
    return {
        "analysis_id": analysis_id,
        "status": "paused",
        "message": "Analysis task paused"
    }

@router.post("/{analysis_id}/resume", response_model=AnalysisResponse)
async def resume_analysis(analysis_id: str):
    """恢复分析任务"""
    if analysis_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="Analysis ID not found")
    
    success = resume_task(analysis_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to resume task")
    
    # Update task status in memory
    analysis_tasks[analysis_id]['status'] = 'running'
    
    return {
        "analysis_id": analysis_id,
        "status": "running",
        "message": "Analysis task resumed"
    }

@router.post("/{analysis_id}/stop", response_model=AnalysisResponse)
async def stop_analysis(analysis_id: str):
    """停止分析任务"""
    if analysis_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="Analysis ID not found")
    
    success = stop_task(analysis_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to stop task")
    
    # Update task status in memory
    analysis_tasks[analysis_id]['status'] = 'stopped'
    
    return {
        "analysis_id": analysis_id,
        "status": "stopped",
        "message": "Analysis task stopped"
    }


@router.get("/{analysis_id}/state")
async def get_task_current_state(analysis_id: str):
    """获取任务当前状态（来自状态机）"""
    state_machine = get_task_state_machine()
    state = state_machine.get_current_state(analysis_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Task state not found")
    
    return state


@router.get("/{analysis_id}/history")
async def get_task_history_states(analysis_id: str):
    """获取任务历史状态（来自状态机）
    
    Args:
        analysis_id: 任务 ID
        
    Returns:
        完整的历史状态列表（JSON数组）
    """
    state_machine = get_task_state_machine()
    history = state_machine.get_history_states(analysis_id)
    
    if not history:
        raise HTTPException(status_code=404, detail="Task history not found")
    
    return history
