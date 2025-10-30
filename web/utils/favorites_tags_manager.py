"""
收藏和标签管理工具
提供分析结果的收藏和标签功能
"""

import json
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


def get_analysis_results_dir():
    """获取分析结果目录"""
    results_dir = Path(__file__).parent.parent / "data" / "analysis_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


def get_favorites_file():
    """获取收藏文件路径"""
    return get_analysis_results_dir() / "favorites.json"


def get_tags_file():
    """获取标签文件路径"""
    return get_analysis_results_dir() / "tags.json"


def load_favorites() -> List[str]:
    """
    加载收藏列表
    
    Returns:
        收藏的分析ID列表
    """
    favorites_file = get_favorites_file()
    if favorites_file.exists():
        try:
            with open(favorites_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载收藏列表失败: {e}")
            return []
    return []


def save_favorites(favorites: List[str]) -> bool:
    """
    保存收藏列表
    
    Args:
        favorites: 收藏的分析ID列表
        
    Returns:
        是否保存成功
    """
    favorites_file = get_favorites_file()
    try:
        with open(favorites_file, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存收藏列表失败: {e}")
        return False


def load_tags() -> Dict[str, List[str]]:
    """
    加载标签数据
    
    Returns:
        标签数据字典 {analysis_id: [tags]}
    """
    tags_file = get_tags_file()
    if tags_file.exists():
        try:
            with open(tags_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载标签数据失败: {e}")
            return {}
    return {}


def save_tags(tags: Dict[str, List[str]]) -> bool:
    """
    保存标签数据
    
    Args:
        tags: 标签数据字典
        
    Returns:
        是否保存成功
    """
    tags_file = get_tags_file()
    try:
        with open(tags_file, 'w', encoding='utf-8') as f:
            json.dump(tags, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存标签数据失败: {e}")
        return False


def add_tag_to_analysis(analysis_id: str, tag: str) -> bool:
    """
    为分析结果添加标签
    
    Args:
        analysis_id: 分析ID
        tag: 标签名称
        
    Returns:
        是否添加成功
    """
    tags = load_tags()
    if analysis_id not in tags:
        tags[analysis_id] = []
    if tag not in tags[analysis_id]:
        tags[analysis_id].append(tag)
        return save_tags(tags)
    return True


def remove_tag_from_analysis(analysis_id: str, tag: str) -> bool:
    """
    从分析结果移除标签
    
    Args:
        analysis_id: 分析ID
        tag: 标签名称
        
    Returns:
        是否移除成功
    """
    tags = load_tags()
    if analysis_id in tags and tag in tags[analysis_id]:
        tags[analysis_id].remove(tag)
        if not tags[analysis_id]:  # 如果没有标签了，删除该条目
            del tags[analysis_id]
        return save_tags(tags)
    return True


def get_analysis_tags(analysis_id: str) -> List[str]:
    """
    获取分析结果的标签
    
    Args:
        analysis_id: 分析ID
        
    Returns:
        标签列表
    """
    tags = load_tags()
    return tags.get(analysis_id, [])


def is_favorite(analysis_id: str) -> bool:
    """
    检查分析是否被收藏
    
    Args:
        analysis_id: 分析ID
        
    Returns:
        是否被收藏
    """
    favorites = load_favorites()
    return analysis_id in favorites


def toggle_favorite(analysis_id: str) -> bool:
    """
    切换收藏状态
    
    Args:
        analysis_id: 分析ID
        
    Returns:
        切换后的收藏状态 (True=已收藏, False=未收藏)
    """
    favorites = load_favorites()
    if analysis_id in favorites:
        favorites.remove(analysis_id)
        save_favorites(favorites)
        return False
    else:
        favorites.append(analysis_id)
        save_favorites(favorites)
        return True


def add_favorite(analysis_id: str) -> bool:
    """
    添加到收藏
    
    Args:
        analysis_id: 分析ID
        
    Returns:
        是否添加成功
    """
    favorites = load_favorites()
    if analysis_id not in favorites:
        favorites.append(analysis_id)
        return save_favorites(favorites)
    return True


def remove_favorite(analysis_id: str) -> bool:
    """
    从收藏中移除
    
    Args:
        analysis_id: 分析ID
        
    Returns:
        是否移除成功
    """
    favorites = load_favorites()
    if analysis_id in favorites:
        favorites.remove(analysis_id)
        return save_favorites(favorites)
    return True


def get_all_tags() -> List[str]:
    """
    获取所有使用过的标签
    
    Returns:
        标签列表（去重并排序）
    """
    tags_data = load_tags()
    all_tags = set()
    for tag_list in tags_data.values():
        all_tags.update(tag_list)
    return sorted(all_tags)


def get_tag_usage_count(tag: str) -> int:
    """
    获取标签的使用次数
    
    Args:
        tag: 标签名称
        
    Returns:
        使用次数
    """
    tags_data = load_tags()
    count = 0
    for tag_list in tags_data.values():
        if tag in tag_list:
            count += 1
    return count


def get_tag_statistics() -> Dict[str, int]:
    """
    获取标签统计信息
    
    Returns:
        标签使用次数字典 {tag: count}
    """
    tags_data = load_tags()
    tag_counts = {}
    for tag_list in tags_data.values():
        for tag in tag_list:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    return tag_counts


def batch_add_tags(analysis_ids: List[str], tag: str) -> int:
    """
    批量添加标签
    
    Args:
        analysis_ids: 分析ID列表
        tag: 标签名称
        
    Returns:
        成功添加的数量
    """
    tags = load_tags()
    added_count = 0
    
    for analysis_id in analysis_ids:
        if analysis_id not in tags:
            tags[analysis_id] = []
        if tag not in tags[analysis_id]:
            tags[analysis_id].append(tag)
            added_count += 1
    
    if save_tags(tags):
        return added_count
    return 0


def batch_remove_tags(analysis_ids: List[str], tag: str) -> int:
    """
    批量移除标签
    
    Args:
        analysis_ids: 分析ID列表
        tag: 标签名称
        
    Returns:
        成功移除的数量
    """
    tags = load_tags()
    removed_count = 0
    
    for analysis_id in analysis_ids:
        if analysis_id in tags and tag in tags[analysis_id]:
            tags[analysis_id].remove(tag)
            if not tags[analysis_id]:  # 如果没有标签了，删除该条目
                del tags[analysis_id]
            removed_count += 1
    
    if save_tags(tags):
        return removed_count
    return 0

