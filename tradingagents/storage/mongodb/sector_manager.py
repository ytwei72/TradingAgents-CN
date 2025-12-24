#!/usr/bin/env python3
"""
板块管理器
用于管理概念板块（dict_concept_themes）和行业板块（dict_industry_sectors）
提供板块及股票关联关系的各种查询以及统计功能

集合名称: 
- dict_concept_themes (概念板块)
- dict_industry_sectors (行业板块)
数据库: tradingagents (MongoDB)

【使用方式】
from tradingagents.storage.mongodb.sector_manager import sector_manager
stocks = sector_manager.get_stocks_by_concept("新能源")
# stocks 直接返回数据库中 stocks 字段的值: [{"code": "300750", "name": "宁德时代"}, ...]
"""

import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('storage')

try:
    from pymongo import ASCENDING, DESCENDING
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    logger.warning("pymongo未安装，MongoDB功能不可用")

# 数据源可用性检查
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.warning("akshare未安装，板块数据更新功能不可用")


class SectorManager:
    """板块管理器"""
    
    # 集合名称
    COLLECTION_CONCEPT_THEMES = "dict_concept_themes"
    COLLECTION_INDUSTRY_SECTORS = "dict_industry_sectors"
    
    def __init__(self):
        self.concept_collection = None
        self.industry_collection = None
        self.connected = False
        
        if MONGODB_AVAILABLE:
            self._connect()
    
    def _connect(self):
        """连接到MongoDB"""
        try:
            from tradingagents.storage.manager import get_mongo_collection
            
            self.concept_collection = get_mongo_collection(self.COLLECTION_CONCEPT_THEMES)
            self.industry_collection = get_mongo_collection(self.COLLECTION_INDUSTRY_SECTORS)
            
            if self.concept_collection is None or self.industry_collection is None:
                logger.warning("⚠️ [板块管理] 统一连接管理不可用，无法连接MongoDB")
                self.connected = False
                return
            
            self.connected = True
            logger.info(f"✅ [板块管理] MongoDB连接成功")
            
            # 创建索引
            self._create_indexes()
            
        except Exception as e:
            logger.warning(f"⚠️ [板块管理] MongoDB连接失败: {e}")
            self.connected = False
    
    def _create_indexes(self):
        """创建索引以提高查询性能"""
        try:
            if not self.connected:
                return
            
            # 概念板块索引
            if self.concept_collection is not None:
                try:
                    self.concept_collection.create_index("name", unique=True)
                    self.concept_collection.create_index("stocks")
                    self.concept_collection.create_index([("updated_at", DESCENDING)])
                    logger.debug("✅ [板块管理] 概念板块索引创建成功")
                except Exception as e:
                    error_str = str(e).lower()
                    if "already exists" in error_str or "indexoptionsconflict" in error_str:
                        logger.debug("✅ [板块管理] 概念板块索引已存在")
                    else:
                        logger.warning(f"⚠️ [板块管理] 创建概念板块索引时出错: {e}")
            
            # 行业板块索引
            if self.industry_collection is not None:
                try:
                    self.industry_collection.create_index("name", unique=True)
                    self.industry_collection.create_index("stocks")
                    self.industry_collection.create_index([("updated_at", DESCENDING)])
                    logger.debug("✅ [板块管理] 行业板块索引创建成功")
                except Exception as e:
                    error_str = str(e).lower()
                    if "already exists" in error_str or "indexoptionsconflict" in error_str:
                        logger.debug("✅ [板块管理] 行业板块索引已存在")
                    else:
                        logger.warning(f"⚠️ [板块管理] 创建行业板块索引时出错: {e}")
            
        except Exception as e:
            logger.warning(f"⚠️ [板块管理] 索引创建失败: {e}")
    
    def is_connected(self) -> bool:
        """检查是否已连接到MongoDB"""
        return self.connected
    
    # ==================== 概念板块查询方法 ====================
    
    def get_concept_list(self, limit: Optional[int] = None, skip: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取所有概念板块列表
        
        Args:
            limit: 返回记录数限制
            skip: 跳过记录数（用于分页）
        
        Returns:
            概念板块列表，每个元素包含 name, stocks, updated_at 等字段
        """
        if not self.connected:
            logger.warning("⚠️ [板块管理] 未连接，无法查询")
            return []
        
        try:
            cursor = self.concept_collection.find({}, {"_id": 0})
            
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            
            results = list(cursor)
            logger.debug(f"✅ [板块管理] 查询概念板块列表成功，返回 {len(results)} 条记录")
            return results
                
        except Exception as e:
            logger.error(f"❌ [板块管理] 查询概念板块列表失败: {e}")
            return []
    
    def get_concept_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        根据名称获取概念板块信息
        
        Args:
            name: 概念板块名称
        
        Returns:
            概念板块信息，如果未找到返回 None
        """
        if not self.connected:
            logger.warning("⚠️ [板块管理] 未连接，无法查询")
            return None
        
        try:
            result = self.concept_collection.find_one({"name": name}, {"_id": 0})
            if result:
                logger.debug(f"✅ [板块管理] 查询概念板块 '{name}' 成功")
            return result
                
        except Exception as e:
            logger.error(f"❌ [板块管理] 查询概念板块 '{name}' 失败: {e}")
            return None
    
    def get_stocks_by_concept(self, concept_name: str) -> List[Dict[str, Any]]:
        """
        根据概念板块名称获取关联的股票列表
        
        Args:
            concept_name: 概念板块名称
        
        Returns:
            股票列表，直接返回 stocks 字段的值
        """
        concept = self.get_concept_by_name(concept_name)
        if concept and 'stocks' in concept:
            stocks = concept['stocks']
            if isinstance(stocks, list):
                return stocks
        return []
    
    def search_concepts(self, keyword: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        搜索概念板块（按名称模糊匹配）
        
        Args:
            keyword: 搜索关键词
            limit: 返回记录数限制
        
        Returns:
            匹配的概念板块列表
        """
        if not self.connected:
            logger.warning("⚠️ [板块管理] 未连接，无法查询")
            return []
        
        try:
            query = {"name": {"$regex": keyword, "$options": "i"}}
            cursor = self.concept_collection.find(query, {"_id": 0})
            
            if limit:
                cursor = cursor.limit(limit)
            
            results = list(cursor)
            logger.debug(f"✅ [板块管理] 搜索概念板块 '{keyword}' 成功，返回 {len(results)} 条记录")
            return results
                
        except Exception as e:
            logger.error(f"❌ [板块管理] 搜索概念板块 '{keyword}' 失败: {e}")
            return []
    
    # ==================== 行业板块查询方法 ====================
    
    def get_industry_list(self, limit: Optional[int] = None, skip: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取所有行业板块列表
        
        Args:
            limit: 返回记录数限制
            skip: 跳过记录数（用于分页）
        
        Returns:
            行业板块列表，每个元素包含 name, stocks, updated_at 等字段
        """
        if not self.connected:
            logger.warning("⚠️ [板块管理] 未连接，无法查询")
            return []
        
        try:
            cursor = self.industry_collection.find({}, {"_id": 0})
            
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            
            results = list(cursor)
            logger.debug(f"✅ [板块管理] 查询行业板块列表成功，返回 {len(results)} 条记录")
            return results
                
        except Exception as e:
            logger.error(f"❌ [板块管理] 查询行业板块列表失败: {e}")
            return []
    
    def get_industry_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        根据名称获取行业板块信息
        
        Args:
            name: 行业板块名称
        
        Returns:
            行业板块信息，如果未找到返回 None
        """
        if not self.connected:
            logger.warning("⚠️ [板块管理] 未连接，无法查询")
            return None
        
        try:
            result = self.industry_collection.find_one({"name": name}, {"_id": 0})
            if result:
                logger.debug(f"✅ [板块管理] 查询行业板块 '{name}' 成功")
            return result
                
        except Exception as e:
            logger.error(f"❌ [板块管理] 查询行业板块 '{name}' 失败: {e}")
            return None
    
    def get_stocks_by_industry(self, industry_name: str) -> List[Dict[str, Any]]:
        """
        根据行业板块名称获取关联的股票列表
        
        Args:
            industry_name: 行业板块名称
        
        Returns:
            股票列表，直接返回 stocks 字段的值
        """
        industry = self.get_industry_by_name(industry_name)
        if industry and 'stocks' in industry:
            stocks = industry['stocks']
            if isinstance(stocks, list):
                return stocks
        return []
    
    def search_industries(self, keyword: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        搜索行业板块（按名称模糊匹配）
        
        Args:
            keyword: 搜索关键词
            limit: 返回记录数限制
        
        Returns:
            匹配的行业板块列表
        """
        if not self.connected:
            logger.warning("⚠️ [板块管理] 未连接，无法查询")
            return []
        
        try:
            query = {"name": {"$regex": keyword, "$options": "i"}}
            cursor = self.industry_collection.find(query, {"_id": 0})
            
            if limit:
                cursor = cursor.limit(limit)
            
            results = list(cursor)
            logger.debug(f"✅ [板块管理] 搜索行业板块 '{keyword}' 成功，返回 {len(results)} 条记录")
            return results
                
        except Exception as e:
            logger.error(f"❌ [板块管理] 搜索行业板块 '{keyword}' 失败: {e}")
            return []
    
    # ==================== 股票关联关系查询方法 ====================
    
    def get_concepts_by_stock(self, stock_code: str) -> List[str]:
        """
        根据股票代码获取所属的概念板块列表
        
        Args:
            stock_code: 股票代码（6位数字，如：000001）
        
        Returns:
            概念板块名称列表
        """
        if not self.connected:
            logger.warning("⚠️ [板块管理] 未连接，无法查询")
            return []
        
        try:
            # 使用 $or 查询，支持字符串列表和字典列表两种格式
            query = {
                "$or": [
                    {"stocks": stock_code},  # 字符串列表格式
                    {"stocks.code": stock_code},  # 字典列表格式
                    {"stocks.股票代码": stock_code},  # 字典列表格式（中文字段名）
                    {"stocks.symbol": stock_code}  # 字典列表格式（symbol字段）
                ]
            }
            
            results = self.concept_collection.find(
                query,
                {"name": 1, "_id": 0}
            )
            concepts = [doc['name'] for doc in results]
            logger.debug(f"✅ [板块管理] 查询股票 {stock_code} 的概念板块成功，返回 {len(concepts)} 个")
            return concepts
                
        except Exception as e:
            logger.error(f"❌ [板块管理] 查询股票 {stock_code} 的概念板块失败: {e}")
            return []
    
    def get_industries_by_stock(self, stock_code: str) -> List[str]:
        """
        根据股票代码获取所属的行业板块列表
        
        Args:
            stock_code: 股票代码（6位数字，如：000001）
        
        Returns:
            行业板块名称列表
        """
        if not self.connected:
            logger.warning("⚠️ [板块管理] 未连接，无法查询")
            return []
        
        try:
            # 使用 $or 查询，支持字符串列表和字典列表两种格式
            query = {
                "$or": [
                    {"stocks": stock_code},  # 字符串列表格式
                    {"stocks.code": stock_code},  # 字典列表格式
                    {"stocks.股票代码": stock_code},  # 字典列表格式（中文字段名）
                    {"stocks.symbol": stock_code}  # 字典列表格式（symbol字段）
                ]
            }
            
            results = self.industry_collection.find(
                query,
                {"name": 1, "_id": 0}
            )
            industries = [doc['name'] for doc in results]
            logger.debug(f"✅ [板块管理] 查询股票 {stock_code} 的行业板块成功，返回 {len(industries)} 个")
            return industries
                
        except Exception as e:
            logger.error(f"❌ [板块管理] 查询股票 {stock_code} 的行业板块失败: {e}")
            return []
    
    def get_all_sectors_by_stock(self, stock_code: str) -> Dict[str, List[str]]:
        """
        根据股票代码获取所属的所有板块（概念+行业）
        
        Args:
            stock_code: 股票代码（6位数字，如：000001）
        
        Returns:
            包含 concepts 和 industries 的字典
        """
        return {
            "concepts": self.get_concepts_by_stock(stock_code),
            "industries": self.get_industries_by_stock(stock_code)
        }
    
    # ==================== 统计方法 ====================
    
    def count_concepts(self) -> int:
        """
        统计概念板块数量
        
        Returns:
            概念板块数量
        """
        if not self.connected:
            logger.warning("⚠️ [板块管理] 未连接，无法统计")
            return 0
        
        try:
            count = self.concept_collection.count_documents({})
            logger.debug(f"✅ [板块管理] 统计概念板块数量成功: {count}")
            return count
                
        except Exception as e:
            logger.error(f"❌ [板块管理] 统计概念板块数量失败: {e}")
            return 0
    
    def count_industries(self) -> int:
        """
        统计行业板块数量
        
        Returns:
            行业板块数量
        """
        if not self.connected:
            logger.warning("⚠️ [板块管理] 未连接，无法统计")
            return 0
        
        try:
            count = self.industry_collection.count_documents({})
            logger.debug(f"✅ [板块管理] 统计行业板块数量成功: {count}")
            return count
                
        except Exception as e:
            logger.error(f"❌ [板块管理] 统计行业板块数量失败: {e}")
            return 0
    
    def count_stocks_in_concept(self, concept_name: str) -> int:
        """
        统计概念板块中的股票数量
        
        Args:
            concept_name: 概念板块名称
        
        Returns:
            股票数量
        """
        stocks = self.get_stocks_by_concept(concept_name)
        return len(stocks)
    
    def count_stocks_in_industry(self, industry_name: str) -> int:
        """
        统计行业板块中的股票数量
        
        Args:
            industry_name: 行业板块名称
        
        Returns:
            股票数量
        """
        stocks = self.get_stocks_by_industry(industry_name)
        return len(stocks)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取板块统计信息
        
        Returns:
            统计信息字典，包含：
            - concept_count: 概念板块数量
            - industry_count: 行业板块数量
            - total_concept_stocks: 概念板块关联的股票总数（去重）
            - total_industry_stocks: 行业板块关联的股票总数（去重）
        """
        if not self.connected:
            logger.warning("⚠️ [板块管理] 未连接，无法统计")
            return {
                "concept_count": 0,
                "industry_count": 0,
                "total_concept_stocks": 0,
                "total_industry_stocks": 0
            }
        
        try:
            concept_count = self.count_concepts()
            industry_count = self.count_industries()
            
            # 统计概念板块关联的股票总数（去重）
            concept_stocks_set = set()
            for concept in self.concept_collection.find({}, {"stocks": 1}):
                if 'stocks' in concept and isinstance(concept['stocks'], list):
                    for item in concept['stocks']:
                        if isinstance(item, str):
                            concept_stocks_set.add(item)
                        elif isinstance(item, dict):
                            code = item.get('code') or item.get('股票代码') or item.get('symbol')
                            if code:
                                concept_stocks_set.add(str(code))
            
            # 统计行业板块关联的股票总数（去重）
            industry_stocks_set = set()
            for industry in self.industry_collection.find({}, {"stocks": 1}):
                if 'stocks' in industry and isinstance(industry['stocks'], list):
                    for item in industry['stocks']:
                        if isinstance(item, str):
                            industry_stocks_set.add(item)
                        elif isinstance(item, dict):
                            code = item.get('code') or item.get('股票代码') or item.get('symbol')
                            if code:
                                industry_stocks_set.add(str(code))
            
            stats = {
                "concept_count": concept_count,
                "industry_count": industry_count,
                "total_concept_stocks": len(concept_stocks_set),
                "total_industry_stocks": len(industry_stocks_set)
            }
            
            logger.debug(f"✅ [板块管理] 统计信息获取成功: {stats}")
            return stats
                
        except Exception as e:
            logger.error(f"❌ [板块管理] 获取统计信息失败: {e}")
            return {
                "concept_count": 0,
                "industry_count": 0,
                "total_concept_stocks": 0,
                "total_industry_stocks": 0
            }
    
    # ==================== 数据更新方法 ====================
    
    def _delay_for_period(self, min_delay: float = 2.0, max_delay: float = 5.0):
        """
        延时等待函数，避免请求过于频繁
        
        Args:
            min_delay: 最小延时（秒）
            max_delay: 最大延时（秒）
        """
        import random
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
    def _update_single_concept_sector(self, concept_name: str) -> tuple[bool, Optional[str], Optional[int]]:
        """
        更新单个概念板块的内部函数
        
        Args:
            concept_name: 概念板块名称
        
        Returns:
            (是否成功, 错误信息, 股票数量)
        """
        try:
            # 获取概念板块中的股票列表
            stocks_df = ak.stock_board_concept_cons_em(symbol=concept_name)
            
            if stocks_df is not None and not stocks_df.empty:
                # 提取股票代码列表
                stock_codes = []
                if '代码' in stocks_df.columns:
                    stock_codes = stocks_df['代码'].tolist()
                elif '股票代码' in stocks_df.columns:
                    stock_codes = stocks_df['股票代码'].tolist()
                else:
                    # 尝试第一列
                    stock_codes = stocks_df.iloc[:, 0].tolist()
                
                # 清理股票代码格式（确保是6位数字）
                stock_codes = [str(code).zfill(6) for code in stock_codes if code]
                
                # 保存到数据库
                self._save_sector(
                    self.concept_collection,
                    concept_name,
                    stock_codes,
                    "概念"
                )
                
                logger.info(f"✅ [板块管理] 概念板块 '{concept_name}' 更新成功，包含 {len(stock_codes)} 只股票")
                return True, None, len(stock_codes)
            else:
                logger.warning(f"⚠️ [板块管理] 概念板块 '{concept_name}' 无股票数据")
                return False, "无股票数据", None
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ [板块管理] 更新概念板块 '{concept_name}' 失败: {e}")
            return False, error_msg, None
    
    def _update_single_industry_sector(self, industry_name: str) -> tuple[bool, Optional[str], Optional[int]]:
        """
        更新单个行业板块的内部函数
        
        Args:
            industry_name: 行业板块名称
        
        Returns:
            (是否成功, 错误信息, 股票数量)
        """
        try:
            # 获取行业板块中的股票列表
            stocks_df = ak.stock_board_industry_cons_em(symbol=industry_name)
            
            if stocks_df is not None and not stocks_df.empty:
                # 提取股票代码列表
                stock_codes = []
                if '代码' in stocks_df.columns:
                    stock_codes = stocks_df['代码'].tolist()
                elif '股票代码' in stocks_df.columns:
                    stock_codes = stocks_df['股票代码'].tolist()
                else:
                    # 尝试第一列
                    stock_codes = stocks_df.iloc[:, 0].tolist()
                
                # 清理股票代码格式（确保是6位数字）
                stock_codes = [str(code).zfill(6) for code in stock_codes if code]
                
                # 保存到数据库
                self._save_sector(
                    self.industry_collection,
                    industry_name,
                    stock_codes,
                    "行业"
                )
                
                logger.info(f"✅ [板块管理] 行业板块 '{industry_name}' 更新成功，包含 {len(stock_codes)} 只股票")
                return True, None, len(stock_codes)
            else:
                logger.warning(f"⚠️ [板块管理] 行业板块 '{industry_name}' 无股票数据")
                return False, "无股票数据", None
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ [板块管理] 更新行业板块 '{industry_name}' 失败: {e}")
            return False, error_msg, None
    
    def update_concept_sectors(self) -> Dict[str, Any]:
        """
        更新所有概念板块数据（从 akshare 获取）
        
        Returns:
            包含成功和失败板块信息的字典:
            {
                "success": ["板块1", "板块2", ...],
                "failed": {"板块3": "错误信息", "板块4": "错误信息", ...},
                "total": 总数量,
                "success_count": 成功数量,
                "failed_count": 失败数量
            }
        """
        if not self.connected:
            logger.error("❌ [板块管理] MongoDB未连接")
            return {
                "success": [],
                "failed": {"整体更新": "MongoDB未连接"},
                "total": 0,
                "success_count": 0,
                "failed_count": 1
            }
        
        if not AKSHARE_AVAILABLE:
            logger.error("❌ [板块管理] akshare库未安装")
            return {
                "success": [],
                "failed": {"整体更新": "akshare库未安装"},
                "total": 0,
                "success_count": 0,
                "failed_count": 1
            }
        
        try:
            logger.info("🔄 [板块管理] 开始更新概念板块信息...")
            
            # 获取概念板块列表
            concept_list = ak.stock_board_concept_name_em()
            
            if concept_list is None or concept_list.empty:
                logger.warning("⚠️ [板块管理] 未获取到概念板块列表")
                return {
                    "success": [],
                    "failed": {},
                    "total": 0,
                    "success_count": 0,
                    "failed_count": 0
                }
            
            concept_names = concept_list['板块名称'].tolist() if '板块名称' in concept_list.columns else []
            
            if not concept_names:
                logger.warning("⚠️ [板块管理] 概念板块列表为空")
                return {
                    "success": [],
                    "failed": {},
                    "total": 0,
                    "success_count": 0,
                    "failed_count": 0
                }
            
            logger.info(f"📊 [板块管理] 获取到 {len(concept_names)} 个概念板块")
            
            success_list = []
            failed_dict = {}
            
            # 为每个概念板块获取并保存股票列表
            for idx, concept_name in enumerate(concept_names, 1):
                logger.info(f"🔄 [板块管理] 正在更新概念板块 {idx}/{len(concept_names)}: {concept_name}")
                
                # 延时避免请求过于频繁
                if idx > 1:
                    self._delay_for_period(2, 5)
                
                success, error_msg, stock_count = self._update_single_concept_sector(concept_name)
                
                if success:
                    success_list.append(concept_name)
                else:
                    failed_dict[concept_name] = error_msg or "未知错误"
            
            result = {
                "success": success_list,
                "failed": failed_dict,
                "total": len(concept_names),
                "success_count": len(success_list),
                "failed_count": len(failed_dict)
            }
            
            logger.info(f"✅ [板块管理] 概念板块更新完成，成功 {len(success_list)} 个，失败 {len(failed_dict)} 个")
            return result
            
        except Exception as e:
            logger.error(f"❌ [板块管理] 更新概念板块失败: {e}", exc_info=True)
            return {
                "success": [],
                "failed": {"整体更新": str(e)},
                "total": 0,
                "success_count": 0,
                "failed_count": 1
            }
    
    def update_industry_sectors(self) -> Dict[str, Any]:
        """
        更新所有行业板块数据（从 akshare 获取）
        
        Returns:
            包含成功和失败板块信息的字典:
            {
                "success": ["板块1", "板块2", ...],
                "failed": {"板块3": "错误信息", "板块4": "错误信息", ...},
                "total": 总数量,
                "success_count": 成功数量,
                "failed_count": 失败数量
            }
        """
        if not self.connected:
            logger.error("❌ [板块管理] MongoDB未连接")
            return {
                "success": [],
                "failed": {"整体更新": "MongoDB未连接"},
                "total": 0,
                "success_count": 0,
                "failed_count": 1
            }
        
        if not AKSHARE_AVAILABLE:
            logger.error("❌ [板块管理] akshare库未安装")
            return {
                "success": [],
                "failed": {"整体更新": "akshare库未安装"},
                "total": 0,
                "success_count": 0,
                "failed_count": 1
            }
        
        try:
            logger.info("🔄 [板块管理] 开始更新行业板块信息...")
            
            # 获取行业板块列表
            industry_list = ak.stock_board_industry_name_em()
            
            if industry_list is None or industry_list.empty:
                logger.warning("⚠️ [板块管理] 未获取到行业板块列表")
                return {
                    "success": [],
                    "failed": {},
                    "total": 0,
                    "success_count": 0,
                    "failed_count": 0
                }
            
            industry_names = industry_list['板块名称'].tolist() if '板块名称' in industry_list.columns else []
            
            if not industry_names:
                logger.warning("⚠️ [板块管理] 行业板块列表为空")
                return {
                    "success": [],
                    "failed": {},
                    "total": 0,
                    "success_count": 0,
                    "failed_count": 0
                }
            
            logger.info(f"📊 [板块管理] 获取到 {len(industry_names)} 个行业板块")
            
            success_list = []
            failed_dict = {}
            
            # 为每个行业板块获取并保存股票列表
            for idx, industry_name in enumerate(industry_names, 1):
                logger.info(f"🔄 [板块管理] 正在更新行业板块 {idx}/{len(industry_names)}: {industry_name}")
                
                # 延时避免请求过于频繁
                if idx > 1:
                    self._delay_for_period(2, 5)
                
                success, error_msg, stock_count = self._update_single_industry_sector(industry_name)
                
                if success:
                    success_list.append(industry_name)
                else:
                    failed_dict[industry_name] = error_msg or "未知错误"
            
            result = {
                "success": success_list,
                "failed": failed_dict,
                "total": len(industry_names),
                "success_count": len(success_list),
                "failed_count": len(failed_dict)
            }
            
            logger.info(f"✅ [板块管理] 行业板块更新完成，成功 {len(success_list)} 个，失败 {len(failed_dict)} 个")
            return result
            
        except Exception as e:
            logger.error(f"❌ [板块管理] 更新行业板块失败: {e}", exc_info=True)
            return {
                "success": [],
                "failed": {"整体更新": str(e)},
                "total": 0,
                "success_count": 0,
                "failed_count": 1
            }
    
    def update_specific_concept_sectors(self, concept_names: List[str]) -> Dict[str, Any]:
        """
        更新指定的概念板块列表
        
        Args:
            concept_names: 概念板块名称列表
        
        Returns:
            包含成功和失败板块信息的字典
        """
        if not self.connected:
            logger.error("❌ [板块管理] MongoDB未连接")
            return {
                "success": [],
                "failed": {"整体更新": "MongoDB未连接"},
                "total": len(concept_names),
                "success_count": 0,
                "failed_count": len(concept_names)
            }
        
        if not AKSHARE_AVAILABLE:
            logger.error("❌ [板块管理] akshare库未安装")
            return {
                "success": [],
                "failed": {"整体更新": "akshare库未安装"},
                "total": len(concept_names),
                "success_count": 0,
                "failed_count": len(concept_names)
            }
        
        if not concept_names:
            return {
                "success": [],
                "failed": {},
                "total": 0,
                "success_count": 0,
                "failed_count": 0
            }
        
        logger.info(f"🔄 [板块管理] 开始更新指定的 {len(concept_names)} 个概念板块...")
        
        success_list = []
        failed_dict = {}
        
        for idx, concept_name in enumerate(concept_names, 1):
            logger.info(f"🔄 [板块管理] 正在更新概念板块 {idx}/{len(concept_names)}: {concept_name}")
            
            # 延时避免请求过于频繁
            if idx > 1:
                self._delay_for_period(2, 5)
            
            success, error_msg, stock_count = self._update_single_concept_sector(concept_name)
            
            if success:
                success_list.append(concept_name)
            else:
                failed_dict[concept_name] = error_msg or "未知错误"
        
        result = {
            "success": success_list,
            "failed": failed_dict,
            "total": len(concept_names),
            "success_count": len(success_list),
            "failed_count": len(failed_dict)
        }
        
        logger.info(f"✅ [板块管理] 指定概念板块更新完成，成功 {len(success_list)} 个，失败 {len(failed_dict)} 个")
        return result
    
    def update_specific_industry_sectors(self, industry_names: List[str]) -> Dict[str, Any]:
        """
        更新指定的行业板块列表
        
        Args:
            industry_names: 行业板块名称列表
        
        Returns:
            包含成功和失败板块信息的字典
        """
        if not self.connected:
            logger.error("❌ [板块管理] MongoDB未连接")
            return {
                "success": [],
                "failed": {"整体更新": "MongoDB未连接"},
                "total": len(industry_names),
                "success_count": 0,
                "failed_count": len(industry_names)
            }
        
        if not AKSHARE_AVAILABLE:
            logger.error("❌ [板块管理] akshare库未安装")
            return {
                "success": [],
                "failed": {"整体更新": "akshare库未安装"},
                "total": len(industry_names),
                "success_count": 0,
                "failed_count": len(industry_names)
            }
        
        if not industry_names:
            return {
                "success": [],
                "failed": {},
                "total": 0,
                "success_count": 0,
                "failed_count": 0
            }
        
        logger.info(f"🔄 [板块管理] 开始更新指定的 {len(industry_names)} 个行业板块...")
        
        success_list = []
        failed_dict = {}
        
        for idx, industry_name in enumerate(industry_names, 1):
            logger.info(f"🔄 [板块管理] 正在更新行业板块 {idx}/{len(industry_names)}: {industry_name}")
            
            # 延时避免请求过于频繁
            if idx > 1:
                self._delay_for_period(2, 5)
            
            success, error_msg, stock_count = self._update_single_industry_sector(industry_name)
            
            if success:
                success_list.append(industry_name)
            else:
                failed_dict[industry_name] = error_msg or "未知错误"
        
        result = {
            "success": success_list,
            "failed": failed_dict,
            "total": len(industry_names),
            "success_count": len(success_list),
            "failed_count": len(failed_dict)
        }
        
        logger.info(f"✅ [板块管理] 指定行业板块更新完成，成功 {len(success_list)} 个，失败 {len(failed_dict)} 个")
        return result
    
    def _save_sector(self, collection, sector_name: str, stock_codes: List[str], sector_type: str):
        """
        保存板块数据到数据库
        
        Args:
            collection: MongoDB集合对象
            sector_name: 板块名称
            stock_codes: 股票代码列表
            sector_type: 板块类型（"概念" 或 "行业"）
        """
        try:
            now = datetime.now()
            
            # 使用 upsert 操作，如果存在则更新，不存在则插入
            collection.update_one(
                {"name": sector_name},
                {
                    "$set": {
                        "name": sector_name,
                        "stocks": stock_codes,
                        "stock_count": len(stock_codes),
                        "updated_at": now
                    },
                    "$setOnInsert": {
                        "created_at": now,
                        "sector_type": sector_type
                    }
                },
                upsert=True
            )
            
            logger.debug(f"✅ [板块管理] 保存{sector_type}板块 '{sector_name}' 成功")
            
        except Exception as e:
            logger.error(f"❌ [板块管理] 保存{sector_type}板块 '{sector_name}' 失败: {e}")
            raise


# 创建全局实例
sector_manager = SectorManager()


# ==================== __main__ 代码 ====================

if __name__ == "__main__":
    """
    简化的主程序，用于更新概念板块和行业板块数据
    """
    import sys
    
    print("=" * 60)
    print("板块数据更新工具")
    print("=" * 60)
    
    # 检查连接
    if not sector_manager.is_connected():
        print("❌ MongoDB未连接，请检查配置")
        sys.exit(1)
    
    if not AKSHARE_AVAILABLE:
        print("❌ akshare库未安装，无法更新数据")
        print("   请运行: pip install akshare")
        sys.exit(1)
    
    # 更新概念板块
    print("\n" + "=" * 60)
    print("开始更新概念板块数据...")
    print("=" * 60)
    concept_result = sector_manager.update_concept_sectors()
    if isinstance(concept_result, dict):
        print(f"✅ 概念板块更新完成")
        print(f"   成功: {concept_result.get('success_count', 0)} 个")
        print(f"   失败: {concept_result.get('failed_count', 0)} 个")
        if concept_result.get('failed'):
            print(f"   失败的板块: {list(concept_result['failed'].keys())}")
    else:
        print("❌ 概念板块更新失败")
    
    # 更新行业板块
    print("\n" + "=" * 60)
    print("开始更新行业板块数据...")
    print("=" * 60)
    industry_result = sector_manager.update_industry_sectors()
    if isinstance(industry_result, dict):
        print(f"✅ 行业板块更新完成")
        print(f"   成功: {industry_result.get('success_count', 0)} 个")
        print(f"   失败: {industry_result.get('failed_count', 0)} 个")
        if industry_result.get('failed'):
            print(f"   失败的板块: {list(industry_result['failed'].keys())}")
    else:
        print("❌ 行业板块更新失败")
    
    # 显示统计信息
    print("\n" + "=" * 60)
    print("板块统计信息")
    print("=" * 60)
    stats = sector_manager.get_statistics()
    print(f"概念板块数量: {stats['concept_count']}")
    print(f"行业板块数量: {stats['industry_count']}")
    print(f"概念板块关联股票总数（去重）: {stats['total_concept_stocks']}")
    print(f"行业板块关联股票总数（去重）: {stats['total_industry_stocks']}")
    
    print("\n✅ 板块数据更新任务完成！")

