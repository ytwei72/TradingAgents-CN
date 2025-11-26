#!/usr/bin/env python3
"""
新闻接口对比测试

对比新版 news 模块接口与老版接口的功能和性能
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_old_interface():
    """测试老版新闻接口"""
    print("\n" + "=" * 60)
    print("测试老版新闻接口")
    print("=" * 60)
    
    try:
        from tradingagents.dataflows.realtime_news_utils import RealtimeNewsAggregator
        
        print("\n初始化 RealtimeNewsAggregator...")
        aggregator = RealtimeNewsAggregator()
        
        # 测试获取新闻
        stock_code = "000002"
        curr_date = datetime.now().strftime("%Y-%m-%d")
        
        print(f"\n获取 {stock_code} 的新�?(日期: {curr_date})...")
        start_time = time.time()
        
        news_result = aggregator.get_realtime_stock_news(
            ticker=stock_code,
            curr_date=curr_date,
            hours_back=6
        )
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        print(f"\n老版接口执行完成")
        print(f"⏱️  耗时: {elapsed:.2f} 秒")
        print(f"📊 返回类型: {type(news_result)}")
        print(f"📏 返回长度: {len(news_result) if news_result else 0} 字符")
        
        if news_result:
            print(f"\n📋 返回内容预览 (前500字符):")
            print(news_result[:500])
            print("...")
        else:
            print("\n未返回新闻数据")
        
        return {
            "success": True,
            "elapsed": elapsed,
            "result_length": len(news_result) if news_result else 0,
            "result_type": "str",
            "result": news_result
        }
        
    except Exception as e:
        print(f"\n老版接口测试失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


def test_new_interface():
    """测试新版 news 模块接口"""
    print("\n" + "=" * 60)
    print("测试新版 news 模块接口")
    print("=" * 60)
    
    try:
        from tradingagents.news_engine import get_stock_news
        
        # 测试获取新闻
        stock_code = "000002"
        
        print(f"\n获取 {stock_code} 的新闻..")
        start_time = time.time()
        
        response = get_stock_news(
            stock_code=stock_code,
            max_news=10,
            hours_back=6
        )
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        print(f"\n新版接口执行完成")
        print(f"⏱️  耗时: {elapsed:.2f} 秒")
        print(f"📊 返回类型: {type(response).__name__}")
        print(f"✔️  成功状态: {response.success}")
        print(f"📰 新闻数量: {response.total_count}")
        print(f"🔍 使用的数据源: {[s.value for s in response.sources_used]}")
        
        if response.news_items:
            print(f"\n📋 返回 {len(response.news_items)} 条新闻")
            for i, news in enumerate(response.news_items[:3], 1):
                print(f"\n  {i}. {news.title[:60]}...")
                print(f"     来源: {news.source.value}")
                print(f"     时间: {news.publish_time}")
                print(f"     相关度: {news.relevance_score:.2f}")
                print(f"     紧急度: {news.urgency.value}")
        else:
            print("\n未获取到新闻数据")
        
        # 生成格式化报�?
        print(f"\n生成格式化报�?..")
        report = response.format_report()
        print(f"📏 报告长度: {len(report)} 字符")
        
        return {
            "success": response.success,
            "elapsed": elapsed,
            "news_count": response.total_count,
            "result_type": "NewsResponse",
            "sources_used": [s.value for s in response.sources_used],
            "response": response,
            "report": report
        }
        
    except Exception as e:
        print(f"\n新版接口测试失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


def compare_interfaces():
    """对比两个接口"""
    print("\n" + "=" * 60)
    print("接口对比分析")
    print("=" * 60)
    
    # 运行老版接口测试
    old_result = test_old_interface()
    
    # 运行新版接口测试
    new_result = test_new_interface()
    
    # 对比结果
    print("\n" + "=" * 60)
    print("对比结果总结")
    print("=" * 60)
    
    print("\n📊 功能对比:")
    print(f"{'特性':<20} {'老版接口':<25} {'新版接口':<25}")
    print("-" * 70)
    
    # 成功状态
    old_success = "成功" if old_result.get("success") else "失败"
    new_success = "成功" if new_result.get("success") else "失败"
    print(f"{'执行状态':<20} {old_success:<25} {new_success:<25}")
    
    # 返回类型
    old_type = old_result.get("result_type", "N/A")
    new_type = new_result.get("result_type", "N/A")
    print(f"{'返回类型':<20} {old_type:<25} {new_type:<25}")
    
    # 数据结构
    print(f"{'数据结构':<20} {'字符数':<25} {'结构化程度':<25}")
    
    # 新闻数量
    old_count = "N/A"
    new_count = str(new_result.get("news_count", 0)) if new_result.get("success") else "N/A"
    print(f"{'新闻数量':<20} {old_count:<25} {new_count:<25}")
    
    # 数据源信息
    old_sources = "不透明"
    new_sources = ", ".join(new_result.get("sources_used", [])) if new_result.get("success") else "N/A"
    print(f"{'数据源':<20} {old_sources:<25} {new_sources[:25]:<25}")
    
    # 性能对比
    print(f"\n性能对比:")
    old_time = old_result.get("elapsed", 0)
    new_time = new_result.get("elapsed", 0)
    print(f"  老版接口耗时: {old_time:.2f} 秒")
    print(f"  新版接口耗时: {new_time:.2f} 秒")
    
    if old_time > 0 and new_time > 0:
        if new_time < old_time:
            improvement = ((old_time - new_time) / old_time) * 100
            print(f"  新版接口比老版接口快 {improvement:.1f}%")
        elif new_time > old_time:
            slower = ((new_time - old_time) / old_time) * 100
            print(f"  新版接口比老版接口慢 {slower:.1f}%")
        else:
            print(f"  性能相当")
    
    # 功能优势对比
    print(f"\n🎯 功能优势对比:")
    
    print(f"\n老版接口优势:")
    print(f"  已经集成到现有系统")
    print(f"  经过实际使用验证")
    print(f"  与现有工具链兼容")
    
    print(f"\n新版接口优势:")
    print(f"  结构化数据返回(NewsResponse 对象)")
    print(f"  类型安全 (完整类型提示)")
    print(f"  多数据源聚合 (自动选择最佳数据源)")
    print(f"  模块化配置 (独立的环境变量)")
    print(f"  数据源透明 (明确显示使用的数据源)")
    print(f"  丰富的元数据 (紧急度、相关性、情绪等)")
    print(f"  格式化报告生成")
    print(f"  去重和过滤机制")
    print(f"  容错设计 (单个数据源失败不影响整体)")
    
    # 使用建议
    print(f"\n💡 使用建议:")
    print(f"  1. 现有代码继续使用老版接口,保持稳定")
    print(f"  2. 新功能开发推荐使用新版接口享受更多功能")
    print(f"  3. 可以逐步迁移到新版接口,两者可以并存")
    print(f"  4. 新版接口提供更好的可维护性和扩展性")


def test_new_interface_advanced():
    """测试新版接口的高级功能"""
    print("\n" + "=" * 60)
    print("测试新版接口高级功能")
    print("=" * 60)
    
    try:
        from tradingagents.news_engine import get_stock_news
        from tradingagents.news_engine.models import NewsSource
        
        # 测试1: 指定数据源
        print("\n测试 1: 指定数据源(只使用AKShare)")
        response1 = get_stock_news(
            "000002",
            sources=[NewsSource.AKSHARE],
            max_news=5
        )
        print(f"  使用的数据源: {[s.value for s in response1.sources_used]}")
        print(f"  新闻数量: {response1.total_count}")
        
        # 测试2: 指定日期范围
        print("\n测试 2: 指定日期范围")
        response2 = get_stock_news(
            "000002",
            start_date="2025-11-20",
            end_date="2025-11-26",
            max_news=10
        )
        print(f"  查询日期: {response2.query.start_date} ~ {response2.query.end_date}")
        print(f"  新闻数量: {response2.total_count}")
        
        # 测试3: 不同市场
        print("\n测试 3: 不同市场类型")
        
        test_stocks = [
            ("000002", "A股"),
            ("0700.HK", "港股"),
            ("AAPL", "美股"),
        ]
        
        for stock_code, market_name in test_stocks:
            try:
                response = get_stock_news(stock_code, max_news=3)
                print(f"  {market_name} ({stock_code}):")
                print(f"    市场类型: {response.query.market_type.value if response.query.market_type else 'N/A'}")
                print(f"    新闻数量: {response.total_count}")
                print(f"    数据源 {[s.value for s in response.sources_used]}")
            except Exception as e:
                print(f"  {market_name} ({stock_code}): {e}")
        
        # 测试4: 格式化报告生成
        print("\n测试 4: 格式化报告生成")
        response4 = get_stock_news("000002", max_news=5)
        report = response4.format_report()
        print(f"  报告长度: {len(report)} 字符")
        print(f"  报告预览 (前300字符):")
        print(report[:300])
        print("  ...")
        
        print("\n新版接口高级功能测试完成")
        
    except Exception as e:
        print(f"\n新版接口高级功能测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_configuration():
    """测试配置管理"""
    print("\n" + "=" * 60)
    print("测试配置管理")
    print("=" * 60)
    
    try:
        from tradingagents.news_engine.config import get_news_config_manager
        
        # 获取配置管理器
        config_manager = get_news_config_manager(verbose=False)
        config = config_manager.get_config()
        
        print("\n📋 当前配置:")
        print(f"  默认回溯时间: {config.default_hours_back} 小时")
        print(f"  默认最大新闻数: {config.default_max_news}")
        print(f"  相关性阈值: {config.relevance_threshold}")
        print(f"  缓存启用: {config.cache_enabled}")
        
        print("\n🔧 数据源状态")
        sources = [
            ("AKShare", config.akshare_enabled),
            ("Tushare", config.tushare_enabled),
            ("FinnHub", config.finnhub_enabled),
            ("EODHD", config.eodhd_enabled),
            ("NewsAPI", config.newsapi_enabled),
            ("Alpha Vantage", config.alpha_vantage_enabled),
        ]
        
        for name, enabled in sources:
            status = "启用" if enabled else "禁用"
            print(f"  {name}: {status}")
        
        print("\n配置管理测试完成")
        
    except Exception as e:
        print(f"\n配置管理测试失败: {e}")
        import traceback
        traceback.print_exc()


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print(" " * 20 + "新闻接口对比测试")
    print("=" * 80)
    
    # 测试配置
    test_configuration()
    
    # 对比基本功能
    compare_interfaces()
    
    # 测试新版高级功能
    test_new_interface_advanced()
    
    print("\n" + "=" * 80)
    print("所有测试完成")
    print("=" * 80)


if __name__ == "__main__":
    run_all_tests()
