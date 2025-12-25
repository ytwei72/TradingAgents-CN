# Migrations 工具说明文档

本目录包含用于数据迁移、数据补充和系统维护的各种工具脚本。这些工具主要用于将历史数据从文件系统迁移到 MongoDB，以及维护和更新数据库中的数据。

## 目录

- [数据迁移工具](#数据迁移工具)
- [数据补充工具](#数据补充工具)
- [数据维护工具](#数据维护工具)
- [使用说明](#使用说明)

---

## 数据迁移工具

### 1. migrate_eval_results.py

**功能**：将 `eval_results` 目录中的历史步骤数据迁移到 MongoDB

**主要作用**：
- 遍历 `eval_results` 目录下所有股票的日期目录
- 读取每个日期的 `all_steps.json` 文件
- 提取最后一个 step 的数据
- 保存到 MongoDB 的 `analysis_steps_status` 集合
- 每只股票的每天只保存一条记录（使用 upsert）

**使用方法**：
```bash
python -m tradingagents.storage.migrations.migrate_eval_results
python -m tradingagents.storage.migrations.migrate_eval_results --eval-results-dir eval_results --dry-run
```

**参数说明**：
- `--eval-results-dir`: eval_results 目录路径（默认: eval_results）
- `--dry-run`: 只扫描文件，不实际保存到 MongoDB

---

### 2. migrate_logs.py

**功能**：将 `logs` 目录下的结构化日志文件迁移到 MongoDB

**主要作用**：
- 遍历 `logs` 目录下所有 `tradingagents_structured.log*` 文件（包括轮转文件）
- 读取每行的 JSON 格式日志
- 清理 ANSI 颜色代码
- 保存到 MongoDB 的 `trading_agents_logs` 集合
- 支持去重（基于 timestamp + logger + message 的组合）
- 批量插入以提高性能

**使用方法**：
```bash
# 使用默认批量大小（1000），包含所有日志文件（包括轮转文件）
python -m tradingagents.storage.migrations.migrate_logs

# 自定义批量大小
python -m tradingagents.storage.migrations.migrate_logs --batch-size 5000

# 不包含轮转文件，只处理主日志文件
python -m tradingagents.storage.migrations.migrate_logs --no-rotated

# 不跳过重复条目
python -m tradingagents.storage.migrations.migrate_logs --no-skip-duplicates

# 只扫描文件，不实际保存
python -m tradingagents.storage.migrations.migrate_logs --dry-run
```

**参数说明**：
- `--logs-dir`: logs 目录路径（默认: logs）
- `--batch-size`: 批量插入的大小（默认: 1000）
- `--no-rotated`: 不包含轮转文件（.log.1, .log.2 等）
- `--no-skip-duplicates`: 不跳过重复条目（默认会跳过重复）
- `--dry-run`: 只扫描文件，不实际保存到 MongoDB

---

### 3. migrate_task_state_to_mongo.py

**功能**：将 Redis 中的任务状态数据迁移到 MongoDB

**主要作用**：
- 扫描 Redis 中所有 `task:*:props` 和 `task:*:current_step` 键
- 读取 Redis 中的任务状态数据
- 迁移到 MongoDB 的 `tasks_state_machine` 集合
- 支持批量处理

**使用方法**：
```bash
python -m tradingagents.storage.migrations.migrate_task_state_to_mongo
```

**注意事项**：
- 需要确保 Redis 和 MongoDB 都已连接
- 迁移完成后，Redis 中的数据仍然保留（如需删除请手动操作）

---

### 4. migrate_usage_json.py

**功能**：将 `config/usage.json` 文件中的使用记录迁移到 MongoDB

**主要作用**：
- 读取 `config/usage.json` 文件
- 将数据迁移到 MongoDB 的 `model_usages` 集合
- 支持增量迁移（跳过已存在的记录）
- 支持验证迁移结果

**使用方法**：
```bash
# 执行迁移
python -m tradingagents.storage.migrations.migrate_usage_json

# 指定 JSON 文件路径
python -m tradingagents.storage.migrations.migrate_usage_json --json-path config/usage-1204.json

# 不跳过已存在的记录
python -m tradingagents.storage.migrations.migrate_usage_json --no-skip-existing

# 不备份原文件
python -m tradingagents.storage.migrations.migrate_usage_json --no-backup

# 仅验证迁移结果，不执行迁移
python -m tradingagents.storage.migrations.migrate_usage_json --verify
```

**参数说明**：
- `--json-path`: usage.json 文件路径（默认: config/usage.json）
- `--no-skip-existing`: 不跳过已存在的记录（默认跳过）
- `--no-backup`: 不备份原文件（默认备份）
- `--verify`: 仅验证迁移结果，不执行迁移

---

### 5. redis_cache_copy.py

**功能**：从源 Redis 数据库复制缓存数据到目标 Redis 数据库

**主要作用**：
- 连接源 Redis 和目标 Redis 服务器
- 扫描匹配模式的键
- 复制键及其数据（支持 string、hash、list、set、zset 等类型）
- 保留 TTL（过期时间）
- 支持数据验证

**使用方法**：
```bash
python -m tradingagents.storage.migrations.redis_cache_copy
```

**配置说明**：
在使用前，需要修改脚本中的配置区域：
- `SOURCE_REDIS_CONFIG`: 源 Redis 配置（主机、端口、密码、数据库编号）
- `TARGET_REDIS_CONFIG`: 目标 Redis 配置
- `COPY_OPTIONS`: 复制选项（模式、批量大小、是否覆盖、是否保留 TTL、是否验证）

**注意事项**：
- 脚本中包含敏感信息（密码、IP 地址），请谨慎使用
- 复制前会要求用户确认操作

---

## 数据补充工具

### 6. supplement_company_name.py

**功能**：为任务状态机数据补充 `company_name` 字段

**主要作用**：
- 查询所有 `props` 子状态的记录
- 根据 `stock_symbol` 查询公司名称
- 补充 `params.company_name` 字段
- 支持批量处理和 dry run 模式

**使用方法**：
```bash
# 补充所有任务的数据
python -m tradingagents.storage.migrations.supplement_company_name

# 补充指定任务的数据
python -m tradingagents.storage.migrations.supplement_company_name --task-id <task_id>

# dry run 模式，只检查不更新
python -m tradingagents.storage.migrations.supplement_company_name --dry-run
```

**参数说明**：
- `--task-id`: 补充指定任务的数据（如果不指定，则补充所有任务）
- `--dry-run`: dry run 模式，只检查不更新

---

## 数据维护工具

### 7. sector_update_task.py

**功能**：更新行业板块和概念板块信息

**主要作用**：
- 获取并保存行业板块列表
- 为每个行业板块获取并保存股票列表
- 获取并保存概念板块列表
- 为每个概念板块获取并保存股票列表
- 使用延迟机制避免请求过于频繁

**使用方法**：
```bash
python -m tradingagents.storage.migrations.sector_update_task
```

**注意事项**：
- 脚本中包含从特定板块开始更新的逻辑（用于解决封 IP 问题）
- 需要确保 MongoDB 连接正常

---

### 8. stock_sector_helper.py

**功能**：股票板块辅助工具类

**主要作用**：
- 获取行业板块列表和概念板块列表
- 获取指定板块下的股票列表
- 保存板块信息到 MongoDB
- 从 MongoDB 读取板块信息

**主要方法**：
- `fetch_industry_sector_list()`: 获取行业板块列表
- `fetch_concept_sector_list()`: 获取概念板块列表
- `fetch_stocks_in_industry_sector(sector_name)`: 获取行业板块下的股票
- `fetch_stocks_in_concept_sector(sector_name)`: 获取概念板块下的股票
- `save_sectors(sector_category, sector_list)`: 保存板块列表
- `save_stocks_in_sector(sector_category, sector_name, stock_list)`: 保存板块股票列表
- `get_sectors(sector_category)`: 从数据库读取板块列表
- `get_stocks_in_sectors(sector_names, sector_category)`: 从数据库读取板块股票列表

**使用场景**：
- 通常被 `sector_update_task.py` 调用
- 也可以在其他脚本中导入使用

---

## 使用说明

### 通用注意事项

1. **连接检查**：所有工具在运行前都会检查必要的连接（MongoDB、Redis 等），请确保相关服务已启动

2. **Dry Run 模式**：大部分迁移工具支持 `--dry-run` 参数，建议先使用此模式检查将要执行的操作

3. **备份数据**：在执行迁移操作前，建议备份相关数据

4. **日志输出**：所有工具都会输出详细的日志信息，包括成功、失败、跳过的记录数量

5. **批量处理**：大部分工具支持批量处理，可以通过参数调整批量大小以优化性能

### 执行顺序建议

如果需要执行多个迁移操作，建议按以下顺序：

1. 首先迁移任务状态数据：`migrate_task_state_to_mongo.py`
2. 补充任务数据：`supplement_company_name.py`
3. 迁移评估结果：`migrate_eval_results.py`
4. 迁移日志：`migrate_logs.py`
5. 迁移使用记录：`migrate_usage_json.py`

### 故障排查

如果遇到问题：

1. 检查 MongoDB 和 Redis 连接是否正常
2. 查看工具输出的错误日志
3. 使用 `--dry-run` 模式检查数据
4. 检查文件路径和权限
5. 确认数据库集合是否存在

---

## 更新日志

- 初始版本：包含所有基础迁移和维护工具
- 各工具的具体更新历史请查看对应文件的注释和文档字符串

