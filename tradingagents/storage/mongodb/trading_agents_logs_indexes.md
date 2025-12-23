# trading_agents_logs 集合索引创建语句

根据 `SystemLogsManager._create_indexes()` 方法生成的 MongoDB 索引创建语句。

## MongoDB Shell 命令

```javascript
// 切换到目标数据库（根据实际情况修改数据库名）
use tradingagents;

// 1. 复合索引：用于去重查询（timestamp + logger + message）
db.trading_agents_logs.createIndex(
    { "timestamp": 1, "logger": 1, "message": 1 },
    { background: true, name: "timestamp_logger_message_idx" }
);

// 2. 时间索引：用于时间范围查询（按时间倒序）
db.trading_agents_logs.createIndex(
    { "timestamp": -1 },
    { background: true, name: "timestamp_idx" }
);

// 3. Logger 索引：用于按日志器查询
db.trading_agents_logs.createIndex(
    { "logger": 1 },
    { background: true, name: "logger_idx" }
);

// 4. Level 索引：用于按日志级别查询
db.trading_agents_logs.createIndex(
    { "level": 1 },
    { background: true, name: "level_idx" }
);
```

## 索引说明

| 索引名称 | 字段 | 排序 | 用途 |
|---------|------|------|------|
| `timestamp_logger_message_idx` | timestamp, logger, message | 1, 1, 1 | 去重查询（基于三个字段的唯一性） |
| `timestamp_idx` | timestamp | -1 | 时间范围查询，按时间倒序排序 |
| `logger_idx` | logger | 1 | 按日志器名称过滤 |
| `level_idx` | level | 1 | 按日志级别过滤 |

## 查看索引

```javascript
// 查看所有索引
db.trading_agents_logs.getIndexes();

// 查看索引统计信息
db.trading_agents_logs.aggregate([{ $indexStats: {} }]);
```

## 删除索引（如果需要）

```javascript
// 删除指定索引
db.trading_agents_logs.dropIndex("timestamp_logger_message_idx");
db.trading_agents_logs.dropIndex("timestamp_idx");
db.trading_agents_logs.dropIndex("logger_idx");
db.trading_agents_logs.dropIndex("level_idx");

// 删除所有索引（保留 _id_ 索引）
db.trading_agents_logs.dropIndexes();
```

## 注意事项

1. **background: true**：索引在后台创建，不会阻塞数据库操作
2. **索引名称**：使用有意义的名称便于管理和维护
3. **复合索引顺序**：复合索引的字段顺序很重要，查询条件应尽量匹配索引的前缀
4. **索引维护**：索引会占用存储空间并影响写入性能，需要根据实际使用情况调整

