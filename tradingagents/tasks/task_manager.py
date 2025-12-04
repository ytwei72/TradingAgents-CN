"""
任务管理器模块
负责任务的创建、执行和生命周期管理
"""
import json
import os
import time
import threading
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from tradingagents.utils.logging_manager import get_logger
from tradingagents.tasks.task_state_machine import TaskStateMachine, TaskStatus
from tradingagents.utils.analysis_runner import run_stock_analysis

logger = get_logger('task_manager')

class AnalysisTask(threading.Thread):
    """分析任务线程包装类"""
    
    def __init__(self, task_id: str, params: Dict[str, Any]):
        super().__init__(name=f"AnalysisTask-{task_id}")
        self.task_id = task_id
        self.params = params
        self.state_machine = TaskStateMachine(task_id)
        self._stop_event = threading.Event()
        
        # 在初始化时立即创建任务状态
        self.state_machine.initialize(self.params)
        
    def run(self):
        """执行任务逻辑"""
        logger.info(f"🚀 [任务启动] 开始执行任务: {self.task_id}")
        
        try:
            # 更新状态为运行中
            self.state_machine.update_state({
                'status': TaskStatus.RUNNING.value,
                'progress': {
                    'current_step': 0,
                    'total_steps': 0,
                    'percentage': 0.0,
                    'message': '分析任务开始执行',
                },
            })
            
            # 定义进度回调
            def progress_callback(message, step=None, total_steps=None):
                self.state_machine.update_state({
                    'progress': {
                        'current_step': step if step is not None else 0,
                        'total_steps': total_steps if total_steps is not None else 0,
                        'percentage': (step / total_steps * 100) if (step and total_steps) else 0,
                        'message': message,
                    },
                })

            # 准备参数
            stock_symbol = self.params.get('stock_symbol')
            market_type = self.params.get('market_type', '美股')
            analysis_date = self.params.get('analysis_date')
            analysts = self.params.get('analysts', [])
            research_depth = self.params.get('research_depth', 3)
            extra_config = self.params.get('extra_config') or {}
            
            llm_provider = extra_config.get('llm_provider', "dashscope")
            llm_model = extra_config.get('llm_model', "qwen-max")

            if not analysis_date:
                analysis_date = datetime.now().strftime('%Y-%m-%d')

            # 执行分析
            results = run_stock_analysis(
                stock_symbol=stock_symbol,
                analysis_date=analysis_date,
                analysts=analysts,
                research_depth=research_depth,
                llm_provider=llm_provider,
                llm_model=llm_model,
                market_type=market_type,
                progress_callback=progress_callback,
                analysis_id=self.task_id
            )
            
            # 检查结果
            if results.get('success', False):
                self.state_machine.update_state({
                    'status': TaskStatus.COMPLETED.value,
                    'result': results,
                    'progress': {
                        'percentage': 100.0,
                        'message': '分析任务已完成',
                    },
                })
            else:
                # 失败
                error_msg = results.get('error', 'Unknown error')
                self.state_machine.update_state({
                    'status': TaskStatus.FAILED.value,
                    'error': error_msg,
                })

        except Exception as e:
            logger.error(f"❌ [任务失败] 任务执行异常: {self.task_id}, {e}", exc_info=True)
            self.state_machine.update_state({
                'status': TaskStatus.FAILED.value,
                'error': str(e),
            })
        finally:
            logger.info(f"🏁 [任务结束] 任务线程退出: {self.task_id}")


class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, AnalysisTask] = {}
        # TaskManager 不再持有 state_machine 实例
        
        # 任务控制相关状态
        self._control_events: Dict[str, threading.Event] = {}  # 停止事件
        self._pause_events: Dict[str, threading.Event] = {}    # 暂停事件
        self._task_states: Dict[str, str] = {}                 # 任务状态: running/paused/stopped
        self._checkpoints: Dict[str, Any] = {}                 # 任务检查点
        self._lock = threading.Lock()
        
        # 持久化目录
        self.checkpoint_dir = Path("./data/checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
    def start_task(self, params: Dict[str, Any]) -> str:
        """启动新任务"""
        # 生成 ID
        task_id = str(uuid.uuid4())
        params['task_id'] = task_id
        
        # 注册任务控制(原 register_task 逻辑)
        with self._lock:
            # 创建停止事件(未设置表示继续运行)
            self._control_events[task_id] = threading.Event()
            # 创建暂停事件(未设置表示正常运行,设置表示暂停)
            self._pause_events[task_id] = threading.Event()
            # 初始状态为运行中
            self._task_states[task_id] = 'running'
            logger.info(f"📋 [任务控制] 注册任务: {task_id}")
        
        # 创建并启动任务(AnalysisTask 负责在状态机中创建记录)
        task = AnalysisTask(task_id, params)
        self.tasks[task_id] = task
        task.start()
        
        return task_id
    

        
    def stop_task(self, task_id: str) -> bool:
        """停止任务"""
        with self._lock:
            if task_id not in self._control_events:
                logger.warning(f"⚠️ [任务控制] 任务不存在: {task_id}")
                return False
            
            # 设置停止标志
            self._control_events[task_id].set()
            # 如果任务处于暂停状态，也要恢复以便能够检测到停止信号
            if self._pause_events[task_id].is_set():
                self._pause_events[task_id].clear()
            
            self._task_states[task_id] = 'stopped'
            
            # 保存停止状态到文件
            self._save_task_state(task_id)
            
            logger.info(f"⏹️ [任务控制] 任务已停止: {task_id}")
            success = True
        
        # 更新状态机
        if success:
            self._get_task_state_machine(task_id).update_state({
                'status': TaskStatus.STOPPED.value,
                'progress': {'message': '任务已停止'}
            })
        
        # 注销任务控制（原 unregister_task 逻辑）
        with self._lock:
            if task_id in self._control_events:
                del self._control_events[task_id]
            if task_id in self._pause_events:
                del self._pause_events[task_id]
            if task_id in self._task_states:
                del self._task_states[task_id]
            if task_id in self._checkpoints:
                del self._checkpoints[task_id]
            logger.info(f"📋 [任务控制] 注销任务: {task_id}")
            
        return success

    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        with self._lock:
            if task_id not in self._pause_events:
                logger.warning(f"⚠️ [任务控制] 任务不存在: {task_id}")
                return False
            
            if self._task_states.get(task_id) == 'stopped':
                logger.warning(f"⚠️ [任务控制] 任务已停止，无法暂停: {task_id}")
                return False
            
            # 设置暂停标志
            self._pause_events[task_id].set()
            self._task_states[task_id] = 'paused'
            
            # 保存暂停状态到文件
            self._save_task_state(task_id)
            
            logger.info(f"⏸️ [任务控制] 任务已暂停: {task_id}")
            success = True

        if success:
            self._get_task_state_machine(task_id).update_state({
                'status': TaskStatus.PAUSED.value,
                'progress': {'message': '任务已暂停'}
            })
        return success

    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        with self._lock:
            if task_id not in self._pause_events:
                logger.warning(f"⚠️ [任务控制] 任务不存在: {task_id}")
                return False
            
            if self._task_states.get(task_id) == 'stopped':
                logger.warning(f"⚠️ [任务控制] 任务已停止，无法恢复: {task_id}")
                return False
            
            # 清除暂停标志
            self._pause_events[task_id].clear()
            self._task_states[task_id] = 'running'
            
            # 保存运行状态到文件
            self._save_task_state(task_id)
            
            logger.info(f"▶️ [任务控制] 任务已恢复: {task_id}")
            success = True

        if success:
            self._get_task_state_machine(task_id).update_state({
                'status': TaskStatus.RUNNING.value,
                'progress': {'message': '任务已恢复'}
            })
        return success
        
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return self._get_task_state_machine(task_id).get_current_state()

    def get_task_history(self, task_id: str) -> List[Dict[str, Any]]:
        """获取任务历史"""
        return self._get_task_state_machine(task_id).get_history_states()
    
    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务结果"""
        state = self.get_task_status(task_id)
        if state and state.get('status') == TaskStatus.COMPLETED.value:
            return state.get('result')
        return None

    def _get_task_state_machine(self, task_id: str) -> TaskStateMachine:
        """获取任务状态机实例"""
        if task_id in self.tasks:
            return self.tasks[task_id].state_machine
        return TaskStateMachine(task_id)

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
    
    def get_task_control_state(self, analysis_id: str) -> str:
        """获取任务控制状态"""
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


# 全局单例
_task_manager = None

def get_task_manager() -> TaskManager:
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
