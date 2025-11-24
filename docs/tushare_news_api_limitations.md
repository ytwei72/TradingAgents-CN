# Tushare新闻接口权限限制说明

## 权限限制

Tushare新闻接口（`news` API）有严格的访问频率限制：

- **免费用户**: 每小时最多访问 **2次**
- **付费用户**: 根据积分等级有不同的访问限制

## 错误信息

当超过访问频率限制时，会收到以下错误：

```
抱歉，您每小时最多访问该接口2次，权限的具体详情访问：https://tushare.pro/document/1?doc_id=108
```

## 代码改进

已在`tushare_utils.py`中添加了以下改进：

### 1. 文档字符串更新

在`get_stock_news`和`get_stock_news_items`方法中添加了权限限制说明：

```python
def get_stock_news(self, symbol: str = None, start_date: str = None, 
                   end_date: str = None, max_news: int = 10) -> pd.DataFrame:
    """
    获取股票新闻（使用Tushare新闻接口）
    
    **重要提示**:
    - Tushare新闻接口有访问频率限制
    - 免费用户：每小时最多访问2次
    - 如遇到权限限制错误，请等待1小时后再试
    - 权限详情: https://tushare.pro/document/1?doc_id=108
    ...
    """
```

### 2. 改进的错误处理

添加了对权限限制错误的特殊识别和友好提示：

```python
except Exception as e:
    error_msg = str(e)
    
    # 检查是否是权限限制错误
    if '每小时最多访问该接口' in error_msg or '权限' in error_msg:
        logger.warning(f"[Tushare新闻] ⚠️ API访问频率限制: {error_msg}")
        logger.warning(f"[Tushare新闻] 💡 提示: Tushare新闻接口免费用户每小时最多访问2次")
        logger.warning(f"[Tushare新闻] 💡 请等待1小时后再试，或访问 https://tushare.pro/document/1?doc_id=108 了解权限详情")
    else:
        logger.error(f"[Tushare新闻] ❌ 获取失败: {symbol}, 错误: {e}")
        # ... 其他错误处理
```

## 使用建议

### 1. 控制调用频率

由于免费用户每小时只能访问2次，建议：

- 在开发和测试时谨慎使用
- 考虑使用缓存机制
- 优先使用AKShare作为新闻源（已在`realtime_news_utils.py`中实现）

### 2. 降级策略

当前系统已实现自动降级：

1. **优先**: Tushare新闻接口
2. **降级**: AKShare东方财富新闻
3. **补充**: 财联社RSS

如果Tushare遇到权限限制，系统会自动切换到AKShare。

### 3. 日志监控

权限限制错误会以`WARNING`级别记录，便于监控：

```
[Tushare新闻] ⚠️ API访问频率限制: 抱歉，您每小时最多访问该接口2次...
[Tushare新闻] 💡 提示: Tushare新闻接口免费用户每小时最多访问2次
[Tushare新闻] 💡 请等待1小时后再试，或访问 https://tushare.pro/document/1?doc_id=108 了解权限详情
```

## 测试注意事项

运行测试脚本`test_chinese_finance_news.py`时：

- 每小时最多运行2次完整测试
- 如果遇到权限限制，等待1小时后再试
- 可以注释掉Tushare相关测试，只测试AKShare部分

## 权限升级

如需更高的访问频率，可以：

1. 访问 https://tushare.pro/document/1?doc_id=108
2. 了解不同积分等级的权限
3. 考虑升级账户权限

## 相关文件

- `tradingagents/dataflows/tushare_utils.py` - Tushare工具类（已更新）
- `tradingagents/dataflows/realtime_news_utils.py` - 新闻聚合器（支持降级）
- `scripts/test_chinese_finance_news.py` - 测试脚本
