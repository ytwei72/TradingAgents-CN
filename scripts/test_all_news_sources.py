#!/usr/bin/env python3
"""
测试所有新闻数据源的获取成效
包括：Tushare、AKShare、EODHD、Finnhub、Alpha Vantage、NewsAPI
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from tradingagents.dataflows.realtime_news_utils import RealtimeNewsAggregator


def print_section_header(title):
    """打印章节标题"""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def test_news_source(source_name, news_items, test_time):
    """测试单个新闻源"""
    if news_items:
        print(f"✅ {source_name}: 成功获取 {len(news_items)} 条新闻，耗时: {test_time:.2f}秒")
        
        # 显示前3条新闻标题
        print(f"\n{source_name} 新闻示例:")
        for idx, item in enumerate(news_items[:3], 1):
            print(f"  {idx}. {item.title[:80]}...")
            print(f"     来源: {item.source}")
            print(f"     时间: {item.publish_time}")
            print(f"     紧急度: {item.urgency}")
            print(f"     相关性: {item.relevance_score:.2f}")
        
        # 统计分析
        print(f"\n{source_name} 统计分析:")
        urgency_counts = {}
        for item in news_items:
            urgency_counts[item.urgency] = urgency_counts.get(item.urgency, 0) + 1
        print(f"  紧急度分布: {urgency_counts}")
        
        avg_relevance = sum(item.relevance_score for item in news_items) / len(news_items)
        print(f"  平均相关性: {avg_relevance:.2f}")
        
        return True
    else:
        print(f"⚠️ {source_name}: 未获取到新闻，耗时: {test_time:.2f}秒")
        return False


def test_chinese_stock_news():
    """测试中国股票新闻获取（Tushare、AKShare、EODHD）"""
    print_section_header("测试中国股票新闻源")
    
    aggregator = RealtimeNewsAggregator()
    
    # 测试股票：贵州茅台
    ticker = '600519.SHG'
    symbol = '600519'
    hours_back = 2400  # 100天
    
    print(f"测试股票: {ticker} (贵州茅台)")
    print(f"回溯时间: {hours_back}小时 ({hours_back//24}天)")
    
    # 计算日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=hours_back)
    end_date_str = end_date.strftime('%Y-%m-%d')
    start_date_str = start_date.strftime('%Y-%m-%d')
    
    print(f"日期范围: {start_date_str} 到 {end_date_str}\n")
    
    results = {}
    
    # 1. 测试Tushare
    try:
        from tradingagents.dataflows.tushare_utils import get_tushare_provider
        print("测试 Tushare Provider...")
        start_time = datetime.now()
        
        provider = get_tushare_provider()
        if provider.connected:
            news_items = provider.get_stock_news_items(
                symbol=symbol,
                start_date=start_date_str,
                end_date=end_date_str,
                ticker=ticker,
                max_news=10
            )
            test_time = (datetime.now() - start_time).total_seconds()
            results['Tushare'] = test_news_source('Tushare', news_items, test_time)
        else:
            print("⚠️ Tushare: 未连接")
            results['Tushare'] = False
    except Exception as e:
        print(f"❌ Tushare: 测试失败 - {e}")
        results['Tushare'] = False
    
    # 2. 测试AKShare
    try:
        from tradingagents.dataflows.akshare_utils import get_akshare_provider
        print("\n测试 AKShare Provider...")
        start_time = datetime.now()
        
        provider = get_akshare_provider()
        if provider.connected:
            news_items = provider.get_stock_news_items(
                symbol=symbol,
                start_date=start_date_str,
                end_date=end_date_str,
                ticker=ticker,
                max_news=10
            )
            test_time = (datetime.now() - start_time).total_seconds()
            results['AKShare'] = test_news_source('AKShare', news_items, test_time)
        else:
            print("⚠️ AKShare: 未连接")
            results['AKShare'] = False
    except Exception as e:
        print(f"❌ AKShare: 测试失败 - {e}")
        results['AKShare'] = False
    
    # 3. 测试EODHD
    try:
        from tradingagents.dataflows.eodhd_utils import get_eodhd_provider
        print("\n测试 EODHD Provider...")
        start_time = datetime.now()
        
        provider = get_eodhd_provider()
        if provider.connected:
            news_items = provider.get_stock_news_items(
                symbol=symbol,
                start_date=start_date_str,
                end_date=end_date_str,
                ticker=ticker,
                max_news=10
            )
            test_time = (datetime.now() - start_time).total_seconds()
            results['EODHD'] = test_news_source('EODHD', news_items, test_time)
        else:
            print("⚠️ EODHD: 未连接")
            results['EODHD'] = False
    except Exception as e:
        print(f"❌ EODHD: 测试失败 - {e}")
        results['EODHD'] = False
    
    return results


def test_us_stock_news():
    """测试美股新闻获取（Finnhub、Alpha Vantage、NewsAPI、EODHD）"""
    print_section_header("测试美股新闻源")
    
    aggregator = RealtimeNewsAggregator()
    
    # 测试股票：苹果
    ticker = 'AAPL'
    hours_back = 168  # 7天
    
    print(f"测试股票: {ticker} (Apple Inc.)")
    print(f"回溯时间: {hours_back}小时 ({hours_back//24}天)")
    
    # 使用聚合器获取新闻（会自动尝试所有源）
    print("\n使用 RealtimeNewsAggregator 获取新闻...")
    start_time = datetime.now()
    
    news_items = aggregator.get_realtime_stock_news(
        ticker=ticker,
        hours_back=hours_back,
        max_news=10
    )
    
    test_time = (datetime.now() - start_time).total_seconds()
    
    if news_items:
        print(f"\n✅ 聚合器总计获取: {len(news_items)} 条新闻，耗时: {test_time:.2f}秒")
        
        # 按来源分组统计
        source_counts = {}
        for item in news_items:
            source_counts[item.source] = source_counts.get(item.source, 0) + 1
        
        print("\n新闻来源分布:")
        for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {source}: {count}条")
        
        # 显示前5条新闻
        print("\n新闻示例:")
        for idx, item in enumerate(news_items[:5], 1):
            print(f"  {idx}. [{item.source}] {item.title[:70]}...")
            print(f"     时间: {item.publish_time}, 紧急度: {item.urgency}, 相关性: {item.relevance_score:.2f}")
        
        return True
    else:
        print(f"⚠️ 聚合器未获取到任何新闻，耗时: {test_time:.2f}秒")
        return False


def test_individual_us_sources():
    """单独测试每个美股新闻源"""
    print_section_header("单独测试美股新闻源")
    
    aggregator = RealtimeNewsAggregator()
    ticker = 'AAPL'
    hours_back = 168
    end_date = datetime.now()
    
    results = {}
    
    # 1. 测试Finnhub
    print("测试 Finnhub...")
    start_time = datetime.now()
    try:
        news_items = aggregator._get_finnhub_realtime_news(ticker, hours_back, end_date)
        test_time = (datetime.now() - start_time).total_seconds()
        results['Finnhub'] = test_news_source('Finnhub', news_items, test_time)
    except Exception as e:
        print(f"❌ Finnhub: 测试失败 - {e}")
        results['Finnhub'] = False
    
    # 2. 测试Alpha Vantage
    print("\n测试 Alpha Vantage...")
    start_time = datetime.now()
    try:
        news_items = aggregator._get_alpha_vantage_news(ticker, hours_back, end_date)
        test_time = (datetime.now() - start_time).total_seconds()
        results['Alpha Vantage'] = test_news_source('Alpha Vantage', news_items, test_time)
    except Exception as e:
        print(f"❌ Alpha Vantage: 测试失败 - {e}")
        results['Alpha Vantage'] = False
    
    # 3. 测试NewsAPI
    print("\n测试 NewsAPI...")
    start_time = datetime.now()
    try:
        news_items = aggregator._get_newsapi_news(ticker, hours_back, end_date)
        test_time = (datetime.now() - start_time).total_seconds()
        results['NewsAPI'] = test_news_source('NewsAPI', news_items, test_time)
    except Exception as e:
        print(f"❌ NewsAPI: 测试失败 - {e}")
        results['NewsAPI'] = False
    
    # 4. 测试EODHD (美股)
    print("\n测试 EODHD (美股)...")
    start_time = datetime.now()
    try:
        from tradingagents.dataflows.eodhd_utils import get_eodhd_provider
        provider = get_eodhd_provider()
        if provider.connected:
            end_date_str = end_date.strftime('%Y-%m-%d')
            start_date_str = (end_date - timedelta(hours=hours_back)).strftime('%Y-%m-%d')
            news_items = provider.get_stock_news_items(
                symbol=ticker,
                start_date=start_date_str,
                end_date=end_date_str,
                ticker=f"{ticker}.US",
                max_news=10
            )
            test_time = (datetime.now() - start_time).total_seconds()
            results['EODHD (US)'] = test_news_source('EODHD (US)', news_items, test_time)
        else:
            print("⚠️ EODHD: 未连接")
            results['EODHD (US)'] = False
    except Exception as e:
        print(f"❌ EODHD (US): 测试失败 - {e}")
        results['EODHD (US)'] = False
    
    return results


def print_final_summary(cn_results, us_aggregated, us_individual):
    """打印最终总结"""
    print_section_header("测试总结")
    
    print("\n中国股票新闻源测试结果:")
    for source, success in cn_results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {source}: {status}")
    
    print("\n美股新闻聚合器测试结果:")
    status = "✅ 成功" if us_aggregated else "❌ 失败"
    print(f"  RealtimeNewsAggregator: {status}")
    
    print("\n美股单独新闻源测试结果:")
    for source, success in us_individual.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {source}: {status}")
    
    # 统计成功率
    total_sources = len(cn_results) + len(us_individual)
    successful_sources = sum(cn_results.values()) + sum(us_individual.values())
    success_rate = (successful_sources / total_sources * 100) if total_sources > 0 else 0
    
    print(f"\n总体成功率: {successful_sources}/{total_sources} ({success_rate:.1f}%)")
    
    # 推荐配置
    print("\n推荐配置:")
    if cn_results.get('Tushare'):
        print("  ✅ Tushare: 推荐用于A股新闻（需要API token）")
    if cn_results.get('AKShare'):
        print("  ✅ AKShare: 推荐用于A股新闻（免费，无需API）")
    if cn_results.get('EODHD'):
        print("  ✅ EODHD: 推荐用于全球市场新闻（需要API token）")
    if us_individual.get('Finnhub'):
        print("  ✅ Finnhub: 推荐用于美股新闻（需要API key）")
    if us_individual.get('NewsAPI'):
        print("  ✅ NewsAPI: 推荐用于全球新闻搜索（需要API key）")


def main():
    """主测试函数"""
    print("=" * 80)
    print("新闻数据源综合测试")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n测试范围:")
    print("  - 中国股票新闻源: Tushare, AKShare, EODHD")
    print("  - 美股新闻源: Finnhub, Alpha Vantage, NewsAPI, EODHD")
    print("  - 新闻聚合器: RealtimeNewsAggregator")
    
    # 测试中国股票新闻源
    cn_results = test_chinese_stock_news()
    
    # 测试美股新闻聚合器
    us_aggregated = test_us_stock_news()
    
    # 单独测试美股新闻源
    us_individual = test_individual_us_sources()
    
    # 打印最终总结
    print_final_summary(cn_results, us_aggregated, us_individual)
    
    print("\n测试完成！")


if __name__ == "__main__":
    main()
