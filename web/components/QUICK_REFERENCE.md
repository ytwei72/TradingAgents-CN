# 组件快速参考

## 🚀 快速开始

### 导入组件

```python
# UI组件
from components.ui_components import (
    render_metric_row,          # 指标行
    render_section_header,      # 章节标题
    render_info_box,            # 信息提示框
    render_card,                # 卡片
    render_empty_state,         # 空状态
    render_status_badge,        # 状态徽章
)

# 工具函数
from components.component_utils import (
    safe_get,                   # 安全获取值
    format_percentage,          # 格式化百分比
    format_currency,            # 格式化货币
    get_display_name,           # 获取显示名称
    validate_stock_symbol,      # 验证股票代码
)

# 结果显示模块
from components.results_modules import (
    render_analysis_config,     # 渲染分析配置
    render_decision_metrics,    # 渲染决策指标
    get_model_display_name,     # 获取模型名称
)
```

---

## 📦 常用组件示例

### 1. 显示指标行

```python
metrics = [
    {
        'label': 'LLM提供商',
        'value': '阿里百炼',
        'help': '使用的AI模型提供商'
    },
    {
        'label': '使用模型',
        'value': 'Qwen Max',
        'delta': '+10%',  # 可选：变化值
        'help': '使用的具体AI模型'
    },
    {
        'label': '分析深度',
        'value': '深度分析'
    }
]

render_metric_row(metrics, columns=3)
```

### 2. 显示信息提示框

```python
# 成功消息
render_info_box("操作成功！", box_type="success")

# 警告消息
render_info_box("请注意风险", box_type="warning", icon="⚠️")

# 错误消息
render_info_box("操作失败，请重试", box_type="error")

# 普通信息
render_info_box("这是一条提示信息", box_type="info")
```

### 3. 使用展开器

```python
with render_section_header("详细信息", icon="📊", expanded=False):
    st.write("这里是详细内容...")
    st.write("可以包含任何Streamlit组件")
```

### 4. 显示空状态

```python
render_empty_state(
    message="暂无数据",
    icon="📭",
    action_button={
        'label': '刷新数据',
        'callback': lambda: st.rerun()
    }
)
```

### 5. 显示状态徽章

```python
# 使用默认状态映射
render_status_badge("success")  # 显示绿色"成功"徽章
render_status_badge("running")  # 显示蓝色"运行中"徽章

# 自定义状态映射
custom_map = {
    'active': ('活跃', 'green'),
    'inactive': ('未激活', 'gray')
}
render_status_badge("active", status_map=custom_map)
```

### 6. 显示卡片

```python
render_card(
    title="市场分析",
    content="当前市场处于上升趋势，建议持续关注",
    icon="📈",
    card_type="success"  # 可选: success, warning, error, info, default
)
```

---

## 🛠️ 常用工具函数

### 1. 安全获取数据

```python
# 简单获取
value = safe_get(data, 'key', default='N/A')

# 嵌套获取
value = safe_get_nested(data, ['level1', 'level2', 'key'], default='N/A')
```

### 2. 格式化显示

```python
# 格式化数字
formatted = format_number(12345.67, decimal_places=2)  # "12,345.67"

# 格式化百分比
percentage = format_percentage(0.1234, decimal_places=2)  # "12.34%"

# 格式化货币
currency = format_currency(12345.67, currency="¥")  # "¥12,345.67"

# 格式化日期
date_str = format_date("2025-10-29", format_str="%Y年%m月%d日")
```

### 3. 验证股票代码

```python
is_valid, error_msg = validate_stock_symbol('000001', 'A股')
if not is_valid:
    st.error(error_msg)
```

### 4. 获取显示名称

```python
# 使用内置映射
provider_name = get_display_name('dashscope')  # "阿里百炼"

# 自定义映射
custom_map = {'custom_key': '自定义名称'}
name = get_display_name('custom_key', name_map=custom_map)
```

---

## 🎨 组合使用示例

### 完整的分析结果显示

```python
def render_my_analysis(results):
    """显示分析结果"""
    
    # 1. 检查数据
    if not results:
        render_empty_state(
            message="暂无分析结果",
            icon="📊"
        )
        return
    
    # 2. 显示标题
    stock_symbol = safe_get(results, 'stock_symbol')
    st.header(f"📊 {stock_symbol} 分析结果")
    
    # 3. 显示配置信息
    with render_section_header("分析配置", icon="⚙️", expanded=False):
        config_metrics = [
            {
                'label': 'LLM提供商',
                'value': get_display_name(safe_get(results, 'llm_provider'))
            },
            {
                'label': '分析时间',
                'value': format_date(safe_get(results, 'timestamp'))
            }
        ]
        render_metric_row(config_metrics, columns=2)
    
    # 4. 显示关键指标
    st.subheader("📈 关键指标")
    key_metrics = [
        {
            'label': '目标价位',
            'value': format_currency(safe_get(results, 'target_price')),
            'delta': '+5%'
        },
        {
            'label': '风险等级',
            'value': safe_get(results, 'risk_level')
        },
        {
            'label': '置信度',
            'value': format_percentage(safe_get(results, 'confidence'))
        }
    ]
    render_metric_row(key_metrics, columns=3)
    
    # 5. 显示风险提示
    render_info_box(
        "投资有风险，入市需谨慎。本分析仅供参考。",
        box_type="warning"
    )
```

---

## 🔧 高级用法

### 1. 动态标签页

```python
tab_config = [
    {
        'title': '市场分析',
        'content': lambda: st.write("市场分析内容")
    },
    {
        'title': '基本面分析',
        'content': lambda: st.write("基本面分析内容")
    },
    {
        'title': '风险评估',
        'content': lambda: st.write("风险评估内容")
    }
]

render_tabs(tab_config)
```

### 2. 自定义分隔线

```python
# 简单分隔线
render_divider()

# 带文字的分隔线
render_divider(text="更多信息")

# 自定义间距
render_divider(text="分析详情", margin="2rem 0")
```

### 3. 可折叠代码块

```python
code = """
def example():
    print("Hello, World!")
"""

render_collapsible_code(
    code=code,
    language="python",
    title="查看示例代码"
)
```

---

## 💡 最佳实践

### 1. 优先使用共用组件
❌ 不推荐:
```python
st.error(f"错误: {error_msg}")
```

✅ 推荐:
```python
render_info_box(f"错误: {error_msg}", box_type="error")
```

### 2. 使用safe_get避免KeyError
❌ 不推荐:
```python
value = data['key']  # 可能抛出KeyError
```

✅ 推荐:
```python
value = safe_get(data, 'key', default='N/A')
```

### 3. 格式化显示数据
❌ 不推荐:
```python
st.metric("价格", f"{price}")  # 可能显示很多小数
```

✅ 推荐:
```python
st.metric("价格", format_currency(price))  # ¥12,345.67
```

### 4. 验证用户输入
❌ 不推荐:
```python
if symbol:
    analyze_stock(symbol)
```

✅ 推荐:
```python
is_valid, error = validate_stock_symbol(symbol, market_type)
if is_valid:
    analyze_stock(symbol)
else:
    render_info_box(error, box_type="error")
```

---

## 📚 更多资源

- [完整重构文档](./COMPONENT_REFACTORING_SUMMARY.md)
- [样式重构文档](../STYLE_REFACTORING_SUMMARY.md)
- [UI组件源码](./ui_components.py)
- [工具函数源码](./component_utils.py)
- [结果模块源码](./results_modules.py)

