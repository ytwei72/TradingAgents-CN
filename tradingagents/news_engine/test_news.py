#!/usr/bin/env python3
"""
News Module Tests

新闻模块测试代码
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_config():
    """测试配置管理器"""
    print("\n" + "=" * 60)
    print("测试 1: 配置管理器")
    print("=" * 60)
    
    from tradingagents.news_engine.config import get_news_config_manager
    
    # 获取配置管理器
    config_manager = get_news_config_manager(verbose=True)
    
    # 打印配置
    config_manager.print_config()
    
    # 获取配置对象
    config = config_manager.get_config()
    
    print("\n配置测试:")
    print(f"  默认回溯时间: {config.default_hours_back} 小时")
    print(f"  默认最大新闻数: {config.default_max_news}")
    print(f"  AKShare 启用: {config.akshare_enabled}")
    print(f"  Tushare 启用: {config.tushare_enabled}")


def test_models():
    """测试数据模型"""
    print("\n" + "=" * 60)
    print("测试 2: 数据模型")
    print("=" * 60)
    
    from tradingagents.news_engine.models import NewsItem, NewsSource, NewsUrgency, NewsQuery
    from datetime import datetime
    
    # 创建新闻项
    news_item = NewsItem(
        title="测试新闻标题",
        content="这是一条测试新闻的内容",
        source=NewsSource.AKSHARE,
        publish_time=datetime.now(),
        url="https://example.com/news/1",
        urgency=NewsUrgency.MEDIUM,
        relevance_score=0.8,
        stock_code="000002"
    )
    
    print(f"\n创建新闻项")
    print(f"  {news_item}")
    
    # 转换为字典
    news_dict = news_item.to_dict()
    print(f"\n转换为字典")
    print(f"  标题: {news_dict['title']}")
    print(f"  来源: {news_dict['source']}")
    print(f"  相关性 {news_dict['relevance_score']}")
    
    # 从字典创建新闻项
    news_item2 = NewsItem.from_dict(news_dict)
    print(f"\n从字典创建新闻项")
    print(f"  {news_item2}")
    
    # 创建查询对象
    query = NewsQuery(
        stock_code="000002",
        max_news=10,
        hours_back=6
    )
    
    print(f"\n创建查询对象:")
    print(f"  股票代码: {query.stock_code}")
    print(f"  最大新闻数: {query.max_news}")
    print(f"  回溯时间: {query.hours_back} 小时")
    
    print("\n数据模型测试通过")


def test_providers():
    """测试新闻提供器"""
    print("\n" + "=" * 60)
    print("测试 3: 新闻提供器")
    print("=" * 60)
    
    from providers.news_prov_tushare import TushareNewsProvider
    from providers.news_prov_finnhub import FinnhubNewsProvider
    from providers.news_prov_eodhd import EODHDNewsProvider
    from providers.news_prov_googlenews import GoogleNewsProvider
    from providers.news_prov_akshare_cls import AkShareClsNewsProvider
    from providers.news_prov_akshare_sina import AkShareSinaNewsProvider
    from providers.news_prov_akshare_em import AkShareEmNewsProvider
    
    providers = [
        ("Tushare", TushareNewsProvider()),
        ("FinnHub", FinnhubNewsProvider()),
        ("EODHD", EODHDNewsProvider()),
        ("GoogleNews", GoogleNewsProvider()),
        ("AkShare_CLS", AkShareClsNewsProvider()),
        ("AkShare_Sina", AkShareSinaNewsProvider()),
        ("AkShare_EM", AkShareEmNewsProvider()),
    ]
    
    print("\n提供者可用性")
    for name, provider in providers:
        status = "可用" if provider.is_available() else "不可用"
        print(f"  {name}: {status}")
    
    # 测试市场类型识别
    print("\n市场类型识别:")
    test_codes = [
        ("000002", "A股"),
        ("600000", "A股"),
        ("0700.HK", "港股"),
        ("AAPL", "美股"),
    ]
    
    # 使用一个支持A股的提供器来测试识别 (AkShare_CLS)
    provider = providers[4][1]
    for code, expected in test_codes:
        market_type = provider.identify_market_type(code)
        print(f"  {code}: {market_type.value} (预期: {expected})")
    
    print("\n提供器测试通过")


def test_aggregator():
    """测试新闻聚合器"""
    print("\n" + "=" * 60)
    print("测试 4: 新闻聚合器")
    print("=" * 60)
    
    from tradingagents.news_engine.aggregator import NewsAggregator
    
    # 创建聚合器
    aggregator = NewsAggregator()
    
    print(f"\n聚合器初始化:")
    print(f"  可用提供者数量: {len(aggregator.providers)}")
    for provider in aggregator.providers:
        print(f"    - {provider.source.value}")
    
    # 测试获取新闻(使用一个示例股票代码)
    print(f"\n尝试获取新闻(000002):")
    try:
        response = aggregator.get_news(
            stock_code="000002",
            max_news=5
        )
        
        print(f"  成功: {response.success}")
        print(f"  新闻数量: {response.total_count}")
        print(f"  使用的数据源: {[s.value for s in response.sources_used]}")
        
        if response.news_items:
            print(f"\n  前3条新闻:")
            for i, news in enumerate(response.news_items[:3], 1):
                print(f"    {i}. {news.title[:50]}...")
                print(f"       来源: {news.source.value}, 时间: {news.publish_time}")
        else:
            print(f"  ⚠️ 未获取到新闻数据")
            
    except Exception as e:
        print(f"  获取失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n聚合器测试完成")


def test_convenience_function():
    """测试便捷函数"""
    print("\n" + "=" * 60)
    print("测试 5: 便捷函数")
    print("=" * 60)
    
    from tradingagents.news_engine import get_stock_news
    
    print(f"\n使用便捷函数获取新闻:")
    try:
        response = get_stock_news(
            stock_code="000002",
            max_news=3,
            hours_back=24
        )
        
        print(f"  成功: {response.success}")
        print(f"  新闻数量: {response.total_count}")
        
        if response.news_items:
            print(f"\n  新闻列表:")
            for i, news in enumerate(response.news_items, 1):
                print(f"    {i}. [{news.source.value}] {news.title[:40]}...")
        
        # 测试格式化报告
        report = response.format_report()
        print(report[:500] + "..." if len(report) > 500 else report)
        
    except Exception as e:
        print(f"  获取失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n便捷函数测试完成")


def test_market_type_selection():
    """测试市场类型选择"""
    print("\n" + "=" * 60)
    print("测试 6: 市场类型数据源选择")
    print("=" * 60)
    
    from tradingagents.news_engine.aggregator import NewsAggregator
    from tradingagents.news_engine.models import MarketType
    
    aggregator = NewsAggregator()
    
    test_cases = [
        (MarketType.A_SHARE, "A股"),
        (MarketType.HK_SHARE, "港股"),
        (MarketType.US_SHARE, "美股"),
    ]
    
    print("\n不同市场类型的数据源选择:")
    for market_type, name in test_cases:
        providers = aggregator._select_providers(market_type)
        sources = [p.source.value for p in providers]
        print(f"  {name}: {', '.join(sources)}")
    
    print("\n市场类型选择测试通过")


def test_comprehensive_news():
    """测试多市场全面新闻获取 (近1个月, 所有数据源)"""
    print("\n" + "=" * 60)
    print("测试 7: 多市场全面新闻获取")
    print("=" * 60)
    
    from tradingagents.news_engine.aggregator import NewsAggregator
    from collections import Counter
    
    aggregator = NewsAggregator()
    
    # 获取所有可用数据源
    all_sources = [p.source for p in aggregator.providers]
    print(f"使用数据源: {[s.value for s in all_sources]}")
    
    test_cases = [
        ("A股-深证", "000002"),      # 万科A
        ("A股-深证", "000001"),      # 平安银行
        ("A股-上证", "600519"),      # 贵州茅台
        ("A股-上证", "601398"),      # 工商银行
        ("港股", "0700.HK"),         # 腾讯控股
        ("港股", "9988.HK"),         # 阿里巴巴
        ("美股", "AAPL"),            # Apple
        ("美股", "NVDA"),            # Nvidia
    ]
    
    for market, code in test_cases:
        print(f"\n测试 {market} ({code}):")
        try:
            response = aggregator.get_news(
                stock_code=code,
                max_news=100,  # 获取足够多的新闻以观察分布
                hours_back=720, # 近1个月 (30天)
                sources=all_sources
            )
            
            print(f"  总新闻数: {response.total_count}")
            
            if response.news_items:
                # 统计各数据源新闻数量
                source_counts = Counter(item.source.value for item in response.news_items)
                print(f"  数据源分布: {dict(source_counts)}")
                
                # 打印第一条新闻
                first = response.news_items[0]
                print(f"  最新新闻: [{first.source.value}] {first.title} ({first.publish_time})")
            else:
                print("  ⚠️ 未获取到新闻")
                
        except Exception as e:
            print(f"  ❌ 获取失败: {e}")
            # import traceback
            # traceback.print_exc()

    print("\n全面测试完成")

def verify_providers():
    """自动验证各个providers是否正常work"""
    print("\n" + "=" * 60)
    print("测试 9: 验证所有 Providers")
    print("=" * 60)

    from providers.news_prov_eodhd import EODHDNewsProvider
    from datetime import datetime, timedelta

    providers = [
        # ("Tushare", TushareNewsProvider(), "000002"), # 万科
        # ("FinnHub", FinnhubNewsProvider(), "AAPL"),   # Apple
        ("EODHD", EODHDNewsProvider(), "AAPL"),       # Apple (or HK stock)
        # ("GoogleNews", GoogleNewsProvider(), "NVDA"), # Nvidia
        # ("AkShare_CLS", AkShareClsNewsProvider(), "000002"),
        # ("AkShare_Sina", AkShareSinaNewsProvider(), "000002"),
        # ("AkShare_EM", AkShareEmNewsProvider(), "000002"),
    ]

    for name, provider, test_code in providers:
        print(f"\n验证 {name} ...")
        if not provider.is_available():
            print(f"  ⚠️ {name} 未启用或不可用")
            continue
            
        try:
            print(f"  尝试获取 {test_code} 的新闻...")
            items = provider.get_news(
                stock_code=test_code,
                max_news=5,
                start_date=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            )
            
            if items:
                print(f"  ✅ 成功获取 {len(items)} 条新闻")
                print(f"  第一条: {items[0].title} ({items[0].publish_time})")
            else:
                print(f"  ⚠️ 成功调用但未返回新闻 (可能是无相关新闻)")
                
        except Exception as e:
            print(f"  ❌ 验证失败: {e}")
            # import traceback
            # traceback.print_exc()

    print("\nProvider 验证完成")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始测试 News 模块")
    print("=" * 60)
    
    tests = [
        # ("配置管理器", test_config),
        # ("数据模型", test_models),
        # ("新闻提供器", test_providers),
        # ("新闻聚合器", test_aggregator),
        # ("便捷函数", test_convenience_function),
        # ("市场类型选择", test_market_type_selection),
        # ("特定提供器测试", test_specific_providers),
        # ("全面新闻获取", test_comprehensive_news),
        ("Provider验证", verify_providers),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n❌ 测试失败: {test_name}")
            print(f"   错误: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # 打印测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"总测试数: {len(tests)}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
