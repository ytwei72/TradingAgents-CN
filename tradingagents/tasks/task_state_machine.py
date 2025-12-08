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
    
    数据结构说明：
    1. task_props (任务对象): 包含任务的基本信息、参数、整体进度、时间统计等
    2. current_step (当前状态): 仅包含当前步骤的信息（名称、序号、描述、状态）
    3. history (历史状态): 步骤状态的列表集合
    """
    
    def __init__(self, task_id: str):
        """初始化任务状态机
        
        Args:
            task_id: 任务 ID
        """
        self.task_id = task_id
        
        # 数据存储结构
        self.task_props: Dict[str, Any] = {}      # 任务对象属性
        self.current_step: Dict[str, Any] = {}    # 当前步骤状态
        self.history: List[Dict[str, Any]] = []   # 历史步骤列表
        
        # 步骤时间跟踪
        self._step_start_time: Optional[float] = None  # 当前步骤开始时间戳
        
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
        self.task_props = self._load_data("props") or {}
        self.current_step = self._load_data("current_step") or {}
        self.history = self._load_data("history") or []
    
    def initialize(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """状态机初始化
        
        Args:
            task_params: 任务参数
            
        Returns:
            初始化的任务对象
        """
        if self.task_props:
            raise ValueError(f"任务已存在: {self.task_id}")
        
        now = datetime.now().isoformat()
        self._step_start_time = time.time()  # 记录步骤开始时间
        
        # 1. 初始化任务对象
        self.task_props = {
            'task_id': self.task_id,
            'status': TaskStatus.PENDING.value,
            'created_at': now,
            'updated_at': now,
            'params': task_params,
            'progress': {
                'percentage': 0.0,
                'message': '任务已创建,等待执行',
                'total_steps': 0,
                'current_step': 0
            },
            'elapsed_time': 0.0,
            'remaining_time': 0.0,
            'error': None,
            'result': None
        }
        
        # 2. 初始化当前步骤（为空，等待第一个实际步骤开始）
        self.current_step = {}
        
        # 3. 初始化历史（空列表，不包含初始化状态）
        self.history = []
        
        # 保存所有数据
        self._save_all()
        
        logger.info(f"📊 [任务创建] 任务已创建: {self.task_id}")
        return self.get_task_object()
    
    def update_state(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新任务状态
        
        Args:
            updates: 更新内容，可以包含任务属性更新和步骤更新
            
        Returns:
            更新后的任务对象
        """
        if not self.task_props:
            self._load_state()
            if not self.task_props:
                raise ValueError(f"任务不存在: {self.task_id}")
        
        now = datetime.now().isoformat()
        now_timestamp = time.time()
        self.task_props['updated_at'] = now
        
        # 1. 处理任务属性更新 (params, progress, status, result, error)
        old_status = self.task_props.get('status')
        new_status = updates.get('status', old_status)
        
        if 'status' in updates:
            self.task_props['status'] = new_status
        
        if 'progress' in updates and isinstance(updates['progress'], dict):
            self.task_props.setdefault('progress', {}).update(updates['progress'])
            
        if 'result' in updates:
            self.task_props['result'] = updates['result']
            
        if 'error' in updates:
            self.task_props['error'] = updates['error']
            
        if 'elapsed_time' in updates:
            self.task_props['elapsed_time'] = updates['elapsed_time']
            
        if 'remaining_time' in updates:
            self.task_props['remaining_time'] = updates['remaining_time']
            
        # 2. 处理步骤更新
        step_update_needed = False
        new_step_info = {}
        
        # 显式步骤信息
        if 'step_name' in updates:
            new_step_info['step_name'] = updates['step_name']
            step_update_needed = True
            
        if 'step_index' in updates:
            new_step_info['step_index'] = updates['step_index']
            step_update_needed = True
            
        # 从 progress 中提取步骤信息
        if 'progress' in updates:
            prog = updates['progress']
            if 'message' in prog:
                new_step_info['description'] = prog['message']
                step_update_needed = True
            if 'current_step' in prog:
                new_step_info['step_index'] = prog['current_step']
                step_update_needed = True
        
        # 从 updates 中提取 step_status（用于明确指定步骤状态）
        step_status = updates.get('step_status')
        
        # 3. 检测步骤是否结束（状态变为完成、失败、停止、取消）
        task_ended = new_status in [
            TaskStatus.COMPLETED.value,
            TaskStatus.FAILED.value,
            TaskStatus.STOPPED.value,
            TaskStatus.CANCELLED.value
        ] and old_status not in [
            TaskStatus.COMPLETED.value,
            TaskStatus.FAILED.value,
            TaskStatus.STOPPED.value,
            TaskStatus.CANCELLED.value
        ]
        
        # 步骤完成的判断：明确指定 step_status 为 completed/failed/success/error
        step_completed = step_status in ['completed', 'failed', 'error', 'success']
        # 步骤开始的判断：明确指定 step_status 为 start
        step_starting = step_status == 'start'
        # 工具调用中的判断
        tool_calling = step_status == 'tool_calling'
        new_step_starting = 'step_name' in new_step_info and new_step_info['step_name'] != self.current_step.get('step_name')
        
        if step_update_needed or task_ended:
            # 计算当前步骤的耗时
            if self._step_start_time is not None:
                elapsed = now_timestamp - self._step_start_time
            else:
                elapsed = 0.0
            
            # 如果任务结束，完成当前步骤并添加到历史
            if task_ended:
                self.current_step['end_time'] = now
                self.current_step['elapsed_time'] = elapsed
                self.current_step['status'] = new_status
                self.current_step['timestamp'] = now
                
                # 将完成的步骤添加到历史
                self.history.append(self.current_step.copy())
                
                # 保存步骤和历史
                self._save_data("current_step", self.current_step)
                self._save_data("history", self.history)
                
                logger.debug(f"📊 [任务结束] {self.current_step.get('step_name', 'Unknown')} - "
                           f"耗时: {elapsed:.2f}秒, 状态: {new_status}")
            
            # 如果是工具调用中（不完成步骤，只追加事件）
            elif tool_calling:
                if self.current_step.get('step_name'):
                    # 计算本次阶段耗时
                    phase_duration = elapsed
                    
                    # 追加工具调用事件
                    event_message = new_step_info.get('description', f"工具调用中: {self.current_step.get('step_name')}")
                    self._add_step_event('tool_calling', event_message, phase_duration)
                    
                    # 重置步骤开始时间（下一阶段从现在开始计时）
                    self._step_start_time = now_timestamp
                    
                    # 保存当前步骤（不添加到历史）
                    self._save_data("current_step", self.current_step)
                    
                    logger.debug(f"📊 [工具调用] {self.current_step.get('step_name', 'Unknown')} - "
                               f"阶段耗时: {phase_duration:.2f}秒")
            
            # 如果当前步骤完成（但任务未结束），完成当前步骤
            elif step_completed:
                # 只有当前步骤存在时才处理完成
                if self.current_step.get('step_name'):
                    # 计算本次阶段耗时
                    phase_duration = elapsed
                    
                    # 追加完成事件
                    event_message = new_step_info.get('description', f"模块完成: {self.current_step.get('step_name')}")
                    final_status = 'complete' if step_status in ['completed', 'success'] else 'error'
                    self._add_step_event(final_status, event_message, phase_duration)
                    
                    # 计算总耗时（从所有事件累加）
                    total_elapsed = sum(e.get('duration', 0) for e in self.current_step.get('events', []))
                    
                    # 完成当前步骤
                    self.current_step['end_time'] = now
                    self.current_step['elapsed_time'] = total_elapsed
                    self.current_step['status'] = 'completed' if step_status in ['completed', 'success'] else 'failed'
                    self.current_step['timestamp'] = now
                    
                    # 将完成的步骤添加到历史
                    self.history.append(self.current_step.copy())
                    
                    # 保存步骤和历史
                    self._save_data("current_step", self.current_step)
                    self._save_data("history", self.history)
                    
                    logger.debug(f"📊 [步骤完成] {self.current_step.get('step_name', 'Unknown')} - "
                               f"总耗时: {total_elapsed:.2f}秒, 状态: {self.current_step['status']}")
            
            # 如果是步骤开始（通过 step_status='start' 明确指定）
            elif step_starting and 'step_name' in new_step_info:
                # 如果当前有正在运行的步骤，先完成它（异常情况处理）
                if self.current_step.get('step_name') and self.current_step.get('status') == 'running':
                    self.current_step['end_time'] = now
                    self.current_step['elapsed_time'] = elapsed
                    self.current_step['status'] = 'completed'
                    self.history.append(self.current_step.copy())
                
                # 创建新步骤（包含events数组）
                self.current_step = {
                    'step_name': new_step_info['step_name'],
                    'step_index': new_step_info.get('step_index', len(self.history) + 1),
                    'description': new_step_info.get('description', ''),
                    'status': 'running',
                    'start_time': now,
                    'end_time': None,
                    'elapsed_time': 0.0,
                    'events': [],  # 事件列表
                    'timestamp': now
                }
                
                # 追加开始事件
                self._add_step_event('start', f"模块开始: {new_step_info['step_name']}")
                
                # 重置步骤开始时间
                self._step_start_time = now_timestamp
                
                # 保存步骤（不添加到历史，等完成时再添加）
                self._save_data("current_step", self.current_step)
                self._save_data("history", self.history)
                
                logger.debug(f"📊 [新步骤] {self.current_step['step_name']} (索引: {self.current_step['step_index']})")
            
            # 如果是新步骤开始（通过步骤名称变化检测）
            elif new_step_starting:
                # 先完成当前步骤（如果存在且还在运行中）
                if self.current_step.get('step_name') and self.current_step.get('status') == 'running':
                    self.current_step['end_time'] = now
                    self.current_step['elapsed_time'] = elapsed
                    self.current_step['status'] = 'completed'
                    self.history.append(self.current_step.copy())
                
                # 创建新步骤（包含events数组）
                self.current_step = {
                    'step_name': new_step_info['step_name'],
                    'step_index': new_step_info.get('step_index', len(self.history) + 1),
                    'description': new_step_info.get('description', ''),
                    'status': 'running',
                    'start_time': now,
                    'end_time': None,
                    'elapsed_time': 0.0,
                    'events': [],  # 事件列表
                    'timestamp': now
                }
                
                # 追加开始事件
                self._add_step_event('start', f"模块开始: {new_step_info['step_name']}")
                
                # 重置步骤开始时间
                self._step_start_time = now_timestamp
                
                # 保存步骤和历史
                self._save_data("current_step", self.current_step)
                self._save_data("history", self.history)
                
                logger.debug(f"📊 [新步骤] {self.current_step['step_name']} (索引: {self.current_step['step_index']})")

            
            else:
                # 只是更新当前步骤的信息，不创建新步骤，不添加历史
                if 'description' in new_step_info:
                    self.current_step['description'] = new_step_info['description']
                if 'step_index' in new_step_info:
                    self.current_step['step_index'] = new_step_info['step_index']
                
                self.current_step['timestamp'] = now
                # 保持当前状态，除非明确指定
                if step_status:
                    self.current_step['status'] = step_status
                
                # 保存当前步骤（不添加到历史）
                self._save_data("current_step", self.current_step)
        
        # 保存任务属性
        self._save_data("props", self.task_props)
        
        return self.get_task_object()
    
    def get_task_object(self) -> Optional[Dict[str, Any]]:
        """获取完整的任务对象 (包含 params, progress 等)"""
        if not self.task_props:
            self._load_state()
            if not self.task_props:
                return None
        return self.task_props.copy()
    
    def get_current_state(self) -> Optional[Dict[str, Any]]:
        """获取当前步骤状态 (仅包含步骤信息)"""
        if not self.current_step:
            self._load_state()
        return self.current_step.copy() if self.current_step else None
    
    def get_history_states(self) -> List[Dict[str, Any]]:
        """获取历史步骤列表（包含当前正在运行的步骤）"""
        if not self.history:
            self._load_state()
        
        # 复制历史记录
        history_with_current = [state.copy() for state in self.history]
        
        # 如果当前步骤存在且状态为 running 或 paused，将其添加到历史末尾
        if self.current_step and self.current_step.get('status') in ['running', 'paused']:
            history_with_current.append(self.current_step.copy())
        
        return history_with_current
    
    def _add_step_event(self, event_type: str, message: str, duration: float = 0.0):
        """向当前步骤追加事件
        
        Args:
            event_type: 事件类型 (start/tool_calling/complete/error)
            message: 事件消息
            duration: 该阶段的耗时（秒）
        """
        if not self.current_step:
            logger.warning(f"📊 [事件追加] 当前步骤不存在，无法追加事件: {event_type}")
            return
        
        # 确保 events 数组存在
        if 'events' not in self.current_step:
            self.current_step['events'] = []
        
        # 创建事件对象
        event = {
            'event': event_type,
            'timestamp': datetime.now().isoformat(),
            'message': message
        }
        
        # 只有非 start 事件才有 duration
        if event_type != 'start' and duration > 0:
            event['duration'] = round(duration, 2)
        
        # 追加事件
        self.current_step['events'].append(event)
        
        logger.debug(f"📊 [事件追加] {event_type}: {message}" + 
                    (f" (耗时: {duration:.2f}s)" if duration > 0 else ""))
    
    def _save_all(self):
        """保存所有数据"""
        self._save_data("props", self.task_props)
        self._save_data("current_step", self.current_step)
        self._save_data("history", self.history)
        
    def _save_data(self, key_suffix: str, data: Any):
        """保存数据通用方法"""
        if self.use_redis:
            try:
                key = f"task:{self.task_id}:{key_suffix}"
                self.redis_client.set(key, json.dumps(data))
            except Exception as e:
                logger.error(f"📊 [存储错误] Redis保存失败 ({key_suffix}): {e}")
        else:
            try:
                file_path = self.storage_dir / f"{self.task_id}_{key_suffix}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"📊 [存储错误] 文件保存失败 ({key_suffix}): {e}")

    def _load_data(self, key_suffix: str) -> Any:
        """加载数据通用方法"""
        if self.use_redis:
            try:
                key = f"task:{self.task_id}:{key_suffix}"
                data = self.redis_client.get(key)
                return json.loads(data) if data else None
            except Exception as e:
                logger.error(f"📊 [存储错误] Redis加载失败 ({key_suffix}): {e}")
                return None
        else:
            try:
                file_path = self.storage_dir / f"{self.task_id}_{key_suffix}.json"
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                return None
            except Exception as e:
                logger.error(f"📊 [存储错误] 文件加载失败 ({key_suffix}): {e}")
                return None
