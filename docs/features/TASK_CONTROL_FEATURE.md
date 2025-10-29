# 任务控制功能说明文档

## 📋 功能概述

本文档描述了TradingAgents系统中新增的**任务暂停、继续和停止**功能。该功能允许用户在分析任务执行过程中进行精细化控制。

## ✨ 核心功能

### 1. 任务暂停 (⏸️ Pause)
- **功能描述**: 暂时挂起正在执行的分析任务
- **应用场景**: 
  - 需要临时释放系统资源
  - 等待更多数据或信息
  - 暂时不需要分析结果
- **技术实现**: 使用 `threading.Event` 实现线程暂停机制
- **状态保持**: 暂停期间保留所有分析状态和进度

### 2. 任务继续 (▶️ Resume)
- **功能描述**: 恢复已暂停的分析任务
- **应用场景**: 准备好继续分析时恢复执行
- **技术实现**: 清除暂停标志，任务自动从暂停点继续
- **时间统计**: 自动排除暂停时长，计算有效执行时间

### 3. 任务停止 (⏹️ Stop)
- **功能描述**: 完全终止正在执行的分析任务
- **应用场景**:
  - 不再需要分析结果
  - 发现分析参数错误
  - 需要释放资源执行其他任务
- **技术实现**: 设置停止标志，任务检测后优雅退出
- **资源清理**: 自动清理线程、任务控制状态和临时数据

## 🏗️ 架构设计

### 核心组件

#### 1. TaskControlManager (任务控制管理器)
- **文件位置**: `web/utils/task_control_manager.py`
- **主要职责**:
  - 管理任务的暂停/恢复/停止状态
  - 维护任务控制事件 (threading.Event)
  - 保存和加载任务检查点
  - 持久化任务状态到文件

- **关键方法**:
  ```python
  register_task(analysis_id)      # 注册任务
  pause_task(analysis_id)          # 暂停任务
  resume_task(analysis_id)         # 恢复任务
  stop_task(analysis_id)           # 停止任务
  should_pause(analysis_id)        # 检查是否应该暂停
  should_stop(analysis_id)         # 检查是否应该停止
  wait_if_paused(analysis_id)      # 如果暂停则等待
  ```

#### 2. ThreadTracker (线程跟踪器)
- **文件位置**: `web/utils/thread_tracker.py`
- **增强功能**:
  - 注册分析线程和停止事件
  - 跟踪线程存活状态
  - 支持线程停止请求
  - 提供线程信息查询

- **关键改进**:
  ```python
  # 支持停止事件注册
  register_analysis_thread(analysis_id, thread, stop_event)
  
  # 请求停止线程
  request_stop_thread(analysis_id)
  
  # 检查分析状态（包含暂停/停止状态）
  check_analysis_status(analysis_id)  # 返回: running/paused/stopped/completed/failed
  ```

#### 3. AsyncProgressTracker (异步进度跟踪器)
- **文件位置**: `web/utils/async_progress_tracker.py`
- **新增功能**:
  - 支持暂停/恢复/停止状态标记
  - 计算有效执行时间（排除暂停时长）
  - 持久化控制状态

- **新增方法**:
  ```python
  mark_paused()                    # 标记任务暂停
  mark_resumed()                   # 标记任务恢复
  mark_stopped(message)            # 标记任务停止
  get_effective_elapsed_time()     # 获取有效执行时间
  ```

- **时间统计**:
  - `total_pause_duration`: 累计暂停时长
  - `pause_start_time`: 当前暂停开始时间
  - `effective_time = total_time - pause_duration`: 有效执行时间

#### 4. LangGraph Checkpointer (检查点支持)
- **文件位置**: `tradingagents/graph/setup.py`
- **功能**: 
  - 集成 LangGraph MemorySaver 检查点机制
  - 支持工作流状态快照
  - 为未来的断点续传功能预留接口

- **配置启用**:
  ```python
  config = {
      "enable_checkpointer": True,  # 启用检查点
      ...
  }
  ```

### 数据流

```
用户操作 (UI按钮)
    ↓
TaskControlManager (设置控制标志)
    ↓
analysis_runner.py (检查控制信号)
    ↓
check_task_control() (检查暂停/停止)
    ↓
wait_if_paused() (如果暂停则等待)
    ↓
继续执行 / 停止任务
    ↓
AsyncProgressTracker (更新状态和时间)
    ↓
UI显示更新
```

## 🖥️ 用户界面

### 任务控制按钮

在Web界面的"股票分析"区域，根据任务状态显示不同的控制按钮：

#### 运行中状态 (Running)
```
┌─────────────────┐
│  ⏸️ 暂停        │
├─────────────────┤
│  ⏹️ 停止        │
└─────────────────┘
```

#### 暂停状态 (Paused)
```
┌─────────────────┐
│  ▶️ 继续        │
├─────────────────┤
│  ⏹️ 停止        │
└─────────────────┘
```

#### 完成/失败/停止状态
- 不显示控制按钮

### 状态显示

- 🔄 **正在分析**: 任务运行中
- ⏸️ **分析已暂停**: 任务已暂停
- ⏹️ **分析已停止**: 任务已停止
- ✅ **分析完成**: 任务成功完成
- ❌ **分析失败**: 任务执行失败

## 📝 使用示例

### 1. 启动分析任务
```python
# 任务自动注册控制管理器
from web.utils.task_control_manager import register_task
register_task(analysis_id)
```

### 2. 暂停正在运行的任务
```python
from web.utils.task_control_manager import pause_task

if pause_task(analysis_id):
    print("任务已暂停")
```

### 3. 恢复暂停的任务
```python
from web.utils.task_control_manager import resume_task

if resume_task(analysis_id):
    print("任务已恢复")
```

### 4. 停止任务
```python
from web.utils.task_control_manager import stop_task

if stop_task(analysis_id):
    print("任务已停止")
```

### 5. 在分析代码中检查控制信号
```python
from web.utils.task_control_manager import should_stop, wait_if_paused

# 在分析循环中
for step in analysis_steps:
    # 检查并等待暂停
    wait_if_paused(analysis_id)
    
    # 检查停止信号
    if should_stop(analysis_id):
        print("收到停止信号，退出分析")
        break
    
    # 执行分析步骤
    perform_analysis_step(step)
```

## 🔧 技术细节

### 线程安全

所有任务控制操作都使用线程锁 (`threading.Lock`) 保护：
```python
with self._lock:
    self._control_events[analysis_id].set()
    self._task_states[analysis_id] = 'stopped'
```

### 状态持久化

任务状态自动保存到文件系统：
```python
# 检查点目录
./data/checkpoints/
    ├── checkpoint_{analysis_id}.json  # 分析检查点
    └── state_{analysis_id}.json       # 任务状态
```

### 时间统计逻辑

```python
# 总时长
total_time = current_time - start_time

# 当前暂停时长（如果正在暂停）
current_pause = current_time - pause_start_time if paused else 0

# 有效时长
effective_time = total_time - total_pause_duration - current_pause
```

## ⚡ 性能考虑

### 1. 检查点频率
- 建议在关键步骤保存检查点
- 避免过于频繁的检查点保存影响性能

### 2. 控制信号检查
- 在分析循环的合适位置检查控制信号
- 推荐在每个主要步骤开始前检查
- 避免在紧密循环中频繁检查

### 3. 资源清理
- 任务完成/停止后自动清理资源
- 定期清理旧的检查点文件（默认24小时）

```python
# 自动清理
task_control_manager.cleanup_old_checkpoints(max_age_hours=24)
```

## 🧪 测试

### 运行测试
```bash
python tests/test_task_control.py
```

### 测试覆盖
- ✅ 任务注册和状态管理
- ✅ 任务暂停功能
- ✅ 任务恢复功能
- ✅ 任务停止功能
- ✅ 暂停时长统计
- ✅ 有效时间计算
- ✅ 检查点保存和加载
- ✅ 线程控制集成

### 测试结果
所有测试均已通过，验证了功能的完整性和稳定性。

## 📊 状态流转图

```
        ┌─────────┐
        │  创建   │
        └────┬────┘
             │
             ▼
        ┌─────────┐
    ┌──▶│ Running │◀──┐
    │   └────┬────┘   │
    │        │         │
    │resume  │pause    │
    │        ▼         │
    │   ┌─────────┐   │
    └───│ Paused  │───┘
        └────┬────┘
             │stop
             ▼
        ┌─────────┐
        │ Stopped │
        └─────────┘
        
        ┌─────────┐
        │Completed│ (自然完成)
        └─────────┘
        
        ┌─────────┐
        │ Failed  │ (异常失败)
        └─────────┘
```

## 🔐 安全性

### 1. 权限控制
- 目前所有用户都可以控制任务
- 未来可添加用户权限验证

### 2. 状态验证
- 停止的任务无法暂停或恢复
- 未注册的任务无法控制

### 3. 资源保护
- 自动清理已终止的任务资源
- 防止资源泄漏

## 🚀 未来改进

### 短期计划
- [ ] 添加任务优先级管理
- [ ] 支持批量任务控制
- [ ] 增强检查点功能（断点续传）

### 长期计划
- [ ] 分布式任务调度
- [ ] 任务队列管理
- [ ] 更细粒度的进度控制

## 📚 相关文档

- [AsyncProgressTracker 使用指南](../technical/async_progress_tracker.md)
- [ThreadTracker 文档](../technical/thread_tracker.md)
- [LangGraph 集成说明](../architecture/langgraph_integration.md)

## 🤝 贡献

如需改进任务控制功能，请：
1. 创建feature分支
2. 添加相应的测试用例
3. 更新本文档
4. 提交Pull Request

## 📞 支持

如遇到任务控制相关问题，请：
- 查看日志文件中的 `[任务控制]` 标记
- 运行测试脚本 `tests/test_task_control.py`
- 检查 `./data/checkpoints/` 目录下的状态文件

---

**版本**: 1.0.0  
**最后更新**: 2025-10-28  
**作者**: TradingAgents Team

