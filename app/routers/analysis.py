from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
import datetime
import asyncio
import time

from tradingagents.tasks import get_task_manager, TaskStatus
from tradingagents.utils.logging_manager import get_logger
from tradingagents.storage.mongodb.tasks_state_machine_helper import tasks_state_machine_helper


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


class BatchSameParamsRequest(BaseModel):
    """批量分析请求 - 多个股票代码使用相同参数"""
    stock_symbols: List[str] = Field(..., description="Stock symbols list (e.g., ['603296', '300458'])")
    market_type: str = Field(..., description="Market type (美股, A股, 港股)")
    analysis_date: Optional[str] = Field(None, description="Analysis date (YYYY-MM-DD)")
    analysts: List[str] = Field(..., description="List of analysts to use")
    research_depth: int = Field(..., ge=1, le=5, description="Research depth (1-5)")
    include_sentiment: bool = Field(True, description="Include sentiment analysis")
    include_risk_assessment: bool = Field(True, description="Include risk assessment")
    custom_prompt: Optional[str] = Field(None, description="Custom analysis prompt")
    extra_config: Optional[Dict[str, Any]] = Field(None, description="Extra configuration parameters")


class BatchTaskResult(BaseModel):
    """批量任务中单个任务的结果"""
    stock_symbol: str
    analysis_id: str
    status: str
    message: str


class BatchAnalysisResponse(BaseModel):
    """批量分析响应"""
    total: int
    success_count: int
    failed_count: int
    tasks: List[BatchTaskResult]


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
        'extra_config': request.extra_config,
    }
    
    analysis_id = task_manager.start_task(task_params)
    
    return {
        "analysis_id": analysis_id,
        "status": "pending",
        "message": "Analysis task started"
    }


@router.post("/start/batch-same-params", response_model=BatchAnalysisResponse)
async def start_batch_analysis_same_params(request: BatchSameParamsRequest):
    """批量启动分析任务 - 多个股票代码使用相同的任务参数
    
    为多个股票代码启动分析任务，所有任务使用相同的分析参数。
    """
    task_manager = get_task_manager()
    
    tasks = []
    success_count = 0
    failed_count = 0
    
    for stock_symbol in request.stock_symbols:
        try:
            task_params = {
                'stock_symbol': stock_symbol,
                'market_type': request.market_type,
                'analysis_date': request.analysis_date,
                'analysts': request.analysts,
                'research_depth': request.research_depth,
                'include_sentiment': request.include_sentiment,
                'include_risk_assessment': request.include_risk_assessment,
                'custom_prompt': request.custom_prompt,
                'extra_config': request.extra_config,
            }
            
            analysis_id = task_manager.start_task(task_params)
            
            tasks.append(BatchTaskResult(
                stock_symbol=stock_symbol,
                analysis_id=analysis_id,
                status="pending",
                message="Analysis task started"
            ))
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to start task for {stock_symbol}: {e}")
            tasks.append(BatchTaskResult(
                stock_symbol=stock_symbol,
                analysis_id="",
                status="failed",
                message=f"Failed to start task: {str(e)}"
            ))
            failed_count += 1
    
    return BatchAnalysisResponse(
        total=len(request.stock_symbols),
        success_count=success_count,
        failed_count=failed_count,
        tasks=tasks
    )


@router.post("/start/batch", response_model=BatchAnalysisResponse)
async def start_batch_analysis(requests: List[AnalysisRequest]):
    """批量启动分析任务 - 每个任务使用独立的参数
    
    为多个分析任务启动，每个任务可以有独立的股票代码和分析参数。
    """
    task_manager = get_task_manager()
    
    tasks = []
    success_count = 0
    failed_count = 0
    
    for request in requests:
        try:
            task_params = {
                'stock_symbol': request.stock_symbol,
                'market_type': request.market_type,
                'analysis_date': request.analysis_date,
                'analysts': request.analysts,
                'research_depth': request.research_depth,
                'include_sentiment': request.include_sentiment,
                'include_risk_assessment': request.include_risk_assessment,
                'custom_prompt': request.custom_prompt,
                'extra_config': request.extra_config,
            }
            
            analysis_id = task_manager.start_task(task_params)
            
            tasks.append(BatchTaskResult(
                stock_symbol=request.stock_symbol,
                analysis_id=analysis_id,
                status="pending",
                message="Analysis task started"
            ))
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to start task for {request.stock_symbol}: {e}")
            tasks.append(BatchTaskResult(
                stock_symbol=request.stock_symbol,
                analysis_id="",
                status="failed",
                message=f"Failed to start task: {str(e)}"
            ))
            failed_count += 1
    
    return BatchAnalysisResponse(
        total=len(requests),
        success_count=success_count,
        failed_count=failed_count,
        tasks=tasks
    )


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
# 步骤显示名称映射已移至 task_manager.py


class PlannedStep(BaseModel):
    step_index: int
    step_name: str
    display_name: str
    description: Optional[str] = None  # Added description field
    phase: str
    status: str = "pending"
    round: Optional[int] = None
    role: Optional[str] = None


class PlannedStepsResponse(BaseModel):
    total_steps: int
    steps: List[PlannedStep]

@router.get("/{analysis_id}/planned_steps", response_model=PlannedStepsResponse)
async def get_planned_steps(analysis_id: str):
    """获取任务计划执行的所有步骤"""
    task_manager = get_task_manager()
    task_status = task_manager.get_task_status(analysis_id)
    
    if not task_status:
        raise HTTPException(status_code=404, detail="Analysis ID not found")
    
    # 使用 TaskManager 获取计划步骤
    steps_data = task_manager.get_task_planned_steps(analysis_id)
    
    # 转换为 Pydantic 模型
    steps = [PlannedStep(**step) for step in steps_data]
    
    return PlannedStepsResponse(
        total_steps=len(steps),
        steps=steps
    )


# ==================== 任务管理类 ====================

class TaskCountResponse(BaseModel):
    """任务总数响应"""
    success: bool
    total: int
    message: str


class TaskListItem(BaseModel):
    """任务列表项"""
    task_id: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    analysis_date: Optional[str] = None
    stock_symbol: Optional[str] = None
    company_name: Optional[str] = None


class TaskListResponse(BaseModel):
    """任务列表响应"""
    success: bool
    data: List[TaskListItem]
    total: int
    page: int
    page_size: int
    pages: int
    message: str


class TaskDetailResponse(BaseModel):
    """任务详细信息响应"""
    success: bool
    data: Dict[str, Any]
    message: str


@router.get("/management/count", response_model=TaskCountResponse)
async def get_task_count(
    task_id: Optional[str] = Query(None, description="任务ID筛选（支持部分匹配）"),
    analysis_date: Optional[str] = Query(None, description="分析日期筛选（精确匹配）"),
    status: Optional[str] = Query(None, description="运行状态筛选（精确匹配）"),
    stock_symbol: Optional[str] = Query(None, description="股票代码筛选（支持部分匹配）"),
    company_name: Optional[str] = Query(None, description="公司名称筛选（支持部分匹配）")
):
    """
    获取任务总数（支持筛选）
    
    返回MongoDB中所有任务的数量，支持多种筛选条件。
    """
    try:
        if not tasks_state_machine_helper.connected:
            raise HTTPException(
                status_code=500,
                detail="MongoDB不可用，请检查MongoDB配置"
            )
        
        # 直接使用helper的get_task_count方法，支持company_name筛选
        total = tasks_state_machine_helper.get_task_count(
            task_id=task_id,
            analysis_date=analysis_date,
            status=status,
            stock_symbol=stock_symbol,
            company_name=company_name
        )
        
        return TaskCountResponse(
            success=True,
            total=total,
            message="获取成功"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务总数失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取任务总数失败: {str(e)}"
        )


@router.get("/management/list", response_model=TaskListResponse)
async def get_task_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    task_id: Optional[str] = Query(None, description="任务ID筛选（支持部分匹配）"),
    analysis_date: Optional[str] = Query(None, description="分析日期筛选（精确匹配）"),
    status: Optional[str] = Query(None, description="运行状态筛选（精确匹配）"),
    stock_symbol: Optional[str] = Query(None, description="股票代码筛选（支持部分匹配）"),
    company_name: Optional[str] = Query(None, description="公司名称筛选（支持部分匹配）")
):
    """
    分页查询任务列表（支持筛选）
    
    返回包含task_id、status、created_at、updated_at、analysis_date、stock_symbol、company_name的列表
    
    筛选参数说明：
    - task_id: 任务ID筛选，支持部分匹配（不区分大小写）
    - analysis_date: 分析日期筛选，精确匹配
    - status: 运行状态筛选，精确匹配（如：completed, running, pending, failed等）
    - stock_symbol: 股票代码筛选，支持部分匹配（不区分大小写）
    - company_name: 公司名称筛选，支持部分匹配（不区分大小写）
    """
    start_time = time.time()
    logger.info(f"[任务列表查询] 开始处理请求 - page={page}, page_size={page_size}, "
                f"filters={{task_id={task_id}, analysis_date={analysis_date}, status={status}, "
                f"stock_symbol={stock_symbol}, company_name={company_name}}}")
    
    try:
        step_start = time.time()
        if not tasks_state_machine_helper.connected:
            raise HTTPException(
                status_code=500,
                detail="MongoDB不可用，请检查MongoDB配置"
            )
        logger.info(f"[任务列表查询] MongoDB连接检查完成，耗时: {time.time() - step_start:.3f}秒")
        
        # 直接使用helper的get_task_list方法，支持company_name筛选
        step_start = time.time()
        result = tasks_state_machine_helper.get_task_list(
            page=page,
            page_size=page_size,
            task_id=task_id,
            analysis_date=analysis_date,
            status=status,
            stock_symbol=stock_symbol,
            company_name=company_name
        )
        logger.info(f"[任务列表查询] 从MongoDB获取任务列表完成，获取到 {len(result['items'])} 条记录，总记录数: {result['total']}，耗时: {time.time() - step_start:.3f}秒")
        
        # 处理返回的数据，直接使用返回的company_name字段
        step_start = time.time()
        task_list = []
        for item in result["items"]:
            task_list.append(TaskListItem(
                task_id=item.get("task_id"),
                status=item.get('status', 'unknown'),
                created_at=item.get('created_at'),
                updated_at=item.get('updated_at'),
                analysis_date=item.get('analysis_date'),
                stock_symbol=item.get('stock_symbol'),
                company_name=item.get('company_name')
            ))
        logger.info(f"[任务列表查询] 数据转换完成，耗时: {time.time() - step_start:.3f}秒")
        
        total_time = time.time() - start_time
        logger.info(f"[任务列表查询] 请求处理完成，总耗时: {total_time:.3f}秒，返回 {len(task_list)} 条记录")
        
        return TaskListResponse(
            success=True,
            data=task_list,
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            pages=result["pages"],
            message="获取成功"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"[任务列表查询] 请求处理失败，总耗时: {total_time:.3f}秒，错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取任务列表失败: {str(e)}"
        )


@router.get("/management/{analysis_id}", response_model=TaskDetailResponse)
async def get_task_detail(analysis_id: str):
    """
    根据analysis_id获取任务的详细信息
    
    返回包含current_step、history、props的完整信息
    每个字段值最多显示50个字符，多余的用省略号表示
    """
    try:
        if not tasks_state_machine_helper.connected:
            raise HTTPException(
                status_code=500,
                detail="MongoDB不可用，请检查MongoDB配置"
            )
        
        # 调用封装的方法获取任务详情
        # 指定要获取的子键和截断长度
        result = tasks_state_machine_helper.get_task_detail(
            task_id=analysis_id,
            sub_keys=["current_step", "history", "props"],
            truncate_length=50
        )
        
        # 如果所有数据都不存在，返回404
        if not any(v for v in result.values() if v is not None):
            raise HTTPException(
                status_code=404,
                detail=f"未找到analysis_id为{analysis_id}的任务记录"
            )
        
        return TaskDetailResponse(
            success=True,
            data=result,
            message="获取成功"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详细信息失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取任务详细信息失败: {str(e)}"
        )
