#!/usr/bin/env python3
"""
任务状态机 MongoDB 管理器
用于管理任务状态机数据在 MongoDB 中的存储

集合名称: tasks_state_machine
数据库: tradingagents (MongoDB)
主键: task_id + task_sub_state (复合唯一索引)
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('storage')

try:
    from pymongo import ASCENDING, DESCENDING
    from pymongo.operations import UpdateOne
    from pymongo.errors import DuplicateKeyError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    UpdateOne = None
    logger.warning("pymongo未安装，MongoDB功能不可用")


class TasksStateMachineHelper:
    """任务状态机 MongoDB 管理器"""
    
    # 集合名称
    COLLECTION_NAME = "tasks_state_machine"
    
    def __init__(self):
        self.collection = None
        self.connected = False
        
        if MONGODB_AVAILABLE:
            self._connect()
    
    def _connect(self):
        """连接到MongoDB"""
        try:
            from tradingagents.storage.manager import get_mongo_collection
            
            self.collection = get_mongo_collection(self.COLLECTION_NAME)
            if self.collection is None:
                logger.error("❌ 统一连接管理不可用，无法连接MongoDB")
                self.connected = False
                return
            
            # 创建索引
            self._create_indexes()
            
            self.connected = True
            logger.info(f"✅ MongoDB连接成功: {self.COLLECTION_NAME}")
            
        except Exception as e:
            logger.error(f"❌ MongoDB连接失败: {e}")
            self.connected = False
    
    def _create_indexes(self):
        """创建索引以提高查询性能"""
        try:
            # 复合唯一索引：task_id + task_sub_state（主键）
            self.collection.create_index(
                [
                    ("task_id", ASCENDING),
                    ("task_sub_state", ASCENDING)
                ],
                unique=True,
                name="task_id_task_sub_state_unique"
            )
            
            # 单字段索引：task_id（用于查询某个任务的所有状态）
            self.collection.create_index("task_id")
            
            # 单字段索引：task_sub_state（用于查询特定状态类型）
            self.collection.create_index("task_sub_state")
            
            # 时间索引：用于按时间查询
            self.collection.create_index("updated_at")
            
            logger.info("✅ tasks_state_machine索引创建成功")
            
        except Exception as e:
            logger.error(f"❌ tasks_state_machine索引创建失败: {e}")
    
    def insert(self, task_id: str, task_sub_state: str, data: Dict[str, Any]) -> bool:
        """
        插入任务状态数据
        
        Args:
            task_id: 任务ID
            task_sub_state: 任务子状态（如：props, current_step, history）
            data: 要存储的数据（JSON格式，字典）
        
        Returns:
            bool: 是否插入成功
        """
        if not self.connected:
            logger.error("❌ MongoDB未连接，无法插入数据")
            return False
        
        try:
            # 构建文档
            doc = {
                'task_id': task_id,
                'task_sub_state': task_sub_state,
                'data': data,  # 直接存储JSON格式，不转换为字符串
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # 插入记录
            result = self.collection.insert_one(doc)
            
            if result.inserted_id:
                logger.debug(f"✅ 任务状态数据已插入: task_id={task_id}, task_sub_state={task_sub_state}")
                return True
            else:
                logger.error(f"❌ MongoDB插入失败：未返回插入ID")
                return False
                
        except DuplicateKeyError:
            # 如果已存在，则更新
            logger.debug(f"⚠️ 记录已存在，将更新: task_id={task_id}, task_sub_state={task_sub_state}")
            return self.update(task_id, task_sub_state, data)
        except Exception as e:
            logger.error(f"❌ 插入任务状态数据失败: {e}")
            return False
    
    def update(self, task_id: str, task_sub_state: str, data: Dict[str, Any]) -> bool:
        """
        更新任务状态数据
        
        Args:
            task_id: 任务ID
            task_sub_state: 任务子状态
            data: 要更新的数据（JSON格式，字典）
        
        Returns:
            bool: 是否更新成功
        """
        if not self.connected:
            logger.error("❌ MongoDB未连接，无法更新数据")
            return False
        
        try:
            # 构建查询条件
            filter_dict = {
                'task_id': task_id,
                'task_sub_state': task_sub_state
            }
            
            # 构建更新数据
            update_dict = {
                '$set': {
                    'data': data,  # 直接存储JSON格式，不转换为字符串
                    'updated_at': datetime.now()
                }
            }
            
            # 更新记录（如果不存在则插入）
            result = self.collection.update_one(
                filter_dict,
                update_dict,
                upsert=True
            )
            
            if result.modified_count > 0 or result.upserted_id:
                logger.debug(f"✅ 任务状态数据已更新: task_id={task_id}, task_sub_state={task_sub_state}")
                return True
            else:
                logger.warning(f"⚠️ 未找到要更新的记录: task_id={task_id}, task_sub_state={task_sub_state}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 更新任务状态数据失败: {e}")
            return False
    
    def find_one(self, task_id: str, task_sub_state: str) -> Optional[Dict[str, Any]]:
        """
        查询单个任务状态数据
        
        Args:
            task_id: 任务ID
            task_sub_state: 任务子状态
        
        Returns:
            Dict: 查询到的数据（data字段），如果不存在返回None
        """
        if not self.connected:
            return None
        
        try:
            # 构建查询条件
            query = {
                'task_id': task_id,
                'task_sub_state': task_sub_state
            }
            
            # 查询记录
            result = self.collection.find_one(query)
            
            if result and 'data' in result:
                return result['data']
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 查询任务状态数据失败: {e}")
            return None
    
    def find_by_task_id(self, task_id: str) -> List[Dict[str, Any]]:
        """
        查询某个任务的所有状态数据
        
        Args:
            task_id: 任务ID
        
        Returns:
            List[Dict]: 该任务的所有状态数据列表，每个元素包含 task_sub_state 和 data
        """
        if not self.connected:
            return []
        
        try:
            # 构建查询条件
            query = {
                'task_id': task_id
            }
            
            # 查询记录
            cursor = self.collection.find(query).sort('updated_at', DESCENDING)
            
            results = []
            for doc in cursor:
                results.append({
                    'task_sub_state': doc.get('task_sub_state'),
                    'data': doc.get('data'),
                    'created_at': doc.get('created_at'),
                    'updated_at': doc.get('updated_at')
                })
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 查询任务所有状态数据失败: {e}")
            return []
    
    def delete(self, task_id: str, task_sub_state: Optional[str] = None) -> int:
        """
        删除任务状态数据
        
        Args:
            task_id: 任务ID
            task_sub_state: 任务子状态，如果为None则删除该任务的所有状态数据
        
        Returns:
            int: 删除的记录数
        """
        if not self.connected:
            logger.error("❌ MongoDB未连接，无法删除数据")
            return 0
        
        try:
            # 构建查询条件
            query = {
                'task_id': task_id
            }
            
            if task_sub_state:
                query['task_sub_state'] = task_sub_state
            
            # 删除记录
            result = self.collection.delete_many(query)
            
            deleted_count = result.deleted_count
            if deleted_count > 0:
                logger.info(f"✅ 已删除 {deleted_count} 条任务状态数据: task_id={task_id}, task_sub_state={task_sub_state or 'all'}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ 删除任务状态数据失败: {e}")
            return 0
    
    def count(self, task_id: Optional[str] = None, task_sub_state: Optional[str] = None) -> int:
        """
        统计任务状态数据数量
        
        Args:
            task_id: 任务ID，如果为None则统计所有任务
            task_sub_state: 任务子状态，如果为None则统计所有状态类型
        
        Returns:
            int: 记录数
        """
        if not self.connected:
            return 0
        
        try:
            # 构建查询条件
            query = {}
            
            if task_id:
                query['task_id'] = task_id
            
            if task_sub_state:
                query['task_sub_state'] = task_sub_state
            
            # 统计记录数
            count = self.collection.count_documents(query)
            return count
            
        except Exception as e:
            logger.error(f"❌ 统计任务状态数据失败: {e}")
            return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict: 统计信息，包括总记录数、任务数、各状态类型数量等
        """
        if not self.connected:
            return {}
        
        try:
            # 总记录数
            total_count = self.collection.count_documents({})
            
            # 任务数（去重）
            task_ids = self.collection.distinct('task_id')
            task_count = len(task_ids)
            
            # 各状态类型数量
            pipeline = [
                {
                    '$group': {
                        '_id': '$task_sub_state',
                        'count': {'$sum': 1}
                    }
                },
                {
                    '$sort': {'count': -1}
                }
            ]
            state_type_counts = {}
            for doc in self.collection.aggregate(pipeline):
                state_type_counts[doc['_id']] = doc['count']
            
            # 最近更新时间
            latest_doc = self.collection.find_one(
                {},
                sort=[('updated_at', DESCENDING)]
            )
            latest_updated_at = latest_doc.get('updated_at') if latest_doc else None
            
            return {
                'total_count': total_count,
                'task_count': task_count,
                'state_type_counts': state_type_counts,
                'latest_updated_at': latest_updated_at.isoformat() if latest_updated_at else None
            }
            
        except Exception as e:
            logger.error(f"❌ 获取统计信息失败: {e}")
            return {}
    
    def _match_filters(
        self,
        props_data: Dict[str, Any],
        task_id: Optional[str] = None,
        analysis_date: Optional[str] = None,
        status: Optional[str] = None,
        stock_symbol: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> bool:
        """
        检查任务是否匹配筛选条件
        
        Args:
            props_data: props子状态的数据
            task_id: 任务ID筛选（支持部分匹配）
            analysis_date: 分析日期筛选（精确匹配）
            status: 运行状态筛选（精确匹配）
            stock_symbol: 股票代码筛选（支持部分匹配）
            company_name: 公司名称筛选（支持部分匹配，不区分大小写）
        
        Returns:
            bool: 是否匹配
        """
        # task_id筛选（部分匹配，不区分大小写）
        if task_id:
            task_id_value = props_data.get('task_id', '')
            if task_id.lower() not in task_id_value.lower():
                return False
        
        # status筛选（精确匹配）
        if status:
            task_status = props_data.get('status', '')
            if task_status != status:
                return False
        
        # analysis_date筛选（精确匹配）
        if analysis_date:
            # 从params中获取analysis_date
            params = props_data.get('params', {})
            task_analysis_date = params.get('analysis_date', '')
            if task_analysis_date != analysis_date:
                return False
        
        # stock_symbol筛选（部分匹配，不区分大小写）
        if stock_symbol:
            params = props_data.get('params', {})
            task_stock_symbol = params.get('stock_symbol', '')
            if not task_stock_symbol or stock_symbol.lower() not in task_stock_symbol.lower():
                return False
        
        # company_name筛选（部分匹配，不区分大小写）
        if company_name:
            params = props_data.get('params', {})
            task_company_name = params.get('company_name', '')
            if not task_company_name or company_name.lower() not in task_company_name.lower():
                return False
        
        return True
    
    def get_task_count(
        self,
        task_id: Optional[str] = None,
        analysis_date: Optional[str] = None,
        status: Optional[str] = None,
        stock_symbol: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> int:
        """
        获取任务总数（支持筛选）
        
        Args:
            task_id: 任务ID筛选（支持部分匹配）
            analysis_date: 分析日期筛选（精确匹配）
            status: 运行状态筛选（精确匹配）
            stock_symbol: 股票代码筛选（支持部分匹配）
            company_name: 公司名称筛选（支持部分匹配）
        
        Returns:
            int: 任务总数
        """
        if not self.connected:
            return 0
        
        try:
            # 查询所有props子状态的记录
            query = {'task_sub_state': 'props'}
            cursor = self.collection.find(query)
            
            count = 0
            for doc in cursor:
                props_data = doc.get('data', {})
                
                # 应用筛选（包括company_name）
                if not self._match_filters(props_data, task_id, analysis_date, status, stock_symbol, company_name):
                    continue
                
                count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"❌ 获取任务总数失败: {e}")
            return 0
    
    def get_task_list(
        self,
        page: int = 1,
        page_size: int = 10,
        task_id: Optional[str] = None,
        analysis_date: Optional[str] = None,
        status: Optional[str] = None,
        stock_symbol: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分页查询任务列表（支持筛选）
        
        Args:
            page: 页码（从1开始）
            page_size: 每页数量
            task_id: 任务ID筛选（支持部分匹配）
            analysis_date: 分析日期筛选（精确匹配）
            status: 运行状态筛选（精确匹配）
            stock_symbol: 股票代码筛选（支持部分匹配）
            company_name: 公司名称筛选（支持部分匹配）
        
        Returns:
            Dict: 包含items（列表）、total（总数）、page（当前页）、page_size（每页数量）、pages（总页数）
        """
        if not self.connected:
            return {
                'items': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'pages': 0
            }
        
        try:
            # 查询所有props子状态的记录
            query = {'task_sub_state': 'props'}
            cursor = self.collection.find(query).sort('updated_at', DESCENDING)
            
            # 先应用筛选，获取所有匹配的任务
            matched_tasks = []
            for doc in cursor:
                props_data = doc.get('data', {})
                task_id_item = props_data.get('task_id', '')
                
                # 应用筛选（包括company_name）
                if not self._match_filters(props_data, task_id, analysis_date, status, stock_symbol, company_name):
                    continue
                
                # 提取需要的字段
                params = props_data.get('params', {})
                item = {
                    'task_id': task_id_item,
                    'status': props_data.get('status', 'unknown'),
                    'created_at': props_data.get('created_at'),
                    'updated_at': props_data.get('updated_at'),
                    'analysis_date': params.get('analysis_date'),
                    'stock_symbol': params.get('stock_symbol'),
                    'company_name': params.get('company_name')
                }
                matched_tasks.append(item)
            
            # 计算分页
            total = len(matched_tasks)
            pages = (total + page_size - 1) // page_size if total > 0 else 0
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            items = matched_tasks[start_idx:end_idx]
            
            return {
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size,
                'pages': pages
            }
            
        except Exception as e:
            logger.error(f"❌ 获取任务列表失败: {e}")
            return {
                'items': [],
                'total': 0,
                'page': page,
                'page_size': page_size,
                'pages': 0
            }
    
    def get_task_detail(
        self,
        task_id: str,
        sub_keys: Optional[List[str]] = None,
        truncate_length: Optional[int] = 50
    ) -> Dict[str, Any]:
        """
        获取任务详细信息
        
        Args:
            task_id: 任务ID
            sub_keys: 要获取的子键列表（如 ['current_step', 'history', 'props']），
                      如果为None则获取所有子键
            truncate_length: 字段截断长度，None表示不截断，默认50
        
        Returns:
            Dict[str, Any]: 包含指定子键的数据字典
        """
        if not self.connected:
            return {}
        
        try:
            # 默认获取所有子键
            if sub_keys is None:
                sub_keys = ["current_step", "history", "props"]
            
            result = {}
            
            for sub_key in sub_keys:
                data = self.find_one(task_id, sub_key)
                if data is not None:
                    # 如果指定了截断长度，则截断字符串字段
                    if truncate_length is not None:
                        data = self._truncate_dict_values(data, truncate_length)
                    result[sub_key] = data
                else:
                    result[sub_key] = None
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 获取任务详细信息失败: {e}")
            return {}
    
    def _truncate_field(self, value: Any, max_length: int) -> str:
        """
        截断字段值
        
        Args:
            value: 字段值
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


# 单例实例
tasks_state_machine_helper = TasksStateMachineHelper()

