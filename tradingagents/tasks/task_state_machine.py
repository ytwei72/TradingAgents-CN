"""
任务状态机模块

提供任务状态管理功能，包括：
1. 任务创建接口
2. 任务更新接口
3. 当前状态查询接口
4. 历史状态查询接口

独立于 AsyncProgressTracker，专门为后端 API 服务。
"""

import json
import time
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from enum import Enum

from tradingagents.utils.logging_manager import get_logger

logger = get_logger('task_state_machine')


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStateMachine:
    """任务状态机
    
    管理单个任务的当前状态和历史状态，支持 Redis 和文件两种存储方式。
    """
    
    def __init__(self, task_id: str):
        """初始化任务状态机
        
        Args:
            task_id: 任务 ID
        """
        self.task_id = task_id
        self.current_state: Optional[Dict[str, Any]] = None  # 当前任务状态
        self.history_state: List[Dict[str, Any]] = []  # 历史任务状态
        
        # 初始化存储后端
        self.redis_client = None
        self.use_redis = self._init_redis()
        
        if not self.use_redis:
            # 使用文件存储
            self.storage_dir = Path("./data/task_states")
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            
        # 尝试加载现有状态
        self._load_state()
        
        logger.debug(f"📊 [任务状态机] 初始化完成: {task_id}, 存储方式: {'Redis' if self.use_redis else '文件'}")
    
    def _init_redis(self) -> bool:
        """初始化 Redis 连接"""
        try:
            redis_enabled = os.getenv('REDIS_ENABLED', 'false').lower() == 'true'
            if not redis_enabled:
                # logger.info("📊 [任务状态机] Redis 已禁用，使用文件存储")
                return False
            
            import redis
            
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_password = os.getenv('REDIS_PASSWORD', None)
            redis_db = int(os.getenv('REDIS_DB', 0))
            
            if redis_password:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password,
                    db=redis_db,
                    decode_responses=True
                )
            else:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=True
                )
            
            self.redis_client.ping()
            logger.info(f"📊 [任务状态机] Redis 连接成功: {redis_host}:{redis_port}")
            return True
        except Exception as e:
            logger.warning(f"📊 [任务状态机] Redis 连接失败，使用文件存储: {e}")
            return False
            
    def _load_state(self):
        """加载状态"""
        self.current_state = self._load_current_state()
        self.history_state = self._load_history_states()
    
    def initialize(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """状态机初始化
        
        Args:
            task_params: 任务参数
            
        Returns:
            创建的初始任务状态
            
        Raises:
            ValueError: 如果任务已存在
        """
        # 检查任务是否已存在
        if self.current_state is not None:
            raise ValueError(f"任务已存在: {self.task_id}")
        
        # 创建初始状态
        current_state = {
            'task_id': self.task_id,
            'status': TaskStatus.PENDING.value,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'params': task_params,
            'progress': {
                'current_step': 0,
                'total_steps': 0,
                'percentage': 0.0,
                'message': '任务已创建，等待执行'
            },
            'error': None
        }
        
        # 保存当前状态
        self.current_state = current_state
        self._save_current_state(current_state)
        
        # 初始化历史状态
        self.history_state = [current_state.copy()]
        self._save_history_state(current_state)
        
        logger.info(f"📊 [任务创建] 任务已创建: {self.task_id}")
        return current_state
    
    def update_state(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新任务状态
        
        Args:
            updates: 更新内容
            
        Returns:
            更新后的任务状态
            
        Raises:
            ValueError: 如果任务不存在
        """
        if self.current_state is None:
            # 尝试重新加载
            self._load_state()
            if self.current_state is None:
                raise ValueError(f"任务不存在: {self.task_id}")
        
        # 获取当前状态
        current_state = self.current_state.copy()
        
        # 保存到历史
        self.history_state.append(current_state.copy())
        self._save_history_state(current_state)
        
        # 更新当前状态
        current_state['updated_at'] = datetime.now().isoformat()
        
        # 更新字段
        for key, value in updates.items():
            if key == 'progress' and isinstance(value, dict):
                # 合并进度信息
                current_state.setdefault('progress', {}).update(value)
            elif key == 'status':
                # 验证状态转换
                current_state['status'] = value
            else:
                current_state[key] = value
        
        # 保存更新后的状态
        self.current_state = current_state
        self._save_current_state(current_state)
        
        logger.debug(f"📊 [任务更新] 任务已更新: {self.task_id}, 状态: {current_state.get('status')}")
        return current_state
    
    def get_current_state(self) -> Optional[Dict[str, Any]]:
        """查询任务当前状态
        
        Returns:
            当前状态，如果任务不存在则返回 None
        """
        # 总是尝试从内存返回，如果内存为空则尝试加载
        if self.current_state is None:
            self.current_state = self._load_current_state()
            
        return self.current_state.copy() if self.current_state else None
    
    def get_history_states(self) -> List[Dict[str, Any]]:
        """查询任务历史状态（返回完整历史）
        
        Returns:
            完整的历史状态列表（JSON数组格式）
        """
        if not self.history_state:
            self.history_state = self._load_history_states()
            
        if not self.history_state:
            return []
        
        # 返回完整历史的副本
        return [state.copy() for state in self.history_state]
    
    def _save_current_state(self, state: Dict[str, Any]):
        """保存当前状态到存储"""
        if self.use_redis:
            try:
                key = f"task:current:{self.task_id}"
                self.redis_client.set(key, json.dumps(state))
            except Exception as e:
                logger.error(f"📊 [存储错误] 保存当前状态失败: {e}")
        else:
            try:
                file_path = self.storage_dir / f"{self.task_id}_current.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(state, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"📊 [存储错误] 保存当前状态失败: {e}")
    
    def _save_history_state(self, state: Dict[str, Any]):
        """保存历史状态到存储"""
        if self.use_redis:
            try:
                key = f"task:history:{self.task_id}"
                # 使用 RPUSH 追加到列表
                self.redis_client.rpush(key, json.dumps(state))
            except Exception as e:
                logger.error(f"📊 [存储错误] 保存历史状态失败: {e}")
        else:
            try:
                file_path = self.storage_dir / f"{self.task_id}_history.json"
                # 读取现有历史
                history = []
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                # 追加新状态
                history.append(state)
                # 写回文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(history, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"📊 [存储错误] 保存历史状态失败: {e}")
    
    def _load_current_state(self) -> Optional[Dict[str, Any]]:
        """从存储加载当前状态"""
        if self.use_redis:
            try:
                key = f"task:current:{self.task_id}"
                data = self.redis_client.get(key)
                return json.loads(data) if data else None
            except Exception as e:
                logger.error(f"📊 [存储错误] 加载当前状态失败: {e}")
                return None
        else:
            try:
                file_path = self.storage_dir / f"{self.task_id}_current.json"
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                return None
            except Exception as e:
                logger.error(f"📊 [存储错误] 加载当前状态失败: {e}")
                return None
    
    def _load_history_states(self) -> List[Dict[str, Any]]:
        """从存储加载历史状态"""
        if self.use_redis:
            try:
                key = f"task:history:{self.task_id}"
                data_list = self.redis_client.lrange(key, 0, -1)
                return [json.loads(data) for data in data_list]
            except Exception as e:
                logger.error(f"📊 [存储错误] 加载历史状态失败: {e}")
                return []
        else:
            try:
                file_path = self.storage_dir / f"{self.task_id}_history.json"
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                return []
            except Exception as e:
                logger.error(f"📊 [存储错误] 加载历史状态失败: {e}")
                return []
