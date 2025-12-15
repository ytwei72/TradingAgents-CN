# MongoDB 存储模块分析

## ✅ 整合完成

### 整合结果
- ✅ `MongoDBStorage` 已删除，功能已整合到 `ModelUsageManager`
- ✅ `UsageRecord` 类已移至 `model_usage_manager.py`
- ✅ 统一使用 `model_usages` 集合
- ✅ 所有模块已统一使用 `storage.manager.get_mongodb_db()` 获取数据库对象
- ✅ 已移除所有直接连接的回退逻辑

### ModelUsageManager (`model_usage_manager.py`)
- **集合名**: `model_usages`
- **功能**: 完整的 CRUD 管理器
- **主要方法**:
  - `insert_usage_record()` - 插入单个记录（返回ID）
  - `save_usage_record()` - 保存单个记录（兼容接口）
  - `insert_many_usage_records()` - 批量插入
  - `update_usage_record()` - 更新记录
  - `query_usage_records()` - 高级查询（支持多条件过滤）
  - `load_usage_records()` - 加载记录（兼容接口）
  - `get_usage_statistics()` - 详细统计（支持过滤）
  - `get_provider_statistics()` - 供应商统计
  - `get_model_statistics()` - 模型统计
  - `count_records()` - 记录计数
  - `delete_old_records()` - 删除旧记录
  - `cleanup_old_records()` - 清理旧记录（兼容接口）
  - `get_usage_by_session_id()` - 按会话ID查询

### 连接管理
- 所有模块使用 `tradingagents.storage.manager.get_mongodb_db()` 获取数据库对象
- 不再需要手动管理连接字符串和客户端
- 连接由统一的 `DatabaseManager` 管理

## 当前状态

- ✅ 所有模块已统一使用 `storage.manager` 进行连接管理
- ✅ 已移除所有直接连接的回退逻辑
- ✅ 模块整合完成，代码更简洁

