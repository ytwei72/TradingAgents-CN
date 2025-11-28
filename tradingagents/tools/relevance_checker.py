"""
股票新闻相关性判定系统
支持多层级策略，可根据需求灵活配置
"""

import re
import json
import os
from typing import Dict, List, Tuple, Optional, Union
from enum import Enum

class RelevanceLevel(Enum):
    """相关性判定层级"""
    QUICK_FILTER = 1  # 快速关键词过滤
    RULE_ENGINE = 2  # 规则引擎打分
    SEMANTIC_MATCH = 3  # 语义匹配（需要额外安装依赖）


class StockNewsRelevanceChecker:
    """
    股票新闻相关性判定器

    用法示例:
        # 基础配置
        checker = StockNewsRelevanceChecker(
            stock_code='000001',
            stock_name='平安银行',
            company_name='平安银行股份有限公司',
            industry='银行业'
        )

        # 设置判定层级
        checker.set_strategy_levels([
            RelevanceLevel.QUICK_FILTER,
            RelevanceLevel.RULE_ENGINE
        ])

        # 判定新闻相关性
        is_relevant, score, details = checker.check_relevance(title, content)
    """

    def __init__(
            self,
            stock_code: str,
            stock_name: str,
            company_name: str,
            industry: str = None,
            aliases: List[str] = None,
            industry_keywords: List[str] = None
    ):
        """
        初始化判定器

        Args:
            stock_code: 股票代码，如 '000001'
            stock_name: 股票名称，如 '平安银行'
            company_name: 公司全称，如 '平安银行股份有限公司'
            industry: 所属行业，如 '银行业'
            aliases: 公司别名列表，如 ['平安', 'PAB']
            industry_keywords: 行业关键词，如 ['存款', '贷款', '利率']
        """
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.company_name = company_name
        self.industry = industry
        self.aliases = aliases or []
        self.industry_keywords = industry_keywords or self._get_default_industry_keywords()

        # 默认使用前两层
        self.strategy_levels = [
            RelevanceLevel.QUICK_FILTER,
            RelevanceLevel.RULE_ENGINE
        ]

        # 用于语义匹配的模型（延迟加载）
        self._semantic_model = None

        # 配置参数
        self.config = {
            'quick_filter_threshold': 1,  # 快速过滤阈值
            'rule_engine_threshold': 8,  # 规则引擎阈值
            'semantic_threshold': 0.3,  # 语义相似度阈值
            'min_name_length': 2,  # 最小名称长度（避免单字误判）
        }

    def set_strategy_levels(self, levels: List[RelevanceLevel]):
        """设置判定策略层级"""
        self.strategy_levels = sorted(levels, key=lambda x: x.value)

    def set_config(self, **kwargs):
        """更新配置参数"""
        self.config.update(kwargs)

    def check_relevance(
            self,
            article: Union[str, Dict[str, str], None] = None,
            return_details: bool = True
    ) -> Tuple[bool, float, Optional[Dict]]:
        """
        判定新闻与股票的相关性

        Args:
            article: 新闻文章，支持字符串或字典类型
                    - 字符串: 直接作为文本内容
                    - 字典: 包含'title'和'content'字段
                    - None: 返回默认值
            return_details: 是否返回详细判定信息

        Returns:
            (是否相关, 相关性分数, 详细信息字典)
        """
        # 处理article参数
        if article is None:
            # 参数为空，返回默认值
            return False, 0.0, {'levels_used': [], 'scores': {}, 'matched_keywords': []} if return_details else None
        
        if isinstance(article, str):
            # article是字符串，直接使用
            if not article:
                return False, 0.0, {'levels_used': [], 'scores': {}, 'matched_keywords': []} if return_details else None
            text = article
        elif isinstance(article, dict):
            # article是字典，提取title和content
            title_text = article.get('title', '')
            content_text = article.get('content', '')
            if not title_text and not content_text:
                return False, 0.0, {'levels_used': [], 'scores': {}, 'matched_keywords': []} if return_details else None
            text = f"{title_text} {content_text}"
        else:
            raise TypeError(f"article参数必须是字符串或字典类型，当前类型: {type(article)}")
        
        details = {
            'levels_used': [],
            'scores': {},
            'matched_keywords': []
        }

        # 按层级依次判定
        for level in self.strategy_levels:
            if level == RelevanceLevel.QUICK_FILTER:
                passed, score, info = self._quick_filter(text)
                details['levels_used'].append('quick_filter')
                details['scores']['quick_filter'] = score
                details['matched_keywords'].extend(info.get('matched', []))

                if not passed:
                    return False, score, details if return_details else None

            elif level == RelevanceLevel.RULE_ENGINE:
                score, info = self._rule_engine(text)
                details['levels_used'].append('rule_engine')
                details['scores']['rule_engine'] = score
                details['matched_keywords'].extend(info.get('matched', []))

                threshold = self.config['rule_engine_threshold']
                if score >= threshold:
                    return True, score, details if return_details else None

            elif level == RelevanceLevel.SEMANTIC_MATCH:
                score, info = self._semantic_match(text)
                details['levels_used'].append('semantic_match')
                details['scores']['semantic_match'] = score

                threshold = self.config['semantic_threshold']
                if score >= threshold:
                    return True, score, details if return_details else None

        # 所有层级判定完成，根据最后一层结果决定
        final_score = list(details['scores'].values())[-1] if details['scores'] else 0
        return False, final_score, details if return_details else None

    def _quick_filter(self, text: str) -> Tuple[bool, float, Dict]:
        """
        第一层：快速关键词过滤
        快速排除明显不相关的新闻
        """
        text_lower = text.lower()
        matched = []
        score = 0

        # 检查核心关键词
        high_priority = [
            self.stock_code,
            self.company_name,
        ]

        for keyword in high_priority:
            if keyword and keyword.lower() in text_lower:
                matched.append(keyword)
                score += 1

        # 检查股票名称（需要长度检查）
        if len(self.stock_name) >= self.config['min_name_length']:
            if self.stock_name.lower() in text_lower:
                matched.append(self.stock_name)
                score += 1

        threshold = self.config['quick_filter_threshold']
        passed = score >= threshold

        return passed, score, {'matched': matched}

    def _rule_engine(self, text: str) -> Tuple[float, Dict]:
        """
        第二层：规则引擎打分
        综合多种规则计算相关性分数
        """
        text_lower = text.lower()
        matched = []
        score = 0

        # 规则1：直接提及股票代码或公司全称（高权重：10分）
        high_priority = [self.stock_code, self.company_name]
        for keyword in high_priority:
            if keyword and keyword.lower() in text_lower:
                matched.append(f"[高权重]{keyword}")
                score += 10
                break  # 只计一次

        # 规则2：股票名称提及（中权重：5分）
        if len(self.stock_name) >= self.config['min_name_length']:
            if self.stock_name.lower() in text_lower:
                # 检查是否是独立词（避免"平安夜"匹配"平安"）
                if self._is_independent_word(text, self.stock_name):
                    matched.append(f"[中权重]{self.stock_name}")
                    score += 5

        # 规则3：别名提及（中权重：3分）
        for alias in self.aliases:
            if alias and len(alias) >= self.config['min_name_length']:
                if alias.lower() in text_lower and self._is_independent_word(text, alias):
                    matched.append(f"[中权重]{alias}")
                    score += 3
                    break

        # 规则4：行业关键词（低权重：每个1分，最多3分）
        industry_count = 0
        for keyword in self.industry_keywords:
            if keyword and keyword.lower() in text_lower:
                industry_count += 1
                matched.append(f"[行业]{keyword}")

        score += min(industry_count, 3)

        # 规则5：负面信号过滤（减分）
        if self._has_negative_signals(text):
            score -= 5
            matched.append("[负面信号]")

        # 规则6：正面信号加成（如财报、公告等）
        if self._has_positive_signals(text):
            score += 2
            matched.append("[正面信号]")

        return score, {'matched': matched}

    def _semantic_match(self, text: str) -> Tuple[float, Dict]:
        """
        第三层：语义匹配
        使用轻量级语义模型判断相关性
        需要安装: pip install sentence-transformers
        """
        try:
            if self._semantic_model is None:
                from sentence_transformers import SentenceTransformer, util
                # 使用轻量级多语言模型
                self._semantic_model = SentenceTransformer(
                    'paraphrase-multilingual-MiniLM-L12-v2'
                )
                self._util = util

            # 构建查询和文档
            query = f"{self.stock_name} {self.company_name} {self.industry or ''}"
            # 限制文本长度以提高速度（取前500个字符）
            doc = text[:500] if len(text) > 500 else text

            # 计算语义相似度
            embeddings = self._semantic_model.encode([query, doc])
            similarity = self._util.cos_sim(embeddings[0], embeddings[1]).item()

            return similarity, {'similarity': similarity}

        except ImportError:
            print("警告: 未安装 sentence-transformers，跳过语义匹配层")
            print("安装命令: pip install sentence-transformers")
            return 0.0, {'error': 'sentence-transformers not installed'}

    def _is_independent_word(self, text: str, word: str) -> bool:
        """
        检查词是否独立出现（避免"平安夜"匹配"平安"）
        简单实现：检查前后是否有中文字符
        """
        pattern = f"[^\\u4e00-\\u9fa5]{re.escape(word)}[^\\u4e00-\\u9fa5]"
        # 也要匹配开头和结尾
        return (
                re.search(pattern, text) is not None or
                text.startswith(word) or
                text.endswith(word)
        )

    def _has_negative_signals(self, text: str) -> bool:
        """检查负面信号（排除不相关内容）"""
        # 根据股票名称定制负面词
        negative_patterns = {
            '平安': ['平安夜', '平安福', '出入平安', '平安无事'],
            '中国': ['中国队', '中国足球', '中国篮球'],  # 如果是"中国银行"
        }

        for key, patterns in negative_patterns.items():
            if key in self.stock_name or key in self.company_name:
                if any(pattern in text for pattern in patterns):
                    return True

        return False

    def _has_positive_signals(self, text: str) -> bool:
        """检查正面信号（增强相关性）"""
        positive_keywords = [
            '财报', '公告', '业绩', '公布', '发布',
            '董事会', '股东大会', '分红', '增持', '回购'
        ]
        return any(keyword in text for keyword in positive_keywords)

    def _get_default_industry_keywords(self) -> List[str]:
        """获取默认行业关键词"""
        industry_map = {
            '银行': ['存款', '贷款', '利率', '不良率', '拨备', '息差'],
            '证券': ['交易', '佣金', '承销', '自营', '投行'],
            '保险': ['保费', '理赔', '承保', '投资收益', '综合成本率'],
            '科技': ['芯片', '半导体', '研发', '专利', '5G', 'AI'],
            '地产': ['销售', '土地', '竣工', '预售', '去化'],
            '医药': ['新药', '临床', '审批', '医保', '集采'],
            '汽车': ['销量', '新能源', '智能驾驶', '交付'],
        }

        if self.industry:
            for key, keywords in industry_map.items():
                if key in self.industry:
                    return keywords

        return []

    def batch_check(
            self,
            news_list: List[Union[str, Dict[str, str]]]
    ) -> List[Tuple[bool, float, Dict]]:
        """
        批量判定新闻相关性

        Args:
            news_list: 新闻列表，每条新闻可以是字符串或字典 {'title': ..., 'content': ...}

        Returns:
            判定结果列表
        """
        results = []
        for news in news_list:
            result = self.check_relevance(
                article=news,
                return_details=True
            )
            results.append(result)

        return results


def _load_stock_metadata(stock_code: str) -> Optional[Dict[str, any]]:
    """
    从JSON文件加载股票元数据
    
    Args:
        stock_code: 股票代码
    
    Returns:
        股票元数据字典，如果未找到则返回None
    """
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 尝试多个可能的文件路径
    possible_files = [
        # os.path.join(current_dir, 'stock_metadata.json'),
        # os.path.join(current_dir, 'stock_metadata.json.example'),
        os.path.join(current_dir, '跳过文件读取元数据.json'),
    ]
    
    metadata_file = None
    for file_path in possible_files:
        if os.path.exists(file_path):
            metadata_file = file_path
            break
    
    # 如果文件不存在，尝试从API获取
    if metadata_file is None:
        return _get_stock_metadata_from_api(stock_code)
    
    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata_dict = json.load(f)
        
        # 查找对应的股票代码
        if stock_code in metadata_dict:
            return metadata_dict[stock_code]
        else:
            # 如果JSON中没有，尝试从API获取
            return _get_stock_metadata_from_api(stock_code)
    
    except Exception as e:
        print(f"警告: 加载股票元数据失败: {e}")
        return _get_stock_metadata_from_api(stock_code)


def _get_stock_metadata_from_api(stock_code: str) -> Optional[Dict[str, any]]:
    """
    从API获取股票元数据
    
    Args:
        stock_code: 股票代码
    
    Returns:
        股票元数据字典，如果获取失败则返回None
    """
    try:
        from tradingagents.api.stock_api import get_stock_info
        
        stock_info = get_stock_info(stock_code)
        
        if stock_info and 'error' not in stock_info:
            # 构造元数据
            metadata = {
                'stock_code': stock_code,
                'stock_name': stock_info.get('name', stock_code),
                'company_name': stock_info.get('name', stock_code),  # 如果有全称字段可以使用
                'industry': stock_info.get('industry', ''),
                'aliases': [],  # 可以根据需要扩展
                'industry_keywords': []  # 将使用默认行业关键词
            }
            return metadata
        else:
            print(f"警告: 无法从API获取股票{stock_code}的信息")
            return None
    
    except Exception as e:
        print(f"警告: 从API获取股票元数据失败: {e}")
        return None


def check_article_relevance(
        stock_code: str,
        article: Union[str, Dict[str, str], None],
        strategy_levels: List[RelevanceLevel] = None,
        quick_filter_threshold: int = 1,
        rule_engine_threshold: int = 8,
        return_details: bool = True
) -> Tuple[bool, float, Optional[Dict]]:
    """
    辅助函数：通过股票代码检查文章相关性
    
    Args:
        stock_code: 股票代码（如 '000001'）
        article: 新闻文章，支持字符串或字典类型
                - 字符串: 直接作为文本内容
                - 字典: 包含'title'和'content'字段
                - None: 返回默认值
        strategy_levels: 判定策略层级列表，默认使用[QUICK_FILTER, RULE_ENGINE]
        quick_filter_threshold: 快速过滤阈值，默认1
        rule_engine_threshold: 规则引擎阈值，默认8
        return_details: 是否返回详细判定信息
    
    Returns:
        (是否相关, 相关性分数, 详细信息字典)
    
    Example:
        >>> # 使用字符串
        >>> is_relevant, score, details = check_article_relevance(
        ...     '000001',
        ...     '平安银行发布2024年第三季度财报'
        ... )
        
        >>> # 使用字典
        >>> is_relevant, score, details = check_article_relevance(
        ...     '000001',
        ...     {'title': '平安银行发布财报', 'content': '净利润同比增长15%'}
        ... )
    """
    # 加载股票元数据
    metadata = _load_stock_metadata(stock_code)
    
    if metadata is None:
        # 如果无法获取元数据，使用基本信息
        print(f"警告: 无法获取股票{stock_code}的元数据，使用基本配置")
        metadata = {
            'stock_code': stock_code,
            'stock_name': stock_code,
            'company_name': stock_code,
            'industry': None,
            'aliases': [],
            'industry_keywords': []
        }
    
    # 创建相关性检查器
    checker = StockNewsRelevanceChecker(
        stock_code=metadata['stock_code'],
        stock_name=metadata['stock_name'],
        company_name=metadata['company_name'],
        industry=metadata.get('industry'),
        aliases=metadata.get('aliases', []),
        industry_keywords=metadata.get('industry_keywords', [])
    )
    
    # 设置策略层级
    if strategy_levels is None:
        strategy_levels = [
            RelevanceLevel.QUICK_FILTER,
            RelevanceLevel.RULE_ENGINE
        ]
    checker.set_strategy_levels(strategy_levels)
    
    # 设置阈值
    checker.set_config(
        quick_filter_threshold=quick_filter_threshold,
        rule_engine_threshold=rule_engine_threshold
    )
    
    # 执行相关性检查
    return checker.check_relevance(
        article=article,
        return_details=return_details
    )


def test_stock_news_relevance_checker():
    """测试 StockNewsRelevanceChecker 类的基本功能"""
    # 创建判定器
    checker = StockNewsRelevanceChecker(
        stock_code='000001',
        stock_name='平安银行',
        company_name='平安银行股份有限公司',
        industry='银行业',
        aliases=['平安', 'PAB'],
        industry_keywords=['存款', '贷款', '利率', '不良率']
    )

    # 配置策略（默认使用前两层）
    checker.set_strategy_levels([
        RelevanceLevel.QUICK_FILTER,
        RelevanceLevel.RULE_ENGINE,
        RelevanceLevel.SEMANTIC_MATCH  # 可选启用语义匹配层
    ])

    # 调整阈值
    checker.set_config(
        quick_filter_threshold=1,
        rule_engine_threshold=13
    )

    # 测试用例
    test_cases = [
        {
            'title': '平安银行发布2024年第三季度财报',
            'content': '平安银行股份有限公司今日发布第三季度财报，净利润同比增长15%，不良率继续下降...'
        },
        {
            'title': '央行调整存贷款利率',
            'content': '中国人民银行宣布调整金融机构存贷款基准利率，各大银行将陆续跟进调整...'
        },
        {
            'title': '祝大家平安夜快乐',
            'content': '今天是平安夜，祝愿大家平安健康，万事如意...'
        },
        {
            'title': '000001号文件发布',
            'content': '关于加强企业管理的通知...'
        }
    ]

    print("=" * 60)
    print("股票新闻相关性判定测试")
    print("=" * 60)

    for i, news in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}:")
        print(f"标题: {news['title']}")

        is_relevant, score, details = checker.check_relevance(
            article=news
        )

        print(f"判定结果: {'✓ 相关' if is_relevant else '✗ 不相关'}")
        print(f"相关性分数: {score}")
        print(f"使用层级: {details['levels_used']}")
        print(f"各层分数: {details['scores']}")
        if details['matched_keywords']:
            print(f"匹配关键词: {', '.join(details['matched_keywords'])}")

    print("\n" + "=" * 60)

    # 批量处理示例
    print("\n批量处理示例:")
    results = checker.batch_check(test_cases)
    relevant_count = sum(1 for r in results if r[0])
    print(f"总计: {len(test_cases)} 条新闻")
    print(f"相关: {relevant_count} 条")
    print(f"不相关: {len(test_cases) - relevant_count} 条")


def test_check_article_relevance_helper():
    """测试 check_article_relevance 辅助函数"""
    print("\n" + "=" * 60)
    print("测试 check_article_relevance 辅助函数")
    print("=" * 60)
    
    # 测试用例1: 使用字符串类型的文章
    print("\n测试用例 1: 字符串类型文章")
    article_str = "平安银行发布2024年第三季度财报，净利润同比增长15%"
    is_relevant, score, details = check_article_relevance(
        stock_code='000001',
        article=article_str
    )
    print(f"文章内容: {article_str}")
    print(f"判定结果: {'✓ 相关' if is_relevant else '✗ 不相关'}")
    print(f"相关性分数: {score}")
    print(f"使用层级: {details['levels_used']}")
    print(f"各层分数: {details['scores']}")
    
    # 测试用例2: 使用字典类型的文章
    print("\n测试用例 2: 字典类型文章")
    article_dict = {
        'title': '平安银行股份有限公司公告',
        'content': '关于召开2024年度股东大会的通知，将讨论分红方案'
    }
    is_relevant, score, details = check_article_relevance(
        stock_code='000001',
        article=article_dict
    )
    print(f"文章标题: {article_dict['title']}")
    print(f"文章内容: {article_dict['content']}")
    print(f"判定结果: {'✓ 相关' if is_relevant else '✗ 不相关'}")
    print(f"相关性分数: {score}")
    print(f"使用层级: {details['levels_used']}")
    print(f"各层分数: {details['scores']}")
    
    # 测试用例3: 不相关的文章
    print("\n测试用例 3: 不相关文章")
    article_irrelevant = {
        'title': '今日天气预报',
        'content': '明天多云转晴，气温15-25度'
    }
    is_relevant, score, details = check_article_relevance(
        stock_code='000001',
        article=article_irrelevant
    )
    print(f"文章标题: {article_irrelevant['title']}")
    print(f"判定结果: {'✓ 相关' if is_relevant else '✗ 不相关'}")
    print(f"相关性分数: {score}")
    
    # 测试用例4: 空文章
    print("\n测试用例 4: 空文章")
    is_relevant, score, details = check_article_relevance(
        stock_code='000001',
        article=None
    )
    print(f"文章内容: None")
    print(f"判定结果: {'✓ 相关' if is_relevant else '✗ 不相关'}")
    print(f"相关性分数: {score}")
    
    # 测试用例5: 自定义阈值
    print("\n测试用例 5: 自定义阈值测试")
    article_medium = "银行业利率调整，各大银行跟进"
    is_relevant, score, details = check_article_relevance(
        stock_code='000001',
        article=article_medium,
        rule_engine_threshold=5  # 降低阈值
    )
    print(f"文章内容: {article_medium}")
    print(f"判定结果: {'✓ 相关' if is_relevant else '✗ 不相关'}")
    print(f"相关性分数: {score}")
    print(f"使用层级: {details['levels_used']}")
    print(f"各层分数: {details['scores']}")


# 使用示例
if __name__ == '__main__':
    # 运行测试
    # test_stock_news_relevance_checker()
    test_check_article_relevance_helper()

