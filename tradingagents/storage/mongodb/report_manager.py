#!/usr/bin/env python3
"""
MongoDB报告管理器
用于保存和读取分析报告到MongoDB数据库
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('storage')

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    logger.warning("pymongo未安装，MongoDB功能不可用")


class MongoDBReportManager:
    """MongoDB报告管理器"""
    
    def __init__(self):
        self.collection = None
        self.connected = False
        
        if MONGODB_AVAILABLE:
            self._connect()
    
    def _connect(self):
        """连接到MongoDB（只使用统一的连接管理）"""
        try:
            # 只使用统一的连接管理
            from tradingagents.storage.manager import get_mongo_collection
            
            self.collection = get_mongo_collection("analysis_reports")
            if self.collection is None:
                logger.error("❌ 统一连接管理不可用，无法连接MongoDB")
                self.connected = False
                return
            
            # 创建索引
            self._create_indexes()
            
            self.connected = True
            logger.info(f"✅ MongoDB连接成功（使用统一连接管理）: analysis_reports")
            
        except Exception as e:
            logger.error(f"❌ MongoDB连接失败: {e}")
            self.connected = False
    
    def _create_indexes(self):
        """创建索引以提高查询性能"""
        try:
            # 创建复合索引
            self.collection.create_index([
                ("stock_symbol", 1),
                ("analysis_date", -1),
                ("timestamp", -1)
            ])
            
            # 创建单字段索引
            self.collection.create_index("analysis_id")
            self.collection.create_index("status")
            
            logger.info("✅ MongoDB索引创建成功")
            
        except Exception as e:
            logger.error(f"❌ MongoDB索引创建失败: {e}")
    
    def save_analysis_report(self, stock_symbol: str, analysis_results: Dict[str, Any],
                           reports: Dict[str, str], analysis_id: str = None) -> bool:
        """
        保存分析报告到MongoDB（使用upsert模式，支持合并更新）
        
        Args:
            stock_symbol: 股票代码
            analysis_results: 分析结果字典
            reports: 报告内容字典
            analysis_id: 分析ID（可选），如果不提供则自动生成
                        如果提供，将使用此ID进行upsert操作
        """
        if not self.connected:
            logger.warning("MongoDB未连接，跳过保存")
            return False

        try:
            timestamp = datetime.now()
            # 优先使用传入的分析日期（字符串 'YYYY-MM-DD'）
            analysis_date_str = analysis_results.get("analysis_date")
            if not analysis_date_str:
                analysis_date_str = timestamp.strftime('%Y-%m-%d')
            
            # 如果未提供analysis_id，则生成一个
            if analysis_id is None:
                analysis_id = f"{stock_symbol}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            
            # 查询是否已存在该analysis_id的记录
            existing_doc = self.collection.find_one({"analysis_id": analysis_id})
            
            if existing_doc:
                # 如果记录已存在，合并reports字段
                existing_reports = existing_doc.get("reports", {})
                
                # 合并reports：新报告覆盖旧报告，但保留旧报告中新报告没有的字段
                merged_reports = {**existing_reports, **reports}
                
                # 构建更新文档
                update_doc = {
                    "$set": {
                        "stock_symbol": stock_symbol,
                        "analysis_date": analysis_date_str,
                        "status": "completed",
                        "source": "mongodb",
                        
                        # 分析结果摘要（使用新数据更新，但保留已有的有效数据）
                        "summary": analysis_results.get("summary", existing_doc.get("summary", "")),
                        "analysts": analysis_results.get("analysts", existing_doc.get("analysts", [])),
                        "research_depth": analysis_results.get("research_depth", existing_doc.get("research_depth", 1)),
                        
                        # 保存formatted_decision（决策信息）
                        "formatted_decision": analysis_results.get("decision", existing_doc.get("formatted_decision", {})),
                        
                        # 合并后的报告内容
                        "reports": merged_reports,
                        
                        # 更新时间戳
                        "updated_at": timestamp
                    }
                }
                
                # 执行upsert更新
                result = self.collection.update_one(
                    {"analysis_id": analysis_id},
                    update_doc,
                    upsert=True
                )
                
                if result.modified_count > 0 or result.upserted_id:
                    logger.info(f"✅ 分析报告已更新到MongoDB: {analysis_id} (合并了 {len(reports)} 个新报告字段)")
                    logger.debug(f"🔍 [MongoDB更新] 合并前报告字段数: {len(existing_reports)}, 合并后: {len(merged_reports)}")
                    return True
                else:
                    logger.warning(f"⚠️ MongoDB更新无变化: {analysis_id}")
                    return True  # 即使无变化也返回True，因为记录已存在
            else:
                # 如果记录不存在，创建新文档
                document = {
                    "analysis_id": analysis_id,
                    "stock_symbol": stock_symbol,
                    "analysis_date": analysis_date_str,
                    "timestamp": timestamp,
                    "status": "completed",
                    "source": "mongodb",

                    # 分析结果摘要
                    "summary": analysis_results.get("summary", ""),
                    "analysts": analysis_results.get("analysts", []),
                    "research_depth": analysis_results.get("research_depth", 1),

                    # 保存formatted_decision（决策信息）
                    "formatted_decision": analysis_results.get("decision", {}),

                    # 报告内容
                    "reports": reports,

                    # 元数据
                    "created_at": timestamp,
                    "updated_at": timestamp
                }
                
                # 使用upsert插入
                result = self.collection.update_one(
                    {"analysis_id": analysis_id},
                    {"$set": document},
                    upsert=True
                )
                
                if result.upserted_id or result.modified_count > 0:
                    logger.info(f"✅ 分析报告已保存到MongoDB: {analysis_id}")
                    return True
                else:
                    logger.error("❌ MongoDB upsert失败")
                    return False
                
        except Exception as e:
            logger.error(f"❌ 保存分析报告到MongoDB失败: {e}")
            import traceback
            logger.error(f"❌ 详细错误: {traceback.format_exc()}")
            return False
    
    def get_analysis_reports(self, limit: int = 100, stock_symbol: str = None,
                           start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """从MongoDB获取分析报告"""
        if not self.connected:
            return []
        
        try:
            # 构建查询条件
            query = {}
            
            if stock_symbol:
                query["stock_symbol"] = stock_symbol
            
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query["$gte"] = start_date
                if end_date:
                    date_query["$lte"] = end_date
                query["analysis_date"] = date_query
            
            # 查询数据
            cursor = self.collection.find(query).sort("timestamp", -1).limit(limit)
            
            results = []
            for doc in cursor:
                # 处理timestamp字段，兼容不同的数据类型
                timestamp_value = doc.get("timestamp")
                if hasattr(timestamp_value, 'timestamp'):
                    # datetime对象
                    timestamp = timestamp_value.timestamp()
                elif isinstance(timestamp_value, (int, float)):
                    # 已经是时间戳
                    timestamp = float(timestamp_value)
                else:
                    # 其他情况，使用当前时间
                    from datetime import datetime
                    timestamp = datetime.now().timestamp()
                
                # 转换为Web应用期望的格式
                result = {
                    "analysis_id": doc["analysis_id"],
                    "timestamp": timestamp,
                    "stock_symbol": doc["stock_symbol"],
                    "analysts": doc.get("analysts", []),
                    "research_depth": doc.get("research_depth", 0),
                    "status": doc.get("status", "completed"),
                    "summary": doc.get("summary", ""),
                    "performance": {},
                    "tags": [],
                    "is_favorite": False,
                    "reports": doc.get("reports", {}),
                    "formatted_decision": doc.get("formatted_decision", {}),
                    "analysis_date": doc.get("analysis_date", ""),
                    "source": "mongodb"
                }
                results.append(result)
            
            logger.info(f"✅ 从MongoDB获取到 {len(results)} 个分析报告")
            return results
            
        except Exception as e:
            logger.error(f"❌ 从MongoDB获取分析报告失败: {e}")
            return []
    
    def get_report_by_id(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取单个分析报告"""
        if not self.connected:
            return None
        
        try:
            doc = self.collection.find_one({"analysis_id": analysis_id})
            
            if doc:
                # 转换为Web应用期望的格式
                result = {
                    "analysis_id": doc["analysis_id"],
                    "timestamp": doc["timestamp"].timestamp(),
                    "stock_symbol": doc["stock_symbol"],
                    "analysts": doc.get("analysts", []),
                    "research_depth": doc.get("research_depth", 0),
                    "status": doc.get("status", "completed"),
                    "summary": doc.get("summary", ""),
                    "performance": {},
                    "tags": [],
                    "is_favorite": False,
                    "reports": doc.get("reports", {}),
                    "source": "mongodb"
                }
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 从MongoDB获取报告失败: {e}")
            return None
    
    def delete_report(self, analysis_id: str) -> bool:
        """删除分析报告"""
        if not self.connected:
            return False
        
        try:
            result = self.collection.delete_one({"analysis_id": analysis_id})
            
            if result.deleted_count > 0:
                logger.info(f"✅ 已删除分析报告: {analysis_id}")
                return True
            else:
                logger.warning(f"⚠️ 未找到要删除的报告: {analysis_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 删除分析报告失败: {e}")
            return False

    def get_all_reports(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """获取所有分析报告"""
        if not self.connected:
            return []

        try:
            # 获取所有报告，按时间戳降序排列
            cursor = self.collection.find().sort("timestamp", -1).limit(limit)
            reports = list(cursor)

            # 转换ObjectId为字符串
            for report in reports:
                if '_id' in report:
                    report['_id'] = str(report['_id'])

            logger.info(f"✅ 从MongoDB获取了 {len(reports)} 个分析报告")
            return reports

        except Exception as e:
            logger.error(f"❌ 从MongoDB获取所有报告失败: {e}")
            return []

    def fix_inconsistent_reports(self) -> bool:
        """修复不一致的报告数据结构"""
        if not self.connected:
            logger.warning("MongoDB未连接，跳过修复")
            return False

        try:
            # 查找缺少reports字段或reports字段为空的文档
            query = {
                "$or": [
                    {"reports": {"$exists": False}},
                    {"reports": {}},
                    {"reports": None}
                ]
            }

            cursor = self.collection.find(query)
            inconsistent_docs = list(cursor)

            if not inconsistent_docs:
                logger.info("✅ 所有报告数据结构一致，无需修复")
                return True

            logger.info(f"🔧 发现 {len(inconsistent_docs)} 个不一致的报告，开始修复...")

            fixed_count = 0
            for doc in inconsistent_docs:
                try:
                    # 为缺少reports字段的文档添加空的reports字段
                    update_data = {
                        "$set": {
                            "reports": {},
                            "updated_at": datetime.now()
                        }
                    }

                    result = self.collection.update_one(
                        {"_id": doc["_id"]},
                        update_data
                    )

                    if result.modified_count > 0:
                        fixed_count += 1
                        logger.info(f"✅ 修复报告: {doc.get('analysis_id', 'unknown')}")

                except Exception as e:
                    logger.error(f"❌ 修复报告失败 {doc.get('analysis_id', 'unknown')}: {e}")

            logger.info(f"✅ 修复完成，共修复 {fixed_count} 个报告")
            return True

        except Exception as e:
            logger.error(f"❌ 修复不一致报告失败: {e}")
            return False

    def save_report(self, report_data: Dict[str, Any]) -> bool:
        """保存报告数据（通用方法）"""
        if not self.connected:
            logger.warning("MongoDB未连接，跳过保存")
            return False

        try:
            # 确保有必要的字段
            if 'analysis_id' not in report_data:
                logger.error("报告数据缺少analysis_id字段")
                return False

            # 添加保存时间戳
            report_data['saved_at'] = datetime.now()

            # 使用upsert操作，如果存在则更新，不存在则插入
            result = self.collection.replace_one(
                {"analysis_id": report_data['analysis_id']},
                report_data,
                upsert=True
            )

            if result.upserted_id or result.modified_count > 0:
                logger.info(f"✅ 报告保存成功: {report_data['analysis_id']}")
                return True
            else:
                logger.warning(f"⚠️ 报告保存无变化: {report_data['analysis_id']}")
                return True

        except Exception as e:
            logger.error(f"❌ 保存报告到MongoDB失败: {e}")
            return False

    def get_paginated_reports(self, page: int = 1, page_size: int = 10) -> tuple[List[Dict[str, Any]], int]:
        """
        获取分页的分析报告列表
        
        :param page: 页码，从1开始
        :param page_size: 每页大小，最大10
        :return: (报告列表, 总条数)
        """
        if not self.connected:
            return [], 0
        
        try:
            skip = (page - 1) * page_size
            total = self.collection.count_documents({})

            # 只获取列表展示所需的基础字段，显式排除体积较大的 reports 字段，
            # 避免在列表接口中一次性加载所有报告内容
            projection = {
                "reports": 0  # 报告详情在 `/api/reports/{analysis_id}/reports` 中按需加载
            }

            cursor = (
                self.collection
                .find({}, projection)
                .sort("updated_at", -1)
                .skip(skip)
                .limit(page_size)
            )
            reports = list(cursor)

            # 关联 stock_dict 字典表，补充上市公司名称 stock_name
            try:
                if reports:
                    # 从当前分页结果中收集所有股票代码
                    symbols = {
                        r.get("stock_symbol")
                        for r in reports
                        if isinstance(r, dict) and r.get("stock_symbol")
                    }

                    if symbols:
                        # 通过当前数据库对象获取 stock_dict 集合
                        stock_dict_collection = self.collection.database.get_collection("stock_dict")
                        stock_docs = stock_dict_collection.find(
                            {"symbol": {"$in": list(symbols)}},
                            {"symbol": 1, "name": 1}
                        )

                        symbol_name_map = {
                            doc.get("symbol"): doc.get("name")
                            for doc in stock_docs
                        }

                        # 将上市公司名称映射到报告对象上
                        for report in reports:
                            symbol = report.get("stock_symbol")
                            if symbol:
                                report["stock_name"] = symbol_name_map.get(symbol)

            except Exception as e:
                # 关联失败不影响主流程，只记录日志
                logger.error(f"❌ 关联 stock_dict 获取上市公司名称失败: {e}")
            
            # 转换ObjectId为字符串
            for report in reports:
                if '_id' in report:
                    report['_id'] = str(report['_id'])
            
            logger.info(f"✅ 从MongoDB获取分页报告: 页 {page}, 大小 {page_size}, 总计 {total}")
            return reports, total
            
        except Exception as e:
            logger.error(f"❌ 分页获取报告失败: {e}")
            return [], 0

    def get_reports_with_formatted_decisions(
        self,
        start_date: str,
        end_date: str,
        stock_code: Optional[str] = None,
        action: Optional[str] = None,
        analyst: Optional[str] = None,
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        获取包含 formatted_decision 的报告数据（用于批量回测）
        
        :param start_date: 开始日期，格式 YYYY-MM-DD
        :param end_date: 结束日期，格式 YYYY-MM-DD
        :param stock_code: 可选，按股票代码筛选
        :param action: 可选，按 formatted_decision.action 筛选
        :param analyst: 可选，按分析师筛选
        :return: (报告列表, 总条数)
        """
        if not self.connected:
            return [], 0
        
        if self.collection is None:
            logger.error("❌ 报告集合未初始化")
            return [], 0
        
        try:
            # 构造 MongoDB 查询条件
            query: Dict[str, Any] = {
                "analysis_date": {"$gte": start_date, "$lte": end_date}
            }

            if stock_code:
                query["stock_symbol"] = stock_code

            if analyst:
                # 分析师字段为数组时，使用 $in 匹配
                query["analysts"] = {"$in": [analyst]}

            if action:
                # formatted_decision 为嵌套 JSON 字段
                query["formatted_decision.action"] = action

            # 只取需要的字段，显式排除体积较大的 reports 字段
            projection = {
                "reports": 0,
            }

            total = self.collection.count_documents(query)

            cursor = (
                self.collection.find(query, projection)
                .sort("analysis_date", 1)
            )

            raw_reports: List[Dict[str, Any]] = list(cursor)
            
            logger.info(
                f"✅ 从MongoDB获取 formatted_decisions: 条数={len(raw_reports)}, 区间={start_date}~{end_date}"
            )
            
            return raw_reports, total
            
        except Exception as e:
            logger.error(f"❌ 获取 formatted_decisions 失败: {e}")
            return [], 0

    def get_reports_by_ids(
        self,
        analysis_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """
        根据 analysis_ids 获取研报数据
        
        :param analysis_ids: 研报 ID 列表
        :return: 研报数据列表，每个元素包含：
            - analysis_id
            - analysis_date
            - stock_symbol
            - formatted_decision
            - summary
        """
        if not self.connected:
            return []
        
        if self.collection is None:
            logger.error("❌ 报告集合未初始化")
            return []
        
        try:
            # 查询研报
            query = {"analysis_id": {"$in": analysis_ids}}
            # 只使用排除字段，不能同时使用包含和排除（除了 _id）
            projection = {
                "reports": 0,  # 排除体积较大的 reports 字段
            }

            raw_reports = list(self.collection.find(query, projection))
            
            logger.info(
                f"✅ 从MongoDB根据ID列表获取报告: 请求{len(analysis_ids)}个, 实际获取{len(raw_reports)}个"
            )
            
            return raw_reports
            
        except Exception as e:
            logger.error(f"❌ 根据ID列表获取报告失败: {e}")
            return []


# 创建全局实例
mongodb_report_manager = MongoDBReportManager()
