#!/usr/bin/env python3
"""
Redis 缓存管理器
提供统一的 Redis 缓存操作接口
"""

import json
import pickle
import re
from typing import Optional, Dict, Any, Union, List
from datetime import timedelta

from tradingagents.utils.logging_manager import get_logger
from .connection import get_redis_client, REDIS_AVAILABLE

logger = get_logger('storage')


class RedisCacheManager:
    """Redis 缓存管理器"""
    
    def __init__(self):
        """初始化缓存管理器"""
        self._client = None
        self._connect()
    
    def _connect(self):
        """连接到 Redis"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis 不可用，缓存功能将受限")
            return
        
        self._client = get_redis_client()
        if self._client:
            logger.info("✅ Redis缓存管理器已初始化")
        else:
            logger.warning("⚠️ Redis连接失败，缓存功能不可用")
    
    def is_available(self) -> bool:
        """检查 Redis 是否可用"""
        if not self._client:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            return False
    
    def get_client(self):
        """获取 Redis 客户端"""
        return self._client if self.is_available() else None
    
    def cache_set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值（支持 dict, list, str, int, float, bool）
            ttl: 过期时间（秒），None 表示不过期
        
        Returns:
            bool: 是否设置成功
        """
        if not self.is_available():
            return False
        
        try:
            # 序列化值
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, (str, int, float, bool)):
                serialized_value = str(value)
            else:
                # 使用 pickle 序列化复杂对象
                serialized_value = pickle.dumps(value)
                # 使用特殊前缀标识 pickle 数据
                key = f"pickle:{key}"
            
            # 设置缓存
            if ttl:
                self._client.setex(key, ttl, serialized_value)
            else:
                self._client.set(key, serialized_value)
            
            return True
        except Exception as e:
            logger.error(f"Redis缓存设置失败: {e}")
            return False
    
    def cache_get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存
        
        Args:
            key: 缓存键
            default: 默认值
        
        Returns:
            缓存值或默认值
        """
        if not self.is_available():
            return default
        
        try:
            # 先尝试普通键
            value = self._client.get(key)
            if value is not None:
                # 尝试 JSON 反序列化
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    # 如果不是 JSON，返回原始字符串
                    return value
            
            # 尝试 pickle 键
            pickle_key = f"pickle:{key}"
            value = self._client.get(pickle_key)
            if value is not None:
                return pickle.loads(value)
            
            return default
        except Exception as e:
            logger.error(f"Redis缓存获取失败: {e}")
            return default
    
    def cache_delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
        
        Returns:
            bool: 是否删除成功
        """
        if not self.is_available():
            return False
        
        try:
            # 删除普通键和 pickle 键
            deleted = self._client.delete(key, f"pickle:{key}")
            return deleted > 0
        except Exception as e:
            logger.error(f"Redis缓存删除失败: {e}")
            return False
    
    def cache_exists(self, key: str) -> bool:
        """
        检查缓存是否存在
        
        Args:
            key: 缓存键
        
        Returns:
            bool: 是否存在
        """
        if not self.is_available():
            return False
        
        try:
            return self._client.exists(key) > 0 or self._client.exists(f"pickle:{key}") > 0
        except Exception as e:
            logger.error(f"Redis缓存检查失败: {e}")
            return False
    
    def cache_ttl(self, key: str) -> int:
        """
        获取缓存的剩余过期时间
        
        Args:
            key: 缓存键
        
        Returns:
            int: 剩余秒数，-1 表示不过期，-2 表示不存在
        """
        if not self.is_available():
            return -2
        
        try:
            ttl = self._client.ttl(key)
            if ttl == -2:
                # 检查 pickle 键
                ttl = self._client.ttl(f"pickle:{key}")
            return ttl
        except Exception as e:
            logger.error(f"Redis缓存TTL获取失败: {e}")
            return -2
    
    def cache_clear_pattern(self, pattern: str) -> int:
        """
        清理匹配模式的缓存
        
        Args:
            pattern: 匹配模式（支持 * 通配符）
        
        Returns:
            int: 清理的键数量
        """
        if not self.is_available():
            return 0
        
        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis缓存清理失败: {e}")
            return 0
    
    def cache_clear_all(self) -> bool:
        """
        清空所有缓存
        
        Returns:
            bool: 是否清空成功
        """
        if not self.is_available():
            return False
        
        try:
            self._client.flushdb()
            logger.info("Redis缓存已清空")
            return True
        except Exception as e:
            logger.error(f"Redis缓存清空失败: {e}")
            return False
    
    def cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        if not self.is_available():
            return {
                "available": False,
                "keys": 0,
                "memory_usage": "N/A"
            }
        
        try:
            info = self._client.info()
            return {
                "available": True,
                "keys": self._client.dbsize(),
                "memory_usage": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0)
            }
        except Exception as e:
            logger.error(f"Redis统计获取失败: {e}")
            return {
                "available": False,
                "keys": 0,
                "memory_usage": "N/A"
            }
    
    def _parse_task_id_from_key(self, key: str) -> Optional[str]:
        """
        从Redis键中解析task_id
        
        Args:
            key: Redis键，格式为 task:{task_id}:{suffix}
            
        Returns:
            Optional[str]: task_id，如果解析失败返回None
        """
        # 格式: task:{task_id}:{suffix}
        match = re.match(r'^task:([^:]+):', key)
        if match:
            return match.group(1)
        return None
    
    def get_all_task_ids(self) -> List[str]:
        """
        获取所有task_id列表
        
        Returns:
            List[str]: task_id列表，按倒序排列
        """
        if not self.is_available():
            return []
        
        try:
            # 获取所有task相关的键（包括props、current_step、history）
            keys = self._client.keys("task:*:*")
            task_ids = []
            for key in keys:
                task_id = self._parse_task_id_from_key(key)
                if task_id:
                    task_ids.append(task_id)
            
            # 去重并排序
            unique_task_ids = list(set(task_ids))
            # 按task_id倒序排列
            return sorted(unique_task_ids, reverse=True)
        except Exception as e:
            logger.error(f"获取task_id列表失败: {e}")
            return []
    
    def get_task_props(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取task的props数据
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[Dict[str, Any]]: task的props数据，如果不存在返回None
        """
        if not self.is_available():
            return None
        
        try:
            key = f"task:{task_id}:props"
            data = self._client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"获取task props失败: {e}")
        
        return None
    
    def get_task_cache_list(
        self,
        sub_key: str = "props",
        fields: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 10,
        task_id: Optional[str] = None,
        analysis_date: Optional[str] = None,
        status: Optional[str] = None,
        stock_symbol: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取缓存记录列表（分页，支持筛选）
        
        Args:
            sub_key: 要查询的子键（如 'props', 'current_step', 'history'），默认为 'props'
            fields: 要提取的字段列表，如果为None则返回所有字段
            page: 页码，从1开始
            page_size: 每页数量
            task_id: 筛选条件：任务ID（支持部分匹配）
            analysis_date: 筛选条件：分析日期（精确匹配）
            status: 筛选条件：运行状态（精确匹配）
            stock_symbol: 筛选条件：股票代码（支持部分匹配）
            company_name: 筛选条件：公司名称（支持部分匹配，需要从stock_dict_manager获取）
            
        Returns:
            Dict[str, Any]: 包含以下键的字典
                - items: List[Dict[str, Any]]: 缓存记录列表
                - total: int: 总记录数（筛选后）
                - page: int: 当前页码
                - page_size: int: 每页数量
                - pages: int: 总页数（筛选后）
        """
        if not self.is_available():
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "pages": 0
            }
        
        try:
            # 获取所有task_id
            all_task_ids = self.get_all_task_ids()
            
            # 获取每个task的数据并进行筛选
            filtered_items = []
            for task_id_item in all_task_ids:
                # 如果指定了task_id筛选，先进行快速筛选
                if task_id and task_id not in task_id_item:
                    continue
                
                key = f"task:{task_id_item}:{sub_key}"
                item = {"task_id": task_id_item}
                try:
                    data = self._client.get(key)
                    if data:
                        task_data = json.loads(data)
                        if isinstance(task_data, dict):
                            # 如果指定了字段列表，只提取指定字段
                            if fields:
                                # 获取params字段（如果存在）
                                params = task_data.get('params', {})
                                for field in fields:
                                    # analysis_date和stock_symbol在params字段下
                                    if field in ['analysis_date', 'stock_symbol']:
                                        item[field] = params.get(field) if isinstance(params, dict) else None
                                    else:
                                        item[field] = task_data.get(field)
                            else:
                                # 返回所有字段
                                item.update(task_data)
                    
                    # 应用筛选条件
                    if self._match_filters(item, task_id, analysis_date, status, stock_symbol, company_name):
                        filtered_items.append(item)
                except Exception as e:
                    logger.warning(f"获取task {task_id_item} 的 {sub_key} 数据失败: {e}")
                    # 即使获取失败，如果只有task_id筛选，也可以添加
                    if task_id and task_id in task_id_item:
                        if self._match_filters(item, task_id, analysis_date, status, stock_symbol, company_name):
                            filtered_items.append(item)
            
            # 计算筛选后的总数和分页
            total = len(filtered_items)
            pages = (total + page_size - 1) // page_size if total > 0 else 0
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            # 获取当前页的数据
            items = filtered_items[start_idx:end_idx]
            
            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": pages
            }
        except Exception as e:
            logger.error(f"获取缓存记录列表失败: {e}")
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "pages": 0
            }
    
    def _match_filters(
        self,
        item: Dict[str, Any],
        task_id: Optional[str] = None,
        analysis_date: Optional[str] = None,
        status: Optional[str] = None,
        stock_symbol: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> bool:
        """
        检查item是否匹配所有筛选条件
        
        Args:
            item: 缓存项数据
            task_id: 任务ID筛选（部分匹配）
            analysis_date: 分析日期筛选（精确匹配）
            status: 状态筛选（精确匹配）
            stock_symbol: 股票代码筛选（部分匹配）
            company_name: 公司名称筛选（部分匹配）
            
        Returns:
            bool: 是否匹配所有筛选条件
        """
        # task_id筛选（部分匹配，不区分大小写）
        if task_id:
            item_task_id = item.get("task_id", "")
            if task_id.lower() not in item_task_id.lower():
                return False
        
        # analysis_date筛选（精确匹配）
        if analysis_date:
            item_analysis_date = item.get("analysis_date", "")
            if item_analysis_date != analysis_date:
                return False
        
        # status筛选（精确匹配）
        if status:
            item_status = item.get("status", "")
            if item_status != status:
                return False
        
        # stock_symbol筛选（部分匹配，不区分大小写）
        if stock_symbol:
            item_stock_symbol = item.get("stock_symbol") or item.get("company_of_interest", "")
            if not item_stock_symbol or stock_symbol.lower() not in item_stock_symbol.lower():
                return False
        
        # company_name筛选（部分匹配，不区分大小写）
        # 注意：company_name不在缓存数据中，需要从stock_dict_manager获取
        if company_name:
            item_stock_symbol = item.get("stock_symbol") or item.get("company_of_interest", "")
            if not item_stock_symbol:
                return False
            # 这里需要从外部获取公司名称，暂时跳过，在路由层处理
            # 因为这里没有stock_dict_manager的引用
        
        return True
    
    def get_task_cache_detail(
        self,
        task_id: str,
        sub_keys: Optional[List[str]] = None,
        truncate_length: Optional[int] = 50
    ) -> Dict[str, Any]:
        """
        获取缓存记录的详细信息
        
        Args:
            task_id: 任务ID（analysis_id）
            sub_keys: 要获取的子键列表（如 ['current_step', 'history', 'props']），
                      如果为None则获取所有子键
            truncate_length: 字段截断长度，None表示不截断，默认50
        
        Returns:
            Dict[str, Any]: 包含指定子键的数据字典，如果所有子键都不存在则返回空字典
        """
        if not self.is_available():
            return {}
        
        # 默认获取所有子键
        if sub_keys is None:
            sub_keys = ["current_step", "history", "props"]
        
        result = {}
        
        for sub_key in sub_keys:
            try:
                key = f"task:{task_id}:{sub_key}"
                data = self._client.get(key)
                if data:
                    sub_data = json.loads(data)
                    # 如果需要截断
                    if truncate_length is not None:
                        result[sub_key] = self._truncate_dict_values(sub_data, truncate_length)
                    else:
                        result[sub_key] = sub_data
                else:
                    result[sub_key] = None
            except Exception as e:
                logger.warning(f"获取task {task_id} 的 {sub_key} 数据失败: {e}")
                result[sub_key] = None
        
        return result
    
    def _truncate_field(self, value: Any, max_length: int) -> str:
        """
        截断字段值，超过长度用省略号表示
        
        Args:
            value: 要截断的值
            max_length: 最大长度
            
        Returns:
            str: 截断后的字符串
        """
        if value is None:
            return ""
        
        str_value = str(value)
        if len(str_value) <= max_length:
            return str_value
        
        return str_value[:max_length] + "..."
    
    def _truncate_dict_values(self, data: Any, max_length: int) -> Any:
        """
        递归截断字典中的字符串值
        
        Args:
            data: 要处理的数据（可以是dict、list、str等）
            max_length: 最大长度
            
        Returns:
            Any: 处理后的数据
        """
        if isinstance(data, dict):
            return {k: self._truncate_dict_values(v, max_length) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._truncate_dict_values(item, max_length) for item in data]
        elif isinstance(data, str):
            return self._truncate_field(data, max_length)
        elif isinstance(data, (int, float, bool)):
            return data
        elif data is None:
            return None
        else:
            # 对于其他类型，转换为字符串后截断
            return self._truncate_field(str(data), max_length)


# 全局缓存管理器实例
_redis_cache_manager = None

def redis_cache_manager() -> RedisCacheManager:
    """获取全局 Redis 缓存管理器实例"""
    global _redis_cache_manager
    if _redis_cache_manager is None:
        _redis_cache_manager = RedisCacheManager()
    return _redis_cache_manager

