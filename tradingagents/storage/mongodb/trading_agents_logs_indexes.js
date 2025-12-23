// MongoDB 索引创建脚本
// 用于 trading_agents_logs 集合
// 根据 SystemLogsManager._create_indexes() 方法生成

// 切换到目标数据库（根据实际情况修改数据库名）
// use tradingagents;

// 1. 创建复合索引用于去重查询
// 索引字段：timestamp (升序), logger (升序), message (升序)
// 用途：用于基于 timestamp + logger + message 的去重查询
db.trading_agents_logs.createIndex(
    { "timestamp": 1, "logger": 1, "message": 1 },
    { 
        background: true,
        name: "timestamp_logger_message_idx"
    }
);

// 2. 创建时间索引用于时间范围查询
// 索引字段：timestamp (降序)
// 用途：用于按时间倒序查询日志（最新的在前）
db.trading_agents_logs.createIndex(
    { "timestamp": -1 },
    { 
        background: true,
        name: "timestamp_idx"
    }
);

// 3. 创建 logger 索引用于按日志器查询
// 索引字段：logger (升序)
// 用途：用于按 logger 名称过滤查询
db.trading_agents_logs.createIndex(
    { "logger": 1 },
    { 
        background: true,
        name: "logger_idx"
    }
);

// 4. 创建 level 索引用于按级别查询
// 索引字段：level (升序)
// 用途：用于按日志级别（INFO, WARNING, ERROR等）过滤查询
db.trading_agents_logs.createIndex(
    { "level": 1 },
    { 
        background: true,
        name: "level_idx"
    }
);

// 查看所有索引
db.trading_agents_logs.getIndexes();

