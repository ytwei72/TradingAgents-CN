"""
报告路由模块
提供报告生成和下载接口
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from app.schemas.report import ReportGenerateRequest, ReportGenerateResponse
from app.services.report_service import report_service
from app.routers.analysis import analysis_tasks
from tradingagents.utils.logging_manager import get_logger

router = APIRouter()
logger = get_logger('reports_router')


@router.post("/generate", response_model=ReportGenerateResponse)
async def generate_report(request: ReportGenerateRequest):
    """
    生成分析报告
    
    - **analysis_id**: 分析任务ID
    - **format**: 报告格式（markdown/md/pdf/docx）
    - **include_charts**: 是否包含图表（当前版本暂不支持）
    """
    try:
        # 检查分析任务是否存在
        if request.analysis_id not in analysis_tasks:
            raise HTTPException(
                status_code=404,
                detail=f"分析任务不存在: {request.analysis_id}"
            )
        
        # 获取分析任务
        task = analysis_tasks[request.analysis_id]
        
        # 检查分析是否完成
        if task['status'] != 'completed':
            raise HTTPException(
                status_code=400,
                detail=f"分析任务未完成，当前状态: {task['status']}"
            )
        
        # 获取分析结果
        analysis_results = task.get('result')
        if not analysis_results:
            raise HTTPException(
                status_code=400,
                detail="分析结果为空"
            )
        
        # 标准化格式
        format_type = request.format.lower()
        if format_type == "md":
            format_type = "markdown"
        
        # 验证格式
        valid_formats = ["markdown", "pdf", "docx"]
        if format_type not in valid_formats:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的报告格式: {request.format}。支持的格式: {', '.join(valid_formats)}"
            )
        
        # 生成报告
        logger.info(f"开始生成报告: analysis_id={request.analysis_id}, format={format_type}")
        
        report_id, file_path, message = report_service.generate_report(
            analysis_results=analysis_results,
            format_type=format_type,
            analysis_id=request.analysis_id
        )
        
        # 构建下载URL
        download_url = f"/reports/{report_id}"
        
        logger.info(f"报告生成成功: {report_id}")
        
        return ReportGenerateResponse(
            report_id=report_id,
            status="completed",
            message=message,
            download_url=download_url,
            format=format_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成报告失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"生成报告失败: {str(e)}"
        )


@router.get("/{report_id}")
async def download_report(report_id: str):
    """
    下载报告文件
    
    - **report_id**: 报告ID
    """
    try:
        # 获取报告文件路径
        file_path = report_service.get_report_path(report_id)
        
        if not file_path or not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"报告不存在: {report_id}"
            )
        
        # 确定文件类型和媒体类型
        suffix = file_path.suffix.lower()
        media_type_map = {
            '.md': 'text/markdown',
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        media_type = media_type_map.get(suffix, 'application/octet-stream')
        
        # 返回文件
        logger.info(f"下载报告: {report_id} -> {file_path}")
        
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=file_path.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载报告失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"下载报告失败: {str(e)}"
        )
