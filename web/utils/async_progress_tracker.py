#!/usr/bin/env python3
"""
异步进度跟踪器
支持Redis和文件两种存储方式，前端定时轮询获取进度
"""

import json
import time
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import threading
from pathlib import Path

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('async_progress')

def safe_serialize(obj):
    """安全序列化对象，处理不可序列化的类型"""
    # 特殊处理LangChain消息对象
    if hasattr(obj, '__class__') and 'Message' in obj.__class__.__name__:
        try:
            # 尝试使用LangChain的序列化方法
            if hasattr(obj, 'dict'):
                return obj.dict()
            elif hasattr(obj, 'to_dict'):
                return obj.to_dict()
            else:
                # 手动提取消息内容
                return {
                    'type': obj.__class__.__name__,
                    'content': getattr(obj, 'content', str(obj)),
                    'additional_kwargs': getattr(obj, 'additional_kwargs', {}),
                    'response_metadata': getattr(obj, 'response_metadata', {})
                }
        except Exception:
            # 如果所有方法都失败，返回字符串表示
            return {
                'type': obj.__class__.__name__,
                'content': str(obj)
            }
    
    if hasattr(obj, 'dict'):
        # Pydantic对象
        try:
            return obj.dict()
        except Exception:
            return str(obj)
    elif hasattr(obj, '__dict__'):
        # 普通对象，转换为字典
        result = {}
        for key, value in obj.__dict__.items():
            if not key.startswith('_'):  # 跳过私有属性
                try:
                    json.dumps(value)  # 测试是否可序列化
                    result[key] = value
                except (TypeError, ValueError):
                    result[key] = safe_serialize(value)  # 递归处理
        return result
    elif isinstance(obj, (list, tuple)):
        return [safe_serialize(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: safe_serialize(value) for key, value in obj.items()}
    else:
        try:
            json.dumps(obj)  # 测试是否可序列化
            return obj
        except (TypeError, ValueError):
            return str(obj)  # 转换为字符串

class AsyncProgressTracker:
    """异步进度跟踪器 - 支持任务控制"""
    
    def __init__(self, analysis_id: str, analysts: List[str], research_depth: int, llm_provider: str):
        self.analysis_id = analysis_id
        self.analysts = analysts
        self.research_depth = research_depth
        self.llm_provider = llm_provider
        self.start_time = time.time()
        self.pause_start_time = None  # 暂停开始时间
        self.total_pause_duration = 0.0  # 总暂停时长
        
        # 生成分析步骤
        self.analysis_steps = self._generate_dynamic_steps()
        self.estimated_duration = self._estimate_total_duration()
        
        # 初始化状态
        self.current_step = 0
        self.step_history = []  # 记录每个步骤的实际执行历史
        self.step_start_times = {0: self.start_time}  # 记录每个步骤的开始时间，第0步从分析开始时计时
        self.progress_data = {
            'analysis_id': analysis_id,
            'status': 'running',
            'control_state': 'running',  # 任务控制状态: running/paused/stopped
            'current_step': 0,
            'total_steps': len(self.analysis_steps),
            'progress_percentage': 0.0,
            'current_step_name': self.analysis_steps[0]['name'],
            'current_step_description': self.analysis_steps[0]['description'],
            'elapsed_time': 0.0,
            'estimated_total_time': self.estimated_duration,
            'remaining_time': self.estimated_duration,
            'last_message': '准备开始分析...',
            'last_update': time.time(),
            'start_time': self.start_time,
            'pause_start_time': None,
            'total_pause_duration': 0.0,
            'steps': self.analysis_steps,
            'step_history': []  # 步骤执行历史
        }
        
        # 尝试初始化Redis，失败则使用文件
        self.redis_client = None
        self.use_redis = self._init_redis()
        
        if not self.use_redis:
            # 使用文件存储
            self.progress_file = f"./data/progress_{analysis_id}.json"
            os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)
        
        # 保存初始状态
        self._save_progress()
        
        logger.info(f"📊 [异步进度] 初始化完成: {analysis_id}, 存储方式: {'Redis' if self.use_redis else '文件'}")

        # 初始化消息机制（如果启用）
        self.message_producer = None
        self._init_message_system()

        # ========== 日志系统注册已禁用（已迁移到消息模式） ==========
        # 注意：任务阶段识别、状态和进度获取已迁移到消息模式
        # 如果消息模式未启用，系统会回退到消息装饰器的日志模式
        # 不再使用 ProgressLogHandler 进行日志识别
        
        # 注册到日志系统进行自动进度更新（已禁用，迁移到消息模式）
        # if not self.message_producer:
        #     try:
        #         from .progress_log_handler import register_analysis_tracker
        #         import threading
        #
        #         # 使用超时机制避免死锁
        #         def register_with_timeout():
        #             try:
        #                 register_analysis_tracker(self.analysis_id, self)
        #                 print(f"✅ [进度集成] 跟踪器注册成功: {self.analysis_id}")
        #             except Exception as e:
        #                 print(f"❌ [进度集成] 跟踪器注册失败: {e}")
        #
        #         # 在单独线程中注册，避免阻塞主线程
        #         register_thread = threading.Thread(target=register_with_timeout, daemon=True)
        #         register_thread.start()
        #         register_thread.join(timeout=2.0)  # 2秒超时
        #
        #         if register_thread.is_alive():
        #             print(f"⚠️ [进度集成] 跟踪器注册超时，继续执行: {self.analysis_id}")
        #
        #     except ImportError:
        #         logger.debug("📊 [异步进度] 日志集成不可用")
        #     except Exception as e:
        #         print(f"❌ [进度集成] 跟踪器注册异常: {e}")
    
    def _init_message_system(self):
        """初始化消息系统"""
        try:
            from tradingagents.messaging.config import get_progress_handler, is_message_mode_enabled
            
            if is_message_mode_enabled():
                progress_handler = get_progress_handler()
                if progress_handler:
                    # 注册跟踪器到消息系统
                    progress_handler.register_tracker(self.analysis_id, self)
                    self.message_producer = progress_handler.get_producer()
                    logger.info(f"📊 [消息系统] 跟踪器已注册到消息系统: {self.analysis_id}")
                else:
                    logger.debug("📊 [消息系统] 消息处理器未初始化")
            else:
                logger.debug("📊 [消息系统] 消息模式未启用")
        except ImportError as e:
            logger.debug(f"📊 [消息系统] 消息模块不可用: {e}")
        except Exception as e:
            logger.warning(f"📊 [消息系统] 初始化失败: {e}")
    
    def _init_redis(self) -> bool:
        """初始化Redis连接"""
        try:
            # 首先检查REDIS_ENABLED环境变量
            redis_enabled_raw = os.getenv('REDIS_ENABLED', 'false')
            redis_enabled = redis_enabled_raw.lower()
            logger.info(f"🔍 [Redis检查] REDIS_ENABLED原值='{redis_enabled_raw}' -> 处理后='{redis_enabled}'")

            if redis_enabled != 'true':
                logger.info(f"📊 [异步进度] Redis已禁用，使用文件存储")
                return False

            import redis

            # 从环境变量获取Redis配置
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_password = os.getenv('REDIS_PASSWORD', None)
            redis_db = int(os.getenv('REDIS_DB', 0))

            # 创建Redis连接
            if redis_password:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password,
                    db=redis_db,
                    decode_responses=True
                )
            else:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=True
                )

            # 测试连接
            self.redis_client.ping()
            logger.info(f"📊 [异步进度] Redis连接成功: {redis_host}:{redis_port}")
            return True
        except Exception as e:
            logger.warning(f"📊 [异步进度] Redis连接失败，使用文件存储: {e}")
            return False
    
    def _generate_dynamic_steps(self) -> List[Dict]:
        """根据分析师数量和研究深度动态生成分析步骤
        
        按照新的12步流程生成步骤：
        1-8: 配置与准备阶段
        9: 多智能体分析执行阶段（包含所有智能体节点）
        10-12: 结果处理与保存阶段
        """
        steps = []
        
        # ========== 第一阶段：配置与准备 (步骤1-8) ==========
        steps.extend([
            {"name": "🚀 分析启动", "description": "记录分析开始日志，初始化分析会话ID", "weight": 0.01},
            {"name": "💰 成本估算", "description": "根据选择的分析师和研究深度估算分析成本，显示预估Token使用量和费用", "weight": 0.01},
            {"name": "🔍 数据预获取和验证", "description": "验证股票代码格式和有效性，预获取股票基础数据（30天历史数据），缓存数据以提高效率", "weight": 0.03},
            {"name": "🔧 环境验证", "description": "检查API密钥配置（DASHSCOPE_API_KEY、FINNHUB_API_KEY等），验证必要的环境变量", "weight": 0.01},
            {"name": "⚙️ 构建配置", "description": "根据选择的LLM提供商和模型构建配置，设置研究深度、市场类型等参数", "weight": 0.01},
            {"name": "📝 格式化股票代码", "description": "根据市场类型格式化股票代码（A股/港股/美股），确保代码格式符合数据源要求", "weight": 0.01},
            {"name": "🏗️ 初始化分析引擎", "description": "创建TradingAgentsGraph实例，初始化所有智能体和工具节点，配置模拟模式（如果启用）", "weight": 0.02},
            {"name": "📁 步骤输出目录准备", "description": "创建步骤输出保存目录，准备保存每步执行结果", "weight": 0.01},
        ])
        
        # ========== 第二阶段：多智能体分析执行 (步骤9) ==========
        # 为每个分析师添加专门的步骤
        analyst_base_weight = 0.5 / max(len(self.analysts), 1)  # 50%的时间用于分析师工作
        for analyst in self.analysts:
            analyst_info = self._get_analyst_step_info(analyst)
            steps.append({
                "name": analyst_info["name"],
                "description": analyst_info["description"] + "（每个节点的输出都会被实时保存到步骤文件）",
                "weight": analyst_base_weight
            })

        # 根据研究深度添加研究员辩论阶段
        if self.research_depth >= 2:
            # 标准和深度分析包含研究员辩论
            steps.extend([
                {"name": "🐂 看涨研究员", "description": "从乐观角度分析投资机会，输出看涨观点和投资理由。输出保存：investment_debate_state.bull_history", "weight": 0.04},
                {"name": "🐻 看跌研究员", "description": "从谨慎角度分析投资风险，输出看跌观点和风险提醒。输出保存：investment_debate_state.bear_history", "weight": 0.04},
                {"name": "👔 研究经理", "description": "综合多头和空头观点，做出综合投资判断。输出保存：investment_debate_state.judge_decision、investment_plan", "weight": 0.03},
            ])

        # 所有深度都包含交易决策
        steps.append({
            "name": "💼 交易员", 
            "description": "基于研究结果制定交易计划，输出具体的投资建议和执行策略。输出保存：trader_investment_plan", 
            "weight": 0.03
        })

        if self.research_depth >= 3:
            # 深度分析包含详细风险评估
            steps.extend([
                {"name": "🔥 激进风险分析师", "description": "从高风险高收益角度分析，输出激进策略建议。输出保存：risk_debate_state.risky_history", "weight": 0.02},
                {"name": "🛡️ 保守风险分析师", "description": "从风险控制角度分析，输出保守策略建议。输出保存：risk_debate_state.safe_history", "weight": 0.02},
                {"name": "⚖️ 中性风险分析师", "description": "从平衡角度分析风险，输出平衡策略建议。输出保存：risk_debate_state.neutral_history", "weight": 0.02},
                {"name": "🎯 风险经理", "description": "综合各方风险评估，做出最终风险决策和风险评级。输出保存：risk_debate_state.judge_decision、final_trade_decision", "weight": 0.03},
            ])
        else:
            # 快速和标准分析的简化风险评估
            steps.append({
                "name": "⚠️ 风险提示", 
                "description": "识别主要投资风险并提供风险提示（快速和标准分析模式）", 
                "weight": 0.02
            })

        # 信号处理
        steps.append({
            "name": "📡 信号处理", 
            "description": "处理最终交易决策信号，提取结构化的投资建议（买入/持有/卖出）", 
            "weight": 0.02
        })
        
        # ========== 第三阶段：结果处理与保存 (步骤10-12) ==========
        steps.extend([
            {"name": "📊 处理分析结果", "description": "提取风险评估数据，记录Token使用情况，格式化分析结果用于显示", "weight": 0.02},
            {"name": "✅ 记录完成日志", "description": "记录分析完成时间，计算总耗时和总成本", "weight": 0.01},
            {"name": "💾 保存分析结果", "description": "保存分模块报告到本地目录，保存分析报告到MongoDB，步骤输出已实时保存到eval_results目录", "weight": 0.02},
        ])

        # 重新平衡权重，确保总和为1.0
        total_weight = sum(step["weight"] for step in steps)
        if total_weight > 0:
            for step in steps:
                step["weight"] = step["weight"] / total_weight

        return steps
    
    def _get_analyst_display_name(self, analyst: str) -> str:
        """获取分析师显示名称（保留兼容性）"""
        name_map = {
            'market': '市场分析师',
            'fundamentals': '基本面分析师',
            'technical': '技术分析师',
            'sentiment': '情绪分析师',
            'risk': '风险分析师'
        }
        return name_map.get(analyst, f'{analyst}分析师')

    def _get_analyst_step_info(self, analyst: str) -> Dict[str, str]:
        """获取分析师步骤信息（名称和描述）"""
        analyst_info = {
            'market': {
                "name": "📈 市场分析师",
                "description": "技术面分析：K线形态、均线系统、价格趋势。技术指标分析：MACD、RSI、KDJ、布林带等。支撑阻力位分析、成交量分析。输出保存：market_report字段"
            },
            'fundamentals': {
                "name": "💰 基本面分析师",
                "description": "财务数据分析：营收、利润、现金流、财务比率。公司基本面研究：业务模式、竞争优势。估值水平评估：PE、PB、PS、ROE等估值指标。输出保存：fundamentals_report字段"
            },
            'technical': {
                "name": "📈 技术分析师",
                "description": "分析K线图形、技术指标、支撑阻力等技术面"
            },
            'sentiment': {
                "name": "💭 情绪分析师",
                "description": "分析市场情绪、投资者心理、舆论倾向等"
            },
            'news': {
                "name": "📰 新闻分析师",
                "description": "新闻事件收集：相关新闻抓取和筛选。事件影响分析：重大事件对股价的影响评估。市场动态追踪：行业动态、政策变化。输出保存：news_report字段"
            },
            'social': {
                "name": "💭 社交媒体分析师",
                "description": "社交媒体数据采集：Reddit、Twitter等平台。投资者情绪分析：散户情绪、机构观点。热度指标监测：讨论热度、关注度变化。输出保存：sentiment_report字段（非A股市场）"
            },
            'social_media': {
                "name": "💭 社交媒体分析师",
                "description": "社交媒体数据采集：Reddit、Twitter等平台。投资者情绪分析：散户情绪、机构观点。热度指标监测：讨论热度、关注度变化。输出保存：sentiment_report字段（非A股市场）"
            },
            'risk': {
                "name": "⚠️ 风险分析师",
                "description": "识别投资风险、评估风险等级、制定风控措施"
            }
        }

        return analyst_info.get(analyst, {
            "name": f"🔍 {analyst}分析师",
            "description": f"进行{analyst}相关的专业分析，每个节点的输出都会被实时保存"
        })
    
    def _estimate_total_duration(self) -> float:
        """根据分析师数量、研究深度、模型类型预估总时长（秒）"""
        # 基础时间（秒）- 环境准备、配置等
        base_time = 60
        
        # 每个分析师的实际耗时（基于真实测试数据）
        analyst_base_time = {
            1: 120,  # 快速分析：每个分析师约2分钟
            2: 180,  # 基础分析：每个分析师约3分钟  
            3: 240   # 标准分析：每个分析师约4分钟
        }.get(self.research_depth, 180)
        
        analyst_time = len(self.analysts) * analyst_base_time
        
        # 模型速度影响（基于实际测试）
        model_multiplier = {
            'dashscope': 1.0,  # 阿里百炼速度适中
            'deepseek': 0.7,   # DeepSeek较快
            'google': 1.3      # Google较慢
        }.get(self.llm_provider, 1.0)
        
        # 研究深度额外影响（工具调用复杂度）
        depth_multiplier = {
            1: 0.8,  # 快速分析，较少工具调用
            2: 1.0,  # 基础分析，标准工具调用
            3: 1.3   # 标准分析，更多工具调用和推理
        }.get(self.research_depth, 1.0)
        
        total_time = (base_time + analyst_time) * model_multiplier * depth_multiplier
        return total_time
    
    def update_progress(self, message: str, step: Optional[int] = None):
        """更新进度状态（保留函数，但已迁移到消息模式）
        
        注意：此函数保留用于向后兼容，但任务阶段识别、状态和进度获取已迁移到消息模式。
        在消息模式下，进度更新通过 update_progress_from_message 和 handle_module_* 方法处理。
        """
        current_time = time.time()
        # 使用有效时长（排除暂停时间）
        elapsed_time = self.get_effective_elapsed_time()

        # 仅记录日志（保留用于调试）
        logger.debug(f"📊 [进度更新-日志模式] {self.analysis_id}: {message[:50]}... (消息模式启用时，状态更新由消息消费处理)")

    def _publish_progress_message(self):
        """发布进度消息"""
        if self.message_producer:
            try:
                from tradingagents.messaging.business.messages import TaskProgressMessage
                
                current_step_info = self.analysis_steps[self.current_step] if self.current_step < len(self.analysis_steps) else self.analysis_steps[-1]
                
                progress_msg = TaskProgressMessage(
                    analysis_id=self.analysis_id,
                    current_step=self.current_step,
                    total_steps=len(self.analysis_steps),
                    progress_percentage=self.progress_data.get('progress_percentage', 0.0),
                    current_step_name=current_step_info.get('name', '未知'),
                    current_step_description=self.progress_data.get('current_step_description', ''),
                    elapsed_time=self.get_effective_elapsed_time(),
                    remaining_time=self.progress_data.get('remaining_time', 0.0),
                    last_message=self.progress_data.get('last_message', '')
                )
                self.message_producer.publish_progress(progress_msg)
            except Exception as e:
                logger.warning(f"📊 [消息系统] 发布进度消息失败: {e}")
    
    def update_progress_from_message(self, message: Dict[str, Any]):
        """从消息更新进度（替代关键字匹配）
        
        Args:
            message: 消息负载字典
        """
        current_time = time.time()
        node_status = message.get('node_status', '')
        module_name = message.get('module_name', '')
        
        # 直接使用消息中的结构化数据
        if 'current_step' in message:
            old_step = self.current_step
            new_step = message['current_step']
            
            # 如果收到完成状态的消息，先确保当前步骤被标记为完成
            if node_status == 'complete' and old_step not in [s['step_index'] for s in self.step_history]:
                # 当前步骤还没有记录，先记录为完成
                step_start = self.step_start_times.get(old_step, current_time)
                step_duration = current_time - step_start
                self.step_history.append({
                    'step_index': old_step,
                    'step_name': self.analysis_steps[old_step]['name'] if old_step < len(self.analysis_steps) else '未知',
                    'start_time': step_start,
                    'end_time': current_time,
                    'duration': step_duration,
                    'message': message.get('last_message', ''),
                    'module_name': module_name,
                    'node_status': 'complete'  # 任务节点状态
                })
            elif node_status == 'complete':
                # 当前步骤已经记录，更新其状态为完成
                for step_record in self.step_history:
                    if step_record['step_index'] == old_step:
                        step_record['node_status'] = 'complete'
                        step_record['end_time'] = current_time
                        step_record['duration'] = current_time - step_record.get('start_time', current_time)
                        step_record['message'] = message.get('last_message', step_record.get('message', ''))
                        if module_name:
                            step_record['module_name'] = module_name
                        break
            
            if new_step != old_step and new_step >= old_step:
                # 记录步骤切换（如果旧步骤还没有记录）
                if old_step not in [s['step_index'] for s in self.step_history]:
                    step_start = self.step_start_times.get(old_step, current_time)
                    step_duration = current_time - step_start
                    self.step_history.append({
                        'step_index': old_step,
                        'step_name': self.analysis_steps[old_step]['name'] if old_step < len(self.analysis_steps) else '未知',
                        'start_time': step_start,
                        'end_time': current_time,
                        'duration': step_duration,
                        'message': message.get('last_message', ''),
                        'module_name': module_name,  # 任务节点名称（英文ID）
                        'node_status': node_status if node_status else 'complete'  # 任务节点状态，默认为完成
                    })
                
                self.current_step = new_step
                if new_step not in self.step_start_times:
                    self.step_start_times[new_step] = current_time
        elif node_status == 'complete':
            # 如果没有current_step但收到完成消息，记录当前步骤的完成状态
            current_step = self.current_step
            if current_step not in [s['step_index'] for s in self.step_history]:
                step_start = self.step_start_times.get(current_step, current_time)
                step_duration = current_time - step_start
                self.step_history.append({
                    'step_index': current_step,
                    'step_name': self.analysis_steps[current_step]['name'] if current_step < len(self.analysis_steps) else '未知',
                    'start_time': step_start,
                    'end_time': current_time,
                    'duration': step_duration,
                    'message': message.get('last_message', ''),
                    'module_name': module_name,
                    'node_status': 'complete'  # 任务节点状态
                })
            else:
                # 更新已存在的步骤记录为完成状态
                for step_record in self.step_history:
                    if step_record['step_index'] == current_step:
                        step_record['node_status'] = 'complete'
                        step_record['end_time'] = current_time
                        step_record['duration'] = current_time - step_record.get('start_time', current_time)
                        step_record['message'] = message.get('last_message', step_record.get('message', ''))
                        if module_name:
                            step_record['module_name'] = module_name
                        break
        
        # 更新进度数据（包含节点信息）
        self.progress_data.update({
            'current_step': message.get('current_step', self.current_step),
            'progress_percentage': message.get('progress_percentage', self.progress_data.get('progress_percentage', 0.0)),
            'current_step_name': message.get('current_step_name', self.progress_data.get('current_step_name', '')),
            'current_step_description': message.get('current_step_description', self.progress_data.get('current_step_description', '')),
            'elapsed_time': message.get('elapsed_time', self.get_effective_elapsed_time()),
            'remaining_time': message.get('remaining_time', self.progress_data.get('remaining_time', 0.0)),
            'last_message': message.get('last_message', self.progress_data.get('last_message', '')),
            'last_update': current_time,
            'current_module_name': message.get('module_name'),  # 当前任务节点名称
            'current_node_status': message.get('node_status'),  # 当前任务节点状态
            'step_history': self.step_history  # 同步步骤历史（包含节点信息和状态）
        })
        
        # 保存到存储
        self._save_progress()
        logger.info(f"📊 [消息更新] 从消息更新进度: {self.analysis_id} - {message.get('progress_percentage', 0):.1f}%")
        
        # 记录任务节点名称和状态
        module_name = message.get('module_name', '')
        node_status = message.get('node_status', '')
        if module_name or node_status:
            logger.info(f"📦 [任务节点] {self.analysis_id} - 节点: {module_name or '未知'}, 状态: {node_status or '未知'}")
    
    def _find_step_by_module_name(self, module_name: str) -> Optional[int]:
        """根据模块名称查找步骤（替代关键字匹配）
        
        Args:
            module_name: 模块名称
            
        Returns:
            Optional[int]: 步骤索引，如果未找到则返回None
        """
        # 使用映射表，而不是关键字匹配
        module_step_map = {
            'market_analyst': self._find_step_by_keyword(['市场分析', '市场']),
            'fundamentals_analyst': self._find_step_by_keyword(['基本面分析', '基本面']),
            'technical_analyst': self._find_step_by_keyword(['技术分析', '技术']),
            'sentiment_analyst': self._find_step_by_keyword(['情绪分析', '情绪']),
            'news_analyst': self._find_step_by_keyword(['新闻分析', '新闻']),
            'social_media_analyst': self._find_step_by_keyword(['社交媒体', '社交']),
            'risk_analyst': self._find_step_by_keyword(['风险分析', '风险']),
            'bull_researcher': self._find_step_by_keyword(['看涨研究员', '多头观点', '多头', '看涨']),
            'bear_researcher': self._find_step_by_keyword(['看跌研究员', '空头观点', '空头', '看跌']),
            'research_manager': self._find_step_by_keyword(['研究经理', '观点整合', '整合']),
            'trader': self._find_step_by_keyword(['交易员', '投资建议', '建议']),
            'risky_analyst': self._find_step_by_keyword(['激进风险分析师', '激进策略', '激进']),
            'safe_analyst': self._find_step_by_keyword(['保守风险分析师', '保守策略', '保守']),
            'neutral_analyst': self._find_step_by_keyword(['中性风险分析师', '平衡策略', '平衡']),
            'risk_manager': self._find_step_by_keyword(['风险经理', '风险控制', '控制']),
            'graph_signal_processing': self._find_step_by_keyword(['信号处理', '处理信号']),
        }
        
        return module_step_map.get(module_name)
    
    def _update_progress_data(self):
        """更新进度数据（内部方法）"""
        current_time = time.time()
        elapsed_time = self.get_effective_elapsed_time()
        
        progress_percentage = self._calculate_weighted_progress() * 100
        remaining_time = self._estimate_remaining_time(progress_percentage / 100, elapsed_time)
        
        current_step_info = self.analysis_steps[self.current_step] if self.current_step < len(self.analysis_steps) else self.analysis_steps[-1]
        
        self.progress_data.update({
            'current_step': self.current_step,
            'progress_percentage': progress_percentage,
            'current_step_name': current_step_info.get('name', '未知'),
            'current_step_description': current_step_info.get('description', ''),
            'elapsed_time': elapsed_time,
            'remaining_time': remaining_time,
            'last_update': current_time,
            'status': 'completed' if progress_percentage >= 100 else 'running',
            'step_history': self.step_history
        })
    
    def _detect_step_from_message(self, message: str) -> Optional[int]:
        """根据消息内容智能检测当前步骤
        
        按照新的12步流程进行匹配：
        1-8: 配置与准备阶段
        9: 多智能体分析执行阶段（包含所有智能体节点）
        10-12: 结果处理与保存阶段
        
        注意：检测顺序很重要，更具体的条件应该放在前面
        """
        message_lower = message.lower()

        # 步骤1: 分析启动
        if "🚀 开始股票分析" in message or ("开始" in message and "分析" in message and "股票" in message):
            return self._find_step_by_keyword(["分析启动", "启动"])
        
        # 步骤11: 记录完成日志（必须在"成本"检测之前，因为完成日志消息可能包含"成本"）
        elif "记录完成" in message or ("完成" in message and "日志" in message) or "完成日志已记录" in message:
            return self._find_step_by_keyword(["记录完成日志", "完成日志"])
        
        # 步骤2: 成本估算（放在记录完成日志之后，避免完成日志消息被误匹配）
        elif "成本" in message or "预估" in message or "估算" in message:
            return self._find_step_by_keyword(["成本估算", "成本"])
        
        # 步骤3: 数据预获取和验证
        elif "验证" in message or "预获取" in message or "数据准备" in message or "验证股票代码" in message:
            return self._find_step_by_keyword(["数据预获取", "验证", "数据准备"])
        
        # 步骤4: 环境验证
        elif "环境" in message or "api" in message_lower or "密钥" in message or "环境变量" in message:
            return self._find_step_by_keyword(["环境验证", "环境检查", "环境"])
        
        # 步骤5: 构建配置
        elif ("配置" in message or "参数" in message) and ("构建" in message or "设置" in message):
            return self._find_step_by_keyword(["构建配置", "配置"])
        
        # 步骤6: 格式化股票代码
        elif "格式化" in message or "代码" in message or "股票代码" in message:
            return self._find_step_by_keyword(["格式化股票代码", "格式化"])
        
        # 步骤7: 初始化分析引擎
        elif "初始化" in message and ("引擎" in message or "分析引擎" in message):
            return self._find_step_by_keyword(["初始化分析引擎", "初始化引擎", "引擎"])
        
        # 步骤8: 步骤输出目录准备
        elif "步骤输出" in message or "目录准备" in message or "保存目录" in message:
            return self._find_step_by_keyword(["步骤输出目录", "目录准备"])
        # 模块开始日志 - 推进到对应步骤并记录步骤开始时间
        elif "模块开始" in message:
            # 从日志中提取分析师类型，匹配新的步骤名称
            detected_step = None
            module_name = ""
            
            if "market_analyst" in message or "market" in message:
                detected_step = self._find_step_by_keyword(["市场分析", "市场"])
                module_name = "market_analyst"
            elif "fundamentals_analyst" in message or "fundamentals" in message:
                detected_step = self._find_step_by_keyword(["基本面分析", "基本面"])
                module_name = "fundamentals_analyst"
            elif "technical_analyst" in message or "technical" in message:
                detected_step = self._find_step_by_keyword(["技术分析", "技术"])
                module_name = "technical_analyst"
            elif "sentiment_analyst" in message or "sentiment" in message:
                detected_step = self._find_step_by_keyword(["情绪分析", "情绪"])
                module_name = "sentiment_analyst"
            elif "news_analyst" in message or "news" in message:
                detected_step = self._find_step_by_keyword(["新闻分析", "新闻"])
                module_name = "news_analyst"
            elif "social_media_analyst" in message or "social" in message:
                detected_step = self._find_step_by_keyword(["社交媒体", "社交"])
                module_name = "social_media_analyst"
            elif "risk_analyst" in message or "risk" in message:
                detected_step = self._find_step_by_keyword(["风险分析", "风险"])
                module_name = "risk_analyst"
            elif "bull_researcher" in message or "bull" in message:
                detected_step = self._find_step_by_keyword(["看涨研究员", "多头观点", "多头", "看涨"])
                module_name = "bull_researcher"
            elif "bear_researcher" in message or "bear" in message:
                detected_step = self._find_step_by_keyword(["看跌研究员", "空头观点", "空头", "看跌"])
                module_name = "bear_researcher"
            elif "research_manager" in message:
                detected_step = self._find_step_by_keyword(["研究经理", "观点整合", "整合"])
                module_name = "research_manager"
            elif "trader" in message:
                detected_step = self._find_step_by_keyword(["交易员", "投资建议", "建议"])
                module_name = "trader"
            elif "risky_analyst" in message or "risky" in message:
                detected_step = self._find_step_by_keyword(["激进风险分析师", "激进策略", "激进"])
                module_name = "risky_analyst"
            elif "safe_analyst" in message or "safe" in message:
                detected_step = self._find_step_by_keyword(["保守风险分析师", "保守策略", "保守"])
                module_name = "safe_analyst"
            elif "neutral_analyst" in message or "neutral" in message:
                detected_step = self._find_step_by_keyword(["中性风险分析师", "平衡策略", "平衡"])
                module_name = "neutral_analyst"
            # risk_manager必须在risk_analyst之前，因为risk_manager包含"risk"
            elif "risk_manager" in message or "risk_judge" in message:
                detected_step = self._find_step_by_keyword(["风险经理", "风险控制", "控制"])
                module_name = "risk_manager"
            elif "risk_analyst" in message or ("risk" in message and "analyst" in message):
                detected_step = self._find_step_by_keyword(["风险分析", "风险"])
                module_name = "risk_analyst"
            elif "graph_signal_processing" in message or ("signal" in message and "处理" in message):
                detected_step = self._find_step_by_keyword(["信号处理", "处理信号"])
                module_name = "graph_signal_processing"
            
            # 详细调试日志
            if detected_step is not None:
                step_name = self.analysis_steps[detected_step]['name'] if detected_step < len(self.analysis_steps) else "未知"
                # 记录该步骤的开始时间（如果还没有记录的话）
                if detected_step not in self.step_start_times:
                    self.step_start_times[detected_step] = time.time()
                    logger.info(f"✅ [步骤检测-开始] 模块: {module_name}, 步骤索引: {detected_step}, 步骤名称: {step_name}, 开始时间: {time.time()}")
                else:
                    logger.warning(f"⚠️ [步骤检测-重复开始] 模块: {module_name}, 步骤索引: {detected_step}, 步骤名称: {step_name}, 已有开始时间: {self.step_start_times[detected_step]}")
            else:
                logger.warning(f"⚠️ [步骤检测-未匹配] 检测到模块开始但未匹配到步骤, 消息: {message[:200]}")
            
            return detected_step
        
        # 步骤10: 处理分析结果
        elif "处理分析结果" in message or ("处理" in message and "结果" in message and "分析" in message):
            return self._find_step_by_keyword(["处理分析结果", "处理结果"])
        
        # 步骤12: 保存分析结果（已在上面处理步骤11，这里不再重复）
        elif "保存分析结果" in message or ("保存" in message and ("结果" in message or "报告" in message)):
            return self._find_step_by_keyword(["保存分析结果", "保存结果", "保存报告"])
        
        # 信号处理
        elif "信号处理" in message or "处理信号" in message:
            return self._find_step_by_keyword(["信号处理", "处理信号"])
        
        # 工具调用日志 - 不推进步骤，只更新描述
        elif "工具调用" in message:
            # 保持当前步骤，不推进
            return None
        # 模块完成日志 - 确保当前步骤被记录，然后推进到下一步
        elif "模块完成" in message:
            current_step_info = self.analysis_steps[self.current_step] if self.current_step < len(self.analysis_steps) else {'name': '未知'}
            current_step_name = current_step_info['name']
            
            # 检查当前步骤是否已记录，如果没有则记录
            if self.current_step not in [s['step_index'] for s in self.step_history]:
                step_start = self.step_start_times.get(self.current_step, time.time())
                step_end = time.time()
                step_duration = step_end - step_start
                
                self.step_history.append({
                    'step_index': self.current_step,
                    'step_name': current_step_name,
                    'start_time': step_start,
                    'end_time': step_end,
                    'duration': step_duration,
                    'message': message
                })
                logger.info(f"✅ [步骤检测-完成] 步骤索引: {self.current_step}, 步骤名称: {current_step_name}, 用时: {step_duration:.2f}秒")
            else:
                logger.warning(f"⚠️ [步骤检测-重复完成] 步骤索引: {self.current_step}, 步骤名称: {current_step_name}, 已记录在历史中")
            
            # 模块完成时，从当前步骤推进到下一步
            # 不再依赖模块名称，而是基于当前进度推进
            next_step = min(self.current_step + 1, len(self.analysis_steps) - 1)
            logger.info(f"📍 [步骤检测-推进] 从步骤 {self.current_step} ({current_step_name}) 推进到步骤 {next_step}")
            return next_step

        return None

    def _find_step_by_keyword(self, keywords) -> Optional[int]:
        """根据关键词查找步骤索引"""
        if isinstance(keywords, str):
            keywords = [keywords]

        for i, step in enumerate(self.analysis_steps):
            for keyword in keywords:
                if keyword in step["name"]:
                    return i
        return None

    def _get_next_step(self, keyword: str) -> Optional[int]:
        """获取指定步骤的下一步"""
        current_step_index = self._find_step_by_keyword(keyword)
        if current_step_index is not None:
            return min(current_step_index + 1, len(self.analysis_steps) - 1)
        return None

    def _calculate_weighted_progress(self) -> float:
        """根据步骤权重计算进度"""
        if self.current_step >= len(self.analysis_steps):
            return 1.0

        # 如果是最后一步，返回100%
        if self.current_step == len(self.analysis_steps) - 1:
            return 1.0

        completed_weight = sum(step["weight"] for step in self.analysis_steps[:self.current_step])
        total_weight = sum(step["weight"] for step in self.analysis_steps)

        return min(completed_weight / total_weight, 1.0)
    
    def _estimate_remaining_time(self, progress: float, elapsed_time: float) -> float:
        """基于总预估时间计算剩余时间"""
        # 如果进度已完成，剩余时间为0
        if progress >= 1.0:
            return 0.0

        # 使用简单而准确的方法：总预估时间 - 已花费时间
        remaining = max(self.estimated_duration - elapsed_time, 0)

        # 如果已经超过预估时间，根据当前进度动态调整
        if remaining <= 0 and progress > 0:
            # 基于当前进度重新估算总时间，然后计算剩余
            estimated_total = elapsed_time / progress
            remaining = max(estimated_total - elapsed_time, 0)

        return remaining
    
    def _save_progress(self):
        """保存进度到存储"""
        try:
            current_step_name = self.progress_data.get('current_step_name', '未知')
            progress_pct = self.progress_data.get('progress_percentage', 0)
            status = self.progress_data.get('status', 'running')

            if self.use_redis:
                # 保存到Redis（安全序列化）
                key = f"progress:{self.analysis_id}"
                safe_data = safe_serialize(self.progress_data)
                data_json = json.dumps(safe_data, ensure_ascii=False)
                self.redis_client.setex(key, 3600, data_json)  # 1小时过期

                logger.info(f"📊 [Redis写入] {self.analysis_id} -> {status} | {current_step_name} | {progress_pct:.1f}%")
                logger.debug(f"📊 [Redis详情] 键: {key}, 数据大小: {len(data_json)} 字节")
            else:
                # 保存到文件（安全序列化）
                safe_data = safe_serialize(self.progress_data)
                with open(self.progress_file, 'w', encoding='utf-8') as f:
                    json.dump(safe_data, f, ensure_ascii=False, indent=2)

                logger.info(f"📊 [文件写入] {self.analysis_id} -> {status} | {current_step_name} | {progress_pct:.1f}%")
                logger.debug(f"📊 [文件详情] 路径: {self.progress_file}")

        except Exception as e:
            logger.error(f"📊 [异步进度] 保存失败: {e}")
            # 尝试备用存储方式
            try:
                if self.use_redis:
                    # Redis失败，尝试文件存储
                    logger.warning(f"📊 [异步进度] Redis保存失败，尝试文件存储")
                    backup_file = f"./data/progress_{self.analysis_id}.json"
                    os.makedirs(os.path.dirname(backup_file), exist_ok=True)
                    safe_data = safe_serialize(self.progress_data)
                    with open(backup_file, 'w', encoding='utf-8') as f:
                        json.dump(safe_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"📊 [备用存储] 文件保存成功: {backup_file}")
                else:
                    # 文件存储失败，尝试简化数据
                    logger.warning(f"📊 [异步进度] 文件保存失败，尝试简化数据")
                    simplified_data = {
                        'analysis_id': self.analysis_id,
                        'status': self.progress_data.get('status', 'unknown'),
                        'progress_percentage': self.progress_data.get('progress_percentage', 0),
                        'last_message': str(self.progress_data.get('last_message', '')),
                        'last_update': self.progress_data.get('last_update', time.time())
                    }
                    backup_file = f"./data/progress_{self.analysis_id}.json"
                    with open(backup_file, 'w', encoding='utf-8') as f:
                        json.dump(simplified_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"📊 [备用存储] 简化数据保存成功: {backup_file}")
            except Exception as backup_e:
                logger.error(f"📊 [异步进度] 备用存储也失败: {backup_e}")
    
    def get_progress(self) -> Dict[str, Any]:
        """获取当前进度"""
        return self.progress_data.copy()
    
    def mark_completed(self, message: str = "分析完成", results: Any = None):
        """标记分析完成"""
        self.update_progress(message)
        self.progress_data['status'] = 'completed'
        self.progress_data['progress_percentage'] = 100.0
        self.progress_data['remaining_time'] = 0.0

        # 保存分析结果（安全序列化）
        if results is not None:
            try:
                self.progress_data['raw_results'] = safe_serialize(results)
                logger.info(f"📊 [异步进度] 保存分析结果: {self.analysis_id}")
            except Exception as e:
                logger.warning(f"📊 [异步进度] 结果序列化失败: {e}")
                self.progress_data['raw_results'] = str(results)  # 最后的fallback

        self._save_progress()
        
        # 发送完成状态消息
        if self.message_producer:
            try:
                from tradingagents.messaging.business.messages import TaskStatus
                self.message_producer.publish_status(
                    self.analysis_id, 
                    TaskStatus.COMPLETED, 
                    message
                )
            except Exception as e:
                logger.warning(f"📊 [消息系统] 发布完成状态失败: {e}")
        
        logger.info(f"📊 [异步进度] 分析完成: {self.analysis_id}")

        # 从日志系统注销（兼容模式）
        if not self.message_producer:
            try:
                from .progress_log_handler import unregister_analysis_tracker
                unregister_analysis_tracker(self.analysis_id)
            except ImportError:
                pass
        
        # 从消息系统注销
        if self.message_producer:
            try:
                from tradingagents.messaging.config import get_progress_handler
                progress_handler = get_progress_handler()
                if progress_handler:
                    progress_handler.unregister_tracker(self.analysis_id)
            except Exception as e:
                logger.warning(f"📊 [消息系统] 注销跟踪器失败: {e}")
    
    def mark_failed(self, error_message: str):
        """标记分析失败"""
        self.progress_data['status'] = 'failed'
        self.progress_data['control_state'] = 'stopped'
        self.progress_data['last_message'] = f"分析失败: {error_message}"
        self.progress_data['last_update'] = time.time()
        self._save_progress()
        
        # 发送失败状态消息
        if self.message_producer:
            try:
                from tradingagents.messaging.business.messages import TaskStatus
                self.message_producer.publish_status(
                    self.analysis_id, 
                    TaskStatus.FAILED, 
                    f"分析失败: {error_message}"
                )
            except Exception as e:
                logger.warning(f"📊 [消息系统] 发布失败状态失败: {e}")
        
        logger.error(f"📊 [异步进度] 分析失败: {self.analysis_id}, 错误: {error_message}")

        # 从日志系统注销（兼容模式）
        if not self.message_producer:
            try:
                from .progress_log_handler import unregister_analysis_tracker
                unregister_analysis_tracker(self.analysis_id)
            except ImportError:
                pass
        
        # 从消息系统注销
        if self.message_producer:
            try:
                from tradingagents.messaging.config import get_progress_handler
                progress_handler = get_progress_handler()
                if progress_handler:
                    progress_handler.unregister_tracker(self.analysis_id)
            except Exception as e:
                logger.warning(f"📊 [消息系统] 注销跟踪器失败: {e}")
    
    def mark_paused(self):
        """标记任务暂停"""
        self.pause_start_time = time.time()
        self.progress_data['control_state'] = 'paused'
        self.progress_data['pause_start_time'] = self.pause_start_time
        self.progress_data['last_message'] = '⏸️ 任务已暂停'
        self.progress_data['last_update'] = time.time()
        self._save_progress()
        logger.info(f"⏸️ [异步进度] 任务已暂停: {self.analysis_id}")
    
    def mark_resumed(self):
        """标记任务恢复"""
        if self.pause_start_time:
            # 累计暂停时长
            pause_duration = time.time() - self.pause_start_time
            self.total_pause_duration += pause_duration
            self.pause_start_time = None
        
        self.progress_data['control_state'] = 'running'
        self.progress_data['pause_start_time'] = None
        self.progress_data['total_pause_duration'] = self.total_pause_duration
        self.progress_data['last_message'] = '▶️ 任务已恢复'
        self.progress_data['last_update'] = time.time()
        self._save_progress()
        logger.info(f"▶️ [异步进度] 任务已恢复: {self.analysis_id}")
    
    def mark_stopped(self, message: str = "任务已停止"):
        """标记任务停止"""
        self.progress_data['status'] = 'stopped'
        self.progress_data['control_state'] = 'stopped'
        self.progress_data['last_message'] = f"⏹️ {message}"
        self.progress_data['last_update'] = time.time()
        self._save_progress()
        
        # 发送停止状态消息
        if self.message_producer:
            try:
                from tradingagents.messaging.business.messages import TaskStatus
                self.message_producer.publish_status(
                    self.analysis_id, 
                    TaskStatus.STOPPED, 
                    message
                )
            except Exception as e:
                logger.warning(f"📊 [消息系统] 发布停止状态失败: {e}")
        
        logger.info(f"⏹️ [异步进度] 任务已停止: {self.analysis_id}")
        
        # 从日志系统注销（兼容模式）
        if not self.message_producer:
            try:
                from .progress_log_handler import unregister_analysis_tracker
                unregister_analysis_tracker(self.analysis_id)
            except ImportError:
                pass
        
        # 从消息系统注销
        if self.message_producer:
            try:
                from tradingagents.messaging.config import get_progress_handler
                progress_handler = get_progress_handler()
                if progress_handler:
                    progress_handler.unregister_tracker(self.analysis_id)
            except Exception as e:
                logger.warning(f"📊 [消息系统] 注销跟踪器失败: {e}")
    
    def get_effective_elapsed_time(self) -> float:
        """获取有效已用时间（排除暂停时长）"""
        current_time = time.time()
        total_elapsed = current_time - self.start_time
        
        # 如果当前正在暂停中，计算当前暂停时长
        current_pause_duration = 0.0
        if self.pause_start_time:
            current_pause_duration = current_time - self.pause_start_time
        
        # 有效时长 = 总时长 - 历史暂停时长 - 当前暂停时长
        effective_time = total_elapsed - self.total_pause_duration - current_pause_duration
        return max(effective_time, 0.0)

def get_progress_by_id(analysis_id: str) -> Optional[Dict[str, Any]]:
    """根据分析ID获取进度"""
    try:
        # 检查REDIS_ENABLED环境变量
        redis_enabled = os.getenv('REDIS_ENABLED', 'false').lower() == 'true'

        # 如果Redis启用，先尝试Redis
        if redis_enabled:
            try:
                import redis

                # 从环境变量获取Redis配置
                redis_host = os.getenv('REDIS_HOST', 'localhost')
                redis_port = int(os.getenv('REDIS_PORT', 6379))
                redis_password = os.getenv('REDIS_PASSWORD', None)
                redis_db = int(os.getenv('REDIS_DB', 0))

                # 创建Redis连接
                if redis_password:
                    redis_client = redis.Redis(
                        host=redis_host,
                        port=redis_port,
                        password=redis_password,
                        db=redis_db,
                        decode_responses=True
                    )
                else:
                    redis_client = redis.Redis(
                        host=redis_host,
                        port=redis_port,
                        db=redis_db,
                        decode_responses=True
                    )

                key = f"progress:{analysis_id}"
                data = redis_client.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.debug(f"📊 [异步进度] Redis读取失败: {e}")

        # 尝试文件
        progress_file = f"./data/progress_{analysis_id}.json"
        if os.path.exists(progress_file):
            with open(progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        return None
    except Exception as e:
        logger.error(f"📊 [异步进度] 获取进度失败: {analysis_id}, 错误: {e}")
        return None

def format_time(seconds: float) -> str:
    """格式化时间显示"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"


def get_latest_analysis_id() -> Optional[str]:
    """获取最新的分析ID"""
    try:
        # 检查REDIS_ENABLED环境变量
        redis_enabled = os.getenv('REDIS_ENABLED', 'false').lower() == 'true'

        # 如果Redis启用，先尝试从Redis获取
        if redis_enabled:
            try:
                import redis

                # 从环境变量获取Redis配置
                redis_host = os.getenv('REDIS_HOST', 'localhost')
                redis_port = int(os.getenv('REDIS_PORT', 6379))
                redis_password = os.getenv('REDIS_PASSWORD', None)
                redis_db = int(os.getenv('REDIS_DB', 0))

                # 创建Redis连接
                if redis_password:
                    redis_client = redis.Redis(
                        host=redis_host,
                        port=redis_port,
                        password=redis_password,
                        db=redis_db,
                        decode_responses=True
                    )
                else:
                    redis_client = redis.Redis(
                        host=redis_host,
                        port=redis_port,
                        db=redis_db,
                        decode_responses=True
                    )

                # 获取所有progress键
                keys = redis_client.keys("progress:*")
                if not keys:
                    return None

                # 获取每个键的数据，找到最新的
                latest_time = 0
                latest_id = None

                for key in keys:
                    try:
                        data = redis_client.get(key)
                        if data:
                            progress_data = json.loads(data)
                            last_update = progress_data.get('last_update', 0)
                            if last_update > latest_time:
                                latest_time = last_update
                                # 从键名中提取analysis_id (去掉"progress:"前缀)
                                latest_id = key.replace('progress:', '')
                    except Exception:
                        continue

                if latest_id:
                    logger.debug(f"📊 [恢复分析] 找到最新分析ID: {latest_id}")
                    return latest_id

            except Exception as e:
                logger.error(f"📊 [恢复分析] Redis查找失败: {e}")

        # 如果Redis失败或未启用，尝试从文件查找
        data_dir = Path("data")
        if data_dir.exists():
            progress_files = list(data_dir.glob("progress_*.json"))
            if progress_files:
                # 按修改时间排序，获取最新的
                latest_file = max(progress_files, key=lambda f: f.stat().st_mtime)
                # 从文件名提取analysis_id
                filename = latest_file.name
                if filename.startswith("progress_") and filename.endswith(".json"):
                    analysis_id = filename[9:-5]  # 去掉前缀和后缀
                    logger.debug(f"📊 [恢复分析] 从文件找到最新分析ID: {analysis_id}")
                    return analysis_id

        return None
    except Exception as e:
        logger.error(f"📊 [恢复分析] 获取最新分析ID失败: {e}")
        return None
