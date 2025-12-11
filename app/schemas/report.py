"""
报告相关的数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import datetime


# 报告显示名称和图标映射
REPORT_DISPLAY_NAMES = {
    # 最终决策和摘要
    'final_trade_decision': '🎯 最终交易决策',
    'summary_report': '📋 分析摘要',
    
    # 基本面和技术面
    'fundamentals_report': '💰 基本面分析',
    'technical_report': '📈 技术面分析',
    'market_report': '📈 市场分析',
    
    # 情绪和新闻分析
    'market_sentiment_report': '💭 市场情绪分析',
    'sentiment_report': '💭 市场情绪分析',
    'news_analysis_report': '📰 新闻分析',
    'news_report': '📰 新闻分析',
    'social_media_report': '📱 社交媒体分析',
    
    # 风险和价格
    'risk_assessment_report': '⚠️ 风险评估',
    'risk_assessment': '⚠️ 风险评估',
    'price_target_report': '🎯 目标价格分析',
    
    # 团队决策
    'bull_state': '🐂 多头观点',
    'bear_state': '🐻 空头观点',
    'trader_state': '💼 交易员分析',
    'invest_judge_state': '⚖️ 投资判断',
    
    # 研究团队和风险管理
    'research_team_state': '🔬 研究团队观点',
    'research_team_decision': '🔬 研究团队决策',
    'risk_debate_state': '⚠️ 风险管理讨论',
    'risk_management_decision': '🛡️ 风险管理决策',
    'investment_debate_state': '💬 投资讨论状态',
    
    # 投资计划
    'investment_plan': '📋 投资计划',
    'trader_investment_plan': '💼 交易员投资计划',

    'markdown': '📋 完整报告',
}


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


class AnalysisReport(BaseModel):
    report_id: Optional[str] = None  # 可选报告ID
    title: str
    stage: str
    stage_display_name: str
    content: str  # Markdown内容
    created_at: datetime
    file_path: Optional[str] = None  # 可选文件备份路径


class ReportResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    message: str = ""
    error: Optional[str] = None
    code: Optional[int] = None


class ReportListItem(BaseModel):
    analysis_id: str = Field(..., description="分析ID")
    analysis_date: str = Field(..., description="分析日期")
    analysts: List[str] = Field(default_factory=list, description="分析师列表")
    formatted_decision: Optional[dict] = Field(default_factory=dict, description="格式化决策")
    research_depth: int = Field(default=1, description="研究深度")
    status: str = Field(..., description="状态")
    stock_symbol: str = Field(..., description="股票代码")
    summary: str = Field(..., description="摘要")
    updated_at: datetime = Field(..., description="更新时间")


class ReportsListResponse(BaseModel):
    success: bool
    data: dict = Field(default_factory=dict, description="数据")
    message: str = Field(default="", description="消息")
