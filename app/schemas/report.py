"""
报告相关的数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class ReportGenerateRequest(BaseModel):
    """报告生成请求模型"""
    analysis_id: str = Field(..., description="分析任务ID")
    format: Literal["markdown", "md", "pdf", "docx"] = Field(
        default="markdown",
        description="报告格式：markdown/md/pdf/docx"
    )
    include_charts: bool = Field(
        default=False,
        description="是否包含图表（当前版本暂不支持）"
    )


class ReportGenerateResponse(BaseModel):
    """报告生成响应模型"""
    report_id: str = Field(..., description="报告ID")
    status: str = Field(..., description="生成状态：completed/failed")
    message: str = Field(..., description="状态消息")
    download_url: Optional[str] = Field(None, description="下载链接")
    format: str = Field(..., description="报告格式")
