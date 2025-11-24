#!/usr/bin/env python3
"""
测试Tushare新闻获取及数据处理功能

测试内容：
1. Tushare provider连接状态
2. 新闻数据获取
3. 新闻数据后处理（时间解析、过滤、评估）
4. NewsItem转换
5. 完整的_get_chinese_finance_news流程
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_tushare_provider():
    """测试Tushare Provider连接"""
    print("=" * 80)
    print("测试1: Tushare Provider连接状态")
    print("=" * 80)
    
    from tradingagents.dataflows.tushare_utils import get_tushare_provider
    
    provider = get_tushare_provider()
    
    if provider.connected:
        print("✅ Tushare Provider连接成功")
        return provider
    else:
        print("❌ Tushare Provider连接失败")
        print("请检查TUSHARE_TOKEN环境变量是否配置正确")
        return None


def test_get_stock_news(provider, symbol='000002'):
    """测试获取股票新闻DataFrame"""
    print("\n" + "=" * 80)
    print(f"测试2: 获取股票 {symbol} 的新闻DataFrame")
    print("=" * 80)
    
    # 设置日期范围（最近7天）
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    print(f"日期范围: {start_date} 到 {end_date}")
    
    news_df = provider.get_stock_news(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        max_news=10
    )
    
    if not news_df.empty:
        print(f"✅ 成功获取 {len(news_df)} 条新闻")
        print("\n新闻DataFrame列名:", news_df.columns.tolist())
        print("\n前3条新闻标题:")
        for idx, row in news_df.head(3).iterrows():
            print(f"  {idx + 1}. {row.get('标题', '无标题')}")
            print(f"     时间: {row.get('时间', '无时间')}")
            print(f"     链接: {row.get('链接', '无链接')[:50]}...")
        return news_df
    else:
        print("⚠️ 未获取到新闻数据")
        return None


def test_get_stock_news_items(provider, symbol='000002', ticker='000002.SZ'):
    """测试获取处理后的NewsItem列表"""
    print("\n" + "=" * 80)
    print(f"测试3: 获取股票 {symbol} 的NewsItem列表（包含后处理）")
    print("=" * 80)
    
    # 设置日期范围
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    print(f"日期范围: {start_date} 到 {end_date}")
    print(f"Ticker: {ticker}")
    
    news_items = provider.get_stock_news_items(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        ticker=ticker,
        max_news=10
    )
    
    if news_items:
        print(f"✅ 成功获取并处理 {len(news_items)} 条新闻")
        print("\nNewsItem详细信息:")
        for idx, item in enumerate(news_items[:3], 1):
            print(f"\n  新闻 {idx}:")
            print(f"    标题: {item.title}")
            print(f"    来源: {item.source}")
            print(f"    时间: {item.publish_time}")
            print(f"    紧急度: {item.urgency}")
            print(f"    相关性: {item.relevance_score:.2f}")
            print(f"    链接: {item.url[:50] if item.url else '无'}...")
            print(f"    内容摘要: {item.content[:100] if item.content else '无'}...")
        
        # 统计分析
        print("\n统计分析:")
        urgency_counts = {}
        for item in news_items:
            urgency_counts[item.urgency] = urgency_counts.get(item.urgency, 0) + 1
        
        print(f"  紧急度分布: {urgency_counts}")
        
        avg_relevance = sum(item.relevance_score for item in news_items) / len(news_items)
        print(f"  平均相关性: {avg_relevance:.2f}")
        
        return news_items
    else:
        print("⚠️ 未获取到NewsItem数据")
        return None


def test_chinese_finance_news(ticker='000002.SZ'):
    """测试完整的_get_chinese_finance_news流程"""
    print("\n" + "=" * 80)
    print(f"测试4: 完整的_get_chinese_finance_news流程 (ticker={ticker})")
    print("=" * 80)
    
    from tradingagents.dataflows.realtime_news_utils import RealtimeNewsAggregator
    
    # 创建新闻聚合器
    aggregator = RealtimeNewsAggregator()
    
    # 设置参数
    hours_back = 168  # 7天
    end_date = datetime.now()
    
    print(f"回溯时间: {hours_back}小时 (约{hours_back//24}天)")
    print(f"结束日期: {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 调用_get_chinese_finance_news
    news_items = aggregator._get_chinese_finance_news(
        ticker=ticker,
        hours_back=hours_back,
        end_date=end_date
    )
    
    if news_items:
        print(f"\n✅ 成功获取 {len(news_items)} 条中文财经新闻")
        
        # 按来源统计
        source_counts = {}
        for item in news_items:
            source_counts[item.source] = source_counts.get(item.source, 0) + 1
        
        print(f"\n新闻来源分布: {source_counts}")
        
        # 显示前5条新闻
        print("\n前5条新闻:")
        for idx, item in enumerate(news_items[:5], 1):
            print(f"\n  {idx}. [{item.source}] {item.title}")
            print(f"     时间: {item.publish_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"     紧急度: {item.urgency} | 相关性: {item.relevance_score:.2f}")
        
        return news_items
    else:
        print("\n⚠️ 未获取到中文财经新闻")
        return None


def test_news_helper_functions():
    """测试news_helper模块的各个函数"""
    print("\n" + "=" * 80)
    print("测试5: News Helper函数")
    print("=" * 80)
    
    from tradingagents.dataflows.news_helper import (
        parse_news_time,
        filter_news_by_date_range,
        assess_news_urgency,
        calculate_relevance_score
    )
    
    # 测试时间解析
    print("\n5.1 测试时间解析:")
    test_times = [
        '2025-11-24 14:30:00',
        '2025-11-24',
        '20251124 143000',
        '20251124',
        'invalid_time'
    ]
    
    for time_str in test_times:
        result = parse_news_time(time_str)
        status = "✅" if result else "❌"
        print(f"  {status} '{time_str}' -> {result}")
    
    # 测试日期范围过滤
    print("\n5.2 测试日期范围过滤:")
    now = datetime.now()
    start = now - timedelta(days=7)
    end = now
    
    test_dates = [
        now - timedelta(days=3),  # 在范围内
        now - timedelta(days=10),  # 早于开始
        now + timedelta(days=1),  # 晚于结束
    ]
    
    for test_date in test_dates:
        result = filter_news_by_date_range(test_date, start, end)
        status = "✅" if result else "❌"
        print(f"  {status} {test_date.strftime('%Y-%m-%d')} 在范围内: {result}")
    
    # 测试紧急度评估
    print("\n5.3 测试紧急度评估:")
    test_news = [
        ("突发：公司停牌公告", "重大事项"),
        ("公司发布2024年财报", "营业收入增长"),
        ("市场分析：行业趋势", "专家观点"),
    ]
    
    for title, content in test_news:
        urgency = assess_news_urgency(title, content)
        print(f"  '{title}' -> 紧急度: {urgency}")
    
    # 测试相关性计算
    print("\n5.4 测试相关性计算:")
    test_cases = [
        ("万科A发布财报", "000002"),
        ("000002股价上涨", "000002.SZ"),
        ("房地产行业分析", "000002"),
    ]
    
    for title, ticker in test_cases:
        score = calculate_relevance_score(title, ticker)
        print(f"  '{title}' vs '{ticker}' -> 相关性: {score:.2f}")


def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("Tushare新闻获取及数据处理测试")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 测试1: Provider连接
    provider = test_tushare_provider()
    if not provider:
        print("\n❌ Tushare Provider连接失败，无法继续测试")
        return
    
    # 测试2: 获取新闻DataFrame
    news_df = test_get_stock_news(provider, symbol='000002')
    
    # 测试3: 获取NewsItem列表
    news_items = test_get_stock_news_items(provider, symbol='000002', ticker='000002.SZ')
    
    # 测试4: 完整流程
    all_news = test_chinese_finance_news(ticker='000002.SZ')
    
    # 测试5: Helper函数
    test_news_helper_functions()
    
    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"✅ Tushare Provider: {'已连接' if provider else '未连接'}")
    print(f"✅ 新闻DataFrame: {'获取成功' if news_df is not None and not news_df.empty else '未获取'}")
    print(f"✅ NewsItem列表: {'获取成功' if news_items else '未获取'}")
    print(f"✅ 完整流程: {'运行成功' if all_news else '未获取'}")
    print("✅ Helper函数: 测试完成")
    
    print("\n测试完成！")


if __name__ == "__main__":
    main()
