# APEX系统API接口手册

## 概述

本文档详细说明了APEX投研智能体系统的所有后端API接口。系统基于FastAPI构建，提供RESTful风格的API服务。

**基础URL**: `http://localhost:8000`

**API版本**: v1.0

---

## 目录

- [1. 健康检查接口](#1-健康检查接口)
- [2. 分析任务接口](#2-分析任务接口)
  - [2.1 启动分析任务](#21-启动分析任务)
  - [2.2 查询任务状态](#22-查询任务状态)
  - [2.3 获取分析结果](#23-获取分析结果)
  - [2.4 暂停任务](#24-暂停任务)
  - [2.5 恢复任务](#25-恢复任务)
  - [2.6 停止任务](#26-停止任务)

---

## 1. 健康检查接口

### 1.1 系统健康检查

**接口描述**: 检查系统运行状态

**请求方式**: `GET`

**接口路径**: `/api/health`

**请求参数**: 无

**响应示例**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": 1700000000
}
```

**响应字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| status | string | 系统状态，固定值 "healthy" |
| version | string | 系统版本号 |
| timestamp | integer | Unix时间戳 |

---

## 2. 分析任务接口

### 2.1 启动分析任务

**接口描述**: 创建并启动一个新的股票分析任务

**请求方式**: `POST`

**接口路径**: `/api/analysis/start`

**请求头**:
```
Content-Type: application/json
```

**请求参数**:
```json
{
  "stock_symbol": "AAPL",
  "market_type": "美股",
  "analysis_date": "2024-01-01",
  "analysts": ["market", "fundamentals"],
  "research_depth": 3,
  "include_sentiment": true,
  "include_risk_assessment": true,
  "custom_prompt": "重点关注技术面分析",
  "extra_config": {
    "llm_provider": "dashscope",
    "llm_model": "qwen-max",
    "cache_reuse_mode": "true",
    "cache_reuse_sleep_min": 2.0,
    "cache_reuse_sleep_max": 10.0
  }
}
```

**请求字段说明**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| stock_symbol | string | 是 | 股票代码，如 "AAPL"、"000001" |
| market_type | string | 是 | 市场类型，可选值："美股"、"A股"、"港股" |
| analysis_date | string | 否 | 分析日期，格式 YYYY-MM-DD，默认为当前日期 |
| analysts | array[string] | 是 | 分析师列表，可选值："market"、"fundamentals"、"news"、"social" |
| research_depth | integer | 是 | 研究深度，范围 1-5 |
| include_sentiment | boolean | 否 | 是否包含情绪分析，默认 true |
| include_risk_assessment | boolean | 否 | 是否包含风险评估，默认 true |
| custom_prompt | string | 否 | 自定义分析提示词 |
| extra_config | object | 否 | 额外配置参数 |

**extra_config 结果复用配置**:

| 参数 | 类型 | 说明 |
|------|------|------|
| cache_reuse_mode | string | 结果复用模式：`false`（禁用）、`true`（全部启用）、或节点列表如 `"market,fundamentals"` |
| cache_reuse_sleep_min | number | 结果复用模拟延迟最小值（秒），默认 2.0 |
| cache_reuse_sleep_max | number | 结果复用模拟延迟最大值（秒），默认 10.0 |

**结果复用说明**: 当分析任务的参数（股票代码、分析日期、研究深度、分析师团队、市场类型）都相同时，系统可以从数据库缓存中读取历史分析结果，避免重复计算。配置优先级：`extra_config` > 环境变量 `CACHE_REUSE_*` > 环境变量 `MOCK_*`（向后兼容）。

**响应示例**:
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Analysis task started"
}
```

**响应字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| analysis_id | string | 任务唯一标识符（UUID格式） |
| status | string | 任务状态："pending" |
| message | string | 响应消息 |

---

### 2.2 查询任务状态

**接口描述**: 查询指定分析任务的当前状态和进度

**请求方式**: `GET`

**接口路径**: `/api/analysis/{analysis_id}/status`

**路径参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| analysis_id | string | 任务ID |

**响应示例**:
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "current_message": "正在执行市场分析...",
  "progress_log": [
    {
      "message": "开始分析",
      "step": 1,
      "total_steps": 5,
      "timestamp": "2024-01-01T10:00:00"
    }
  ],
  "error": null
}
```

**响应字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| analysis_id | string | 任务ID |
| status | string | 任务状态："pending"、"running"、"paused"、"completed"、"failed"、"stopped" |
| current_message | string | 当前进度消息 |
| progress_log | array | 进度日志（最近5条） |
| error | string/null | 错误信息（如果有） |

---

### 2.3 获取分析结果

**接口描述**: 获取已完成任务的分析结果

**请求方式**: `GET`

**接口路径**: `/api/analysis/{analysis_id}/result`

**路径参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| analysis_id | string | 任务ID |

**响应示例**:
```json
{
  "stock_symbol": "AAPL",
  "analysis_date": "2024-01-01",
  "decision": {
    "action": "买入",
    "confidence": 0.85,
    "reasoning": "技术面和基本面均显示积极信号..."
  },
  "state": {
    "market_report": "市场分析报告内容...",
    "fundamentals_report": "基本面分析报告内容...",
    "news_report": "新闻分析报告内容...",
    "sentiment_report": "情绪分析报告内容...",
    "risk_assessment": "风险评估报告内容...",
    "investment_plan": "投资计划内容..."
  }
}
```

**注意事项**:
- 只有状态为 "completed" 的任务才能获取结果
- 如果任务未完成，将返回 400 错误

---

### 2.4 暂停任务

**接口描述**: 暂停正在运行的分析任务

**请求方式**: `POST`

**接口路径**: `/api/analysis/{analysis_id}/pause`

**路径参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| analysis_id | string | 任务ID |

**响应示例**:
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "paused",
  "message": "Analysis task paused"
}
```

**注意事项**:
- 只能暂停状态为 "running" 的任务
- 已停止的任务无法暂停

---

### 2.5 恢复任务

**接口描述**: 恢复已暂停的分析任务

**请求方式**: `POST`

**接口路径**: `/api/analysis/{analysis_id}/resume`

**路径参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| analysis_id | string | 任务ID |

**响应示例**:
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "message": "Analysis task resumed"
}
```

**注意事项**:
- 只能恢复状态为 "paused" 的任务
- 已停止的任务无法恢复

---

### 2.6 停止任务

**接口描述**: 停止正在运行或已暂停的分析任务

**请求方式**: `POST`

**接口路径**: `/api/analysis/{analysis_id}/stop`

**路径参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| analysis_id | string | 任务ID |

**响应示例**:
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "stopped",
  "message": "Analysis task stopped"
}
```

**注意事项**:
- 可以停止 "running" 或 "paused" 状态的任务
- 停止后的任务无法恢复，需要重新启动新任务

---

## 错误码说明

| HTTP状态码 | 说明 |
|-----------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误或操作不允许 |
| 404 | 资源不存在（如任务ID不存在） |
| 500 | 服务器内部错误 |

**错误响应示例**:
```json
{
  "detail": "Analysis ID not found"
}
```

---

## 使用示例

### cURL示例

#### 启动分析任务
```bash
curl -X POST "http://localhost:8000/api/analysis/start" \
  -H "Content-Type: application/json" \
  -d '{
    "stock_symbol": "AAPL",
    "market_type": "美股",
    "research_depth": 3,
    "analysts": ["market", "fundamentals"]
  }'
```

#### 查询任务状态
```bash
curl -X GET "http://localhost:8000/api/analysis/{analysis_id}/status"
```

#### 暂停任务
```bash
curl -X POST "http://localhost:8000/api/analysis/{analysis_id}/pause"
```

#### 恢复任务
```bash
curl -X POST "http://localhost:8000/api/analysis/{analysis_id}/resume"
```

#### 停止任务
```bash
curl -X POST "http://localhost:8000/api/analysis/{analysis_id}/stop"
```

---

## 附录

### 任务状态流转图

```
pending → running → completed
    ↓         ↓         
    ↓     paused → running
    ↓         ↓
    └─→ stopped ←─┘
```

### 分析师类型说明

| 类型 | 说明 |
|------|------|
| market | 市场分析师 - 分析技术面和市场趋势 |
| fundamentals | 基本面分析师 - 分析财务数据和公司基本面 |
| news | 新闻分析师 - 分析相关新闻和事件 |
| social | 社交媒体分析师 - 分析社交媒体情绪 |

### 研究深度说明

| 深度 | 说明 |
|------|------|
| 1 | 快速分析 - 基础指标和简要结论 |
| 2 | 标准分析 - 常规指标和分析 |
| 3 | 深入分析 - 详细指标和多维度分析 |
| 4 | 专业分析 - 专业级深度分析 |
| 5 | 全面分析 - 最全面的深度研究 |

---

**文档版本**: 1.0  
**最后更新**: 2024-11-20  
**维护团队**: APEX开发团队
