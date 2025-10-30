"""
报告配置常量
定义所有报告相关的显示名称、图标等常量
"""

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
}


# 分析模块配置
ANALYSIS_MODULES = [
    {
        'key': 'market_report',
        'title': '📈 市场技术分析',
        'icon': '📈',
        'description': '技术指标、价格趋势、支撑阻力位分析'
    },
    {
        'key': 'fundamentals_report',
        'title': '💰 基本面分析',
        'icon': '💰',
        'description': '财务数据、估值水平、盈利能力分析'
    },
    {
        'key': 'sentiment_report',
        'title': '💭 市场情绪分析',
        'icon': '💭',
        'description': '投资者情绪、社交媒体情绪指标'
    },
    {
        'key': 'news_report',
        'title': '📰 新闻事件分析',
        'icon': '📰',
        'description': '相关新闻事件、市场动态影响分析'
    },
    {
        'key': 'risk_assessment',
        'title': '⚠️ 风险评估',
        'icon': '⚠️',
        'description': '风险因素识别、风险等级评估'
    },
    {
        'key': 'investment_plan',
        'title': '📋 投资建议',
        'icon': '📋',
        'description': '具体投资策略、仓位管理建议'
    },
    {
        'key': 'investment_debate_state',
        'title': '🔬 研究团队决策',
        'icon': '🔬',
        'description': '多头/空头研究员辩论分析，研究经理综合决策'
    },
    {
        'key': 'trader_investment_plan',
        'title': '💼 交易团队计划',
        'icon': '💼',
        'description': '专业交易员制定的具体交易执行计划'
    },
    {
        'key': 'risk_debate_state',
        'title': '⚖️ 风险管理团队',
        'icon': '⚖️',
        'description': '激进/保守/中性分析师风险评估，投资组合经理最终决策'
    },
    {
        'key': 'final_trade_decision',
        'title': '🎯 最终交易决策',
        'icon': '🎯',
        'description': '综合所有团队分析后的最终投资决策'
    }
]


# 任务状态配置
TASK_STATUS_CONFIG = {
    'running': {
        'icon': '🔄',
        'title': '分析进行中',
        'color': '#4CAF50',
        'gradient': 'linear-gradient(135deg, #4CAF50 0%, #45a049 100%)',
        'message': '分析ID: {}'
    },
    'paused': {
        'icon': '⏸️',
        'title': '分析已暂停',
        'color': '#FFA726',
        'gradient': 'linear-gradient(135deg, #FFA726 0%, #FB8C00 100%)',
        'message': '使用上方的任务控制按钮'
    },
    'stopped': {
        'icon': '⏹️',
        'title': '分析已停止',
        'color': '#f44336',
        'gradient': 'linear-gradient(135deg, #f44336 0%, #d32f2f 100%)',
        'message': '任务已被用户停止'
    },
    'completed': {
        'icon': '✅',
        'title': '分析完成',
        'color': '#2196F3',
        'gradient': 'linear-gradient(135deg, #2196F3 0%, #1976D2 100%)',
        'message': '查看下方分析报告'
    },
    'failed': {
        'icon': '❌',
        'title': '分析失败',
        'color': '#f44336',
        'gradient': 'linear-gradient(135deg, #f44336 0%, #d32f2f 100%)',
        'message': '请查看错误信息'
    }
}


def get_report_display_name(report_key: str) -> str:
    """
    获取报告的显示名称
    
    Args:
        report_key: 报告键名
        
    Returns:
        显示名称（带图标）
    """
    return REPORT_DISPLAY_NAMES.get(
        report_key, 
        f"📄 {report_key.replace('_', ' ').title()}"
    )


def get_task_status_config(status: str) -> dict:
    """
    获取任务状态配置
    
    Args:
        status: 任务状态
        
    Returns:
        状态配置字典
    """
    return TASK_STATUS_CONFIG.get(status, {
        'icon': '❓',
        'title': '状态未知',
        'color': '#9E9E9E',
        'gradient': 'linear-gradient(135deg, #9E9E9E 0%, #757575 100%)',
        'message': f'未知状态: {status}'
    })

