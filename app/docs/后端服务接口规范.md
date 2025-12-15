# TradingAgents 后端服务接口规范

## 文档说明

本文档详细描述了 TradingAgents 后端服务的 RESTful API 接口规范，包括已完成和近期计划的接口。所有接口定义与实际代码实现保持高度一致。

**版本**: 1.2  
**更新时间**: 2025-12-15  
**基础 URL**: `http://localhost:8000` (开发环境)  
**API 文档**: `http://localhost:8000/docs` (Swagger UI)

---

## 目录

1. [通用说明](#1-通用说明)
2. [健康检查接口](#2-健康检查接口)
3. [股票分析接口](#3-股票分析接口)
4. [报告管理接口](#4-报告管理接口)
5. [配置管理接口](#5-配置管理接口)
6. [模型使用日志接口](#6-模型使用日志接口)
7. [WebSocket接口](#7-websocket接口)
8. [用户认证接口](#8-用户认证接口-计划中)
9. [错误码说明](#9-错误码说明)
10. [完整使用示例](#10-完整使用示例)
11. [版本历史](#11-版本历史)
12. [联系方式](#12-联系方式)

---

## 1. 通用说明

### 1.1 请求格式

- **Content-Type**: `application/json`
- **字符编码**: UTF-8
- **时间格式**: ISO 8601 (`YYYY-MM-DDTHH:mm:ss`)
- **日期格式**: `YYYY-MM-DD`

### 1.2 响应格式

所有接口返回 JSON 格式数据，基本结构如下:

**成功响应**:
```json
{
  "data": { ... },
  "message": "操作成功",
  "timestamp": "2025-12-02T14:30:00"
}
```

**错误响应**:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": "详细错误信息",
    "timestamp": "2025-12-02T14:30:00"
  }
}
```

### 1.3 HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（需要登录） |
| 403 | 禁止访问（权限不足） |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
| 503 | 服务暂时不可用 |

### 1.4 认证方式（计划中）

使用 JWT (JSON Web Token) 进行认证:

```http
Authorization: Bearer <token>
```

### 1.5 限流策略（计划中）

- 未认证用户: 100 请求/小时
- 已认证用户: 1000 请求/小时
- 分析接口: 10 并发任务/用户

---

## 2. 健康检查接口

### 2.1 根路径信息

**状态**: ✅ 已完成

#### 请求

```http
GET /
```

#### 响应

```json
{
  "name": "TradingAgents-CN API",
  "version": "0.1.0",
  "status": "healthy",
  "docs_url": "/docs"
}
```

#### 示例

```bash
curl http://localhost:8000/
```

---

### 2.2 健康检查

**状态**: ✅ 已完成

#### 请求

```http
GET /api/health
```

#### 响应

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": 1701504000
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| status | string | 服务状态 (`healthy` / `unhealthy`) |
| version | string | API 版本号 |
| timestamp | integer | Unix 时间戳 |

#### 示例

```bash
curl http://localhost:8000/api/health
```

---

## 3. 股票分析接口

### 3.1 启动分析任务

**状态**: ✅ 已完成

启动一个异步股票分析任务。

#### 请求

```http
POST /api/analysis/start
Content-Type: application/json
```

#### 请求体

```json
{
  "stock_symbol": "AAPL",
  "market_type": "美股",
  "analysis_date": "2025-12-02",
  "analysts": [
    "market_analyst",
    "fundamental_analyst",
    "news_analyst"
  ],
  "research_depth": 3,
  "include_sentiment": true,
  "include_risk_assessment": true,
  "custom_prompt": "重点关注公司的AI业务发展",
  "extra_config": {
    "llm_provider": "dashscope",
    "llm_model": "qwen-max"
  }
}
```

#### 请求参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| stock_symbol | string | ✅ | 股票代码（如 AAPL, 000001, 9988.HK） |
| market_type | string | ✅ | 市场类型：`美股` / `A股` / `港股` |
| analysis_date | string | ❌ | 分析日期，格式 YYYY-MM-DD，默认今天 |
| analysts | array | ✅ | 分析师列表，见下表 |
| research_depth | integer | ✅ | 研究深度，1-5，数字越大越深入 |
| include_sentiment | boolean | ❌ | 是否包含情绪分析，默认 true |
| include_risk_assessment | boolean | ❌ | 是否包含风险评估，默认 true |
| custom_prompt | string | ❌ | 自定义分析提示 |
| extra_config | object | ❌ | 额外配置参数 |

**可用分析师列表**:

| 分析师 ID | 说明 |
|-----------|------|
| market_analyst | 市场分析师 |
| fundamental_analyst | 基本面分析师 |
| news_analyst | 新闻分析师 |
| social_media_analyst | 社交媒体分析师 |
| technical_analyst | 技术分析师 |

**extra_config 参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| llm_provider | string | LLM 提供商：`dashscope` / `openai` / `google` |
| llm_model | string | 模型名称：`qwen-max` / `gpt-4` / `gemini-pro` |

#### 响应

```json
{
  "analysis_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending",
  "message": "Analysis task started"
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| analysis_id | string | 分析任务唯一标识符（UUID） |
| status | string | 任务状态：`pending` |
| message | string | 状态消息 |

#### 示例

```bash
curl -X POST http://localhost:8000/api/analysis/start \
  -H "Content-Type: application/json" \
  -d '{
    "stock_symbol": "AAPL",
    "market_type": "美股",
    "analysts": ["market_analyst", "fundamental_analyst"],
    "research_depth": 3
  }'
```

---

### 3.2 查询任务状态

**状态**: ✅ 已完成

查询分析任务的当前状态和进度。

#### 请求

```http
GET /api/analysis/{analysis_id}/status
```

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| analysis_id | string | 分析任务 ID |

#### 响应

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "running",
  "created_at": "2025-12-02T14:30:00",
  "updated_at": "2025-12-02T14:35:00",
  "params": {
    "stock_symbol": "AAPL",
    "market_type": "美股",
    "analysis_date": "2025-12-02",
    "analysts": ["market_analyst", "fundamental_analyst"],
    "research_depth": 3
  },
  "progress": {
    "current_step": 3,
    "total_steps": 10,
    "percentage": 30.0,
    "message": "正在执行基本面分析..."
  },
  "error": null,
  "result": null
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | string | 分析任务 ID |
| status | string | 任务状态，见下表 |
| created_at | string | 任务创建时间 (ISO 8601) |
| updated_at | string | 任务最后更新时间 (ISO 8601) |
| params | object | 任务参数 |
| progress | object | 进度信息对象 |
| error | string/null | 错误信息（仅失败时） |
| result | object/null | 分析结果（仅完成时） |

**任务状态说明**:

| 状态 | 说明 |
|------|------|
| pending | 等待执行 |
| running | 正在执行 |
| paused | 已暂停 |
| stopped | 已停止 |
| completed | 已完成 |
| failed | 执行失败 |
| cancelled | 已取消 |

**进度信息字段** (`progress` 对象):

| 字段 | 类型 | 说明 |
|------|------|------|
| current_step | integer | 当前步骤编号 |
| total_steps | integer | 总步骤数 |
| percentage | float | 完成百分比 (0-100) |
| message | string | 当前步骤描述 |

#### 示例

```bash
curl http://localhost:8000/api/analysis/a1b2c3d4-e5f6-7890-abcd-ef1234567890/status
```

---

### 3.3 获取分析结果

**状态**: ✅ 已完成

获取已完成的分析任务的完整结果。

#### 请求

```http
GET /api/analysis/{analysis_id}/result
```

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| analysis_id | string | 分析任务 ID |

#### 响应

```json
{
  "stock_symbol": "AAPL",
  "market_type": "美股",
  "analysis_date": "2025-12-02",
  "decision": "买入",
  "confidence": 0.85,
  "full_report": "# 苹果公司(AAPL)投资分析报告\n\n## 综合评分: 85/100\n\n...",
  "analyst_reports": {
    "market_analyst": {
      "summary": "市场趋势向好，技术面支撑强劲",
      "rating": "买入",
      "confidence": 0.82,
      "key_points": [
        "大盘走势稳健，科技股表现优异",
        "成交量放大，资金流入明显"
      ]
    },
    "fundamental_analyst": {
      "summary": "基本面稳健，盈利能力强",
      "rating": "买入",
      "confidence": 0.88,
      "key_points": [
        "营收同比增长15%，超出市场预期",
        "净利润率保持在25%以上",
        "现金流充沛，财务状况健康"
      ]
    }
  },
  "risk_assessment": {
    "overall_risk": "中等",
    "risk_factors": [
      "市场波动风险",
      "行业竞争加剧"
    ],
    "risk_score": 0.45
  },
  "sentiment_analysis": {
    "overall_sentiment": "积极",
    "sentiment_score": 0.72,
    "news_sentiment": 0.68,
    "social_sentiment": 0.76
  },
  "metadata": {
    "analysis_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "created_at": "2025-12-02T14:30:00",
    "completed_at": "2025-12-02T14:35:30",
    "duration_seconds": 330,
    "llm_provider": "dashscope",
    "llm_model": "qwen-max",
    "analysts_used": ["market_analyst", "fundamental_analyst"]
  }
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| stock_symbol | string | 股票代码 |
| market_type | string | 市场类型 |
| analysis_date | string | 分析日期 |
| decision | string | 投资决策：`买入` / `持有` / `卖出` |
| confidence | float | 决策置信度 (0-1) |
| full_report | string | 完整分析报告（Markdown 格式） |
| analyst_reports | object | 各分析师的详细报告 |
| risk_assessment | object | 风险评估结果 |
| sentiment_analysis | object | 情绪分析结果 |
| metadata | object | 元数据信息 |

#### 错误响应

**任务未完成**:
```json
{
  "detail": "Analysis not completed. Current status: running"
}
```
HTTP 状态码: 400

**任务不存在**:
```json
{
  "detail": "Analysis ID not found"
}
```
HTTP 状态码: 404

#### 示例

```bash
curl http://localhost:8000/api/analysis/a1b2c3d4-e5f6-7890-abcd-ef1234567890/result
```

---

### 3.4 暂停分析任务

**状态**: ✅ 已完成

暂停正在运行的分析任务。

#### 请求

```http
POST /api/analysis/{analysis_id}/pause
```

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| analysis_id | string | 分析任务 ID |

#### 响应

```json
{
  "analysis_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "paused",
  "message": "Analysis task paused"
}
```

#### 示例

```bash
curl -X POST http://localhost:8000/api/analysis/a1b2c3d4-e5f6-7890-abcd-ef1234567890/pause
```

---

### 3.5 恢复分析任务

**状态**: ✅ 已完成

恢复已暂停的分析任务。

#### 请求

```http
POST /api/analysis/{analysis_id}/resume
```

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| analysis_id | string | 分析任务 ID |

#### 响应

```json
{
  "analysis_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "running",
  "message": "Analysis task resumed"
}
```

#### 示例

```bash
curl -X POST http://localhost:8000/api/analysis/a1b2c3d4-e5f6-7890-abcd-ef1234567890/resume
```

---

### 3.6 停止分析任务

**状态**: ✅ 已完成

停止分析任务（不可恢复）。

#### 请求

```http
POST /api/analysis/{analysis_id}/stop
```

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| analysis_id | string | 分析任务 ID |

#### 响应

```json
{
  "analysis_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "stopped",
  "message": "Analysis task stopped"
}
```

#### 示例

```bash
curl -X POST http://localhost:8000/api/analysis/a1b2c3d4-e5f6-7890-abcd-ef1234567890/stop
```

---

### 3.7 查询任务当前步骤

**状态**: ✅ 已完成

从任务状态机查询任务的当前步骤信息。

#### 请求

```http
GET /api/analysis/{analysis_id}/current_step
```

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| analysis_id | string | 分析任务 ID |

#### 响应

```json
{
  "step_name": "market_analyst",
  "step_index": 3,
  "description": "正在执行市场分析...",
  "status": "running",
  "start_time": "2025-12-03T14:30:00",
  "end_time": null,
  "elapsed_time": 0.0,
  "events": [
    {
      "event": "start",
      "timestamp": "2025-12-03T14:30:00",
      "message": "模块开始: market_analyst"
    }
  ],
  "timestamp": "2025-12-03T14:30:05"
}
```

#### 示例

```bash
curl http://localhost:8000/api/analysis/a1b2c3d4-e5f6-7890-abcd-ef1234567890/current_step
```

---

### 3.8 查询任务历史步骤

**状态**: ✅ 已完成

获取任务历史步骤（从状态机获取）。每个步骤记录包含完整的生命周期事件。

#### 请求

```http
GET /api/analysis/{analysis_id}/history
```

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| analysis_id | string | 分析任务 ID |

#### 响应

返回完整的历史状态列表（JSON数组格式）。每个步骤只有一条记录，包含该步骤的所有生命周期事件：

```json
[
  {
    "step_name": "market_analyst",
    "step_index": 1,
    "status": "completed",
    "start_time": "2025-12-08T10:01:00.000000",
    "end_time": "2025-12-08T10:01:40.750000",
    "elapsed_time": 40.75,
    "events": [
      {
        "event": "start",
        "timestamp": "2025-12-08T10:01:00.000000",
        "message": "模块开始: market_analyst"
      },
      {
        "event": "complete",
        "timestamp": "2025-12-08T10:01:40.750000",
        "message": "模块完成: market_analyst",
        "duration": 40.75
      }
    ],
    "timestamp": "2025-12-08T10:01:40.750000"
  },
  {
    "step_name": "fundamentals_analyst",
    "step_index": 2,
    "status": "completed",
    "start_time": "2025-12-08T10:01:41.000000",
    "end_time": "2025-12-08T10:03:11.000000",
    "elapsed_time": 90.10,
    "events": [
      {
        "event": "start",
        "timestamp": "2025-12-08T10:01:41.000000",
        "message": "模块开始: fundamentals_analyst"
      },
      {
        "event": "tool_calling",
        "timestamp": "2025-12-08T10:01:50.500000",
        "message": "工具调用中: fundamentals_analyst",
        "duration": 9.5
      },
      {
        "event": "complete",
        "timestamp": "2025-12-08T10:03:11.000000",
        "message": "模块完成: fundamentals_analyst",
        "duration": 80.6
      }
    ],
    "timestamp": "2025-12-08T10:03:11.000000"
  }
]
```

#### 响应字段说明

**步骤对象**:

| 字段 | 类型 | 说明 |
|------|------|------|
| step_name | string | 步骤名称（模块ID） |
| step_index | integer | 步骤序号（从1开始） |
| status | string | 步骤状态：`running` / `completed` / `failed` |
| start_time | string | 步骤开始时间 (ISO 8601) |
| end_time | string/null | 步骤结束时间（运行中为 null） |
| elapsed_time | float | 总耗时（秒），所有阶段累计 |
| events | array | 生命周期事件列表 |
| timestamp | string | 最后更新时间 |

**事件对象** (`events` 数组元素):

| 字段 | 类型 | 说明 |
|------|------|------|
| event | string | 事件类型：`start` / `tool_calling` / `complete` / `error` |
| timestamp | string | 事件发生时间 (ISO 8601) |
| message | string | 事件描述 |
| duration | float | 该阶段耗时（秒，仅非 start 事件有此字段） |

**事件类型说明**:

| 事件类型 | 说明 |
|----------|------|
| start | 步骤开始 |
| tool_calling | 工具调用中（如 LLM 调用外部数据接口） |
| complete | 步骤完成 |
| error | 步骤出错 |

#### 示例

```bash
curl http://localhost:8000/api/analysis/a1b2c3d4-e5f6-7890-abcd-ef1234567890/history
```

---


### 3.9 获取任务计划步骤

**状态**: ✅ 已完成

在任务启动时或启动前，返回该任务预计执行的所有步骤列表。

#### 请求

```http
GET /api/analysis/{analysis_id}/planned_steps
```

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| analysis_id | string | 分析任务 ID |

#### 响应

```json
{
  "total_steps": 18,
  "steps": [
    {
      "step_index": 1,
      "step_name": "environment_validation",
      "display_name": "环境验证",
      "phase": "preparation",
      "status": "pending",
      "round": null,
      "role": null
    },
    {
      "step_index": 7,
      "step_name": "market_analyst",
      "display_name": "市场分析师",
      "phase": "analyst",
      "status": "pending",
      "round": null,
      "role": null
    },
    {
      "step_index": 10,
      "step_name": "bull_debate",
      "display_name": "看多分析师辩论",
      "phase": "debate",
      "status": "pending",
      "round": 1,
      "role": "bull"
    }
  ]
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| total_steps | integer | 总步骤数 |
| steps | array | 计划步骤列表 |

**步骤对象字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| step_index | integer | 步骤序号（从1开始） |
| step_name | string | 步骤名称（模块ID） |
| display_name | string | 步骤中文显示名称 |
| phase | string | 步骤阶段：`preparation` / `analyst` / `debate` / `trading` / `risk_assessment` |
| status | string | 步骤状态：`pending` |
| round | integer/null | 辩论轮次（仅辩论阶段有效） |
| role | string/null | 角色名称（仅辩论阶段有效） |

**步骤阶段说明**:

| 阶段 | 说明 | 包含步骤 |
|------|------|----------|
| preparation | 准备阶段 | 环境验证、参数验证、数据源初始化、工具初始化、图配置、数据收集 |
| analyst | 分析师阶段 | 市场分析师、基本面分析师、新闻分析师、社交媒体分析师（根据任务配置） |
| debate | 研究团队辩论 | 看多分析师、看空分析师、研究经理 |
| trading | 交易决策 | 交易员 |
| risk_assessment | 风险评估 | 激进风险评估、保守风险评估、中性风险评估、风险裁决 |

#### 示例

```bash
curl http://localhost:8000/api/analysis/a1b2c3d4-e5f6-7890-abcd-ef1234567890/planned_steps
```

---


## 4. 报告管理接口

### 4.1 生成报告

**状态**: 🚧 草稿

从分析结果生成格式化报告文件。

#### 请求

```http
POST /reports/generate
Content-Type: application/json
```

#### 请求体

```json
{
  "analysis_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "format": "pdf",
  "include_charts": true,
  "language": "zh-CN"
}
```

#### 请求参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| analysis_id | string | ✅ | 分析任务 ID |
| format | string | ✅ | 报告格式：`pdf` / `markdown` / `docx` |
| include_charts | boolean | ❌ | 是否包含图表，默认 true |
| language | string | ❌ | 报告语言：`zh-CN` / `en-US`，默认 zh-CN |

#### 响应

```json
{
  "report_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890_markdown",
  "status": "completed",
  "message": "报告生成成功",
  "download_url": "/reports/a1b2c3d4-e5f6-7890-abcd-ef1234567890_markdown",
  "format": "markdown"
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| report_id | string | 报告 ID（格式：{analysis_id}_{format}） |
| status | string | 生成状态：`completed` / `failed` |
| message | string | 状态消息 |
| download_url | string | 下载链接 |
| format | string | 报告格式 |

#### 错误响应

**分析任务不存在**:
```json
{
  "detail": "分析任务不存在: {analysis_id}"
}
```
HTTP 状态码: 404

**分析未完成**:
```json
{
  "detail": "分析任务未完成，当前状态: running"
}
```
HTTP 状态码: 400

**不支持的格式**:
```json
{
  "detail": [
    {
      "type": "literal_error",
      "loc": ["body", "format"],
      "msg": "Input should be 'markdown', 'md', 'pdf' or 'docx'"
    }
  ]
}
```
HTTP 状态码: 422

#### 示例

```bash
curl -X POST http://localhost:8000/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "format": "markdown"
  }'

---

### 4.2 下载报告

**状态**: 🚧 草稿

下载已生成的报告文件。

#### 请求

```http
GET /reports/{report_id}
```

#### 路径参数

| 参数 | 类型 | 说明 |
|------|------|------|
| report_id | string | 报告 ID |

#### 响应

返回报告文件（二进制流）。

**响应头**:
```
Content-Type: application/pdf | text/markdown | application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="report_{analysis_id}.{ext}"
```

#### 错误响应

**报告不存在**:
```json
{
  "detail": "报告不存在: {report_id}"
}
```
HTTP 状态码: 404

#### 示例

```bash
# 下载报告
curl -O -J http://localhost:8000/reports/a1b2c3d4-e5f6-7890-abcd-ef1234567890_markdown
```

---

## 5. 配置管理接口

### 5.1 获取系统配置

**状态**: ✅ 已完成

获取系统配置。系统配置包括四种类型：`models`（模型配置）、`pricing`（定价配置）、`settings`（设置配置）。可以通过查询参数指定要获取的配置类型。

#### 请求

```http
GET /api/config/system?config_types=settings,models
```

#### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| config_types | string | ❌ | 逗号分隔的配置类型列表，可选值：`models`、`pricing`、`settings`。如果不指定，默认只返回 `settings` |

#### 响应示例

**只获取 settings（默认）**:
```json
{
  "success": true,
  "data": {
    "llm_provider": "dashscope",
    "deep_think_llm": "qwen-max",
    "quick_think_llm": "qwen-plus",
    "research_depth_default": 3,
    "market_type_default": "美股",
    "memory_enabled": true,
    "online_tools": true,
    "online_news": true,
    "realtime_data": true,
    "max_recur_limit": 5,
    "backend_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "custom_openai_base_url": null,
    "data_dir": "./data",
    "results_dir": "./results",
    "data_cache_dir": "./cache",
    "db": {
      "mongo": {
        "mongo_host": "localhost",
        "mongo_port": 27017,
        "mongo_username": null,
        "mongo_password": null,
        "mongo_database": "tradingagents",
        "mongo_auth_source": "admin",
        "mongo_max_connections": 100,
        "mongo_min_connections": 10,
        "mongo_connect_timeout_ms": 5000,
        "mongo_socket_timeout_ms": 30000,
        "mongo_server_selection_timeout_ms": 5000,
        "mongo_uri": "mongodb://localhost:27017/",
        "mongo_db": "tradingagents"
      }
    }
  },
  "message": "系统配置获取成功"
}
```

**获取多种配置类型**:
```json
{
  "success": true,
  "data": {
    "models": [
      {
        "provider": "dashscope",
        "model_name": "qwen-turbo",
        "api_key": "",
        "base_url": null,
        "max_tokens": 4000,
        "temperature": 0.7,
        "enabled": true
      }
    ],
    "pricing": [
      {
        "provider": "dashscope",
        "model_name": "qwen-turbo",
        "input_price_per_1k": 0.002,
        "output_price_per_1k": 0.006,
        "currency": "CNY"
      }
    ],
    "settings": {
      "llm_provider": "dashscope",
      "default_model": "qwen-turbo"
    }
  },
  "message": "系统配置获取成功"
}
```

#### 响应字段说明

**顶层字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 操作是否成功 |
| data | object/array | 配置数据。如果只请求一种配置类型，直接返回该配置；如果请求多种，返回包含所有请求配置的对象 |
| message | string | 响应消息 |

**配置类型说明**:

- **models**: 模型配置列表，每个元素包含 `provider`、`model_name`、`api_key`、`base_url`、`max_tokens`、`temperature`、`enabled` 等字段
- **pricing**: 定价配置列表，每个元素包含 `provider`、`model_name`、`input_price_per_1k`、`output_price_per_1k`、`currency` 等字段
- **settings**: 设置字典，包含 `llm_provider`、`deep_think_llm`、`quick_think_llm`、`research_depth_default`、`market_type_default`、`memory_enabled`、`online_tools`、`online_news`、`realtime_data`、`max_recur_limit`、`backend_url`、`custom_openai_base_url`、`data_dir`、`results_dir`、`data_cache_dir`、`db` 等字段

#### 错误响应

**无效的配置类型**:
```json
{
  "detail": "无效的配置类型: ['invalid_type']。有效类型: ['models', 'pricing', 'settings']"
}
```
HTTP 状态码: 400

**服务器内部错误**:
```json
{
  "detail": "获取系统配置失败: {错误信息}"
}
```
HTTP 状态码: 500

#### 示例

**获取默认配置（settings）**:
```bash
curl http://localhost:8000/api/config/system
```

**获取所有配置**:
```bash
curl "http://localhost:8000/api/config/system?config_types=models,pricing,settings"
```

**只获取 models 和 pricing**:
```bash
curl "http://localhost:8000/api/config/system?config_types=models,pricing"
```

---

### 5.2 更新系统配置

**状态**: ✅ 已完成

更新系统配置并持久化。请求体是一个 JSON 对象，可以包含 `models`、`pricing`、`settings` 中的任意几个键。根据请求中包含的键来更新对应的配置。

#### 请求

```http
PUT /api/config/system
Content-Type: application/json
```

#### 请求体

请求体可以包含以下键的任意几个：

- **models**: `List[Dict]` - 模型配置列表，会完全替换现有模型配置
- **pricing**: `List[Dict]` - 定价配置列表，会完全替换现有定价配置
- **settings**: `Dict` - 设置字典，会完全替换现有设置配置

**示例 1：只更新 settings**:
```json
{
  "settings": {
    "llm_provider": "dashscope",
    "deep_think_llm": "qwen-max",
    "research_depth_default": 4,
    "memory_enabled": false
  }
}
```

**示例 2：同时更新 models 和 pricing**:
```json
{
  "models": [
    {
      "provider": "dashscope",
      "model_name": "qwen-turbo",
      "api_key": "your-api-key",
      "base_url": null,
      "max_tokens": 4000,
      "temperature": 0.7,
      "enabled": true
    }
  ],
  "pricing": [
    {
      "provider": "dashscope",
      "model_name": "qwen-turbo",
      "input_price_per_1k": 0.002,
      "output_price_per_1k": 0.006,
      "currency": "CNY"
    }
  ]
}
```

**示例 3：更新所有配置类型**:
```json
{
  "models": [...],
  "pricing": [...],
  "settings": {
    "llm_provider": "dashscope",
    "default_model": "qwen-turbo"
  }
}
```

#### 请求参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| models | List[Dict] | ❌ | 模型配置列表，每个元素包含 `provider`、`model_name`、`api_key`、`base_url`、`max_tokens`、`temperature`、`enabled` 等字段 |
| pricing | List[Dict] | ❌ | 定价配置列表，每个元素包含 `provider`、`model_name`、`input_price_per_1k`、`output_price_per_1k`、`currency` 等字段 |
| settings | Dict | ❌ | 设置字典，包含各种系统设置参数 |

**注意事项**:
- 请求中必须包含至少一个配置类型（models、pricing、usage、settings 中的至少一个）
- 对于每种配置类型，会完全替换现有配置，不会进行合并
- 如果请求中不包含某个配置类型，该配置不会被更新

#### 响应

```json
{
  "success": true,
  "data": {},
  "message": "系统配置更新成功"
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 操作是否成功 |
| data | object | 空对象（不返回更新后的配置） |
| message | string | 响应消息 |

#### 错误响应

**请求中未包含任何配置类型**:
```json
{
  "detail": "请求中必须包含至少一个配置类型。有效类型: ['models', 'pricing', 'settings']"
}
```
HTTP 状态码: 400

**参数验证错误**:
```json
{
  "detail": [
    {
      "type": "list_type",
      "loc": ["body", "models"],
      "msg": "Input should be a valid list",
      "input": {}
    }
  ]
}
```
HTTP 状态码: 422

**服务器内部错误**:
```json
{
  "detail": "更新系统配置失败: {错误信息}"
}
```
HTTP 状态码: 500

#### 示例

**只更新 settings**:
```bash
curl -X PUT http://localhost:8000/api/config/system \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "research_depth_default": 4,
      "memory_enabled": false
    }
  }'
```

**同时更新 models 和 pricing**:
```bash
curl -X PUT http://localhost:8000/api/config/system \
  -H "Content-Type: application/json" \
  -d '{
    "models": [
      {
        "provider": "dashscope",
        "model_name": "qwen-turbo",
        "api_key": "",
        "enabled": true
      }
    ],
    "pricing": [
      {
        "provider": "dashscope",
        "model_name": "qwen-turbo",
        "input_price_per_1k": 0.002,
        "output_price_per_1k": 0.006,
        "currency": "CNY"
      }
    ]
  }'
```

---

## 6. 模型使用日志接口

模型使用日志接口用于记录和查询 LLM 模型的调用情况，包括 token 使用量、成本统计等信息。数据存储在 MongoDB 的 `model_usages` 集合中。

### 6.1 查询使用记录

**状态**: ✅ 已完成

查询模型使用记录，支持多种过滤条件。

#### 请求

```http
GET /api/logs/model_usage/records
```

#### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| limit | integer | ❌ | 返回记录数限制，默认 100，最大 10000 |
| days | integer | ❌ | 最近 N 天的记录 |
| provider | string | ❌ | 按供应商过滤（如 `dashscope`、`openai`） |
| model_name | string | ❌ | 按模型名称过滤（如 `qwen-max`、`gpt-4`） |
| session_id | string | ❌ | 按会话 ID 过滤 |
| analysis_type | string | ❌ | 按分析类型过滤 |
| start_date | string | ❌ | 开始日期（ISO 格式，如 `2025-12-01T00:00:00`） |
| end_date | string | ❌ | 结束日期（ISO 格式） |

#### 响应

```json
{
  "success": true,
  "data": [
    {
      "timestamp": "2025-12-15T10:30:00",
      "provider": "dashscope",
      "model_name": "qwen-max",
      "input_tokens": 1500,
      "output_tokens": 800,
      "cost": 0.05,
      "session_id": "analysis-abc123",
      "analysis_type": "stock_analysis"
    }
  ],
  "total": 1,
  "message": "查询成功"
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 操作是否成功 |
| data | array | 使用记录列表 |
| total | integer | 返回的记录数量 |
| message | string | 响应消息 |

**使用记录字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| timestamp | string | 记录时间（ISO 8601 格式） |
| provider | string | LLM 供应商名称 |
| model_name | string | 模型名称 |
| input_tokens | integer | 输入 token 数量 |
| output_tokens | integer | 输出 token 数量 |
| cost | float | 本次调用成本 |
| session_id | string | 会话/任务 ID |
| analysis_type | string | 分析类型 |

#### 示例

```bash
# 查询最近7天的使用记录
curl "http://localhost:8000/api/logs/model_usage/records?days=7&limit=50"

# 按供应商和模型过滤
curl "http://localhost:8000/api/logs/model_usage/records?provider=dashscope&model_name=qwen-max"
```

---

### 6.2 获取使用统计

**状态**: ✅ 已完成

获取模型使用的总体统计信息。

#### 请求

```http
GET /api/logs/model_usage/statistics
```

#### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| days | integer | ❌ | 统计最近 N 天的数据，默认 30，范围 1-365 |
| provider | string | ❌ | 按供应商过滤 |
| model_name | string | ❌ | 按模型名称过滤 |

#### 响应

```json
{
  "success": true,
  "data": {
    "period_days": 30,
    "total_cost": 12.5678,
    "total_input_tokens": 150000,
    "total_output_tokens": 80000,
    "total_requests": 500,
    "avg_cost": 0.025136,
    "avg_input_tokens": 300.0,
    "avg_output_tokens": 160.0
  },
  "message": "统计查询成功"
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| period_days | integer | 统计周期（天） |
| total_cost | float | 总成本 |
| total_input_tokens | integer | 总输入 token 数 |
| total_output_tokens | integer | 总输出 token 数 |
| total_requests | integer | 总请求数 |
| avg_cost | float | 平均每次请求成本 |
| avg_input_tokens | float | 平均输入 token 数 |
| avg_output_tokens | float | 平均输出 token 数 |

#### 示例

```bash
# 获取最近30天的统计
curl "http://localhost:8000/api/logs/model_usage/statistics?days=30"

# 获取特定供应商的统计
curl "http://localhost:8000/api/logs/model_usage/statistics?provider=dashscope"
```

---

### 6.3 按供应商统计

**状态**: ✅ 已完成

按供应商分组获取统计信息。

#### 请求

```http
GET /api/logs/model_usage/statistics/providers
```

#### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| days | integer | ❌ | 统计最近 N 天的数据，默认 30，范围 1-365 |

#### 响应

```json
{
  "success": true,
  "data": {
    "dashscope": {
      "cost": 8.5234,
      "input_tokens": 100000,
      "output_tokens": 50000,
      "requests": 350,
      "avg_cost": 0.024352
    },
    "openai": {
      "cost": 4.0444,
      "input_tokens": 50000,
      "output_tokens": 30000,
      "requests": 150,
      "avg_cost": 0.026963
    }
  },
  "message": "供应商统计查询成功"
}
```

#### 示例

```bash
curl "http://localhost:8000/api/logs/model_usage/statistics/providers?days=30"
```

---

### 6.4 按模型统计

**状态**: ✅ 已完成

按模型分组获取统计信息。

#### 请求

```http
GET /api/logs/model_usage/statistics/models
```

#### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| days | integer | ❌ | 统计最近 N 天的数据，默认 30，范围 1-365 |
| provider | string | ❌ | 按供应商过滤 |

#### 响应

```json
{
  "success": true,
  "data": {
    "dashscope/qwen-max": {
      "provider": "dashscope",
      "model_name": "qwen-max",
      "cost": 6.1234,
      "input_tokens": 80000,
      "output_tokens": 40000,
      "requests": 200,
      "avg_cost": 0.030617
    },
    "dashscope/qwen-plus": {
      "provider": "dashscope",
      "model_name": "qwen-plus",
      "cost": 2.4000,
      "input_tokens": 20000,
      "output_tokens": 10000,
      "requests": 150,
      "avg_cost": 0.016000
    }
  },
  "message": "模型统计查询成功"
}
```

#### 示例

```bash
# 获取所有模型的统计
curl "http://localhost:8000/api/logs/model_usage/statistics/models?days=30"

# 只获取特定供应商的模型统计
curl "http://localhost:8000/api/logs/model_usage/statistics/models?provider=dashscope"
```

---

### 6.5 统计记录数量

**状态**: ✅ 已完成

统计符合条件的记录总数。

#### 请求

```http
GET /api/logs/model_usage/count
```

#### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| days | integer | ❌ | 统计最近 N 天的记录 |
| provider | string | ❌ | 按供应商过滤 |
| model_name | string | ❌ | 按模型名称过滤 |

#### 响应

```json
{
  "success": true,
  "count": 1500,
  "message": "统计成功"
}
```

#### 示例

```bash
# 统计所有记录数量
curl "http://localhost:8000/api/logs/model_usage/count"

# 统计最近7天的记录数量
curl "http://localhost:8000/api/logs/model_usage/count?days=7"
```

---

### 6.6 添加使用记录

**状态**: ✅ 已完成

添加单条模型使用记录。

#### 请求

```http
POST /api/logs/model_usage/records
Content-Type: application/json
```

#### 请求体

```json
{
  "timestamp": "2025-12-15T10:30:00",
  "provider": "dashscope",
  "model_name": "qwen-max",
  "input_tokens": 1500,
  "output_tokens": 800,
  "cost": 0.05,
  "session_id": "analysis-abc123",
  "analysis_type": "stock_analysis"
}
```

#### 请求参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| timestamp | string | ❌ | 时间戳（ISO 格式），不传则使用当前时间 |
| provider | string | ✅ | 供应商名称 |
| model_name | string | ✅ | 模型名称 |
| input_tokens | integer | ✅ | 输入 token 数（≥0） |
| output_tokens | integer | ✅ | 输出 token 数（≥0） |
| cost | float | ✅ | 成本（≥0） |
| session_id | string | ✅ | 会话 ID |
| analysis_type | string | ❌ | 分析类型，默认为空字符串 |

#### 响应

```json
{
  "success": true,
  "record_id": "507f1f77bcf86cd799439011",
  "message": "记录添加成功"
}
```

#### 示例

```bash
curl -X POST "http://localhost:8000/api/logs/model_usage/records" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "dashscope",
    "model_name": "qwen-max",
    "input_tokens": 1000,
    "output_tokens": 500,
    "cost": 0.05,
    "session_id": "session-123",
    "analysis_type": "stock_analysis"
  }'
```

---

### 6.7 批量添加使用记录

**状态**: ✅ 已完成

批量添加多条模型使用记录。

#### 请求

```http
POST /api/logs/model_usage/records/batch
Content-Type: application/json
```

#### 请求体

```json
[
  {
    "provider": "dashscope",
    "model_name": "qwen-max",
    "input_tokens": 1000,
    "output_tokens": 500,
    "cost": 0.05,
    "session_id": "session-123",
    "analysis_type": "stock_analysis"
  },
  {
    "provider": "dashscope",
    "model_name": "qwen-plus",
    "input_tokens": 800,
    "output_tokens": 400,
    "cost": 0.02,
    "session_id": "session-123",
    "analysis_type": "stock_analysis"
  }
]
```

#### 响应

```json
{
  "success": true,
  "inserted_count": 2,
  "message": "成功插入 2 条记录"
}
```

#### 示例

```bash
curl -X POST "http://localhost:8000/api/logs/model_usage/records/batch" \
  -H "Content-Type: application/json" \
  -d '[
    {"provider": "dashscope", "model_name": "qwen-max", "input_tokens": 1000, "output_tokens": 500, "cost": 0.05, "session_id": "s1", "analysis_type": "test"},
    {"provider": "dashscope", "model_name": "qwen-plus", "input_tokens": 800, "output_tokens": 400, "cost": 0.02, "session_id": "s1", "analysis_type": "test"}
  ]'
```

---

### 6.8 清理旧记录

**状态**: ✅ 已完成

删除指定天数之前的历史记录，用于数据清理和空间管理。

⚠️ **注意**: 此操作不可逆，请谨慎使用。

#### 请求

```http
DELETE /api/logs/model_usage/records/cleanup
```

#### 查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| days | integer | ❌ | 删除 N 天前的记录，默认 90，范围 1-365 |

#### 响应

```json
{
  "success": true,
  "deleted_count": 150,
  "message": "成功清理 150 条超过 90 天的记录"
}
```

#### 示例

```bash
# 清理90天前的旧记录
curl -X DELETE "http://localhost:8000/api/logs/model_usage/records/cleanup?days=90"

# 清理30天前的旧记录
curl -X DELETE "http://localhost:8000/api/logs/model_usage/records/cleanup?days=30"
```

---

### 6.9 服务健康检查

**状态**: ✅ 已完成

检查模型使用记录服务的健康状态。

#### 请求

```http
GET /api/logs/model_usage/health
```

#### 响应

```json
{
  "success": true,
  "connected": true,
  "collection": "model_usages",
  "total_records": 1500,
  "message": "服务正常"
}
```

#### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| success | boolean | 检查是否成功 |
| connected | boolean | MongoDB 连接状态 |
| collection | string | 集合名称 |
| total_records | integer | 总记录数（仅连接正常时返回） |
| message | string | 状态消息 |

#### 错误响应

**MongoDB 连接不可用**:
```json
{
  "success": true,
  "connected": false,
  "collection": null,
  "message": "MongoDB 连接不可用"
}
```

#### 示例

```bash
curl "http://localhost:8000/api/logs/model_usage/health"
```

---

## 7. WebSocket接口

### 7.1 实时通知连接

**状态**: ✅ 已完成

建立 WebSocket 连接以接收实时通知（如分析进度、系统消息）。

#### 请求

```http
WS /ws/notifications
```

#### 交互流程

1. **连接建立**: 客户端连接到 `/ws/notifications`
2. **心跳检测**: 客户端定期发送 `ping`，服务器回复 `pong`
3. **消息接收**: 服务器主动推送 JSON 格式的通知消息

#### 消息格式

**通知消息**:
```json
{
  "topic": "task/progress",
  "payload": {
    "analysis_id": "a1b2c3d4...",
    "progress_percentage": 45.5,
    "current_step": 3,
    "current_step_name": "市场分析",
    "message": "正在分析市场趋势..."
  },
  "timestamp": "2025-12-02T14:30:00"
}
```

#### 示例代码 (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/notifications');

ws.onopen = () => {
    console.log('Connected');
    // 发送心跳
    setInterval(() => ws.send('ping'), 30000);
};

ws.onmessage = (event) => {
    if (event.data === 'pong') return;
    
    const notification = JSON.parse(event.data);
    console.log('Received:', notification);
};
```

---

## 8. 用户认证接口（计划中）

### 8.1 用户登录

**状态**: 📋 计划中

用户登录，获取访问令牌。

#### 请求

```http
POST /api/auth/login
Content-Type: application/json
```

#### 请求体

```json
{
  "username": "user@example.com",
  "password": "password123"
}
```

#### 响应

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "user123",
    "username": "user@example.com",
    "name": "张三"
  }
}
```

---

### 8.2 用户注册

**状态**: 📋 计划中

注册新用户账号。

#### 请求

```http
POST /api/auth/register
Content-Type: application/json
```

#### 请求体

```json
{
  "username": "user@example.com",
  "password": "password123",
  "name": "张三",
  "phone": "13800138000"
}
```

#### 响应

```json
{
  "user_id": "user123",
  "username": "user@example.com",
  "message": "Registration successful"
}
```

---

## 9. 错误码说明

### 9.1 通用错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| INVALID_REQUEST | 400 | 请求参数无效 |
| UNAUTHORIZED | 401 | 未授权，需要登录 |
| FORBIDDEN | 403 | 禁止访问 |
| NOT_FOUND | 404 | 资源不存在 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |

### 9.2 分析相关错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| ANALYSIS_NOT_FOUND | 404 | 分析任务不存在 |
| ANALYSIS_NOT_COMPLETED | 400 | 分析任务未完成 |
| ANALYSIS_FAILED | 500 | 分析任务执行失败 |
| INVALID_STOCK_SYMBOL | 400 | 无效的股票代码 |
| INVALID_MARKET_TYPE | 400 | 无效的市场类型 |
| INVALID_ANALYST | 400 | 无效的分析师类型 |
| TASK_CONTROL_FAILED | 400 | 任务控制操作失败 |

### 9.3 配置相关错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| CONFIG_LOAD_FAILED | 500 | 配置加载失败 |
| CONFIG_SAVE_FAILED | 500 | 配置保存失败 |
| INVALID_CONFIG_VALUE | 422 | 配置值无效（如 research_depth_default 超出范围） |

### 9.4 认证相关错误码（计划中）

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| INVALID_CREDENTIALS | 401 | 用户名或密码错误 |
| TOKEN_EXPIRED | 401 | 令牌已过期 |
| TOKEN_INVALID | 401 | 令牌无效 |
| USER_EXISTS | 400 | 用户已存在 |

---

## 10. 完整使用示例

### 10.1 Python 示例

```python
import requests
import time

# 基础 URL
BASE_URL = "http://localhost:8000"

# 1. 启动分析任务
response = requests.post(
    f"{BASE_URL}/api/analysis/start",
    json={
        "stock_symbol": "AAPL",
        "market_type": "美股",
        "analysts": ["market_analyst", "fundamental_analyst"],
        "research_depth": 3,
        "include_sentiment": True,
        "include_risk_assessment": True
    }
)

analysis_id = response.json()["analysis_id"]
print(f"分析任务已启动: {analysis_id}")

# 2. 轮询任务状态
while True:
    status_response = requests.get(
        f"{BASE_URL}/api/analysis/{analysis_id}/status"
    )
    status_data = status_response.json()
    
    print(f"当前状态: {status_data['status']}")
    print(f"当前步骤: {status_data['current_message']}")
    
    if status_data['status'] == 'completed':
        break
    elif status_data['status'] == 'failed':
        print(f"分析失败: {status_data['error']}")
        exit(1)
    
    time.sleep(5)  # 每5秒查询一次

# 3. 获取分析结果
result_response = requests.get(
    f"{BASE_URL}/api/analysis/{analysis_id}/result"
)
result = result_response.json()

print(f"投资决策: {result['decision']}")
print(f"置信度: {result['confidence']}")
print(f"\n完整报告:\n{result['full_report']}")
```

### 10.2 JavaScript 示例

```javascript
const BASE_URL = 'http://localhost:8000';

// 启动分析任务
async function startAnalysis() {
  const response = await fetch(`${BASE_URL}/api/analysis/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      stock_symbol: 'AAPL',
      market_type: '美股',
      analysts: ['market_analyst', 'fundamental_analyst'],
      research_depth: 3,
    }),
  });
  
  const data = await response.json();
  return data.analysis_id;
}

// 查询任务状态
async function checkStatus(analysisId) {
  const response = await fetch(
    `${BASE_URL}/api/analysis/${analysisId}/status`
  );
  return await response.json();
}

// 获取分析结果
async function getResult(analysisId) {
  const response = await fetch(
    `${BASE_URL}/api/analysis/${analysisId}/result`
  );
  return await response.json();
}

// 主流程
async function main() {
  const analysisId = await startAnalysis();
  console.log(`分析任务已启动: ${analysisId}`);
  
  // 轮询状态
  while (true) {
    const status = await checkStatus(analysisId);
    console.log(`当前状态: ${status.status}`);
    
    if (status.status === 'completed') {
      break;
    } else if (status.status === 'failed') {
      console.error(`分析失败: ${status.error}`);
      return;
    }
    
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
  
  // 获取结果
  const result = await getResult(analysisId);
  console.log(`投资决策: ${result.decision}`);
  console.log(`置信度: ${result.confidence}`);
}

main();
```

---

## 11. 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 0.3 | 2025-12-15 | 新增模型使用日志接口（查询、统计、添加、清理等） |
| 0.2 | 2025-12-22 | 新增配置管理接口（获取和更新系统配置） |
| 0.1 | 2025-12-02 | 初始版本，包含已完成的健康检查和分析接口 |

---

## 12. 联系方式

- **项目仓库**: https://github.com/hsliuping/TradingAgents-CN
- **问题反馈**: GitHub Issues
- **API 文档**: http://localhost:8000/docs

---

**注意事项**:
1. 本文档基于当前实现编写，与代码保持高度一致
2. 标注为"计划中"的接口尚未实现，仅供参考
3. 生产环境部署前请修改基础 URL 和安全配置
4. 建议使用 HTTPS 协议保护数据传输安全
