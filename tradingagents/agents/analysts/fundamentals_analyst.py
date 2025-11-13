"""
基本面分析师 - 统一工具架构版本
使用统一工具自动识别股票类型并调用相应数据源
"""

from datetime import datetime, timedelta
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage

# 导入消息装饰器（优先使用消息模式）
from tradingagents.messaging.decorators.message_decorators import message_analysis_module

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger("default")

# 导入Google工具调用处理器
from tradingagents.agents.utils.google_tool_handler import GoogleToolCallHandler

# 模块级变量：基本面分析的时间窗口大小（天数）
FUNDAMENTALS_ANALYSIS_WINDOW_DAYS = 60


def _get_company_name_for_fundamentals(ticker: str, market_info: dict) -> str:
    """
    为基本面分析师获取公司名称

    Args:
        ticker: 股票代码
        market_info: 市场信息字典

    Returns:
        str: 公司名称
    """
    try:
        if market_info['is_china']:
            # 中国A股：使用统一接口获取股票信息
            from tradingagents.dataflows.interface import get_china_stock_info_unified
            stock_info = get_china_stock_info_unified(ticker)

            # 解析股票名称
            if "股票名称:" in stock_info:
                company_name = stock_info.split("股票名称:")[1].split("\n")[0].strip()
                logger.debug(f"📊 [基本面分析师] 从统一接口获取中国股票名称: {ticker} -> {company_name}")
                return company_name
            else:
                logger.warning(f"⚠️ [基本面分析师] 无法从统一接口解析股票名称: {ticker}")
                return f"股票代码{ticker}"

        elif market_info['is_hk']:
            # 港股：使用改进的港股工具
            try:
                from tradingagents.dataflows.improved_hk_utils import get_hk_company_name_improved
                company_name = get_hk_company_name_improved(ticker)
                logger.debug(f"📊 [基本面分析师] 使用改进港股工具获取名称: {ticker} -> {company_name}")
                return company_name
            except Exception as e:
                logger.debug(f"📊 [基本面分析师] 改进港股工具获取名称失败: {e}")
                # 降级方案：生成友好的默认名称
                clean_ticker = ticker.replace('.HK', '').replace('.hk', '')
                return f"港股{clean_ticker}"

        elif market_info['is_us']:
            # 美股：使用简单映射或返回代码
            us_stock_names = {
                'AAPL': '苹果公司',
                'TSLA': '特斯拉',
                'NVDA': '英伟达',
                'MSFT': '微软',
                'GOOGL': '谷歌',
                'AMZN': '亚马逊',
                'META': 'Meta',
                'NFLX': '奈飞'
            }

            company_name = us_stock_names.get(ticker.upper(), f"美股{ticker}")
            logger.debug(f"📊 [基本面分析师] 美股名称映射: {ticker} -> {company_name}")
            return company_name

        else:
            return f"股票{ticker}"

    except Exception as e:
        logger.error(f"❌ [基本面分析师] 获取公司名称失败: {e}")
        return f"股票{ticker}"


def create_fundamentals_analyst(llm, toolkit):
    @message_analysis_module("fundamentals_analyst")
    def fundamentals_analyst_node(state):
        logger.debug(f"📊 [DEBUG] ===== 基本面分析师节点开始 =====")

        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        
        # 动态计算 start_date：基于 current_date 向前推窗口天数
        try:
            current_date_obj = datetime.strptime(current_date, '%Y-%m-%d')
            start_date_obj = current_date_obj - timedelta(days=FUNDAMENTALS_ANALYSIS_WINDOW_DAYS)
            start_date = start_date_obj.strftime('%Y-%m-%d')
            logger.debug(f"📊 [DEBUG] 动态计算日期窗口: current_date={current_date}, start_date={start_date} (窗口={FUNDAMENTALS_ANALYSIS_WINDOW_DAYS}天)")
        except Exception as e:
            # 如果日期解析失败，使用默认值（当前日期向前推窗口天数）
            logger.warning(f"⚠️ [基本面分析师] 日期解析失败，使用默认窗口: {e}")
            try:
                current_date_obj = datetime.now()
                start_date_obj = current_date_obj - timedelta(days=FUNDAMENTALS_ANALYSIS_WINDOW_DAYS)
                start_date = start_date_obj.strftime('%Y-%m-%d')
            except:
                # 最后的降级方案：使用固定日期
                start_date = '2020-01-01'
                logger.error(f"❌ [基本面分析师] 日期计算完全失败，使用降级方案: {start_date}")

        logger.debug(f"📊 [DEBUG] 输入参数: ticker={ticker}, date={current_date}, start_date={start_date}")
        logger.debug(f"📊 [DEBUG] 当前状态中的消息数量: {len(state.get('messages', []))}")
        logger.debug(f"📊 [DEBUG] 现有基本面报告: {state.get('fundamentals_report', 'None')}")

        # 获取股票市场信息
        from tradingagents.utils.stock_utils import StockUtils
        logger.info(f"📊 [基本面分析师] 正在分析股票: {ticker}")

        # 添加详细的股票代码追踪日志
        logger.debug(f"🔍 [股票代码追踪] 基本面分析师接收到的原始股票代码: '{ticker}' (类型: {type(ticker)})")
        logger.debug(f"🔍 [股票代码追踪] 股票代码长度: {len(str(ticker))}")
        logger.debug(f"🔍 [股票代码追踪] 股票代码字符: {list(str(ticker))}")

        market_info = StockUtils.get_market_info(ticker)
        logger.debug(f"🔍 [股票代码追踪] StockUtils.get_market_info 返回的市场信息: {market_info}")

        logger.debug(f"📊 [DEBUG] 股票类型检查: {ticker} -> {market_info['market_name']} ({market_info['currency_name']}")
        logger.debug(f"📊 [DEBUG] 详细市场信息: is_china={market_info['is_china']}, is_hk={market_info['is_hk']}, is_us={market_info['is_us']}")
        logger.debug(f"📊 [DEBUG] 工具配置检查: online_tools={toolkit.config['online_tools']}")

        # 获取公司名称
        company_name = _get_company_name_for_fundamentals(ticker, market_info)
        logger.debug(f"📊 [DEBUG] 公司名称: {ticker} -> {company_name}")

        # 选择工具
        if toolkit.config["online_tools"]:
            # 使用统一的基本面分析工具，工具内部会自动识别股票类型
            logger.info(f"📊 [基本面分析师] 使用统一基本面分析工具，自动识别股票类型")
            tools = [toolkit.get_stock_fundamentals_unified]
            # 安全地获取工具名称用于调试
            tool_names_debug = []
            for tool in tools:
                if hasattr(tool, 'name'):
                    tool_names_debug.append(tool.name)
                elif hasattr(tool, '__name__'):
                    tool_names_debug.append(tool.__name__)
                else:
                    tool_names_debug.append(str(tool))
            logger.debug(f"📊 [DEBUG] 选择的工具: {tool_names_debug}")
            logger.debug(f"📊 [DEBUG] 🔧 统一工具将自动处理: {market_info['market_name']}")
        else:
            # 离线模式：优先使用FinnHub数据，SimFin作为补充
            if market_info['is_china']:
                # A股使用本地缓存数据
                tools = [
                    toolkit.get_china_stock_data,
                    toolkit.get_china_fundamentals
                ]
            else:
                # 美股/港股：优先FinnHub，SimFin作为补充
                tools = [
                    toolkit.get_fundamentals_openai,  # 使用现有的OpenAI基本面数据工具
                    toolkit.get_finnhub_company_insider_sentiment,
                    toolkit.get_finnhub_company_insider_transactions,
                    toolkit.get_simfin_balance_sheet,
                    toolkit.get_simfin_cashflow,
                    toolkit.get_simfin_income_stmt,
                ]

        # 统一的系统提示，适用于所有股票类型
        system_message = (
            f"你是一位专业的股票基本面分析师。"
            f"⚠️ 绝对强制要求：你必须调用工具获取真实数据！不允许任何假设或编造！"
            f"任务：分析{company_name}（股票代码：{ticker}，{market_info['market_name']}）"
            f"🔴 立即调用 get_stock_fundamentals_unified 工具"
            f"参数：ticker='{ticker}', start_date='{start_date}', end_date='{current_date}', curr_date='{current_date}'"
            "📊 分析要求："
            "- 基于真实数据进行深度基本面分析"
            f"- 计算并提供合理价位区间（使用{market_info['currency_name']}{market_info['currency_symbol']}）"
            "- 分析当前股价是否被低估或高估"
            "- 提供基于基本面的目标价位建议"
            "- 包含PE、PB、PEG等估值指标分析"
            "- 结合市场特点进行分析"
            "🌍 语言和货币要求："
            "- 所有分析内容必须使用中文"
            "- 投资建议必须使用中文：买入、持有、卖出"
            "- 绝对不允许使用英文：buy、hold、sell"
            f"- 货币单位使用：{market_info['currency_name']}（{market_info['currency_symbol']}）"
            "🚫 严格禁止："
            "- 不允许说'我将调用工具'"
            "- 不允许假设任何数据"
            "- 不允许编造公司信息"
            "- 不允许直接回答而不调用工具"
            "- 不允许回复'无法确定价位'或'需要更多信息'"
            "- 不允许使用英文投资建议（buy/hold/sell）"
            "✅ 你必须："
            "- 立即调用统一基本面分析工具"
            "- 等待工具返回真实数据"
            "- 基于真实数据进行分析"
            "- 提供具体的价位区间和目标价"
            "- 使用中文投资建议（买入/持有/卖出）"
            "现在立即开始调用工具！不要说任何其他话！"
        )

        # 系统提示模板
        system_prompt = (
            "🔴 强制要求：你必须调用工具获取真实数据！"
            "🚫 绝对禁止：不允许假设、编造或直接回答任何问题！"
            "✅ 你必须：立即调用提供的工具获取真实数据，然后基于真实数据进行分析。"
            "可用工具：{tool_names}。\n{system_message}"
            "当前日期：{current_date}。"
            "分析目标：{company_name}（股票代码：{ticker}）。"
            "请确保在分析中正确区分公司名称和股票代码。"
        )

        # 创建提示模板
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ])

        prompt = prompt.partial(system_message=system_message)
        # 安全地获取工具名称，处理函数和工具对象
        tool_names = []
        for tool in tools:
            if hasattr(tool, 'name'):
                tool_names.append(tool.name)
            elif hasattr(tool, '__name__'):
                tool_names.append(tool.__name__)
            else:
                tool_names.append(str(tool))

        prompt = prompt.partial(tool_names=", ".join(tool_names))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)
        prompt = prompt.partial(company_name=company_name)

        # 检测阿里百炼模型并创建新实例
        if hasattr(llm, '__class__') and 'DashScope' in llm.__class__.__name__:
            logger.debug(f"📊 [DEBUG] 检测到阿里百炼模型，创建新实例以避免工具缓存")
            from tradingagents.llm_adapters import ChatDashScopeOpenAI
            fresh_llm = ChatDashScopeOpenAI(
                model=llm.model_name,
                temperature=llm.temperature,
                max_tokens=getattr(llm, 'max_tokens', 2000)
            )
        else:
            fresh_llm = llm

        logger.debug(f"📊 [DEBUG] 创建LLM链，工具数量: {len(tools)}")
        # 安全地获取工具名称用于调试
        debug_tool_names = []
        for tool in tools:
            if hasattr(tool, 'name'):
                debug_tool_names.append(tool.name)
            elif hasattr(tool, '__name__'):
                debug_tool_names.append(tool.__name__)
            else:
                debug_tool_names.append(str(tool))
        logger.debug(f"📊 [DEBUG] 绑定的工具列表: {debug_tool_names}")
        logger.debug(f"📊 [DEBUG] 创建工具链，让模型自主决定是否调用工具")

        try:
            chain = prompt | fresh_llm.bind_tools(tools)
            logger.debug(f"📊 [DEBUG] ✅ 工具绑定成功，绑定了 {len(tools)} 个工具")
        except Exception as e:
            logger.error(f"📊 [DEBUG] ❌ 工具绑定失败: {e}")
            raise e

        logger.debug(f"📊 [DEBUG] 调用LLM链...")

        # 添加详细的股票代码追踪日志
        logger.debug(f"🔍 [股票代码追踪] LLM调用前，ticker参数: '{ticker}'")
        logger.debug(f"🔍 [股票代码追踪] 传递给LLM的消息数量: {len(state['messages'])}")

        # 检查消息内容中是否有其他股票代码
        for i, msg in enumerate(state["messages"]):
            if hasattr(msg, 'content') and msg.content:
                content = str(msg.content)
                if "002021" in content:
                    logger.debug(f"🔍 [股票代码追踪] 警告：消息 {i} 中包含错误股票代码 002021")
                    logger.debug(f"🔍 [股票代码追踪] 消息内容: {content[:200]}...")
                if "002027" in content:
                    logger.debug(f"🔍 [股票代码追踪] 消息 {i} 中包含正确股票代码 002027")

        result = chain.invoke(state["messages"])
        logger.debug(f"📊 [DEBUG] LLM调用完成")

        # 使用统一的Google工具调用处理器
        if GoogleToolCallHandler.is_google_model(fresh_llm):
            logger.info(f"📊 [基本面分析师] 检测到Google模型，使用统一工具调用处理器")
            
            # 创建分析提示词
            analysis_prompt_template = GoogleToolCallHandler.create_analysis_prompt(
                ticker=ticker,
                company_name=company_name,
                analyst_type="基本面分析",
                specific_requirements="重点关注财务数据、盈利能力、估值指标、行业地位等基本面因素。"
            )
            
            # 处理Google模型工具调用
            report, messages = GoogleToolCallHandler.handle_google_tool_calls(
                result=result,
                llm=fresh_llm,
                tools=tools,
                state=state,
                analysis_prompt_template=analysis_prompt_template,
                analyst_name="基本面分析师"
            )
            
            # 检查返回的消息，确保最后一条消息不包含tool_calls
            clean_messages = []
            for msg in messages:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    # 如果消息包含tool_calls，创建一个清洁版本
                    from langchain_core.messages import AIMessage
                    clean_msg = AIMessage(
                        content=msg.content if hasattr(msg, 'content') else str(msg),
                        name="fundamentals_analyst"
                    )
                    clean_messages.append(clean_msg)
                    logger.debug(f"📊 [基本面分析师] 清理包含tool_calls的消息")
                else:
                    clean_messages.append(msg)
            
            # 确保最后一条消息是清洁的（不包含tool_calls）
            if clean_messages:
                last_msg = clean_messages[-1]
                if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                    # 创建最终的清洁消息
                    from langchain_core.messages import AIMessage
                    final_clean_msg = AIMessage(
                        content=report,
                        name="fundamentals_analyst"
                    )
                    clean_messages[-1] = final_clean_msg
                    logger.info(f"📊 [基本面分析师] 确保最后一条消息不包含tool_calls")
            
            return {
                "messages": clean_messages if clean_messages else [AIMessage(content=report, name="fundamentals_analyst")],
                "fundamentals_report": report
            }
        else:
            # 非Google模型的处理逻辑
            logger.debug(f"📊 [DEBUG] 非Google模型 ({fresh_llm.__class__.__name__})，使用标准处理逻辑")
            
            # 检查是否已经有完整的报告（避免重复执行）
            existing_report = state.get('fundamentals_report', '')
            if existing_report and len(existing_report) > 100:
                # 检查报告是否包含错误信息（如果是错误，允许重试）
                error_indicators = ['失败', '错误', '异常', '不可用', '无法获取', '调用失败']
                is_error_report = any(indicator in existing_report for indicator in error_indicators)
                
                if not is_error_report:
                    logger.info(f"📊 [基本面分析师] 检测到已有完整报告（{len(existing_report)}字符），跳过重复执行")
                    # 返回清洁消息，不包含tool_calls，确保节点完成
                    from langchain_core.messages import AIMessage
                    clean_message = AIMessage(
                        content=existing_report,
                        name="fundamentals_analyst"
                    )
                    return {"messages": [clean_message], "fundamentals_report": existing_report}
            
            # 检查消息历史，避免重复工具调用导致的死循环
            messages = state.get("messages", [])
            tool_call_attempts = 0
            tool_messages_count = 0
            last_tool_message = None
            
            for msg in messages:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    tool_call_attempts += len(msg.tool_calls)
                # 检查是否是工具返回的消息（ToolMessage）
                if hasattr(msg, '__class__') and 'ToolMessage' in msg.__class__.__name__:
                    tool_messages_count += 1
                    last_tool_message = msg
            
            # 如果已经有工具返回的消息，检查工具执行结果
            if tool_messages_count > 0 and last_tool_message:
                # 检查工具返回的内容是否包含错误
                tool_result = str(last_tool_message.content) if hasattr(last_tool_message, 'content') else str(last_tool_message)
                error_indicators = ['失败', '错误', '异常', '不可用', '无法获取', '调用失败', '数据为空', '获取失败', '❌']
                
                if any(indicator in tool_result for indicator in error_indicators):
                    logger.warning(f"📊 [基本面分析师] 检测到工具执行返回错误，工具调用次数: {tool_call_attempts}")
                    
                    # 如果工具调用次数>=2或工具返回错误，生成降级报告
                    if tool_call_attempts >= 2:
                        logger.warning(f"📊 [基本面分析师] 工具调用失败多次（{tool_call_attempts}次），生成降级报告以避免死循环")
                        fallback_report = f"""## {company_name}（股票代码：{ticker}）基本面分析报告

**分析日期**: {current_date}

### ⚠️ 数据获取说明

由于指定日期为历史日期（{current_date}），基本面数据获取遇到以下问题：

**工具执行结果**:
{tool_result[:500]}

### 📊 分析建议

1. **数据限制**: 历史日期的实时基本面数据可能不可用或已过期
2. **建议**: 如需完整的基本面分析，建议使用当前日期或近期日期进行分析
3. **替代方案**: 可以查看该股票的历史财务报告和公开信息

**注意**: 本报告基于有限的数据生成，建议结合其他分析结果进行投资决策。
"""
                        # 返回清洁消息，不包含tool_calls
                        from langchain_core.messages import AIMessage
                        clean_message = AIMessage(
                            content=fallback_report,
                            name="fundamentals_analyst"
                        )
                        return {"messages": [clean_message], "fundamentals_report": fallback_report}
            
            # 如果已经尝试过多次工具调用，检查是否有工具返回的错误
            if tool_call_attempts > 0:
                # 检查最后几条消息，看是否有工具返回的错误
                recent_messages = messages[-min(5, len(messages)):]
                has_tool_error = False
                for msg in recent_messages:
                    if hasattr(msg, 'content') and msg.content:
                        content = str(msg.content)
                        error_indicators = ['失败', '错误', '异常', '不可用', '无法获取', '调用失败', '数据为空']
                        if any(indicator in content for indicator in error_indicators):
                            has_tool_error = True
                            logger.warning(f"📊 [基本面分析师] 检测到工具调用错误，尝试生成降级报告")
                            break
                
                # 如果检测到工具错误且已经尝试过多次，生成降级报告（降低到1次）
                if has_tool_error and tool_call_attempts >= 1:
                    logger.warning(f"📊 [基本面分析师] 工具调用失败多次（{tool_call_attempts}次），生成降级报告以避免死循环")
                    # 生成基于错误信息的降级报告
                    error_summary = "\n".join([
                        str(msg.content) for msg in recent_messages 
                        if hasattr(msg, 'content') and msg.content
                    ])
                    fallback_report = f"""## {company_name}（股票代码：{ticker}）基本面分析报告

**分析日期**: {current_date}

### ⚠️ 数据获取说明

由于指定日期为历史日期（{current_date}），部分基本面数据可能无法获取或已过期。

**数据获取情况**:
{error_summary[:500]}

### 📊 分析建议

1. **数据限制**: 历史日期的实时基本面数据可能不可用
2. **建议**: 如需完整的基本面分析，建议使用当前日期或近期日期进行分析
3. **替代方案**: 可以查看该股票的历史财务报告和公开信息

**注意**: 本报告基于有限的数据生成，建议结合其他分析结果进行投资决策。
"""
                    # 返回清洁消息，不包含tool_calls
                    from langchain_core.messages import AIMessage
                    clean_message = AIMessage(
                        content=fallback_report,
                        name="fundamentals_analyst"
                    )
                    return {"messages": [clean_message], "fundamentals_report": fallback_report}
            
            # 检查工具调用情况
            tool_call_count = len(result.tool_calls) if hasattr(result, 'tool_calls') else 0
            logger.debug(f"📊 [DEBUG] 工具调用数量: {tool_call_count}")
            
            if tool_call_count > 0:
                # 有工具调用，检查是否已经尝试过多次
                # 降低限制到2次，避免死循环
                if tool_call_attempts >= 2:
                    logger.warning(f"📊 [基本面分析师] 工具调用次数过多（{tool_call_attempts}次），生成降级报告以避免死循环")
                    # 生成降级报告
                    fallback_report = f"""## {company_name}（股票代码：{ticker}）基本面分析报告

**分析日期**: {current_date}

### ⚠️ 分析说明

基本面分析过程中工具调用次数过多，为避免死循环，生成此降级报告。

**可能原因**:
1. 指定日期为历史日期，数据可能不可用
2. 工具调用失败或返回错误
3. 数据源连接问题

**建议**: 尝试使用当前日期或近期日期进行分析。
"""
                    # 返回清洁消息，不包含tool_calls
                    from langchain_core.messages import AIMessage
                    clean_message = AIMessage(
                        content=fallback_report,
                        name="fundamentals_analyst"
                    )
                    return {"messages": [clean_message], "fundamentals_report": fallback_report}
                
                # 检查是否已经有工具返回的消息，如果有且包含错误，立即停止
                if tool_messages_count > 0 and last_tool_message:
                    tool_result = str(last_tool_message.content) if hasattr(last_tool_message, 'content') else str(last_tool_message)
                    error_indicators = ['失败', '错误', '异常', '不可用', '无法获取', '调用失败', '数据为空', '获取失败', '❌']
                    
                    if any(indicator in tool_result for indicator in error_indicators):
                        logger.warning(f"📊 [基本面分析师] 检测到工具执行返回错误，立即生成降级报告（工具调用次数: {tool_call_attempts}）")
                        fallback_report = f"""## {company_name}（股票代码：{ticker}）基本面分析报告

**分析日期**: {current_date}

### ⚠️ 数据获取说明

由于指定日期为历史日期（{current_date}），基本面数据获取遇到以下问题：

**工具执行结果**:
{tool_result[:500]}

### 📊 分析建议

1. **数据限制**: 历史日期的实时基本面数据可能不可用或已过期
2. **建议**: 如需完整的基本面分析，建议使用当前日期或近期日期进行分析
3. **替代方案**: 可以查看该股票的历史财务报告和公开信息

**注意**: 本报告基于有限的数据生成，建议结合其他分析结果进行投资决策。
"""
                        # 返回清洁消息，不包含tool_calls
                        from langchain_core.messages import AIMessage
                        clean_message = AIMessage(
                            content=fallback_report,
                            name="fundamentals_analyst"
                        )
                        return {"messages": [clean_message], "fundamentals_report": fallback_report}
                
                # 有工具调用，返回状态让工具执行（但限制最多2次）
                tool_calls_info = []
                for tc in result.tool_calls:
                    tool_calls_info.append(tc['name'])
                    logger.debug(f"📊 [DEBUG] 工具调用 {len(tool_calls_info)}: {tc}")
                
                logger.info(f"📊 [基本面分析师] 工具调用: {tool_calls_info} (尝试 {tool_call_attempts + 1}/2)")
                return {
                    "messages": [result],
                    "fundamentals_report": result.content if hasattr(result, 'content') else str(result)
                }
            else:
                # 没有工具调用，使用强制工具调用修复
                logger.debug(f"📊 [DEBUG] 检测到模型未调用工具，启用强制工具调用模式")
                
                # 强制调用统一基本面分析工具
                try:
                    logger.debug(f"📊 [DEBUG] 强制调用 get_stock_fundamentals_unified...")
                    # 安全地查找统一基本面分析工具
                    unified_tool = None
                    for tool in tools:
                        tool_name = None
                        if hasattr(tool, 'name'):
                            tool_name = tool.name
                        elif hasattr(tool, '__name__'):
                            tool_name = tool.__name__

                        if tool_name == 'get_stock_fundamentals_unified':
                            unified_tool = tool
                            break
                    if unified_tool:
                        logger.debug(f"🔍 [股票代码追踪] 强制调用统一工具，传入ticker: '{ticker}'")
                        combined_data = unified_tool.invoke({
                            'ticker': ticker,
                            'start_date': start_date,
                            'end_date': current_date,
                            'curr_date': current_date
                        })
                        logger.debug(f"📊 [DEBUG] 统一工具数据获取成功，长度: {len(combined_data)}字符")
                    else:
                        combined_data = "统一基本面分析工具不可用"
                        logger.debug(f"📊 [DEBUG] 统一工具未找到")
                except Exception as e:
                    combined_data = f"统一基本面分析工具调用失败: {e}"
                    logger.debug(f"📊 [DEBUG] 统一工具调用异常: {e}")
                
                currency_info = f"{market_info['currency_name']}（{market_info['currency_symbol']}）"
                
                # 生成基于真实数据的分析报告
                analysis_prompt = f"""基于以下真实数据，对{company_name}（股票代码：{ticker}）进行详细的基本面分析：

{combined_data}

请提供：
1. 公司基本信息分析（{company_name}，股票代码：{ticker}）
2. 财务状况评估
3. 盈利能力分析
4. 估值分析（使用{currency_info}）
5. 投资建议（买入/持有/卖出）

要求：
- 基于提供的真实数据进行分析
- 正确使用公司名称"{company_name}"和股票代码"{ticker}"
- 价格使用{currency_info}
- 投资建议使用中文
- 分析要详细且专业"""

                try:
                    # 检查工具返回的数据是否包含错误
                    if "失败" in combined_data or "错误" in combined_data or "异常" in combined_data or "不可用" in combined_data:
                        logger.warning(f"📊 [基本面分析师] 工具返回错误数据，生成降级报告")
                        # 生成降级报告
                        report = f"""## {company_name}（股票代码：{ticker}）基本面分析报告

**分析日期**: {current_date}

### ⚠️ 数据获取说明

由于指定日期为历史日期（{current_date}），基本面数据获取遇到以下问题：

{combined_data[:300]}

### 📊 分析建议

1. **数据限制**: 历史日期的实时基本面数据可能不可用或已过期
2. **建议**: 如需完整的基本面分析，建议使用当前日期或近期日期进行分析
3. **替代方案**: 可以查看该股票的历史财务报告和公开信息

**注意**: 本报告基于有限的数据生成，建议结合其他分析结果进行投资决策。
"""
                    else:
                        # 创建简单的分析链
                        analysis_prompt_template = ChatPromptTemplate.from_messages([
                            ("system", "你是专业的股票基本面分析师，基于提供的真实数据进行分析。"),
                            ("human", "{analysis_request}")
                        ])
                        
                        analysis_chain = analysis_prompt_template | fresh_llm
                        analysis_result = analysis_chain.invoke({"analysis_request": analysis_prompt})
                        
                        if hasattr(analysis_result, 'content'):
                            report = analysis_result.content
                        else:
                            report = str(analysis_result)

                        logger.info(f"📊 [基本面分析师] 强制工具调用完成，报告长度: {len(report)}")
                    
                except Exception as e:
                    logger.error(f"❌ [DEBUG] 强制工具调用分析失败: {e}")
                    report = f"""## {company_name}（股票代码：{ticker}）基本面分析报告

**分析日期**: {current_date}

### ⚠️ 分析失败

基本面分析过程中遇到错误：{str(e)}

**可能原因**:
1. 指定日期为历史日期，数据可能不可用
2. 数据源连接问题
3. API调用限制

**建议**: 尝试使用当前日期或近期日期进行分析。
"""
                
                # 返回清洁消息，不包含tool_calls，确保节点完成
                from langchain_core.messages import AIMessage
                clean_message = AIMessage(
                    content=report,
                    name="fundamentals_analyst"
                )
                return {"messages": [clean_message], "fundamentals_report": report}

        # 这里不应该到达，但作为备用
        logger.warning(f"📊 [DEBUG] 到达备用返回路径，生成最终报告")
        report_content = result.content if hasattr(result, 'content') else str(result)
        
        # 如果报告内容为空或太短，生成一个默认报告
        if not report_content or len(report_content) < 50:
            report_content = f"""## {company_name}（股票代码：{ticker}）基本面分析报告

**分析日期**: {current_date}

### 📊 分析说明

基本面分析已完成，但报告内容可能不完整。

**建议**: 如需完整的基本面分析，建议使用当前日期或近期日期进行分析。
"""
        
        # 返回清洁消息，不包含tool_calls，确保节点完成
        from langchain_core.messages import AIMessage
        clean_message = AIMessage(
            content=report_content,
            name="fundamentals_analyst"
        )
        return {
            "messages": [clean_message],
            "fundamentals_report": report_content
        }

    return fundamentals_analyst_node
