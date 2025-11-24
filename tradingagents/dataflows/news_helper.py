#!/usr/bin/env python3
"""
新闻数据后处理辅助模块
提供新闻数据的通用后处理函数
"""

import pandas as pd
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')


@dataclass
class NewsItem:
    """新闻项目数据结构"""
    title: str
    content: str
    source: str
    publish_time: datetime
    url: str
    urgency: str  # high, medium, low
    relevance_score: float


def parse_news_time(time_str: str) -> Optional[datetime]:
    """
    解析新闻时间字符串
    
    Args:
        time_str: 时间字符串
        
    Returns:
        datetime对象，解析失败返回None
    """
    if not time_str:
        return None
    
    # 尝试ISO 8601格式（带时区，如：2025-10-30T20:00:00+00:00）
    try:
        # Python 3.7+支持fromisoformat，但需要处理时区
        from datetime import timezone
        # 移除时区信息中的冒号（如果有）
        if '+' in time_str or time_str.endswith('Z'):
            # 处理Z结尾（UTC时间）
            if time_str.endswith('Z'):
                time_str = time_str[:-1] + '+00:00'
            # 使用fromisoformat解析
            dt = datetime.fromisoformat(time_str)
            # 转换为本地时间（移除时区信息）
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            return dt
    except Exception:
        pass
    
    # 尝试多种常见时间格式
    time_formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
        '%Y%m%d %H:%M:%S',
        '%Y%m%d'
    ]
    
    for fmt in time_formats:
        try:
            return datetime.strptime(time_str, fmt)
        except:
            continue
    
    logger.warning(f"[新闻Helper] 无法解析时间格式: {time_str}")
    return None


def filter_news_by_date_range(publish_time: datetime, start_time: datetime, end_time: datetime) -> bool:
    """
    检查新闻是否在指定的时间范围内
    
    Args:
        publish_time: 新闻发布时间
        start_time: 开始时间
        end_time: 结束时间
        
    Returns:
        bool: 是否在时间范围内
    """
    return start_time <= publish_time <= end_time


def assess_news_urgency(title: str, content: str) -> str:
    """
    评估新闻紧急程度
    
    Args:
        title: 新闻标题
        content: 新闻内容
        
    Returns:
        str: 紧急程度 ('high', 'medium', 'low')
    """
    text = (title + ' ' + content).lower()
    
    # 高紧急度关键词
    high_urgency_keywords = [
        'breaking', 'urgent', 'alert', 'emergency', 'halt', 'suspend',
        '突发', '紧急', '暂停', '停牌', '重大'
    ]
    
    # 中等紧急度关键词
    medium_urgency_keywords = [
        'earnings', 'report', 'announce', 'launch', 'merger', 'acquisition',
        '财报', '发布', '宣布', '并购', '收购'
    ]
    
    # 检查高紧急度关键词
    for keyword in high_urgency_keywords:
        if keyword in text:
            return 'high'
    
    # 检查中等紧急度关键词
    for keyword in medium_urgency_keywords:
        if keyword in text:
            return 'medium'
    
    return 'low'


def calculate_relevance_score(title: str, ticker: str) -> float:
    """
    计算新闻相关性分数
    
    Args:
        title: 新闻标题
        ticker: 股票代码
        
    Returns:
        float: 相关性分数 (0.0-1.0)
    """
    text = title.lower()
    ticker_lower = ticker.lower()
    
    # 基础相关性 - 股票代码直接出现在标题中
    if ticker_lower in text:
        return 1.0
    
    # 公司名称匹配
    company_names = {
        'aapl': ['apple', 'iphone', 'ipad', 'mac'],
        'tsla': ['tesla', 'elon musk', 'electric vehicle'],
        'nvda': ['nvidia', 'gpu', 'ai chip'],
        'msft': ['microsoft', 'windows', 'azure'],
        'googl': ['google', 'alphabet', 'search']
    }
    
    # 检查公司相关关键词
    if ticker_lower in company_names:
        for name in company_names[ticker_lower]:
            if name in text:
                return 0.8
    
    # 提取股票代码的纯数字部分（适用于中国股票）
    pure_code = ''.join(filter(str.isdigit, ticker))
    if pure_code and pure_code in text:
        return 0.9
    
    return 0.3  # 默认相关性


def convert_news_df_to_items(
    news_df: pd.DataFrame,
    source: str,
    ticker: str,
    start_time_filter: datetime,
    end_time: datetime
) -> List[NewsItem]:
    """
    将新闻DataFrame转换为NewsItem列表，并进行过滤和评估
    
    Args:
        news_df: 新闻DataFrame，必须包含'标题', '内容', '时间', '链接'列
        source: 新闻来源名称
        ticker: 股票代码
        start_time_filter: 开始时间过滤
        end_time: 结束时间过滤
        
    Returns:
        List[NewsItem]: 新闻项目列表
    """
    news_items = []
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    logger.debug(f"[新闻Helper] 开始转换 {len(news_df)} 条 {source} 新闻数据")
    
    for _, row in news_df.iterrows():
        try:
            # 解析时间
            time_str = row.get('时间', '')
            publish_time = parse_news_time(time_str)
            
            if not publish_time:
                logger.warning(f"[新闻Helper] 新闻时间为空或无法解析，跳过该新闻")
                skipped_count += 1
                continue
            
            # 检查时效性：只获取指定日期范围内的新闻
            if not filter_news_by_date_range(publish_time, start_time_filter, end_time):
                skipped_count += 1
                continue
            
            # 获取新闻内容
            title = row.get('标题', '')
            content = row.get('内容', '')
            url = row.get('链接', '')
            
            # 评估紧急程度
            urgency = assess_news_urgency(title, content)
            
            # 计算相关性
            relevance_score = calculate_relevance_score(title, ticker)
            
            # 创建NewsItem
            news_items.append(NewsItem(
                title=title,
                content=content,
                source=source,
                publish_time=publish_time,
                url=url,
                urgency=urgency,
                relevance_score=relevance_score
            ))
            processed_count += 1
            
        except Exception as e:
            logger.error(f"[新闻Helper] 处理 {source} 新闻项目失败: {e}")
            error_count += 1
            continue
    
    logger.info(f"[新闻Helper] {source} 新闻转换完成，成功: {processed_count}条，跳过: {skipped_count}条，错误: {error_count}条")
    
    return news_items
