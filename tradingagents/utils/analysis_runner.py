"""
股票分析执行工具
"""

import sys
import os
import uuid
import time
import random
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger, get_logger_manager
from tradingagents.messaging.business.messages import NodeStatus
from tradingagents.exceptions import TaskControlStoppedException
logger = get_logger('web')

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 确保环境变量正确加载
load_dotenv(project_root / ".env", override=True)

# 导入统一日志系统
from tradingagents.utils.logging_init import setup_web_logging
logger = setup_web_logging()

# 添加配置管理器
try:
    from tradingagents.config.config_manager import token_tracker
    TOKEN_TRACKING_ENABLED = True
    logger.info("✅ Token跟踪功能已启用")
except ImportError:
    TOKEN_TRACKING_ENABLED = False
    logger.warning("⚠️ Token跟踪功能未启用")

def translate_analyst_labels(text):
    """将分析师的英文标签转换为中文"""
    if not text:
        return text

    # 分析师标签翻译映射
    translations = {
        'Bull Analyst:': '看涨分析师:',
        'Bear Analyst:': '看跌分析师:',
        'Risky Analyst:': '激进风险分析师:',
        'Safe Analyst:': '保守风险分析师:',
        'Neutral Analyst:': '中性风险分析师:',
        'Research Manager:': '研究经理:',
        'Portfolio Manager:': '投资组合经理:',
        'Risk Judge:': '风险管理委员会:',
        'Trader:': '交易员:'
    }

    # 替换所有英文标签
    for english, chinese in translations.items():
        text = text.replace(english, chinese)

    return text

def extract_risk_assessment(state):
    """从分析状态中提取风险评估数据"""
    try:
        risk_debate_state = state.get('risk_debate_state', {})

        if not risk_debate_state:
            return None

        # 提取各个风险分析师的观点并进行中文化
        risky_analysis = translate_analyst_labels(risk_debate_state.get('risky_history', ''))
        safe_analysis = translate_analyst_labels(risk_debate_state.get('safe_history', ''))
        neutral_analysis = translate_analyst_labels(risk_debate_state.get('neutral_history', ''))
        judge_decision = translate_analyst_labels(risk_debate_state.get('judge_decision', ''))

        # 格式化风险评估报告
        risk_assessment = f"""
## ⚠️ 风险评估报告

### 🔴 激进风险分析师观点
{risky_analysis if risky_analysis else '暂无激进风险分析'}

### 🟡 中性风险分析师观点
{neutral_analysis if neutral_analysis else '暂无中性风险分析'}

### 🟢 保守风险分析师观点
{safe_analysis if safe_analysis else '暂无保守风险分析'}

### 🏛️ 风险管理委员会最终决议
{judge_decision if judge_decision else '暂无风险管理决议'}

---
*风险评估基于多角度分析，请结合个人风险承受能力做出投资决策*
        """.strip()

        return risk_assessment

    except Exception as e:
        logger.info(f"提取风险评估数据时出错: {e}")
        return None


def run_stock_analysis(stock_symbol, analysis_date, analysts, research_depth, market_type="美股", progress_callback=None, analysis_id=None, async_tracker=None):
    """执行股票分析
    
    主函数结构：
    - 第一阶段：配置与准备
      * 准备步骤1: 记录分析开始日志
      * 准备步骤2: 成本估算
      * 准备步骤3: 任务控制检查
      * 准备步骤4: 数据预获取和验证
      * 准备步骤5: 环境验证
      * 准备步骤6: 构建配置
      * 准备步骤7: 格式化股票代码
      * 准备步骤8: 初始化分析引擎
    - 第二阶段：多智能体分析执行
    - 第三阶段：结果处理与保存
      * 后处理步骤1: 处理分析结果
      * 后处理步骤2: 记录完成日志
      * 后处理步骤3: 保存分析结果

    Args:
        stock_symbol: 股票代码
        analysis_date: 分析日期
        analysts: 分析师列表
        research_depth: 研究深度
        market_type: 市场类型
        progress_callback: 进度回调函数，用于更新UI状态
        analysis_id: 分析任务ID（用于任务控制）
        async_tracker: AsyncProgressTracker实例（用于任务控制）
    """
    
    # 导入辅助模块
    from .analysis_helpers import (
        prepare_analysis_steps,
        check_task_control as check_task_control_helper,
        execute_analysis,
        post_process_analysis_steps
    )

    def update_progress(message, step=None, total_steps=None):
        """更新进度"""
        if progress_callback:
            progress_callback(message, step, total_steps)
        logger.info(f"[进度] {message}")
    
    # 规范化分析师名称
    # 将前端可能传入的长名称转换为系统内部使用的短名称
    normalized_analysts = []
    analyst_mapping = {
        'market_analyst': 'market',
        'social_media_analyst': 'social',
        'news_analyst': 'news',
        'fundamentals_analyst': 'fundamentals',
        'fundamental_analyst': 'fundamentals',
        # 保持原有短名称支持
        'market': 'market',
        'social': 'social',
        'news': 'news',
        'fundamentals': 'fundamentals'
    }
    
    for a in analysts:
        if a in analyst_mapping:
            normalized_analysts.append(analyst_mapping[a])
        else:
            normalized_analysts.append(a)
    
    analysts = normalized_analysts

    # ========== 第一阶段：配置与准备（准备步骤1-8） ==========
    prep_success, prep_result, prep_error = prepare_analysis_steps(
        stock_symbol=stock_symbol,
        analysis_date=analysis_date,
        market_type=market_type,
        analysts=analysts,
        research_depth=research_depth,
        analysis_id=analysis_id,
        async_tracker=async_tracker
    )
    
    if not prep_success:
        # 生成临时session_id用于错误返回
        session_id = f"analysis_error_{uuid.uuid4().hex[:8]}"
        return {
            'success': False,
            'error': prep_error or '准备分析步骤失败',
            'stock_symbol': stock_symbol,
            'analysis_date': analysis_date,
            'session_id': session_id if analysis_id else None
        }
    
    # 从准备结果中提取必要信息
    config = prep_result['config']
    formatted_symbol = prep_result['formatted_symbol']
    graph = prep_result['graph']
    session_id = prep_result['session_id']
    analysis_start_time = prep_result['analysis_start_time']

    # TODO: 需解决extra参数中字段未输出的问题
    logger.info(f"🚀 [分析开始] 股票分析启动",
               extra={
                   'stock_symbol': stock_symbol,
                   'analysis_date': analysis_date,
                   'analysts': analysts,
                   'research_depth': research_depth,
                   'market_type': market_type,
                   'session_id': session_id,
                   'event_type': 'web_analysis_start'
               })

    try:
        # ========== 第二阶段：多智能体分析执行（步骤9 ~ n） ==========
        def check_task_control():
            return check_task_control_helper(analysis_id, async_tracker)
        
        state, decision = execute_analysis(
            graph=graph,
            formatted_symbol=formatted_symbol,
            analysis_date=analysis_date,
            analysis_id=analysis_id,
            session_id=session_id,
            update_progress=update_progress,
            async_tracker=async_tracker,
            analysis_start_time=analysis_start_time,
            check_task_control=check_task_control
        )

        # ========== 第三阶段：结果处理与保存（步骤n+1 ~ n+3） ==========
        logger.debug(f"🔍 [DEBUG] 分析完成，decision类型: {type(decision)}")
        logger.debug(f"🔍 [DEBUG] decision内容: {decision}")
        
        # ========== 后处理步骤1-3: 处理结果、记录日志、保存结果 ==========
        results = post_process_analysis_steps(
            analysis_id=analysis_id,
            state=state,
            decision=decision
        )

        update_progress("✅ 分析成功完成！")
        
        # 发布任务完成状态消息
        from .message_utils import publish_task_status
        publish_task_status(analysis_id, "COMPLETED", "✅ 分析成功完成！")
        
        return results

    except TaskControlStoppedException as e:
        # 任务被用户停止
        logger.info(f"⏹️ [任务停止] 任务被用户停止: {analysis_id}")
        
        # 发布任务停止状态消息
        from .message_utils import publish_task_status
        publish_task_status(analysis_id, "STOPPED", f"⏹️ 任务已停止")
        
        return {
            'stock_symbol': stock_symbol,
            'analysis_date': analysis_date,
            'analysts': analysts,
            'research_depth': research_depth,
            'state': {},
            'decision': {},
            'success': False,
            'stopped': True,
            'error': str(e),
            'session_id': session_id if 'session_id' in locals() else None
        }

    except Exception as e:
        # 记录分析失败的详细日志
        analysis_duration = time.time() - analysis_start_time
        
        # 如果session_id未定义（异常发生在准备阶段之前），使用临时ID
        error_session_id = session_id if 'session_id' in locals() else f"analysis_error_{uuid.uuid4().hex[:8]}"

        logger.error(f"❌ [分析失败] 股票分析执行失败",
                    extra={
                        'stock_symbol': stock_symbol,
                        'session_id': error_session_id,
                        'duration': analysis_duration,
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'analysts_used': analysts,
                        'success': False,
                        'event_type': 'web_analysis_error'
                    }, exc_info=True)
        
        # 发布任务失败状态消息
        from .message_utils import publish_task_status
        publish_task_status(analysis_id, "FAILED", f"❌ 分析失败: {str(e)}")

        # 如果真实分析失败，返回错误信息而不是误导性演示数据
        return {
            'stock_symbol': stock_symbol,
            'analysis_date': analysis_date,
            'analysts': analysts,
            'research_depth': research_depth,
            'state': {},  # 空状态，将显示占位符
            'decision': {},  # 空决策
            'success': False,
            'error': str(e),
            'is_demo': False,
            'error_reason': f"分析失败: {str(e)}",
            'session_id': error_session_id if analysis_id else None
        }

def format_analysis_results(results):
    """格式化分析结果用于显示"""
    
    if not results['success']:
        return {
            'error': results['error'],
            'success': False
        }
    
    state = results['state']
    decision = results['decision']

    # 提取关键信息
    # decision 可能是字符串（如 "BUY", "SELL", "HOLD"）或字典
    if isinstance(decision, str):
        # 将英文投资建议转换为中文
        action_translation = {
            'BUY': '买入',
            'SELL': '卖出',
            'HOLD': '持有',
            'buy': '买入',
            'sell': '卖出',
            'hold': '持有'
        }
        action = action_translation.get(decision.strip(), decision.strip())

        formatted_decision = {
            'action': action,
            'confidence': 0.7,  # 默认置信度
            'risk_score': 0.3,  # 默认风险分数
            'target_price': None,  # 字符串格式没有目标价格
            'reasoning': f'基于AI分析，建议{decision.strip().upper()}'
        }
    elif isinstance(decision, dict):
        # 处理目标价格 - 确保正确提取数值
        target_price = decision.get('target_price')
        if target_price is not None and target_price != 'N/A':
            try:
                # 尝试转换为浮点数
                if isinstance(target_price, str):
                    # 移除货币符号和空格
                    clean_price = target_price.replace('$', '').replace('¥', '').replace('￥', '').strip()
                    target_price = float(clean_price) if clean_price and clean_price != 'None' else None
                elif isinstance(target_price, (int, float)):
                    target_price = float(target_price)
                else:
                    target_price = None
            except (ValueError, TypeError):
                target_price = None
        else:
            target_price = None

        # 将英文投资建议转换为中文
        action_translation = {
            'BUY': '买入',
            'SELL': '卖出',
            'HOLD': '持有',
            'buy': '买入',
            'sell': '卖出',
            'hold': '持有'
        }
        action = decision.get('action', '持有')
        chinese_action = action_translation.get(action, action)

        formatted_decision = {
            'action': chinese_action,
            'confidence': decision.get('confidence', 0.5),
            'risk_score': decision.get('risk_score', 0.3),
            'target_price': target_price,
            'reasoning': decision.get('reasoning', '暂无分析推理')
        }
    else:
        # 处理其他类型
        formatted_decision = {
            'action': '持有',
            'confidence': 0.5,
            'risk_score': 0.3,
            'target_price': None,
            'reasoning': f'分析结果: {str(decision)}'
        }
    
    # 格式化状态信息
    formatted_state = {}
    
    # 处理各个分析模块的结果 - 包含完整的智能体团队分析
    analysis_keys = [
        'market_report',
        'fundamentals_report',
        'sentiment_report',
        'news_report',
        'risk_assessment',
        'investment_plan',
        # 添加缺失的团队决策数据，确保与CLI端一致
        'investment_debate_state',  # 研究团队辩论（多头/空头研究员）
        'trader_investment_plan',   # 交易团队计划
        'risk_debate_state',        # 风险管理团队决策
        'final_trade_decision'      # 最终交易决策
    ]
    
    for key in analysis_keys:
        if key in state:
            # 对文本内容进行中文化处理
            content = state[key]
            if isinstance(content, str):
                content = translate_analyst_labels(content)
            formatted_state[key] = content
        elif key == 'risk_assessment':
            # 特殊处理：从 risk_debate_state 生成 risk_assessment
            risk_assessment = extract_risk_assessment(state)
            if risk_assessment:
                formatted_state[key] = risk_assessment
    
    return {
        'stock_symbol': results['stock_symbol'],
        'decision': formatted_decision,
        'state': formatted_state,
        'success': True,
        # 将配置信息放在顶层，供前端直接访问
        'analysis_date': results['analysis_date'],
        'analysts': results['analysts'],
        'research_depth': results['research_depth'],
        'llm_provider': results.get('llm_provider', 'dashscope'),
        'deep_think_llm': results.get('deep_think_llm', 'qwen-max'),
        'quick_think_llm': results.get('quick_think_llm', 'qwen-plus'),
        'metadata': {
            'analysis_date': results['analysis_date'],
            'analysts': results['analysts'],
            'research_depth': results['research_depth'],
            'llm_provider': results.get('llm_provider', 'dashscope'),
            'deep_think_llm': results.get('deep_think_llm', 'qwen-max'),
            'quick_think_llm': results.get('quick_think_llm', 'qwen-plus')
        }
    }

def validate_analysis_params(stock_symbol, analysis_date, analysts, research_depth, market_type="美股"):
    """验证分析参数"""

    errors = []

    # 验证股票代码
    if not stock_symbol or len(stock_symbol.strip()) == 0:
        errors.append("股票代码不能为空")
    elif len(stock_symbol.strip()) > 10:
        errors.append("股票代码长度不能超过10个字符")
    else:
        # 根据市场类型验证代码格式
        symbol = stock_symbol.strip()
        if market_type == "A股":
            # A股：6位数字
            import re
            if not re.match(r'^\d{6}$', symbol):
                errors.append("A股代码格式错误，应为6位数字（如：000001）")
        elif market_type == "港股":
            # 港股：4-5位数字.HK 或 纯4-5位数字
            import re
            symbol_upper = symbol.upper()
            # 检查是否为 XXXX.HK 或 XXXXX.HK 格式
            hk_format = re.match(r'^\d{4,5}\.HK$', symbol_upper)
            # 检查是否为纯4-5位数字格式
            digit_format = re.match(r'^\d{4,5}$', symbol)

            if not (hk_format or digit_format):
                errors.append("港股代码格式错误，应为4位数字.HK（如：0700.HK）或4位数字（如：0700）")
        elif market_type == "美股":
            # 美股：1-5位字母
            import re
            if not re.match(r'^[A-Z]{1,5}$', symbol.upper()):
                errors.append("美股代码格式错误，应为1-5位字母（如：AAPL）")
    
    # 验证分析师列表
    if not analysts or len(analysts) == 0:
        errors.append("必须至少选择一个分析师")
    
    valid_analysts = [
        'market', 'social', 'news', 'fundamentals',
        'market_analyst', 'social_media_analyst', 'news_analyst', 'fundamentals_analyst', 'fundamental_analyst'
    ]
    invalid_analysts = [a for a in analysts if a not in valid_analysts]
    if invalid_analysts:
        errors.append(f"无效的分析师类型: {', '.join(invalid_analysts)}")
    
    # 验证研究深度
    if not isinstance(research_depth, int) or research_depth < 1 or research_depth > 5:
        errors.append("研究深度必须是1-5之间的整数")
    
    # 验证分析日期
    try:
        from datetime import datetime
        datetime.strptime(analysis_date, '%Y-%m-%d')
    except ValueError:
        errors.append("分析日期格式无效，应为YYYY-MM-DD格式")
    
    return len(errors) == 0, errors

def get_supported_stocks():
    """获取支持的股票列表"""
    
    # 常见的美股股票代码
    popular_stocks = [
        {'symbol': 'AAPL', 'name': '苹果公司', 'sector': '科技'},
        {'symbol': 'MSFT', 'name': '微软', 'sector': '科技'},
        {'symbol': 'GOOGL', 'name': '谷歌', 'sector': '科技'},
        {'symbol': 'AMZN', 'name': '亚马逊', 'sector': '消费'},
        {'symbol': 'TSLA', 'name': '特斯拉', 'sector': '汽车'},
        {'symbol': 'NVDA', 'name': '英伟达', 'sector': '科技'},
        {'symbol': 'META', 'name': 'Meta', 'sector': '科技'},
        {'symbol': 'NFLX', 'name': '奈飞', 'sector': '媒体'},
        {'symbol': 'AMD', 'name': 'AMD', 'sector': '科技'},
        {'symbol': 'INTC', 'name': '英特尔', 'sector': '科技'},
        {'symbol': 'SPY', 'name': 'S&P 500 ETF', 'sector': 'ETF'},
        {'symbol': 'QQQ', 'name': '纳斯达克100 ETF', 'sector': 'ETF'},
    ]
    
    return popular_stocks

