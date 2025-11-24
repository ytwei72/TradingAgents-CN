#!/usr/bin/env python3
"""
测试EODHD新闻获取功能
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_eodhd_provider():
    """测试EODHD Provider连接和新闻获取"""
    print("=" * 80)
    print("测试EODHD Provider")
    print("=" * 80)
    
    from tradingagents.dataflows.eodhd_utils import get_eodhd_provider
    
    provider = get_eodhd_provider()
    
    if provider.connected:
        print("✅ EODHD Provider连接成功")
    else:
        print("❌ EODHD Provider连接失败")
        print("请检查EODHD_API_TOKEN环境变量是否配置正确")
        return None
    
    return provider


def test_get_stock_news(provider, symbol='600519'):
    """测试获取股票新闻"""
    print("\n" + "=" * 80)
    print(f"测试获取股票 {symbol} 的新闻")
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
            print(f"     链接: {row.get('链接', '无链接')[:80]}...")
        return news_df
    else:
        print("⚠️ 未获取到新闻数据")
        return None


def test_get_stock_news_items(provider, symbol='600519', ticker='600519.SHG'):
    """测试获取处理后的NewsItem列表"""
    print("\n" + "=" * 80)
    print(f"测试获取股票 {symbol} 的NewsItem列表（包含后处理）")
    print("=" * 80)
    
    # 设置日期范围
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=70)).strftime('%Y-%m-%d')
    
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
            print(f"    链接: {item.url[:80] if item.url else '无'}...")
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


def test_symbol_normalization(provider):
    """测试股票代码标准化"""
    print("\n" + "=" * 80)
    print("测试股票代码标准化")
    print("=" * 80)
    
    test_symbols = [
        ('600519', '600519.SHG'),  # A股上海
        ('000001', '000001.SHE'),  # A股深圳
        ('600519.SH', '600519.SHG'),  # A股上海带后缀
        ('000001.SZ', '000001.SHE'),  # A股深圳带后缀
        ('AAPL', 'AAPL.US'),  # 美股
        ('0700.HK', '0700.HK'),  # 港股
    ]
    
    for original, expected in test_symbols:
        result = provider._normalize_symbol_for_eodhd(original)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{original}' -> '{result}' (期望: '{expected}')")


def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("EODHD新闻获取测试")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 测试1: Provider连接
    provider = test_eodhd_provider()
    if not provider:
        print("\n❌ EODHD Provider连接失败，无法继续测试")
        return
    
    # 测试2: 股票代码标准化
    # test_symbol_normalization(provider)
    
    # 测试3: 获取新闻DataFrame (贵州茅台)
    # news_df = test_get_stock_news(provider, symbol='600519')
    
    # 测试4: 获取NewsItem列表
    news_items = test_get_stock_news_items(provider, symbol='600519', ticker='600519.SHG')
    
    # 测试5: 美股新闻 (苹果)
    print("\n" + "=" * 80)
    print("测试美股新闻获取 (AAPL)")
    print("=" * 80)
    us_news = test_get_stock_news(provider, symbol='AAPL')
    
    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"✅ EODHD Provider: {'已连接' if provider else '未连接'}")
    # print(f"✅ A股新闻DataFrame: {'获取成功' if news_df is not None and not news_df.empty else '未获取'}")
    print(f"✅ A股NewsItem列表: {'获取成功' if news_items else '未获取'}")
    print(f"✅ 美股新闻DataFrame: {'获取成功' if us_news is not None and not us_news.empty else '未获取'}")
    
    print("\n测试完成！")


if __name__ == "__main__":
    main()
