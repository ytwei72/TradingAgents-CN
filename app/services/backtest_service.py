"""
回测服务模块

实现研报批量回测服务，包括收益序列计算和加权平均。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
import pandas as pd

from tradingagents.utils.logging_manager import get_logger
from tradingagents.storage.mongodb.system_config_manager import SystemConfigManager
from tradingagents.storage.mongodb.report_manager import mongodb_report_manager
from tradingagents.storage.mongodb.stock_dict_manager import stock_dict_manager
from tradingagents.storage.mongodb.stock_history_manager import stock_history_manager

def _get_market_index_code(stock_code: str) -> tuple[str, str]:
    """根据股票代码确定对应的大盘指数代码"""
    # A股：根据代码前缀判断市场
    if stock_code.startswith(('60', '68', '90')):
        # 上海市场 - 使用上证指数
        return "000001", "上证指数"
    elif stock_code.startswith(('00', '30', '20')):
        # 深圳市场 - 使用深证成指
        return "399001", "深证成指"
    else:
        # 默认使用上证指数
        return "000001", "上证指数"

logger = get_logger("backtest_service")


class BacktestService:
    """回测服务类

    负责接收批量回测请求参数，实现完整的回测逻辑。
    """

    def __init__(self) -> None:
        self.config_manager = SystemConfigManager()
        self._initialized = True

    def start_report_batch_backtest(
        self,
        *,
        analysis_ids: list[str],
    ) -> dict:
        """启动研报批量回测任务

        Args:
            analysis_ids: 研报 analysis_id 列表

        Returns:
            dict: 包含 profits 和 stats 的回测结果
        """
        logger.info(
            "BacktestService.start_report_batch_backtest | analysis_ids_count=%s",
            len(analysis_ids),
        )

        # 1. 从数据库读取回测配置
        try:
            backtest_config = self.config_manager.load_backtest_config()
            logger.info("✅ 已加载回测配置: %s", backtest_config)
        except Exception as e:
            logger.error(f"❌ 加载回测配置失败: {e}")
            raise RuntimeError(f"加载回测配置失败: {e}") from e

        horizon_days = backtest_config.get("horizon_days", 90)
        extend_days_before = backtest_config.get("extend_days_before", 30)
        extend_days_after = backtest_config.get("extend_days_after", 180)
        weight_mode = backtest_config.get("weight_mode", "equal")
        date_mode = backtest_config.get("date_mode", "calendar_day")

        # 2. 根据 analysis_ids 获取研报数据
        if not mongodb_report_manager or not mongodb_report_manager.connected:
            raise RuntimeError("报告数据库未连接")
        
        raw_reports = mongodb_report_manager.get_reports_by_ids(analysis_ids)
        if not raw_reports:
            raise ValueError("未找到任何研报数据")
        
        # 组装报告数据（添加公司名称和confidence）
        reports_data = []
        for report in raw_reports:
            stock_symbol = report.get("stock_symbol", "")
            company_name = self._get_company_name(stock_symbol)
            formatted_decision = report.get("formatted_decision", {})
            
            reports_data.append({
                "analysis_id": report.get("analysis_id", ""),
                "analysis_date": report.get("analysis_date", ""),
                "stock_symbol": stock_symbol,
                "formatted_decision": formatted_decision,
                "company_name": company_name,
                # 保存confidence用于加权计算
                "confidence": formatted_decision.get("confidence", 1.0),
            })

        logger.info(f"✅ 获取到 {len(reports_data)} 篇研报数据")

        # 3. 对每篇研报计算收益序列
        profits_list = []
        for report in reports_data:
            try:
                profit_result = self._calculate_report_profits(
                    report=report,
                    horizon_days=horizon_days,
                    extend_days_before=extend_days_before,
                    extend_days_after=extend_days_after,
                    date_mode=date_mode,
                )
                if profit_result:
                    # 保留confidence用于加权计算
                    profit_result["confidence"] = report.get("confidence", 1.0)
                    profits_list.append(profit_result)
            except Exception as e:
                logger.error(f"❌ 计算研报 {report.get('analysis_id')} 收益失败: {e}")
                continue

        if not profits_list:
            raise ValueError("所有研报的收益计算均失败")

        # 4. 计算加权平均收益序列
        weighted_avg = self._calculate_weighted_average(
            profits_list=profits_list,
            weight_mode=weight_mode,
            horizon_days=horizon_days,
        )

        # 5. 组装返回结果
        return {
            "data": {
                "profits": profits_list,
                "stats": {
                    "weighted_avg": weighted_avg,
                },
            }
        }


    def _get_company_name(self, stock_symbol: str) -> str:
        """从 stock_dict 获取公司名称

        Args:
            stock_symbol: 股票代码

        Returns:
            str: 公司名称，如果获取失败则返回股票代码
        """
        if not stock_dict_manager or not stock_dict_manager.connected:
            logger.warning("stock_dict 未连接，无法获取公司名称")
            return stock_symbol

        try:
            # 清理股票代码（移除交易所后缀）
            clean_symbol = stock_symbol.split('.')[0] if '.' in stock_symbol else stock_symbol

            stock_info = stock_dict_manager.get_by_symbol(clean_symbol)
            if stock_info and "name" in stock_info:
                return stock_info["name"]
            else:
                logger.warning(f"未找到股票 {stock_symbol} 的公司名称")
                return stock_symbol
        except Exception as e:
            logger.error(f"获取股票 {stock_symbol} 公司名称失败: {e}")
            return stock_symbol

    def _calculate_report_profits(
        self,
        report: Dict[str, Any],
        horizon_days: int,
        extend_days_before: int,
        extend_days_after: int,
        date_mode: str,
    ) -> Optional[Dict[str, Any]]:
        """计算单篇研报的收益序列

        Args:
            report: 研报数据
            horizon_days: 回测期限（天）
            extend_days_before: 分析日前向前扩展的历史天数
            extend_days_after: 分析日后向后扩展的历史天数
            date_mode: 日期模式（"calendar_day" 或 "trading_day"）

        Returns:
            Dict: 包含收益序列的结果，格式：
                {
                    "analysis_id": str,
                    "stock_symbol": str,
                    "company_name": str,
                    "analysis_date": str,
                    "action": str,
                    "profits": List[float],
                    "formatted_decision": Dict,
                    "trade_dates": List[str],
                    "trade_prices": List[float],
                }
        """
        analysis_id = report.get("analysis_id", "")
        stock_symbol = report.get("stock_symbol", "")
        company_name = report.get("company_name", stock_symbol)
        analysis_date_str = report.get("analysis_date", "")
        formatted_decision = report.get("formatted_decision", {})
        action = formatted_decision.get("action", "").lower()

        if not analysis_date_str:
            logger.error(f"研报 {analysis_id} 缺少 analysis_date")
            return None

        try:
            analysis_date = datetime.strptime(analysis_date_str, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"研报 {analysis_id} 的 analysis_date 格式错误: {analysis_date_str}")
            return None

        # 计算历史数据区间
        start_date = analysis_date - timedelta(days=extend_days_before)
        end_date = analysis_date + timedelta(days=extend_days_after)

        # 获取股票历史数据（从 stock_history_manager）
        # 处理股票代码格式：去掉交易所后缀（如 .SZ, .SH）
        clean_stock_code = stock_symbol.split('.')[0] if '.' in stock_symbol else stock_symbol
        
        stock_data = stock_history_manager.get_stock_history(
            stock_code=clean_stock_code,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
        )

        if stock_data is None or stock_data.empty:
            logger.error(f"研报 {analysis_id} 无法获取股票 {stock_symbol} 的历史数据")
            return None
        
        # stock_history_manager 返回的 date 列是字符串格式，需要转换为 date 类型
        if 'date' in stock_data.columns:
            stock_data['date'] = pd.to_datetime(stock_data['date']).dt.date

        # 获取大盘指数代码
        index_code, index_name = _get_market_index_code(clean_stock_code)
        
        # 获取大盘指数历史数据
        index_data = stock_history_manager.get_stock_history(
            stock_code=index_code,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
        )
        if index_data is not None and not index_data.empty and 'date' in index_data.columns:
            index_data['date'] = pd.to_datetime(index_data['date']).dt.date
        else:
            index_data = pd.DataFrame()

        # 计算收益序列（包含交易日期、成交价、收盘价和大盘指数）
        profit_details = self._calculate_profit_sequence(
            stock_data=stock_data,
            index_data=index_data,
            analysis_date=analysis_date,
            action=action,
            horizon_days=horizon_days,
            date_mode=date_mode,
        )

        return {
            "analysis_id": analysis_id,
            "stock_symbol": stock_symbol,
            "company_name": company_name,
            "analysis_date": analysis_date_str,
            "action": action,
            "profits": profit_details["profits"],
            "formatted_decision": formatted_decision,
            "trade_dates": profit_details["trade_dates"],
            "trade_prices": profit_details["trade_prices"],
            "close_prices": profit_details["close_prices"],
            "index_prices": profit_details["index_prices"],
        }

    def _calculate_profit_sequence(
        self,
        stock_data: pd.DataFrame,
        index_data: pd.DataFrame,
        analysis_date: date,
        action: str,
        horizon_days: int,
        date_mode: str,
    ) -> Dict[str, Any]:
        """计算收益序列

        Args:
            stock_data: 股票历史数据 DataFrame
            index_data: 大盘指数历史数据 DataFrame
            analysis_date: 分析日期
            action: 操作类型 ("buy", "hold", "sell")
            horizon_days: 回测期限（天）
            date_mode: 日期模式（"calendar_day" 或 "trading_day"）

        Returns:
            Dict: 包含收益序列、交易日期、成交价、收盘价和大盘指数的字典
                {
                    "profits": List[float],  # 收益序列（%）
                    "trade_dates": List[str],  # 交易日期列表
                    "trade_prices": List[float],  # 成交价列表（开盘价）
                    "close_prices": List[float],  # 收盘价列表
                    "index_prices": List[float],  # 大盘指数价格列表
                }
        """
        # 找到分析日期对应的交易日（或最近的交易日）
        analysis_trade_date = self._find_nearest_trade_date(stock_data, analysis_date)
        if analysis_trade_date is None:
            logger.error(f"无法找到分析日期 {analysis_date} 对应的交易日")
            return {
                "profits": [0.0] * horizon_days,
                "trade_dates": [""] * horizon_days,
                "trade_prices": [0.0] * horizon_days,
                "close_prices": [0.0] * horizon_days,
                "index_prices": [0.0] * horizon_days,
            }

        # 获取起始价格（分析日期的收盘价）
        start_price = self._get_price_on_date(stock_data, analysis_trade_date, "close")
        if start_price is None:
            logger.error(f"无法获取分析日期 {analysis_date} 的收盘价")
            return {
                "profits": [0.0] * horizon_days,
                "trade_dates": [""] * horizon_days,
                "trade_prices": [0.0] * horizon_days,
                "close_prices": [0.0] * horizon_days,
                "index_prices": [0.0] * horizon_days,
            }

        # 判断操作模式
        is_margin_trading = action in ["buy", "hold"]  # 融资模式：先买入后卖出
        is_short_selling = action == "sell"  # 融券模式：先卖出后买入

        profits = []
        trade_dates = []
        trade_prices = []
        close_prices = []
        index_prices = []
        trade_days = stock_data[stock_data['date'] > analysis_trade_date].copy()

        # 获取分析日期的大盘指数价格（作为基准）
        index_start_price = self._get_price_on_date(index_data, analysis_trade_date, "close") if not index_data.empty else None

        for day in range(1, horizon_days + 1):
            if date_mode == "calendar_day":
                # 自然日模式：计算目标自然日，然后找最近的交易日
                target_date = analysis_date + timedelta(days=day)
                target_trade_date = self._find_nearest_trade_date(stock_data, target_date, forward=True)
            else:
                # 交易日模式：直接取第 day 个交易日
                if day <= len(trade_days):
                    target_trade_date = trade_days.iloc[day - 1]['date']
                else:
                    target_trade_date = None

            if target_trade_date is None:
                # 如果找不到对应的交易日，使用最后一个交易日的数据
                if len(trade_days) > 0:
                    target_trade_date = trade_days.iloc[-1]['date']
                else:
                    profits.append(0.0)
                    trade_dates.append("")
                    trade_prices.append(0.0)
                    close_prices.append(0.0)
                    index_prices.append(0.0)
                    continue

            # 获取结束价格（目标日期的开盘价）
            end_price = self._get_price_on_date(stock_data, target_trade_date, "open")
            # 获取收盘价
            close_price = self._get_price_on_date(stock_data, target_trade_date, "close")
            # 获取大盘指数价格
            index_price = self._get_price_on_date(index_data, target_trade_date, "close") if not index_data.empty else None

            if end_price is None:
                profits.append(0.0)
                trade_dates.append("")
                trade_prices.append(0.0)
                close_prices.append(0.0)
                index_prices.append(0.0)
                continue

            # 计算收益
            if is_margin_trading:
                # 融资模式：(卖出价 - 买入价) / 买入价
                profit = (end_price - start_price) / start_price
            else:  # is_short_selling
                # 融券模式：(买入价 - 卖出价) / 卖出价
                profit = (start_price - end_price) / start_price

            profits.append(profit * 100)  # 转换为百分比
            trade_dates.append(target_trade_date.strftime("%Y-%m-%d"))
            trade_prices.append(end_price)
            close_prices.append(close_price if close_price is not None else 0.0)
            
            # 计算大盘指数相对收益（相对于分析日期）
            if index_price is not None and index_start_price is not None and index_start_price > 0:
                index_return = ((index_price - index_start_price) / index_start_price) * 100
                index_prices.append(index_return)
            else:
                index_prices.append(0.0)

        return {
            "profits": profits,
            "trade_dates": trade_dates,
            "trade_prices": trade_prices,
            "close_prices": close_prices,
            "index_prices": index_prices,
        }

    def _find_nearest_trade_date(
        self, stock_data: pd.DataFrame, target_date: date, forward: bool = True
    ) -> Optional[date]:
        """找到最近的交易日

        Args:
            stock_data: 股票历史数据
            target_date: 目标日期
            forward: 如果为 True，向前找（下一个交易日），否则向后找（上一个交易日）

        Returns:
            Optional[date]: 最近的交易日
        """
        if stock_data.empty:
            return None

        # 找到目标日期之后（或之前）的交易日
        if forward:
            # 向前找：下一个交易日
            after_dates = stock_data[stock_data['date'] >= target_date]
            if not after_dates.empty:
                return after_dates.iloc[0]['date']
        else:
            # 向后找：上一个交易日
            before_dates = stock_data[stock_data['date'] <= target_date]
            if not before_dates.empty:
                return before_dates.iloc[-1]['date']

        # 如果找不到，返回最接近的日期
        stock_data['date_diff'] = (stock_data['date'] - target_date).abs()
        nearest = stock_data.loc[stock_data['date_diff'].idxmin()]
        return nearest['date']

    def _get_price_on_date(
        self, stock_data: pd.DataFrame, trade_date: date, price_type: str = "close"
    ) -> Optional[float]:
        """获取指定日期的价格

        Args:
            stock_data: 股票历史数据
            trade_date: 交易日
            price_type: 价格类型 ("open", "close", "high", "low")

        Returns:
            Optional[float]: 价格，如果找不到则返回 None
        """
        row = stock_data[stock_data['date'] == trade_date]
        if row.empty:
            return None

        # 尝试不同的列名
        price_columns = [price_type, f"{price_type}_price", price_type.upper()]
        for col in price_columns:
            if col in row.columns:
                price = row.iloc[0][col]
                if pd.notna(price):
                    return float(price)

        return None

    def _calculate_weighted_average(
        self,
        profits_list: List[Dict[str, Any]],
        weight_mode: str,
        horizon_days: int,
    ) -> List[float]:
        """计算加权平均收益序列

        Args:
            profits_list: 每篇研报的收益序列列表
            weight_mode: 权重模式 ("equal" 或 "confidence")
            horizon_days: 回测期限（天）

        Returns:
            List[float]: 加权平均收益序列
        """
        if not profits_list:
            return [0.0] * horizon_days

        # 计算权重
        weights = []
        if weight_mode == "confidence":
            # 置信度加权：从报告中获取confidence
            for profit_item in profits_list:
                confidence = profit_item.get("confidence", 1.0)
                # 确保confidence是数值类型且在合理范围内
                if isinstance(confidence, (int, float)) and confidence > 0:
                    weights.append(float(confidence))
                else:
                    weights.append(1.0)
        else:
            # 等权模式
            weights = [1.0] * len(profits_list)

        # 归一化权重
        total_weight = sum(weights)
        if total_weight > 0:
            normalized_weights = [w / total_weight for w in weights]
        else:
            normalized_weights = [1.0 / len(weights)] * len(weights)

        # 计算加权平均
        weighted_avg = [0.0] * horizon_days
        for i, profit_item in enumerate(profits_list):
            profits = profit_item.get("profits", [])
            weight = normalized_weights[i]
            for day in range(min(len(profits), horizon_days)):
                weighted_avg[day] += profits[day] * weight

        return weighted_avg


backtest_service = BacktestService()


