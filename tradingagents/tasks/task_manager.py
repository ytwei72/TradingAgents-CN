"""
任务管理器模块
负责任务的创建、执行和生命周期管理
"""
import json
import os
import time
import threading
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from tradingagents.utils.logging_manager import get_logger
from tradingagents.tasks.task_state_machine import TaskStateMachine, TaskStatus
from tradingagents.utils.analysis_runner import run_stock_analysis

logger = get_logger('task_manager')

# 步骤显示名称映射 (保持与 async_progress_tracker.py 一致)
STEP_DISPLAY_NAMES = {
    # 准备阶段
    "analysis_start": "🚀 分析启动",
    "cost_estimation": "💰 成本估算",
    "data_preparation": "🔍 数据预获取和验证",
    "environment_validation": "🔧 环境验证",
    "config_builder": "⚙️ 构建配置",
    "symbol_formatting": "📝 格式化股票代码",
    "graph_initialization": "🏗️ 初始化分析引擎",
    "step_output_directory": "📁 步骤输出目录准备",
    # 分析师阶段
    "market_analyst": "📈 市场分析师",
    "market": "📈 市场分析师",
    "fundamentals_analyst": "💰 基本面分析师",
    "fundamentals": "💰 基本面分析师",
    "news_analyst": "📰 新闻分析师",
    "news": "📰 新闻分析师",
    "social_media_analyst": "💭 社交媒体分析师",
    "social": "💭 社交媒体分析师",
    "risk_analyst": "⚠️ 风险分析师",
    "risk": "⚠️ 风险分析师",
    "technical_analyst": "📈 技术分析师",
    "technical": "📈 技术分析师",
    "sentiment_analyst": "💭 情绪分析师",
    "sentiment": "💭 情绪分析师",
    # 研究团队
    "bull": "🐂 看涨研究员",
    "bear": "🐻 看跌研究员",
    "manager": "👔 研究经理",
    # 交易决策
    "trader": "💼 交易员",
    # 风险评估
    "risky": "🔥 激进风险分析师",
    "safe": "🛡️ 保守风险分析师",
    "neutral": "⚖️ 中性风险分析师",
    "judge": "🎯 风险经理",
    "risk_tip": "⚠️ 风险提示",
    # 后处理
    "graph_signal_processing": "📡 信号处理",
    "result_processing": "📊 处理分析结果",
    "completion_logging": "✅ 记录完成日志",
    "save_results": "💾 保存分析结果",
}

class AnalysisTask(threading.Thread):
    """分析任务线程包装类"""
    
    def __init__(self, task_id: str, params: Dict[str, Any]):
        super().__init__(name=f"AnalysisTask-{task_id}")
        self.task_id = task_id
        self.params = params
        self.state_machine = TaskStateMachine(task_id)
        self._stop_event = threading.Event()
        
        # 在初始化时立即创建任务状态
        self.planned_steps = self.generate_planned_steps()
        self.state_machine.initialize(self.params, self.planned_steps)
    
    def calculate_total_steps(self) -> int:
        """计算任务总步骤数"""
        return len(self.planned_steps)
    
    def generate_planned_steps(self) -> List[Dict[str, Any]]:
        """生成任务计划步骤列表 (与 async_progress_tracker.py 保持一致)"""
        steps = []
        step_index = 1
        
        # 1. 准备阶段 (8步)
        preparation_steps = [
            ("analysis_start", "🚀 分析启动", "记录分析开始日志，初始化分析会话ID"),
            ("cost_estimation", "💰 成本估算", "根据选择的分析师和研究深度估算分析成本，显示预估Token使用量和费用"),
            ("data_preparation", "🔍 数据预获取和验证", "验证股票代码格式和有效性，预获取股票基础数据（30天历史数据），缓存数据以提高效率"),
            ("environment_validation", "🔧 环境验证", "检查API密钥配置（DASHSCOPE_API_KEY、FINNHUB_API_KEY等），验证必要的环境变量"),
            ("config_builder", "⚙️ 构建配置", "根据选择的LLM提供商和模型构建配置，设置研究深度、市场类型等参数"),
            ("symbol_formatting", "📝 格式化股票代码", "根据市场类型格式化股票代码（A股/港股/美股），确保代码格式符合数据源要求"),
            ("graph_initialization", "🏗️ 初始化分析引擎", "创建TradingAgentsGraph实例，初始化所有智能体和工具节点，配置模拟模式（如果启用）"),
            ("step_output_directory", "📁 步骤输出目录准备", "创建步骤输出保存目录，准备保存每步执行结果"),
        ]
        for step_name, display_name, desc in preparation_steps:
            steps.append({
                "step_index": step_index,
                "step_name": step_name,
                "display_name": display_name,
                "description": desc,
                "phase": "preparation",
                "status": "pending"
            })
            step_index += 1
        
        # 2. 分析师阶段
        analysts = self.params.get('analysts', [])
        analyst_mapping = {
            "market": "market_analyst",
            "fundamentals": "fundamentals_analyst",
            "news": "news_analyst",
            "social": "social_media_analyst",
            "risk": "risk_analyst",
            "technical": "technical_analyst",
            "sentiment": "sentiment_analyst",
        }
        
        # 完整的分析师描述映射
        analyst_descriptions = {
            "market_analyst": "技术面分析：K线形态、均线系统、价格趋势。技术指标分析：MACD、RSI、KDJ、布林带等。支撑阻力位分析、成交量分析。输出保存：market_report字段",
            "fundamentals_analyst": "财务数据分析：营收、利润、现金流、财务比率。公司基本面研究：业务模式、竞争优势。估值水平评估：PE、PB、PS、ROE等估值指标。输出保存：fundamentals_report字段",
            "news_analyst": "新闻事件收集：相关新闻抓取和筛选。事件影响分析：重大事件对股价的影响评估。市场动态追踪：行业动态、政策变化。输出保存：news_report字段",
            "social_media_analyst": "社交媒体数据采集：Reddit、Twitter等平台。投资者情绪分析：散户情绪、机构观点。热度指标监测：讨论热度、关注度变化。输出保存：sentiment_report字段（非A股市场）",
            "risk_analyst": "识别投资风险、评估风险等级、制定风控措施",
            "technical_analyst": "分析K线图形、技术指标、支撑阻力等技术面",
            "sentiment_analyst": "分析市场情绪、投资者心理、舆论倾向等",
        }
        
        for analyst in analysts:
            full_name = analyst_mapping.get(analyst, analyst)
            display_name = STEP_DISPLAY_NAMES.get(full_name, STEP_DISPLAY_NAMES.get(analyst, f"🔍 {analyst}分析师"))
            
            # 确保描述包含统一后缀
            base_desc = analyst_descriptions.get(full_name, f"进行{analyst}相关的专业分析")
            desc = f"{base_desc}（每个节点的输出都会被实时保存到步骤文件）"
            
            steps.append({
                "step_index": step_index,
                "step_name": full_name,
                "display_name": display_name,
                "description": desc,
                "phase": "analyst",
                "status": "pending"
            })
            step_index += 1
        
        # 获取配置中的轮数和深度
        research_depth = self.params.get('research_depth', 2)
        extra_config = self.params.get('extra_config', {}) or {}
        max_debate_rounds = extra_config.get('max_debate_rounds', 1)
        # max_risk_discuss_rounds = extra_config.get('max_risk_discuss_rounds', 1) # 暂时没用到

        # 3. 研究团队辩论阶段 (深度 >= 2)
        if research_depth >= 2:
            # 标准和深度分析包含研究员辩论
            debate_roles = [
                ("bull_researcher", "🐂 看涨研究员", "从乐观角度分析投资机会，输出看涨观点和投资理由。输出保存：investment_debate_state.bull_history"),
                ("bear_researcher", "🐻 看跌研究员", "从谨慎角度分析投资风险，输出看跌观点和风险提醒。输出保存：investment_debate_state.bear_history"),
                ("research_manager", "👔 研究经理", "综合多头和空头观点，做出综合投资判断。输出保存：investment_debate_state.judge_decision、investment_plan"),
            ]
            
            for step_name, display_name, desc in debate_roles:
                steps.append({
                    "step_index": step_index,
                    "step_name": step_name,
                    "display_name": display_name,
                    "description": desc,
                    "phase": "debate",
                    "status": "pending"
                })
                step_index += 1
        
        # 4. 交易决策阶段 (所有深度)
        steps.append({
            "step_index": step_index,
            "step_name": "trader",
            "display_name": "💼 交易员",
            "description": "基于研究结果制定交易计划，输出具体的投资建议和执行策略。输出保存：trader_investment_plan",
            "phase": "trading",
            "status": "pending"
        })
        step_index += 1
        
        # 5. 风险评估阶段
        if research_depth >= 3:
            # 深度分析包含详细风险评估
            risk_roles = [
                ("risky_analyst", "🔥 激进风险分析师", "从高风险高收益角度分析，输出激进策略建议。输出保存：risk_debate_state.risky_history"),
                ("safe_analyst", "🛡️ 保守风险分析师", "从风险控制角度分析，输出保守策略建议。输出保存：risk_debate_state.safe_history"),
                ("neutral_analyst", "⚖️ 中性风险分析师", "从平衡角度分析风险，输出平衡策略建议。输出保存：risk_debate_state.neutral_history"),
                ("risk_manager", "🎯 风险经理", "综合各方风险评估，做出最终风险决策和风险评级。输出保存：risk_debate_state.judge_decision、final_trade_decision"),
            ]
            for step_name, display_name, desc in risk_roles:
                steps.append({
                    "step_index": step_index,
                    "step_name": step_name,
                    "display_name": display_name,
                    "description": desc,
                    "phase": "risk_assessment",
                    "status": "pending"
                })
                step_index += 1
        else:
            # 快速和标准分析的简化风险评估
            steps.append({
                "step_index": step_index,
                "step_name": "risk_tip",
                "display_name": "⚠️ 风险提示",
                "description": "识别主要投资风险并提供风险提示（快速和标准分析模式）",
                "phase": "risk_assessment",
                "status": "pending"
            })
            step_index += 1
        
        # 6. 后处理阶段
        post_processing_steps = [
            ("graph_signal_processing", "📡 信号处理", "处理最终交易决策信号，提取结构化的投资建议（买入/持有/卖出）"),
            ("result_processing", "📊 处理分析结果", "提取风险评估数据，记录Token使用情况，格式化分析结果用于显示"),
            ("completion_logging", "✅ 记录完成日志", "记录分析完成时间，计算总耗时和总成本"),
            ("save_results", "💾 保存分析结果", "保存分模块报告到本地目录，保存分析报告到MongoDB，步骤输出已实时保存到eval_results目录"),
        ]
        
        for step_name, display_name, desc in post_processing_steps:
            steps.append({
                "step_index": step_index,
                "step_name": step_name,
                "display_name": display_name,
                "description": desc,
                "phase": "post_processing",
                "status": "pending"
            })
            step_index += 1
            
        return steps
    
    def estimate_remaining_time(self) -> float:
        """估算剩余时间
        
        基于已完成步骤的平均耗时计算剩余时间。
        如果还没有完成任何步骤，使用默认每步5秒估算。
        
        Returns:
            预估剩余时间（秒）
        """
        task_obj = self.state_machine.get_task_object()
        if not task_obj:
            return self.calculate_total_steps() * 5.0
        
        progress = task_obj.get('progress', {})
        current_step = progress.get('current_step', 0)
        total_steps = progress.get('total_steps', self.calculate_total_steps())
        elapsed_time = progress.get('elapsed_time', 0.0)
        
        remaining_steps = max(0, total_steps - current_step)
        
        if current_step > 0 and elapsed_time > 0:
            # 基于实际平均耗时估算
            avg_time_per_step = elapsed_time / current_step
            return remaining_steps * avg_time_per_step
        else:
            # 默认每步5秒
            return remaining_steps * 5.0
        
    def run(self):
        """执行任务逻辑"""
        logger.info(f"🚀 [任务启动] 开始执行任务: {self.task_id}")
        
        try:
            # 更新状态为运行中
            total_steps = self.calculate_total_steps()
            self.state_machine.update_state({
                'status': TaskStatus.RUNNING.value,
                'progress': {
                    'current_step': 0,
                    'total_steps': total_steps,
                    'percentage': 0.0,
                    'message': '分析任务开始执行',
                    'elapsed_time': 0.0,
                    'remaining_time': self.estimate_remaining_time(),
                },
            })
            
            # 定义进度回调
            def progress_callback(message, step=None, total_steps=None):
                self.state_machine.update_state({
                    'progress': {
                        'current_step': step if step is not None else 0,
                        'total_steps': total_steps if total_steps is not None else 0,
                        'percentage': (step / total_steps * 100) if (step and total_steps) else 0,
                        'message': message,
                    },
                })

            # 准备参数
            stock_symbol = self.params.get('stock_symbol')
            market_type = self.params.get('market_type', '美股')
            analysis_date = self.params.get('analysis_date')
            analysts = self.params.get('analysts', [])
            research_depth = self.params.get('research_depth', 3)

            if not analysis_date:
                analysis_date = datetime.now().strftime('%Y-%m-%d')

            # 执行分析
            results = run_stock_analysis(
                stock_symbol=stock_symbol,
                analysis_date=analysis_date,
                analysts=analysts,
                research_depth=research_depth,
                market_type=market_type,
                progress_callback=progress_callback,
                analysis_id=self.task_id
            )
            
            # 检查结果
            if results.get('success', False):
                self.state_machine.update_state({
                    'status': TaskStatus.COMPLETED.value,
                    'result': results,
                    'progress': {
                        'percentage': 100.0,
                        'message': '分析任务已完成',
                    },
                })
            elif results.get('stopped', False):
                # 任务被用户停止，状态已在 stop_task() 中更新为 STOPPED
                # 这里不需要再更新状态，只记录日志
                logger.info(f"⏹️ [任务停止] 任务已停止: {self.task_id}")
            else:
                # 失败
                error_msg = results.get('error', 'Unknown error')
                self.state_machine.update_state({
                    'status': TaskStatus.FAILED.value,
                    'error': error_msg,
                })

        except Exception as e:
            logger.error(f"❌ [任务失败] 任务执行异常: {self.task_id}, {e}", exc_info=True)
            self.state_machine.update_state({
                'status': TaskStatus.FAILED.value,
                'error': str(e),
            })
        finally:
            logger.info(f"🏁 [任务结束] 任务线程退出: {self.task_id}")
            # 清理任务控制资源
            from tradingagents.tasks import get_task_manager
            get_task_manager().cleanup_task(self.task_id)


class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, AnalysisTask] = {}
        # TaskManager 不再持有 state_machine 实例
        
        # 任务控制相关状态
        self._control_events: Dict[str, threading.Event] = {}  # 停止事件
        self._pause_events: Dict[str, threading.Event] = {}    # 暂停事件
        self._task_states: Dict[str, str] = {}                 # 任务状态: running/paused/stopped
        self._checkpoints: Dict[str, Any] = {}                 # 任务检查点
        self._lock = threading.Lock()
        
        # 持久化目录
        self.checkpoint_dir = Path("./data/checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
    def start_task(self, params: Dict[str, Any]) -> str:
        """启动新任务"""
        # 生成 ID
        task_id = str(uuid.uuid4())
        params['task_id'] = task_id
        
        # 注册任务控制(原 register_task 逻辑)
        with self._lock:
            # 创建停止事件(未设置表示继续运行)
            self._control_events[task_id] = threading.Event()
            # 创建暂停事件(未设置表示正常运行,设置表示暂停)
            self._pause_events[task_id] = threading.Event()
            # 初始状态为运行中
            self._task_states[task_id] = 'running'
            logger.info(f"📋 [任务控制] 注册任务: {task_id}")
        
        # 创建并启动任务(AnalysisTask 负责在状态机中创建记录)
        task = AnalysisTask(task_id, params)
        self.tasks[task_id] = task
        task.start()
        
        return task_id

        
    def stop_task(self, task_id: str) -> bool:
        """停止任务
        
        注意：此方法设置停止标志，但不会立即删除控制事件。
        控制事件会在任务线程检测到停止信号并退出后，由 cleanup_task() 方法清理。
        """
        with self._lock:
            if task_id not in self._control_events:
                logger.warning(f"⚠️ [任务控制] 任务不存在: {task_id}")
                return False
            
            # 设置停止标志
            self._control_events[task_id].set()
            # 如果任务处于暂停状态，也要恢复以便能够检测到停止信号
            if self._pause_events[task_id].is_set():
                self._pause_events[task_id].clear()
            
            self._task_states[task_id] = 'stopped'
            
            # 保存停止状态到文件
            self._save_task_state(task_id)
            
            logger.info(f"⏹️ [任务控制] 任务停止信号已发送: {task_id}")
            success = True
        
        # 更新状态机
        if success:
            self._get_task_state_machine(task_id).update_state({
                'status': TaskStatus.STOPPED.value,
                'progress': {'message': '任务已停止'}
            })
        
        # 不再立即清理控制事件，等待任务线程退出后由 cleanup_task() 清理
        return success
    
    def cleanup_task(self, task_id: str):
        """清理任务资源（在任务线程退出后调用）"""
        with self._lock:
            if task_id in self._control_events:
                del self._control_events[task_id]
            if task_id in self._pause_events:
                del self._pause_events[task_id]
            if task_id in self._task_states:
                del self._task_states[task_id]
            if task_id in self._checkpoints:
                del self._checkpoints[task_id]
            logger.info(f"📋 [任务控制] 任务资源已清理: {task_id}")

    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        with self._lock:
            if task_id not in self._pause_events:
                logger.warning(f"⚠️ [任务控制] 任务不存在: {task_id}")
                return False
            
            if self._task_states.get(task_id) == 'stopped':
                logger.warning(f"⚠️ [任务控制] 任务已停止，无法暂停: {task_id}")
                return False
            
            # 设置暂停标志
            self._pause_events[task_id].set()
            self._task_states[task_id] = 'paused'
            
            # 保存暂停状态到文件
            self._save_task_state(task_id)
            
            logger.info(f"⏸️ [任务控制] 任务已暂停: {task_id}")
            success = True

        if success:
            self._get_task_state_machine(task_id).update_state({
                'status': TaskStatus.PAUSED.value,
                'step_status': TaskStatus.PAUSED.value
            })
        return success

    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        with self._lock:
            if task_id not in self._pause_events:
                logger.warning(f"⚠️ [任务控制] 任务不存在: {task_id}")
                return False
            
            if self._task_states.get(task_id) == 'stopped':
                logger.warning(f"⚠️ [任务控制] 任务已停止，无法恢复: {task_id}")
                return False
            
            # 清除暂停标志
            self._pause_events[task_id].clear()
            self._task_states[task_id] = 'running'
            
            # 保存运行状态到文件
            self._save_task_state(task_id)
            
            logger.info(f"▶️ [任务控制] 任务已恢复: {task_id}")
            success = True

        if success:
            self._get_task_state_machine(task_id).update_state({
                'status': TaskStatus.RUNNING.value,
                'step_status': TaskStatus.RUNNING.value
            })
        return success
        
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return self._get_task_state_machine(task_id).get_task_object()

    def get_task_history(self, task_id: str) -> List[Dict[str, Any]]:
        """获取任务历史"""
        return self._get_task_state_machine(task_id).get_history_states()

    def get_task_current_step(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务当前步骤状态"""
        return self._get_task_state_machine(task_id).get_current_state()
    
    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务结果"""
        state = self.get_task_status(task_id)
        if state and state.get('status') == TaskStatus.COMPLETED.value:
            return state.get('result')
        return None

    def get_task_planned_steps(self, task_id: str) -> List[Dict[str, Any]]:
        """获取任务计划步骤"""
        task = self.tasks.get(task_id)
        if task:
            return task.planned_steps
        return []

    def _get_task_state_machine(self, task_id: str) -> TaskStateMachine:
        """获取任务状态机实例"""
        if task_id in self.tasks:
            return self.tasks[task_id].state_machine
        return TaskStateMachine(task_id)

    def should_stop(self, analysis_id: str) -> bool:
        """检查任务是否应该停止"""
        if analysis_id not in self._control_events:
            return False
        return self._control_events[analysis_id].is_set()
    
    def should_pause(self, analysis_id: str) -> bool:
        """检查任务是否应该暂停"""
        if analysis_id not in self._pause_events:
            return False
        return self._pause_events[analysis_id].is_set()
    
    def wait_if_paused(self, analysis_id: str, check_interval: float = 0.5):
        """如果任务被暂停，则等待直到恢复或停止
        
        Args:
            analysis_id: 任务ID
            check_interval: 检查间隔（秒）
        """
        while self.should_pause(analysis_id):
            # 检查是否被停止
            if self.should_stop(analysis_id):
                logger.info(f"⏹️ [任务控制] 暂停中的任务收到停止信号: {analysis_id}")
                return
            
            # 等待一段时间后再次检查
            time.sleep(check_interval)
    
    def get_task_control_state(self, analysis_id: str) -> str:
        """获取任务控制状态"""
        with self._lock:
            return self._task_states.get(analysis_id, 'unknown')
    
    def save_checkpoint(self, analysis_id: str, checkpoint_data: Dict[str, Any]):
        """保存任务检查点"""
        with self._lock:
            self._checkpoints[analysis_id] = checkpoint_data
            
            # 保存到文件
            checkpoint_file = self.checkpoint_dir / f"checkpoint_{analysis_id}.json"
            try:
                with open(checkpoint_file, 'w', encoding='utf-8') as f:
                    json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
                logger.debug(f"💾 [检查点] 保存成功: {analysis_id}")
            except Exception as e:
                logger.error(f"❌ [检查点] 保存失败: {e}")
    
    def load_checkpoint(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """加载任务检查点"""
        # 先从内存加载
        with self._lock:
            if analysis_id in self._checkpoints:
                return self._checkpoints[analysis_id]
        
        # 从文件加载
        checkpoint_file = self.checkpoint_dir / f"checkpoint_{analysis_id}.json"
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)
                
                with self._lock:
                    self._checkpoints[analysis_id] = checkpoint_data
                
                logger.info(f"📂 [检查点] 从文件加载成功: {analysis_id}")
                return checkpoint_data
            except Exception as e:
                logger.error(f"❌ [检查点] 从文件加载失败: {e}")
        
        return None
    
    def _save_task_state(self, analysis_id: str):
        """保存任务状态到文件"""
        state_file = self.checkpoint_dir / f"state_{analysis_id}.json"
        try:
            state_data = {
                'analysis_id': analysis_id,
                'state': self._task_states.get(analysis_id, 'unknown'),
                'is_paused': self._pause_events[analysis_id].is_set() if analysis_id in self._pause_events else False,
                'is_stopped': self._control_events[analysis_id].is_set() if analysis_id in self._control_events else False,
                'timestamp': time.time()
            }
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"💾 [任务状态] 保存成功: {analysis_id} -> {state_data['state']}")
        except Exception as e:
            logger.error(f"❌ [任务状态] 保存失败: {e}")
    
    def load_task_state(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """从文件加载任务状态"""
        state_file = self.checkpoint_dir / f"state_{analysis_id}.json"
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"❌ [任务状态] 从文件加载失败: {e}")
        return None
    
    def get_all_task_states(self) -> Dict[str, str]:
        """获取所有任务状态"""
        with self._lock:
            return self._task_states.copy()
    
    def cleanup_old_checkpoints(self, max_age_hours: int = 24):
        """清理旧的检查点文件"""
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            cleaned = 0
            for file in self.checkpoint_dir.glob("*.json"):
                if file.stat().st_mtime < current_time - max_age_seconds:
                    file.unlink()
                    cleaned += 1
            
            if cleaned > 0:
                logger.info(f"🧹 [清理] 清理了 {cleaned} 个旧检查点文件")
        except Exception as e:
            logger.error(f"❌ [清理] 清理检查点文件失败: {e}")

    def update_task_progress(self, task_id: str, step_name: str, exec_msg: str, status: str):
        """更新任务进度状态并发布状态更新消息
        
        Args:
            task_id: 任务ID
            step_name: 步骤名称
            exec_msg: 执行消息
            status: 状态 ('start', 'success', 'error')
        """
        if not task_id:
            return
        
        state_machine = self._get_task_state_machine(task_id)
        
        # 获取任务计划步骤以查找 step_index
        planned_steps = self.get_task_planned_steps(task_id)
        step_index = 0
        
        # 查找对应的 step_index
        # 查找对应的 step_index 和信息
        step_desc = ""
        step_display = step_name
        for step in planned_steps:
            if step['step_name'] == step_name:
                step_index = step['step_index']
                step_desc = step.get('description', '')
                step_display = step.get('display_name', step_name)
                break
        
        # 获取任务的总步骤数
        total_steps = len(planned_steps) if planned_steps else 10
        
        # 计算进度百分比
        if total_steps > 0:
            if status == 'start':
                percentage = ((step_index - 1) / total_steps) * 100
            else:
                percentage = (step_index / total_steps) * 100
        else:
            percentage = 0
        
        # 计算 elapsed_time
        task_obj = state_machine.get_task_object()
        if task_obj:
            created_at = task_obj.get('created_at', datetime.now().isoformat())
            created_time = datetime.fromisoformat(created_at)
            elapsed_time = (datetime.now() - created_time).total_seconds()
        else:
            elapsed_time = 0.0
        
        # 估算剩余时间
        remaining_steps = max(0, total_steps - step_index)
        if step_index > 0 and elapsed_time > 0:
            avg_time_per_step = elapsed_time / step_index
            remaining_time = remaining_steps * avg_time_per_step
        else:
            remaining_time = remaining_steps * 5.0  # 默认每步5秒
        
        updates = {
            'progress': {
                'current_step': step_index,
                'total_steps': total_steps,
                'percentage': percentage,
                'message': exec_msg,
                'elapsed_time': elapsed_time,
                'remaining_time': remaining_time,
            },
            'step_name': step_name,
            'step_status': status,
        }
        state_machine.update_state(updates)
        
        # 发布消息
        # 发布消息
        try:
            from tradingagents.messaging.config import get_message_producer, is_message_mode_enabled
            from tradingagents.messaging.business.messages import TaskProgressMessage, NodeStatus
            
            if is_message_mode_enabled():
                producer = get_message_producer()
                if producer:
                    # 映射状态
                    node_status_map = {
                        'start': NodeStatus.START.value,
                        'success': NodeStatus.COMPLETE.value,
                        'error': NodeStatus.ERROR.value
                    }
                    node_status = node_status_map.get(status, NodeStatus.START.value)
                    
                    # 构建进度消息
                    progress_msg = TaskProgressMessage(
                        analysis_id=task_id,
                        current_step=step_index,
                        total_steps=total_steps,
                        progress_percentage=percentage,
                        current_step_name=step_display,
                        current_step_description=step_desc or exec_msg,
                        elapsed_time=elapsed_time,
                        remaining_time=remaining_time,
                        last_message=exec_msg,
                        module_name=step_name,
                        node_status=node_status
                    )
                    
                    producer.publish_progress(progress_msg)
                    logger.info(f"📤 发布任务进度消息: {task_id} - {step_name} - {status}")
        except Exception as e:
            logger.debug(f"发布任务进度消息失败: {e}")


# 全局单例
_task_manager = None

def get_task_manager() -> TaskManager:
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
