#!/usr/bin/env python3
"""
测试relevance_checker.py的新功能
测试check_article_relevance辅助函数
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradingagents.tools.relevance_checker import check_article_relevance, RelevanceLevel


def test_string_article():
    """测试使用字符串类型的article参数"""
    print("=" * 60)
    print("测试1: 使用字符串类型的article参数")
    print("=" * 60)
    
    # 测试平安银行相关新闻
    article_text = "平安银行发布2024年第三季度财报，净利润同比增长15%，不良率继续下降"
    
    is_relevant, score, details = check_article_relevance(
        stock_code='000001',
        article=article_text
    )
    
    print(f"\n股票代码: 000001")
    print(f"文章内容: {article_text}")
    print(f"判定结果: {'✓ 相关' if is_relevant else '✗ 不相关'}")
    print(f"相关性分数: {score}")
    print(f"使用层级: {details['levels_used']}")
    print(f"各层分数: {details['scores']}")
    if details['matched_keywords']:
        print(f"匹配关键词: {', '.join(details['matched_keywords'])}")


def test_dict_article():
    """测试使用字典类型的article参数"""
    print("\n" + "=" * 60)
    print("测试2: 使用字典类型的article参数")
    print("=" * 60)
    
    # 测试万科相关新闻
    article_dict = {
        'title': '万科A发布年度销售数据',
        'content': '万科企业股份有限公司今日发布年度销售数据，全年销售额达到新高，土地储备充足'
    }
    
    is_relevant, score, details = check_article_relevance(
        stock_code='000002',
        article=article_dict
    )
    
    print(f"\n股票代码: 000002")
    print(f"文章标题: {article_dict['title']}")
    print(f"文章内容: {article_dict['content']}")
    print(f"判定结果: {'✓ 相关' if is_relevant else '✗ 不相关'}")
    print(f"相关性分数: {score}")
    print(f"使用层级: {details['levels_used']}")
    print(f"各层分数: {details['scores']}")
    if details['matched_keywords']:
        print(f"匹配关键词: {', '.join(details['matched_keywords'])}")


def test_empty_article():
    """测试空article参数"""
    print("\n" + "=" * 60)
    print("测试3: 测试空article参数")
    print("=" * 60)
    
    # 测试空字符串
    is_relevant, score, details = check_article_relevance(
        stock_code='000001',
        article=''
    )
    
    print(f"\n股票代码: 000001")
    print(f"文章内容: (空字符串)")
    print(f"判定结果: {'✓ 相关' if is_relevant else '✗ 不相关'}")
    print(f"相关性分数: {score}")
    
    # 测试None
    is_relevant, score, details = check_article_relevance(
        stock_code='000001',
        article=None
    )
    
    print(f"\n股票代码: 000001")
    print(f"文章内容: None")
    print(f"判定结果: {'✓ 相关' if is_relevant else '✗ 不相关'}")
    print(f"相关性分数: {score}")


def test_irrelevant_article():
    """测试不相关的文章"""
    print("\n" + "=" * 60)
    print("测试4: 测试不相关的文章")
    print("=" * 60)
    
    # 测试与平安银行无关的新闻
    article_text = "今天天气很好，适合外出游玩"
    
    is_relevant, score, details = check_article_relevance(
        stock_code='000001',
        article=article_text
    )
    
    print(f"\n股票代码: 000001 (平安银行)")
    print(f"文章内容: {article_text}")
    print(f"判定结果: {'✓ 相关' if is_relevant else '✗ 不相关'}")
    print(f"相关性分数: {score}")
    print(f"使用层级: {details['levels_used']}")
    print(f"各层分数: {details['scores']}")


def test_custom_thresholds():
    """测试自定义阈值"""
    print("\n" + "=" * 60)
    print("测试5: 测试自定义阈值")
    print("=" * 60)
    
    article_dict = {
        'title': '央行调整存贷款利率',
        'content': '中国人民银行宣布调整金融机构存贷款基准利率，各大银行将陆续跟进调整'
    }
    
    # 使用默认阈值
    is_relevant1, score1, details1 = check_article_relevance(
        stock_code='000001',
        article=article_dict
    )
    
    print(f"\n股票代码: 000001 (平安银行)")
    print(f"文章标题: {article_dict['title']}")
    print(f"使用默认阈值 (rule_engine_threshold=8):")
    print(f"  判定结果: {'✓ 相关' if is_relevant1 else '✗ 不相关'}")
    print(f"  相关性分数: {score1}")
    
    # 使用更低的阈值
    is_relevant2, score2, details2 = check_article_relevance(
        stock_code='000001',
        article=article_dict,
        rule_engine_threshold=3
    )
    
    print(f"\n使用较低阈值 (rule_engine_threshold=3):")
    print(f"  判定结果: {'✓ 相关' if is_relevant2 else '✗ 不相关'}")
    print(f"  相关性分数: {score2}")


def test_api_fallback():
    """测试从API获取股票信息的降级逻辑"""
    print("\n" + "=" * 60)
    print("测试6: 测试从API获取股票信息")
    print("=" * 60)
    
    # 测试一个不在stock_metadata.json.example中的股票
    article_text = "比亚迪发布新能源汽车销量数据，月销量再创新高"
    
    is_relevant, score, details = check_article_relevance(
        stock_code='002594',  # 比亚迪
        article=article_text
    )
    
    print(f"\n股票代码: 002594 (比亚迪 - 不在metadata文件中)")
    print(f"文章内容: {article_text}")
    print(f"判定结果: {'✓ 相关' if is_relevant else '✗ 不相关'}")
    print(f"相关性分数: {score}")
    print(f"使用层级: {details['levels_used']}")
    print(f"各层分数: {details['scores']}")


if __name__ == "__main__":
    print("🧪 测试relevance_checker新功能")
    print("=" * 60)
    print("📝 测试check_article_relevance辅助函数")
    print("=" * 60)
    
    try:
        test_string_article()
        test_dict_article()
        test_empty_article()
        test_irrelevant_article()
        test_custom_thresholds()
        test_api_fallback()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
