#!/usr/bin/env python3
"""
统一新闻分析工具 V2 - 草稿版本
整合news_engine模块，实现新旧版混合模式
"""

import logging
from datetime import datetime
from typing import Optional
import re

logger = logging.getLogger(__name__)

class UnifiedNewsAnalyzerV2:
    """统一新闻分析器 V2，整合news_engine"""
    
    def __init__(self, toolkit, use_news_engine: bool = True):
        """
        初始化统一新闻分析器
        
        Args:
            toolkit: 包含旧版新闻工具的工具包
            use_news_engine: 是否启用news_engine（默认True，可通过配置关闭）
        """
        self.toolkit = toolkit
        self.use_news_engine = use_news_engine
        
        # 尝试导入news_engine
        self.news_engine_available = False
        if use_news_engine:
            try:
                from tradingagents.news_engine import get_stock_news, NewsResponse
                self.get_stock_news = get_stock_news
                self.NewsResponse = NewsResponse
                self.news_engine_available = True
                logger.info("[统一新闻工具V2] news_engine 模块已加载")
            except ImportError as e:
                logger.warning(f"[统一新闻工具V2] 无法导入news_engine: {e}，将使用旧版逻辑")
                self.news_engine_available = False
    
    def get_stock_news_unified(
        self, 
        stock_code: str, 
        max_news: int = 10, 
        model_info: str = "", 
        curr_date: str = None
    ) -> str:
        """
        统一新闻获取接口 - 混合模式
        
        Args:
            stock_code: 股票代码
            max_news: 最大新闻数量
            model_info: 当前使用的模型信息
            curr_date: 指定日期（格式：YYYY-MM-DD）
            
        Returns:
            str: 格式化的新闻内容
        """
        if curr_date is None:
            curr_date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"[统一新闻工具V2] 开始获取 {stock_code} 的新闻，日期: {curr_date}")
        
        # 识别股票类型
        stock_type = self._identify_stock_type(stock_code)
        logger.debug(f"[统一新闻工具V2] 股票类型: {stock_type}")
        
        # 根据股票类型和配置选择获取策略
        if stock_type == "A股":
            return self._get_a_share_news(stock_code, max_news, model_info, curr_date)
        elif stock_type == "港股":
            return self._get_hk_share_news(stock_code, max_news, model_info, curr_date)
        elif stock_type == "美股":
            return self._get_us_share_news(stock_code, max_news, model_info, curr_date)
        else:
            # 默认尝试news_engine，失败后降级到旧版
            return self._get_news_with_fallback(stock_code, max_news, model_info, curr_date)
    
    def _get_a_share_news(
        self, 
        stock_code: str, 
        max_news: int, 
        model_info: str, 
        curr_date: str
    ) -> str:
        """
        获取A股新闻 - 优先使用news_engine
        
        策略：
        1. 优先news_engine (AKShare + Tushare)
        2. 降级到旧版东方财富
        3. 最后尝试Google新闻
        """
        logger.debug(f"[统一新闻工具V2] A股新闻获取策略：news_engine优先")
        
        # 策略1: 尝试news_engine
        if self.news_engine_available:
            try:
                logger.debug(f"[统一新闻工具V2] 尝试使用news_engine获取A股新闻...")
                result = self._try_news_engine(stock_code, max_news, curr_date)
                
                if result and len(result.strip()) > 100:
                    logger.info(f"[统一新闻工具V2] ✅ news_engine成功获取A股新闻")
                    return self._format_news_result(result, "news_engine (A股)", model_info)
                else:
                    logger.warning(f"[统一新闻工具V2] news_engine返回内容过短或为空")
            except Exception as e:
                logger.warning(f"[统一新闻工具V2] news_engine获取失败: {e}")
        
        # 策略2: 降级到旧版东方财富
        logger.debug(f"[统一新闻工具V2] 降级到旧版东方财富新闻源...")
        try:
            if hasattr(self.toolkit, 'get_realtime_stock_news'):
                result = self.toolkit.get_realtime_stock_news.invoke({
                    "ticker": stock_code, 
                    "curr_date": curr_date
                })
                if result and len(result.strip()) > 100:
                    logger.info(f"[统一新闻工具V2] ✅ 旧版东方财富成功")
                    return self._format_news_result(result, "东方财富（旧版）", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具V2] 旧版东方财富失败: {e}")
        
        # 策略3: 最后尝试Google新闻
        logger.debug(f"[统一新闻工具V2] 尝试Google新闻作为最后备选...")
        try:
            if hasattr(self.toolkit, 'get_google_news'):
                query = f"{stock_code} 股票 新闻 财报 业绩"
                result = self.toolkit.get_google_news.invoke({
                    "query": query, 
                    "curr_date": curr_date
                })
                if result and len(result.strip()) > 50:
                    logger.info(f"[统一新闻工具V2] ✅ Google新闻成功")
                    return self._format_news_result(result, "Google新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具V2] Google新闻失败: {e}")
        
        return "❌ 无法获取A股新闻数据，所有新闻源均不可用"
    
    def _get_hk_share_news(
        self, 
        stock_code: str, 
        max_news: int, 
        model_info: str, 
        curr_date: str
    ) -> str:
        """
        获取港股新闻 - 优先使用news_engine
        
        策略：
        1. 优先news_engine (EODHD + FinnHub)
        2. 降级到Google新闻
        3. 最后尝试旧版实时新闻
        """
        logger.debug(f"[统一新闻工具V2] 港股新闻获取策略：news_engine优先")
        
        # 策略1: 尝试news_engine
        if self.news_engine_available:
            try:
                logger.debug(f"[统一新闻工具V2] 尝试使用news_engine获取港股新闻...")
                result = self._try_news_engine(stock_code, max_news, curr_date)
                
                if result and len(result.strip()) > 100:
                    logger.info(f"[统一新闻工具V2] ✅ news_engine成功获取港股新闻")
                    return self._format_news_result(result, "news_engine (港股)", model_info)
            except Exception as e:
                logger.warning(f"[统一新闻工具V2] news_engine获取失败: {e}")
        
        # 策略2: 降级到Google新闻
        logger.debug(f"[统一新闻工具V2] 降级到Google港股新闻...")
        try:
            if hasattr(self.toolkit, 'get_google_news'):
                query = f"{stock_code} 港股 香港股票 新闻"
                result = self.toolkit.get_google_news.invoke({
                    "query": query, 
                    "curr_date": curr_date
                })
                if result and len(result.strip()) > 50:
                    logger.info(f"[统一新闻工具V2] ✅ Google港股新闻成功")
                    return self._format_news_result(result, "Google港股新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具V2] Google港股新闻失败: {e}")
        
        # 策略3: 最后尝试旧版实时新闻
        logger.debug(f"[统一新闻工具V2] 尝试旧版实时新闻...")
        try:
            if hasattr(self.toolkit, 'get_realtime_stock_news'):
                result = self.toolkit.get_realtime_stock_news.invoke({
                    "ticker": stock_code, 
                    "curr_date": curr_date
                })
                if result and len(result.strip()) > 100:
                    logger.info(f"[统一新闻工具V2] ✅ 旧版实时新闻成功")
                    return self._format_news_result(result, "实时新闻（旧版）", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具V2] 旧版实时新闻失败: {e}")
        
        return "❌ 无法获取港股新闻数据，所有新闻源均不可用"
    
    def _get_us_share_news(
        self, 
        stock_code: str, 
        max_news: int, 
        model_info: str, 
        curr_date: str
    ) -> str:
        """
        获取美股新闻 - 混合模式
        
        策略：
        1. 优先news_engine (FinnHub + EODHD)
        2. 降级到OpenAI全球新闻
        3. 最后尝试Google新闻
        
        美股保留更多备选源，因为新闻获取难度较大
        """
        logger.debug(f"[统一新闻工具V2] 美股新闻获取策略：混合模式")
        
        # 策略1: 尝试news_engine
        if self.news_engine_available:
            try:
                logger.debug(f"[统一新闻工具V2] 尝试使用news_engine获取美股新闻...")
                result = self._try_news_engine(stock_code, max_news, curr_date)
                
                if result and len(result.strip()) > 100:
                    logger.info(f"[统一新闻工具V2] ✅ news_engine成功获取美股新闻")
                    return self._format_news_result(result, "news_engine (美股)", model_info)
            except Exception as e:
                logger.warning(f"[统一新闻工具V2] news_engine获取失败: {e}")
        
        # 策略2: 降级到OpenAI全球新闻
        logger.debug(f"[统一新闻工具V2] 降级到OpenAI全球新闻...")
        try:
            if hasattr(self.toolkit, 'get_global_news_openai'):
                result = self.toolkit.get_global_news_openai.invoke({
                    "curr_date": curr_date
                })
                if result and len(result.strip()) > 50:
                    logger.info(f"[统一新闻工具V2] ✅ OpenAI美股新闻成功")
                    return self._format_news_result(result, "OpenAI美股新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具V2] OpenAI美股新闻失败: {e}")
        
        # 策略3: 最后尝试Google新闻
        logger.debug(f"[统一新闻工具V2] 尝试Google美股新闻...")
        try:
            if hasattr(self.toolkit, 'get_google_news'):
                query = f"{stock_code} stock news earnings financial"
                result = self.toolkit.get_google_news.invoke({
                    "query": query, 
                    "curr_date": curr_date
                })
                if result and len(result.strip()) > 50:
                    logger.info(f"[统一新闻工具V2] ✅ Google美股新闻成功")
                    return self._format_news_result(result, "Google美股新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具V2] Google美股新闻失败: {e}")
        
        return "❌ 无法获取美股新闻数据，所有新闻源均不可用"
    
    def _try_news_engine(
        self, 
        stock_code: str, 
        max_news: int, 
        curr_date: str
    ) -> Optional[str]:
        """
        尝试使用news_engine获取新闻
        
        Args:
            stock_code: 股票代码
            max_news: 最大新闻数量
            curr_date: 指定日期
            
        Returns:
            格式化的新闻字符串，失败返回None
        """
        if not self.news_engine_available:
            return None
        
        try:
            # 调用news_engine
            response = self.get_stock_news(
                stock_code=stock_code,
                end_date=curr_date,
                max_news=max_news,
                hours_back=24  # 回溯24小时
            )
            
            # 检查响应
            if not response.success:
                logger.warning(f"[news_engine] 获取失败: {response.error_message}")
                return None
            
            if not response.news_items:
                logger.warning(f"[news_engine] 未返回新闻数据")
                return None
            
            # 格式化新闻
            formatted_news = self._format_news_engine_response(response)
            logger.debug(f"[news_engine] 格式化完成，内容长度: {len(formatted_news)}")
            
            return formatted_news
            
        except Exception as e:
            logger.error(f"[news_engine] 调用异常: {e}")
            return None
    
    def _format_news_engine_response(self, response) -> str:
        """
        格式化news_engine的NewsResponse对象
        
        Args:
            response: NewsResponse对象
            
        Returns:
            格式化的新闻字符串
        """
        report = f"# {response.query.stock_code} 新闻报告 (news_engine)\n\n"
        report += f"📅 生成时间: {response.fetch_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"📊 新闻总数: {response.total_count}条\n"
        report += f"🔗 数据源: {', '.join([s.value for s in response.sources_used])}\n"
        report += f"📅 查询日期: {response.query.start_date} ~ {response.query.end_date}\n\n"
        
        # 按紧急程度分组
        high_urgency = [n for n in response.news_items if n.urgency.value == '高']
        medium_urgency = [n for n in response.news_items if n.urgency.value == '中']
        low_urgency = [n for n in response.news_items if n.urgency.value == '低']
        
        # 输出紧急新闻
        if high_urgency:
            report += "## 🚨 紧急新闻\n\n"
            for news in high_urgency[:3]:
                report += f"### {news.title}\n"
                report += f"**来源**: {news.source.value} | **时间**: {news.publish_time.strftime('%Y-%m-%d %H:%M')}\n"
                report += f"**相关性**: {news.relevance_score:.2f}\n"
                report += f"{news.content[:500]}...\n\n"
        
        # 输出重要新闻
        if medium_urgency:
            report += "## 📢 重要新闻\n\n"
            for news in medium_urgency[:5]:
                report += f"### {news.title}\n"
                report += f"**来源**: {news.source.value} | **时间**: {news.publish_time.strftime('%Y-%m-%d %H:%M')}\n"
                report += f"**相关性**: {news.relevance_score:.2f}\n"
                report += f"{news.content[:300]}...\n\n"
        
        # 输出一般新闻
        if low_urgency:
            report += "## 📰 一般新闻\n\n"
            for news in low_urgency[:3]:
                report += f"### {news.title}\n"
                report += f"**来源**: {news.source.value} | **时间**: {news.publish_time.strftime('%Y-%m-%d %H:%M')}\n"
                report += f"{news.content[:200]}...\n\n"
        
        # 添加数据质量说明
        if response.news_items:
            latest_news = max(response.news_items, key=lambda x: x.publish_time)
            time_diff = datetime.now() - latest_news.publish_time
            
            report += f"\n## ⏰ 数据时效性\n"
            report += f"最新新闻发布于: {time_diff.total_seconds() / 60:.0f}分钟前\n"
            
            if time_diff.total_seconds() < 1800:  # 30分钟内
                report += "🟢 数据时效性: 优秀 (30分钟内)\n"
            elif time_diff.total_seconds() < 3600:  # 1小时内
                report += "🟡 数据时效性: 良好 (1小时内)\n"
            else:
                report += "🔴 数据时效性: 一般 (超过1小时)\n"
        
        return report
    
    def _get_news_with_fallback(
        self, 
        stock_code: str, 
        max_news: int, 
        model_info: str, 
        curr_date: str
    ) -> str:
        """
        通用新闻获取（带降级）
        
        先尝试news_engine，失败后降级到旧版逻辑
        """
        # 尝试news_engine
        if self.news_engine_available:
            result = self._try_news_engine(stock_code, max_news, curr_date)
            if result and len(result.strip()) > 100:
                return self._format_news_result(result, "news_engine", model_info)
        
        # 降级到旧版逻辑
        logger.debug(f"[统一新闻工具V2] 降级到旧版通用逻辑...")
        try:
            if hasattr(self.toolkit, 'get_realtime_stock_news'):
                result = self.toolkit.get_realtime_stock_news.invoke({
                    "ticker": stock_code, 
                    "curr_date": curr_date
                })
                if result and len(result.strip()) > 100:
                    return self._format_news_result(result, "实时新闻（旧版）", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具V2] 旧版实时新闻失败: {e}")
        
        return "❌ 无法获取新闻数据"
    
    def _identify_stock_type(self, stock_code: str) -> str:
        """识别股票类型"""
        stock_code = stock_code.upper().strip()
        
        # A股判断
        if re.match(r'^(00|30|60|68)\d{4}$', stock_code):
            return "A股"
        elif re.match(r'^(SZ|SH)\d{6}$', stock_code):
            return "A股"
        
        # 港股判断
        elif re.match(r'^\d{4,5}\.HK$', stock_code):
            return "港股"
        elif re.match(r'^\d{4,5}$', stock_code) and len(stock_code) <= 5:
            return "港股"
        
        # 美股判断
        elif re.match(r'^[A-Z]{1,5}$', stock_code):
            return "美股"
        elif '.' in stock_code and not stock_code.endswith('.HK'):
            return "美股"
        
        return "未知"
    
    def _format_news_result(self, news_content: str, source: str, model_info: str = "") -> str:
        """
        格式化新闻结果
        
        Args:
            news_content: 原始新闻内容
            source: 数据源名称
            model_info: 模型信息
            
        Returns:
            格式化的新闻字符串
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Google模型长度控制（保留旧版逻辑）
        is_google_model = any(keyword in model_info.lower() for keyword in ['google', 'gemini', 'gemma'])
        original_length = len(news_content)
        google_control_applied = False
        
        if is_google_model and len(news_content) > 5000:
            logger.warning(f"[统一新闻工具V2] Google模型长度控制: {original_length} -> 3000字符")
            # 简单截断
            news_content = news_content[:3000] + "...(内容已优化长度)"
            google_control_applied = True
        
        formatted_result = f"""
=== 📰 新闻数据来源: {source} ===
获取时间: {timestamp}
数据长度: {len(news_content)} 字符
{f"模型类型: {model_info}" if model_info else ""}
{f"🔧 Google模型长度控制已应用 (原长度: {original_length} 字符)" if google_control_applied else ""}

=== 📋 新闻内容 ===
{news_content}

=== ✅ 数据状态 ===
状态: 成功获取
来源: {source}
时间戳: {timestamp}
"""
        return formatted_result.strip()


def create_unified_news_tool_v2(toolkit, use_news_engine: bool = True):
    """
    创建统一新闻工具V2
    
    Args:
        toolkit: 工具包
        use_news_engine: 是否启用news_engine（可通过环境变量或配置控制）
        
    Returns:
        新闻获取函数
    """
    analyzer = UnifiedNewsAnalyzerV2(toolkit, use_news_engine)
    
    def get_stock_news_unified(
        stock_code: str, 
        max_news: int = 10, 
        model_info: str = "", 
        curr_date: str = None
    ):
        """
        统一新闻获取工具V2 - 混合模式
        
        Args:
            stock_code (str): 股票代码 (支持A股、港股、美股)
            max_news (int): 最大新闻数量，默认10
            model_info (str): 模型信息
            curr_date (str): 指定日期（YYYY-MM-DD）
        
        Returns:
            str: 格式化的新闻内容
        """
        if not stock_code:
            return "❌ 错误: 未提供股票代码"
        
        return analyzer.get_stock_news_unified(stock_code, max_news, model_info, curr_date)
    
    # 设置工具属性
    get_stock_news_unified.name = "get_stock_news_unified"
    get_stock_news_unified.description = """
统一新闻获取工具 V2 - 混合模式

功能:
- 自动识别股票类型（A股/港股/美股）
- 优先使用news_engine专业数据源
- 自动降级到旧版备选源
- A股: news_engine -> 东方财富 -> Google
- 港股: news_engine -> Google -> 实时新闻
- 美股: news_engine -> OpenAI -> Google
- 返回格式化的新闻内容
- 支持Google模型的特殊长度控制
"""
    
    return get_stock_news_unified

