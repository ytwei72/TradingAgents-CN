"""
任务控制管理器
支持分析任务的暂停、恢复和停止功能
"""

import threading
import json
import os
import time
from typing import Dict, Optional, Any
from pathlib import Path
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('task_control')


class TaskControlManager:
    """任务控制管理器 - 管理任务的暂停、恢复和停止"""
    
    def __init__(self):
        self._control_events: Dict[str, threading.Event] = {}  # 停止事件
        self._pause_events: Dict[str, threading.Event] = {}    # 暂停事件
        self._task_states: Dict[str, str] = {}                 # 任务状态: running/paused/stopped
        self._checkpoints: Dict[str, Any] = {}                 # 任务检查点
        self._lock = threading.Lock()
        
        # 持久化目录
        self.checkpoint_dir = Path("./data/checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def register_task(self, analysis_id: str):
        """注册新任务"""
        with self._lock:
            # 创建停止事件（未设置表示继续运行）
            self._control_events[analysis_id] = threading.Event()
            # 创建暂停事件（未设置表示正常运行，设置表示暂停）
            self._pause_events[analysis_id] = threading.Event()
            # 初始状态为运行中
            self._task_states[analysis_id] = 'running'
            logger.info(f"📋 [任务控制] 注册任务: {analysis_id}")
    
    def unregister_task(self, analysis_id: str):
        """注销任务"""
        with self._lock:
            if analysis_id in self._control_events:
                del self._control_events[analysis_id]
            if analysis_id in self._pause_events:
                del self._pause_events[analysis_id]
            if analysis_id in self._task_states:
                del self._task_states[analysis_id]
            if analysis_id in self._checkpoints:
                del self._checkpoints[analysis_id]
            logger.info(f"📋 [任务控制] 注销任务: {analysis_id}")
    
    def pause_task(self, analysis_id: str) -> bool:
        """暂停任务"""
        with self._lock:
            if analysis_id not in self._pause_events:
                logger.warning(f"⚠️ [任务控制] 任务不存在: {analysis_id}")
                return False
            
            if self._task_states.get(analysis_id) == 'stopped':
                logger.warning(f"⚠️ [任务控制] 任务已停止，无法暂停: {analysis_id}")
                return False
            
            # 设置暂停标志
            self._pause_events[analysis_id].set()
            self._task_states[analysis_id] = 'paused'
            
            # 保存暂停状态到文件
            self._save_task_state(analysis_id)
            
            logger.info(f"⏸️ [任务控制] 任务已暂停: {analysis_id}")
            return True
    
    def resume_task(self, analysis_id: str) -> bool:
        """恢复任务"""
        with self._lock:
            if analysis_id not in self._pause_events:
                logger.warning(f"⚠️ [任务控制] 任务不存在: {analysis_id}")
                return False
            
            if self._task_states.get(analysis_id) == 'stopped':
                logger.warning(f"⚠️ [任务控制] 任务已停止，无法恢复: {analysis_id}")
                return False
            
            # 清除暂停标志
            self._pause_events[analysis_id].clear()
            self._task_states[analysis_id] = 'running'
            
            # 保存运行状态到文件
            self._save_task_state(analysis_id)
            
            logger.info(f"▶️ [任务控制] 任务已恢复: {analysis_id}")
            return True
    
    def stop_task(self, analysis_id: str) -> bool:
        """停止任务"""
        with self._lock:
            if analysis_id not in self._control_events:
                logger.warning(f"⚠️ [任务控制] 任务不存在: {analysis_id}")
                return False
            
            # 设置停止标志
            self._control_events[analysis_id].set()
            # 如果任务处于暂停状态，也要恢复以便能够检测到停止信号
            if self._pause_events[analysis_id].is_set():
                self._pause_events[analysis_id].clear()
            
            self._task_states[analysis_id] = 'stopped'
            
            # 保存停止状态到文件
            self._save_task_state(analysis_id)
            
            logger.info(f"⏹️ [任务控制] 任务已停止: {analysis_id}")
            return True
    
    def should_stop(self, analysis_id: str) -> bool:
        """检查任务是否应该停止"""
        if analysis_id not in self._control_events:
            return False
        return self._control_events[analysis_id].is_set()
    
    def should_pause(self, analysis_id: str) -> bool:
        """检查任务是否应该暂停"""
        if analysis_id not in self._pause_events:
            return False
        return self._pause_events[analysis_id].is_set()
    
    def wait_if_paused(self, analysis_id: str, check_interval: float = 0.5):
        """如果任务被暂停，则等待直到恢复或停止
        
        Args:
            analysis_id: 任务ID
            check_interval: 检查间隔（秒）
        """
        while self.should_pause(analysis_id):
            # 检查是否被停止
            if self.should_stop(analysis_id):
                logger.info(f"⏹️ [任务控制] 暂停中的任务收到停止信号: {analysis_id}")
                return
            
            # 等待一段时间后再次检查
            time.sleep(check_interval)
    
    def get_task_state(self, analysis_id: str) -> str:
        """获取任务状态"""
        with self._lock:
            return self._task_states.get(analysis_id, 'unknown')
    
    def save_checkpoint(self, analysis_id: str, checkpoint_data: Dict[str, Any]):
        """保存任务检查点"""
        with self._lock:
            self._checkpoints[analysis_id] = checkpoint_data
            
            # 保存到文件
            checkpoint_file = self.checkpoint_dir / f"checkpoint_{analysis_id}.json"
            try:
                with open(checkpoint_file, 'w', encoding='utf-8') as f:
                    json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
                logger.debug(f"💾 [检查点] 保存成功: {analysis_id}")
            except Exception as e:
                logger.error(f"❌ [检查点] 保存失败: {e}")
    
    def load_checkpoint(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """加载任务检查点"""
        # 先从内存加载
        with self._lock:
            if analysis_id in self._checkpoints:
                return self._checkpoints[analysis_id]
        
        # 从文件加载
        checkpoint_file = self.checkpoint_dir / f"checkpoint_{analysis_id}.json"
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)
                
                with self._lock:
                    self._checkpoints[analysis_id] = checkpoint_data
                
                logger.info(f"📂 [检查点] 从文件加载成功: {analysis_id}")
                return checkpoint_data
            except Exception as e:
                logger.error(f"❌ [检查点] 从文件加载失败: {e}")
        
        return None
    
    def _save_task_state(self, analysis_id: str):
        """保存任务状态到文件"""
        state_file = self.checkpoint_dir / f"state_{analysis_id}.json"
        try:
            state_data = {
                'analysis_id': analysis_id,
                'state': self._task_states.get(analysis_id, 'unknown'),
                'is_paused': self._pause_events[analysis_id].is_set() if analysis_id in self._pause_events else False,
                'is_stopped': self._control_events[analysis_id].is_set() if analysis_id in self._control_events else False,
                'timestamp': time.time()
            }
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"💾 [任务状态] 保存成功: {analysis_id} -> {state_data['state']}")
        except Exception as e:
            logger.error(f"❌ [任务状态] 保存失败: {e}")
    
    def load_task_state(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """从文件加载任务状态"""
        state_file = self.checkpoint_dir / f"state_{analysis_id}.json"
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"❌ [任务状态] 从文件加载失败: {e}")
        return None
    
    def get_all_task_states(self) -> Dict[str, str]:
        """获取所有任务状态"""
        with self._lock:
            return self._task_states.copy()
    
    def cleanup_old_checkpoints(self, max_age_hours: int = 24):
        """清理旧的检查点文件"""
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            cleaned = 0
            for file in self.checkpoint_dir.glob("*.json"):
                if file.stat().st_mtime < current_time - max_age_seconds:
                    file.unlink()
                    cleaned += 1
            
            if cleaned > 0:
                logger.info(f"🧹 [清理] 清理了 {cleaned} 个旧检查点文件")
        except Exception as e:
            logger.error(f"❌ [清理] 清理检查点文件失败: {e}")


# 全局任务控制管理器实例
task_control_manager = TaskControlManager()


def register_task(analysis_id: str):
    """注册任务"""
    task_control_manager.register_task(analysis_id)


def unregister_task(analysis_id: str):
    """注销任务"""
    task_control_manager.unregister_task(analysis_id)


def pause_task(analysis_id: str) -> bool:
    """暂停任务"""
    return task_control_manager.pause_task(analysis_id)


def resume_task(analysis_id: str) -> bool:
    """恢复任务"""
    return task_control_manager.resume_task(analysis_id)


def stop_task(analysis_id: str) -> bool:
    """停止任务"""
    return task_control_manager.stop_task(analysis_id)


def should_stop(analysis_id: str) -> bool:
    """检查是否应该停止"""
    return task_control_manager.should_stop(analysis_id)


def should_pause(analysis_id: str) -> bool:
    """检查是否应该暂停"""
    return task_control_manager.should_pause(analysis_id)


def wait_if_paused(analysis_id: str):
    """如果暂停则等待"""
    task_control_manager.wait_if_paused(analysis_id)


def get_task_state(analysis_id: str) -> str:
    """获取任务状态"""
    return task_control_manager.get_task_state(analysis_id)


def save_checkpoint(analysis_id: str, checkpoint_data: Dict[str, Any]):
    """保存检查点"""
    task_control_manager.save_checkpoint(analysis_id, checkpoint_data)


def load_checkpoint(analysis_id: str) -> Optional[Dict[str, Any]]:
    """加载检查点"""
    return task_control_manager.load_checkpoint(analysis_id)

