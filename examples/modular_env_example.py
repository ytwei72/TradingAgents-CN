#!/usr/bin/env python3
"""
模块化环境变量配置使用示例

演示如何使用模块化环境变量配置系统
"""

import os
from pathlib import Path


def example_1_basic_usage():
    """示例 1: 基础使用 - 使用配置管理器"""
    print("=" * 60)
    print("示例 1: 基础使用 - 使用配置管理器")
    print("=" * 60)
    
    from tradingagents.dataflows.news_config import get_news_config_manager
    
    # 获取配置管理器(启用详细日志)
    config_manager = get_news_config_manager(verbose=True)
    
    # 打印配置
    config_manager.print_config()
    
    # 获取配置对象
    config = config_manager.get_config()
    
    # 使用配置
    print("\n使用配置:")
    print(f"  FinnHub 启用: {config.finnhub_enabled}")
    print(f"  默认回溯时间: {config.default_hours_back} 小时")
    print(f"  最大新闻数: {config.default_max_news} 条")
    print(f"  缓存启用: {config.cache_enabled}")
    
    # 根据配置执行逻辑
    if config.finnhub_enabled and config.finnhub_key:
        print("\n✅ FinnHub 已配置且启用,可以使用")
    else:
        print("\n❌ FinnHub 未配置或未启用")


def example_2_direct_loader():
    """示例 2: 直接使用环境变量加载器"""
    print("\n" + "=" * 60)
    print("示例 2: 直接使用环境变量加载器")
    print("=" * 60)
    
    from tradingagents.utils.env_loader import ModularEnvLoader
    
    # 创建加载器
    loader = ModularEnvLoader(module_name="dataflows")
    
    # 加载环境变量
    loaded_vars = loader.load_env(verbose=True)
    
    print(f"\n加载了 {len(loaded_vars)} 个模块级环境变量")
    
    # 获取不同类型的环境变量
    print("\n获取环境变量:")
    
    # 字符串
    api_key = loader.get_env('NEWSAPI_KEY', default='未配置')
    print(f"  NewsAPI Key: {api_key[:10]}..." if len(api_key) > 10 else f"  NewsAPI Key: {api_key}")
    
    # 布尔值
    enabled = loader.get_env_bool('NEWS_FINNHUB_ENABLED', default=True)
    print(f"  FinnHub 启用: {enabled}")
    
    # 整数
    max_news = loader.get_env_int('NEWS_DEFAULT_MAX_NEWS', default=10)
    print(f"  最大新闻数: {max_news}")
    
    # 浮点数
    threshold = loader.get_env_float('NEWS_RELEVANCE_THRESHOLD', default=0.3)
    print(f"  相关性阈值: {threshold}")
    
    # 列表
    sources = loader.get_env_list('NEWS_ENABLED_SOURCES', default=['finnhub', 'akshare'])
    print(f"  启用的数据源: {sources}")


def example_3_custom_module():
    """示例 3: 为自定义模块创建配置"""
    print("\n" + "=" * 60)
    print("示例 3: 为自定义模块创建配置")
    print("=" * 60)
    
    from tradingagents.utils.env_loader import ModularEnvLoader
    
    # 假设我们有一个自定义模块在 tradingagents/custom_module
    # 我们可以为它创建专门的配置
    
    # 方式 1: 通过模块路径
    custom_module_path = Path(__file__).parent.parent / "tradingagents" / "agents"
    loader = ModularEnvLoader(module_path=custom_module_path)
    loader.load_env(verbose=True)
    
    # 获取自定义配置
    max_iterations = loader.get_env_int('AGENT_MAX_ITERATIONS', default=10)
    timeout = loader.get_env_int('AGENT_TIMEOUT', default=300)
    
    print(f"\n自定义模块配置:")
    print(f"  最大迭代次数: {max_iterations}")
    print(f"  超时时间: {timeout} 秒")


def example_4_config_priority():
    """示例 4: 演示配置优先级"""
    print("\n" + "=" * 60)
    print("示例 4: 演示配置优先级")
    print("=" * 60)
    
    from tradingagents.utils.env_loader import ModularEnvLoader
    
    # 1. 全局配置
    print("\n1. 全局配置 (项目根目录 .env):")
    print("   FINNHUB_API_KEY=global_key")
    
    # 2. 模块配置(会覆盖全局配置)
    print("\n2. 模块配置 (tradingagents/dataflows/.env):")
    print("   FINNHUB_API_KEY=module_key")
    print("   NEWS_DEFAULT_MAX_NEWS=20")
    
    # 3. 加载配置
    loader = ModularEnvLoader(module_name="dataflows")
    loader.load_env(verbose=False)
    
    # 4. 查看最终结果
    print("\n3. 最终配置:")
    finnhub_key = loader.get_env('FINNHUB_API_KEY')
    max_news = loader.get_env_int('NEWS_DEFAULT_MAX_NEWS', default=10)
    
    print(f"   FINNHUB_API_KEY: {finnhub_key[:15]}..." if finnhub_key and len(finnhub_key) > 15 else f"   FINNHUB_API_KEY: {finnhub_key}")
    print(f"   NEWS_DEFAULT_MAX_NEWS: {max_news}")
    
    print("\n说明:")
    print("  - FINNHUB_API_KEY 使用模块配置(覆盖了全局配置)")
    print("  - NEWS_DEFAULT_MAX_NEWS 使用模块配置(全局没有此配置)")


def example_5_conditional_loading():
    """示例 5: 条件加载和动态配置"""
    print("\n" + "=" * 60)
    print("示例 5: 条件加载和动态配置")
    print("=" * 60)
    
    from tradingagents.dataflows.news_config import get_news_config
    
    # 获取配置
    config = get_news_config()
    
    # 根据配置决定使用哪些数据源
    enabled_sources = []
    
    if config.finnhub_enabled and config.finnhub_key:
        enabled_sources.append('FinnHub')
    
    if config.alpha_vantage_enabled and config.alpha_vantage_key:
        enabled_sources.append('Alpha Vantage')
    
    if config.newsapi_enabled and config.newsapi_key:
        enabled_sources.append('NewsAPI')
    
    if config.tushare_enabled:
        enabled_sources.append('Tushare')
    
    if config.akshare_enabled:
        enabled_sources.append('AKShare')
    
    print(f"\n启用的新闻数据源: {', '.join(enabled_sources)}")
    print(f"总计: {len(enabled_sources)} 个数据源")
    
    # 根据配置调整行为
    if config.verbose_logging:
        print("\n详细日志已启用,将输出更多调试信息")
    
    if config.cache_enabled:
        print(f"缓存已启用,过期时间: {config.cache_expiry} 秒")
    else:
        print("缓存已禁用,每次都会重新获取数据")


def example_6_reload_config():
    """示例 6: 重新加载配置"""
    print("\n" + "=" * 60)
    print("示例 6: 重新加载配置")
    print("=" * 60)
    
    from tradingagents.dataflows.news_config import get_news_config_manager
    
    # 获取配置管理器
    config_manager = get_news_config_manager()
    
    # 获取初始配置
    config = config_manager.get_config()
    print(f"\n初始配置:")
    print(f"  最大新闻数: {config.default_max_news}")
    
    # 模拟修改环境变量(实际应用中可能是修改 .env 文件)
    import os
    os.environ['NEWS_DEFAULT_MAX_NEWS'] = '50'
    
    # 重新加载配置
    print("\n修改环境变量后重新加载...")
    config_manager.reload_config()
    
    # 获取新配置
    config = config_manager.get_config()
    print(f"\n新配置:")
    print(f"  最大新闻数: {config.default_max_news}")


def example_7_error_handling():
    """示例 7: 错误处理和验证"""
    print("\n" + "=" * 60)
    print("示例 7: 错误处理和验证")
    print("=" * 60)
    
    from tradingagents.utils.env_loader import ModularEnvLoader
    
    loader = ModularEnvLoader(module_name="dataflows")
    loader.load_env()
    
    # 1. 必需的配置项
    try:
        api_key = loader.get_env('CRITICAL_API_KEY', required=True)
        print(f"✅ 必需配置已设置: {api_key}")
    except ValueError as e:
        print(f"❌ 错误: {e}")
    
    # 2. 类型转换错误处理
    os.environ['INVALID_NUMBER'] = 'not_a_number'
    invalid_num = loader.get_env_int('INVALID_NUMBER', default=10)
    print(f"\n类型转换失败时使用默认值: {invalid_num}")
    
    # 3. 配置验证
    max_news = loader.get_env_int('NEWS_DEFAULT_MAX_NEWS', default=10)
    if max_news <= 0 or max_news > 100:
        print(f"⚠️ 警告: NEWS_DEFAULT_MAX_NEWS={max_news} 超出合理范围,建议设置为 1-100")
    else:
        print(f"✅ NEWS_DEFAULT_MAX_NEWS={max_news} 在合理范围内")


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("模块化环境变量配置使用示例")
    print("=" * 60)
    
    try:
        # 运行所有示例
        example_1_basic_usage()
        example_2_direct_loader()
        example_3_custom_module()
        example_4_config_priority()
        example_5_conditional_loading()
        example_6_reload_config()
        example_7_error_handling()
        
        print("\n" + "=" * 60)
        print("所有示例运行完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 运行示例时出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
