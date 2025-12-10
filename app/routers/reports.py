"""
报告路由模块
提供报告生成和下载接口
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path

from app.schemas.report import ReportGenerateRequest, ReportGenerateResponse, ReportResponse
from app.services.report_service import report_service, get_reports
from tradingagents.utils.logging_manager import get_logger
from tradingagents.utils.mongodb_report_manager import mongodb_report_manager
from typing import Optional

router = APIRouter()
logger = get_logger("reports_router")


@router.post("/generate", response_model=ReportGenerateResponse)
async def generate_report(request: ReportGenerateRequest):
    """
    生成分析报告
    
    - **analysis_id**: 分析任务ID
    - **format**: 报告格式（markdown/md/pdf/docx）
    - **include_charts**: 是否包含图表（当前版本暂不支持）
    """
    try:
        # 从数据库(MongoDB)读取分析报告/结果
        if not mongodb_report_manager or not mongodb_report_manager.connected:
            raise HTTPException(
                status_code=500,
                detail="报告数据库未连接，无法生成报告"
            )

        db_report = mongodb_report_manager.get_report_by_id(request.analysis_id)
        if not db_report:
            raise HTTPException(
                status_code=404,
                detail=f"未在数据库中找到分析报告: {request.analysis_id}"
            )

        # 检查分析是否完成
        status = db_report.get("status", "completed")
        if status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"分析任务未完成，当前状态: {status}"
            )

        # 从MongoDB文档中构造 analysis_results 供报告服务使用
        # 优先使用 summary / analysts / research_depth / formatted_decision 等字段
        analysis_results = {
            "analysis_id": db_report.get("analysis_id"),
            "stock_symbol": db_report.get("stock_symbol"),
            "analysis_date": db_report.get("analysis_date"),
            "summary": db_report.get("summary"),
            "analysts": db_report.get("analysts", []),
            "research_depth": db_report.get("research_depth", 1),
            "decision": db_report.get("formatted_decision", {}),
            # 报告生成器期望的模块化报告字段，从 reports 中拆分/映射
            **db_report.get("reports", {}),
        }

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


@router.get("/{analysis_id}/reports", response_model=ReportResponse)
async def get_analysis_reports(analysis_id: str, stage: Optional[str] = Query(None, description="Filter reports by stage")):
    """获取分析任务的报告列表"""
    try:
        reports = get_reports(analysis_id, stage)
        return ReportResponse(
            success=True,
            data={
                "analysis_id": analysis_id,
                "reports": [r.model_dump() for r in reports]
            },
            message="报告获取成功"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching reports for {analysis_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
