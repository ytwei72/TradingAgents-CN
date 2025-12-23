#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告数据提取器
从分析报告中提取结构化的量化数据和信息
使用大模型服务进行智能提取
"""

import json
import re
import os
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('utils.report_extractor')

# 加载环境变量
load_dotenv()


class ReportDataExtractor:
    """报告数据提取器 - 从报告中提取结构化的量化数据"""
    
    @staticmethod
    def extract_data(report_content: str, fields: List[str], 
                     llm_provider: str = None, deep_think_llm: str = None, quick_think_llm: str = None) -> Dict[str, Any]:
        """
        从报告中提取指定的数据或信息字段
        
        Args:
            report_content: 报告内容（Markdown或文本格式）
            fields: 需要提取的数据字段列表，例如：
                ['target_price', 'investment_action', 'confidence', 'risk_score', 
                 'revenue', 'profit', 'pe_ratio', 'market_sentiment']
            llm_provider: LLM提供商（可选），如果不提供则从环境变量获取
                - "dashscope": 阿里百炼
                - "deepseek": DeepSeek
                - "google": Google AI
                - "openai": OpenAI
            deep_think_llm: 深度思考模型名称（可选），优先使用
            quick_think_llm: 快速思考模型名称（可选），如果deep_think_llm为None则使用此模型
        
        Returns:
            包含提取数据的JSON对象，格式如：
            {
                "target_price": 45.50,
                "investment_action": "买入",
                "confidence": 0.85,
                "risk_score": 0.3,
                "revenue": 1000000000,
                "profit": 150000000,
                "pe_ratio": 25.5,
                "market_sentiment": "乐观"
            }
            如果某个字段无法提取，则返回None或默认值
        """
        
        # 验证输入参数
        if not report_content or not isinstance(report_content, str) or len(report_content.strip()) == 0:
            logger.error("❌ [ReportDataExtractor] 报告内容为空或无效")
            return {}
        
        if not fields or not isinstance(fields, list) or len(fields) == 0:
            logger.error("❌ [ReportDataExtractor] 字段列表为空或无效")
            return {}
        
        # 清理报告内容
        report_content = report_content.strip()
        if len(report_content) == 0:
            logger.error("❌ [ReportDataExtractor] 报告内容为空")
            return {}
        
        # 选择使用的模型：优先使用deep_think_llm，如果为None则使用quick_think_llm
        llm_model = deep_think_llm if deep_think_llm is not None else quick_think_llm
        
        logger.info(f"🔍 [ReportDataExtractor] 开始提取数据，字段数量: {len(fields)}")
        logger.debug(f"🔍 [ReportDataExtractor] 报告长度: {len(report_content)} 字符")
        logger.debug(f"🔍 [ReportDataExtractor] 需要提取的字段: {fields}")
        logger.debug(f"🔍 [ReportDataExtractor] 使用模型: {llm_model} (deep_think_llm={deep_think_llm}, quick_think_llm={quick_think_llm})")
        
        # 创建LLM实例
        try:
            llm = ReportDataExtractor._create_llm(llm_provider, llm_model)
        except Exception as e:
            logger.error(f"❌ [ReportDataExtractor] LLM创建失败: {e}")
            return {}
        
        # 构建提取提示词
        prompt = ReportDataExtractor._build_extraction_prompt(report_content, fields)
        
        # 调用LLM进行提取
        try:
            response = llm.invoke(prompt).content
            logger.debug(f"🔍 [ReportDataExtractor] LLM响应: {response[:200]}...")
            
            # 解析JSON响应
            extracted_data = ReportDataExtractor._parse_response(response, fields)
            
            logger.info(f"✅ [ReportDataExtractor] 数据提取完成，成功提取 {len(extracted_data)} 个字段")
            return extracted_data
            
        except Exception as e:
            logger.error(f"❌ [ReportDataExtractor] 数据提取失败: {e}")
            import traceback
            logger.error(f"❌ [ReportDataExtractor] 详细错误: {traceback.format_exc()}")
            return {}
    
    @staticmethod
    def _create_llm(llm_provider: Optional[str] = None, llm_model: Optional[str] = None):
        """
        创建LLM实例
        
        Args:
            llm_provider: LLM提供商
            llm_model: 模型名称
        
        Returns:
            LLM实例
        """
        
        # 如果没有指定提供商，从环境变量获取或使用默认值
        if not llm_provider:
            llm_provider = os.getenv('LLM_PROVIDER', 'dashscope').lower()
        
        logger.info(f"🔧 [ReportDataExtractor] 使用LLM提供商: {llm_provider}")
        
        try:
            if llm_provider == 'dashscope' or llm_provider == 'alibaba' or 'dashscope' in llm_provider:
                # 使用阿里百炼
                from tradingagents.llm_adapters.dashscope_openai_adapter import ChatDashScopeOpenAI
                
                model = llm_model or os.getenv('DASHSCOPE_MODEL', 'qwen-turbo')
                llm = ChatDashScopeOpenAI(
                    model=model,
                    temperature=0.1,
                    max_tokens=2000
                )
                logger.info(f"✅ [ReportDataExtractor] 阿里百炼模型初始化成功: {model}")
                return llm
                
            elif llm_provider == 'deepseek' or 'deepseek' in llm_provider:
                # 使用DeepSeek
                from tradingagents.llm_adapters.deepseek_adapter import ChatDeepSeek
                
                model = llm_model or os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
                api_key = os.getenv('DEEPSEEK_API_KEY')
                base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
                
                if not api_key:
                    raise ValueError("使用DeepSeek需要设置DEEPSEEK_API_KEY环境变量")
                
                llm = ChatDeepSeek(
                    model=model,
                    api_key=api_key,
                    base_url=base_url,
                    temperature=0.1,
                    max_tokens=2000
                )
                logger.info(f"✅ [ReportDataExtractor] DeepSeek模型初始化成功: {model}")
                return llm
                
            elif llm_provider == 'google':
                # 使用Google AI
                from tradingagents.llm_adapters.google_openai_adapter import ChatGoogleOpenAI
                
                model = llm_model or os.getenv('GOOGLE_MODEL', 'gemini-pro')
                llm = ChatGoogleOpenAI(
                    model=model,
                    temperature=0.1,
                    max_tokens=2000
                )
                logger.info(f"✅ [ReportDataExtractor] Google模型初始化成功: {model}")
                return llm
                
            elif llm_provider == 'openai':
                # 使用OpenAI
                from langchain_openai import ChatOpenAI
                
                model = llm_model or os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
                llm = ChatOpenAI(
                    model=model,
                    temperature=0.1,
                    max_tokens=2000
                )
                logger.info(f"✅ [ReportDataExtractor] OpenAI模型初始化成功: {model}")
                return llm
                
            else:
                # 默认使用阿里百炼
                logger.warning(f"⚠️ [ReportDataExtractor] 未知的LLM提供商: {llm_provider}，使用默认的阿里百炼")
                from tradingagents.llm_adapters.dashscope_openai_adapter import ChatDashScopeOpenAI
                
                model = llm_model or os.getenv('DASHSCOPE_MODEL', 'qwen-turbo')
                llm = ChatDashScopeOpenAI(
                    model=model,
                    temperature=0.1,
                    max_tokens=2000
                )
                return llm
                
        except ImportError as e:
            logger.error(f"❌ [ReportDataExtractor] 导入LLM适配器失败: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ [ReportDataExtractor] 创建LLM实例失败: {e}")
            raise
    
    @staticmethod
    def _build_extraction_prompt(report_content: str, fields: List[str]) -> List:
        """
        构建提取提示词
        
        Args:
            report_content: 报告内容
            fields: 需要提取的字段列表
        
        Returns:
            消息列表，用于LLM调用
        """
        
        # 字段描述映射（支持中英文）
        field_descriptions = {
            # 投资决策相关
            'target_price': '目标价格（数值，单位为相应货币）',
            'investment_action': '投资建议（买入/持有/卖出）',
            'confidence': '置信度（0-1之间的数值）',
            'risk_score': '风险评分（0-1之间的数值，越高风险越大）',
            'stop_loss': '止损价格（数值）',
            'take_profit': '止盈价格（数值）',
            'position_size': '建议仓位（百分比或数值）',
            
            # 财务数据相关
            'revenue': '营业收入（数值）',
            'profit': '净利润（数值）',
            'pe_ratio': '市盈率（数值）',
            'pb_ratio': '市净率（数值）',
            'roe': '净资产收益率（百分比）',
            'debt_ratio': '负债率（百分比）',
            'growth_rate': '增长率（百分比）',
            
            # 市场数据相关
            'market_sentiment': '市场情绪（乐观/中性/悲观）',
            'price_trend': '价格趋势（上涨/横盘/下跌）',
            'volume_trend': '成交量趋势（放大/持平/萎缩）',
            'support_level': '支撑位（数值）',
            'resistance_level': '阻力位（数值）',
            
            # 其他
            'analysis_date': '分析日期（YYYY-MM-DD格式）',
            'stock_symbol': '股票代码',
            'market_type': '市场类型（A股/美股/港股等）',
        }
        
        # 构建字段描述文本
        field_descriptions_text = []
        for field in fields:
            description = field_descriptions.get(field, field)
            field_descriptions_text.append(f"- {field}: {description}")
        
        system_prompt = f"""您是一位专业的金融数据分析助手，负责从股票分析报告中提取结构化的量化数据。

请仔细阅读提供的分析报告，并从报告中提取以下字段的信息，并以严格的JSON格式返回：

{chr(10).join(field_descriptions_text)}

返回要求：
1. 必须以JSON格式返回，格式如下：
{{
    "field1": value1,
    "field2": value2,
    ...
}}

2. 数据类型要求：
   - 数值类型字段返回数字（整数或浮点数）
   - 文本类型字段返回字符串
   - 如果某个字段在报告中找不到，返回null
   - 百分比值转换为小数（例如：25%转换为0.25）
   - 日期格式统一为YYYY-MM-DD

3. 提取规则：
   - 必须从报告原文中提取，不能编造数据
   - 如果报告中没有明确提及，返回null
   - 对于投资建议，统一使用中文：买入、持有、卖出
   - 对于市场情绪，使用：乐观、中性、悲观
   - 对于趋势，使用：上涨、横盘、下跌

4. 只返回JSON对象，不要包含任何其他文字说明"""

        human_message = f"""请从以下分析报告中提取指定的数据字段：

---
报告内容：
{report_content}
---

请严格按照JSON格式返回提取的数据。"""

        return [
            ("system", system_prompt),
            ("human", human_message)
        ]
    
    @staticmethod
    def _parse_response(response: str, fields: List[str]) -> Dict[str, Any]:
        """
        解析LLM响应，提取JSON数据
        
        Args:
            response: LLM响应文本
            fields: 期望的字段列表
        
        Returns:
            解析后的数据字典
        """
        
        if not response or len(response.strip()) == 0:
            logger.warning("⚠️ [ReportDataExtractor] LLM响应为空")
            return {}
        
        try:
            # 尝试提取JSON部分
            # 方法1：直接解析整个响应
            try:
                data = json.loads(response)
                if isinstance(data, dict):
                    logger.debug(f"✅ [ReportDataExtractor] 直接解析JSON成功")
                    return ReportDataExtractor._validate_and_normalize(data, fields)
            except json.JSONDecodeError:
                pass
            
            # 方法2：使用正则表达式提取JSON块
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, response, re.DOTALL)
            
            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict):
                        logger.debug(f"✅ [ReportDataExtractor] 正则提取JSON成功")
                        return ReportDataExtractor._validate_and_normalize(data, fields)
                except json.JSONDecodeError:
                    continue
            
            # 方法3：尝试修复常见的JSON格式问题
            # 移除markdown代码块标记
            cleaned_response = re.sub(r'```json\s*', '', response)
            cleaned_response = re.sub(r'```\s*', '', cleaned_response)
            cleaned_response = cleaned_response.strip()
            
            try:
                data = json.loads(cleaned_response)
                if isinstance(data, dict):
                    logger.debug(f"✅ [ReportDataExtractor] 清理后解析JSON成功")
                    return ReportDataExtractor._validate_and_normalize(data, fields)
            except json.JSONDecodeError:
                pass
            
            # 如果所有方法都失败，记录警告并返回空字典
            logger.warning(f"⚠️ [ReportDataExtractor] 无法解析JSON响应，响应内容: {response[:200]}...")
            return {}
            
        except Exception as e:
            logger.error(f"❌ [ReportDataExtractor] 解析响应失败: {e}")
            return {}
    
    @staticmethod
    def _validate_and_normalize(data: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
        """
        验证和规范化提取的数据
        
        Args:
            data: 原始数据字典
            fields: 期望的字段列表
        
        Returns:
            规范化后的数据字典
        """
        
        result = {}
        
        for field in fields:
            if field in data:
                value = data[field]
                
                # 处理null值
                if value is None or value == "null" or value == "":
                    result[field] = None
                    continue
                
                # 类型规范化
                # 数值字段
                if field in ['target_price', 'confidence', 'risk_score', 'stop_loss', 
                            'take_profit', 'position_size', 'revenue', 'profit', 
                            'pe_ratio', 'pb_ratio', 'roe', 'debt_ratio', 'growth_rate',
                            'support_level', 'resistance_level']:
                    try:
                        # 如果是字符串，尝试提取数字
                        if isinstance(value, str):
                            # 移除货币符号和逗号
                            value = re.sub(r'[¥$€£,\s]', '', value)
                            # 提取数字
                            numbers = re.findall(r'\d+\.?\d*', value)
                            if numbers:
                                value = float(numbers[0])
                            else:
                                value = None
                        elif isinstance(value, (int, float)):
                            value = float(value)
                        else:
                            value = None
                    except (ValueError, TypeError):
                        value = None
                
                # 百分比处理（growth_rate, roe, debt_ratio等）
                if field in ['roe', 'debt_ratio', 'growth_rate']:
                    if isinstance(value, str) and '%' in value:
                        try:
                            value = float(re.sub(r'[%]', '', value)) / 100
                        except (ValueError, TypeError):
                            value = None
                
                # 文本字段规范化
                if field == 'investment_action':
                    # 统一投资建议格式
                    if isinstance(value, str):
                        value = value.strip()
                        action_map = {
                            'buy': '买入', 'BUY': '买入', 'Buy': '买入',
                            'hold': '持有', 'HOLD': '持有', 'Hold': '持有',
                            'sell': '卖出', 'SELL': '卖出', 'Sell': '卖出',
                            '购买': '买入', '保持': '持有', '出售': '卖出'
                        }
                        value = action_map.get(value, value)
                        if value not in ['买入', '持有', '卖出']:
                            value = '持有'  # 默认值
                
                elif field == 'market_sentiment':
                    # 统一市场情绪格式
                    if isinstance(value, str):
                        value = value.strip()
                        sentiment_map = {
                            'optimistic': '乐观', '乐观的': '乐观', 'positive': '乐观',
                            'neutral': '中性', '中性的': '中性',
                            'pessimistic': '悲观', '悲观的': '悲观', 'negative': '悲观'
                        }
                        value = sentiment_map.get(value.lower(), value)
                        if value not in ['乐观', '中性', '悲观']:
                            value = '中性'  # 默认值
                
                elif field == 'price_trend' or field == 'volume_trend':
                    # 统一趋势格式
                    if isinstance(value, str):
                        value = value.strip()
                        trend_map = {
                            'up': '上涨', '上涨的': '上涨', 'rising': '上涨',
                            'sideways': '横盘', '横盘的': '横盘', 'flat': '横盘',
                            'down': '下跌', '下跌的': '下跌', 'falling': '下跌'
                        }
                        value = trend_map.get(value.lower(), value)
                
                result[field] = value
            else:
                # 字段不存在，设置为None
                result[field] = None
        
        return result
    
    @staticmethod
    def read_reports_from_mongodb(stock_symbol: Optional[str] = None,
                                  start_time: Optional[Any] = None,
                                  end_time: Optional[Any] = None,
                                  valid_report_only: bool = True) -> List[Dict[str, Any]]:
        """
        从MongoDB数据库中读取分析报告记录
        
        Args:
            stock_symbol: 股票代码（可选），如果为None则不进行股票代码筛选
            start_time: 开始时间（可选），如果为None则不进行开始时间筛选
                支持格式：
                - datetime对象
                - ISO格式字符串（如：'2024-01-01T00:00:00'）
                - 时间戳（浮点数）
            end_time: 截止时间（可选），如果为None则不进行截止时间筛选
                支持格式：
                - datetime对象
                - ISO格式字符串（如：'2024-12-31T23:59:59'）
                - 时间戳（浮点数）
            valid_report_only: 是否只返回有效报告，默认为True
                有效报告的判断依据：
                - reports字段存在且为字典类型
                - reports字典中包含"final_trade_decision"键
                - "final_trade_decision"对应的报告内容长度不小于20
        
        Returns:
            符合条件的记录列表，每个记录包含完整的MongoDB文档数据
            如果MongoDB未连接或查询失败，返回空列表
        """
        
        try:
            # 使用统一的 MongoDB 报告管理器
            from tradingagents.storage.mongodb.report_manager import mongodb_report_manager
            
            if not mongodb_report_manager.connected or not mongodb_report_manager.collection:
                logger.warning("⚠️ [ReportDataExtractor] MongoDB未连接")
                return []
            
            # 构建查询条件
            query = {}
            
            # 股票代码筛选
            if stock_symbol is not None:
                query["stock_symbol"] = stock_symbol
                logger.debug(f"🔍 [ReportDataExtractor] 筛选股票代码: {stock_symbol}")
            
            # 时间范围筛选（使用 timestamp 字段）
            time_query = {}
            if start_time is not None:
                start_dt = ReportDataExtractor._parse_time(start_time)
                if start_dt:
                    time_query["$gte"] = start_dt
                    logger.debug(f"🔍 [ReportDataExtractor] 开始时间: {start_dt}")
            
            if end_time is not None:
                end_dt = ReportDataExtractor._parse_time(end_time)
                if end_dt:
                    time_query["$lte"] = end_dt
                    logger.debug(f"🔍 [ReportDataExtractor] 截止时间: {end_dt}")
            
            if time_query:
                query["timestamp"] = time_query
            
            logger.info(f"🔍 [ReportDataExtractor] 查询条件: {query}")
            
            # 执行查询（获取原始 MongoDB 文档）
            try:
                cursor = mongodb_report_manager.collection.find(query).sort("timestamp", -1)
                all_results = list(cursor)
                
                logger.info(f"📊 [ReportDataExtractor] 查询到 {len(all_results)} 条记录")
                
                # 筛选有效报告
                if valid_report_only:
                    filtered_results = []
                    for record in all_results:
                        if ReportDataExtractor._is_valid_report(record):
                            filtered_results.append(record)
                    
                    logger.info(f"✅ [ReportDataExtractor] 有效报告数量: {len(filtered_results)}/{len(all_results)}")
                    return filtered_results
                else:
                    return all_results
                    
            except Exception as e:
                logger.error(f"❌ [ReportDataExtractor] 查询失败: {e}")
                return []
                
        except ImportError:
            logger.error("❌ [ReportDataExtractor] MongoDB报告管理器不可用")
            return []
        except Exception as e:
            logger.error(f"❌ [ReportDataExtractor] 读取MongoDB记录失败: {e}")
            import traceback
            logger.error(f"❌ [ReportDataExtractor] 详细错误: {traceback.format_exc()}")
            return []
    
    @staticmethod
    def _parse_time(time_input: Any) -> Optional[Any]:
        """
        解析时间输入，转换为datetime对象
        
        Args:
            time_input: 时间输入，支持：
                - datetime对象
                - ISO格式字符串（如：'2024-01-01T00:00:00'）
                - 时间戳（浮点数）
        
        Returns:
            datetime对象，如果解析失败则返回None
        """
        from datetime import datetime
        
        try:
            # 如果已经是datetime对象
            if isinstance(time_input, datetime):
                return time_input
            
            # 如果是字符串，尝试解析ISO格式
            if isinstance(time_input, str):
                # 尝试ISO格式
                try:
                    return datetime.fromisoformat(time_input.replace('Z', '+00:00'))
                except ValueError:
                    pass
                
                # 尝试其他常见格式
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d',
                    '%Y/%m/%d %H:%M:%S',
                    '%Y/%m/%d'
                ]
                for fmt in formats:
                    try:
                        return datetime.strptime(time_input, fmt)
                    except ValueError:
                        continue
                
                logger.warning(f"⚠️ [ReportDataExtractor] 无法解析时间字符串: {time_input}")
                return None
            
            # 如果是数字，作为时间戳处理
            if isinstance(time_input, (int, float)):
                return datetime.fromtimestamp(time_input)
            
            logger.warning(f"⚠️ [ReportDataExtractor] 不支持的时间格式: {type(time_input)}")
            return None
            
        except Exception as e:
            logger.error(f"❌ [ReportDataExtractor] 时间解析失败: {e}")
            return None
    
    @staticmethod
    def _is_valid_report(record: Dict[str, Any]) -> bool:
        """
        判断报告是否有效
        
        Args:
            record: MongoDB记录字典
        
        Returns:
            True表示有效报告，False表示无效
        """
        try:
            # 检查reports字段是否存在
            if "reports" not in record:
                return False
            
            reports = record["reports"]
            
            # 检查reports是否为字典类型
            if not isinstance(reports, dict):
                return False
            
            # 检查是否包含"final_trade_decision"键
            if "final_trade_decision" not in reports:
                return False
            
            # 获取final_trade_decision报告内容
            final_decision = reports["final_trade_decision"]
            
            # 检查内容长度是否不小于20
            if isinstance(final_decision, str):
                content_length = len(final_decision.strip())
                return content_length >= 20
            elif isinstance(final_decision, (dict, list)):
                # 如果是字典或列表，转换为字符串计算长度
                content_str = str(final_decision)
                return len(content_str.strip()) >= 20
            else:
                return False
                
        except Exception as e:
            logger.debug(f"🔍 [ReportDataExtractor] 判断报告有效性时出错: {e}")
            return False

