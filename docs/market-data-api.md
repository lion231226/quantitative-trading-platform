# 市场数据 API 文档

## 概述

市场数据API提供期货市场历史数据的获取、缓存和管理功能。支持多个版块（能源、金属、农产品、化工）的数据查询，具有完善的缓存机制和错误处理。

## 基础信息

- **基础URL**: `/api/v1/market-data`
- **认证**: 目前不需要认证
- **数据格式**: JSON
- **字符编码**: UTF-8

## 版块说明

支持的期货版块：

| 版块ID | 中文名称 | 说明 |
|--------|----------|------|
| energy | 能源 | 原油、燃油等能源期货 |
| metal | 金属 | 铜、铝、锌、镍、黄金、白银等金属期货 |
| agriculture | 农产品 | 大豆、玉米、棉花、白糖等农产品期货 |
| chemical | 化工 | PTA、甲醇、PVC等化工期货 |

## API 端点

### 1. 获取支持的版块列表

获取系统支持的所有期货版块。

**请求:**
```
GET /api/v1/market-data/sectors
```

**响应示例:**
```json
[
  "energy",
  "metal",
  "agriculture",
  "chemical"
]
```

### 2. 获取可用品种列表

获取指定版块的期货品种信息。如果不指定版块，则返回所有版块的品种。

**请求:**
```
GET /api/v1/market-data/symbols?sector={sector}
```

**参数:**
- `sector` (可选): 版块类型，值为 energy/metal/agriculture/chemical

**响应示例:**
```json
[
  {
    "symbol": "CU",
    "name": "铜",
    "exchange": "SHFE",
    "sector": "metal",
    "contract_size": 5,
    "trading_unit": "手",
    "price_quote": "元/吨",
    "min_price_change": 10,
    "is_active": true
  },
  {
    "symbol": "SC",
    "name": "原油",
    "exchange": "INE",
    "sector": "energy",
    "contract_size": 1000,
    "trading_unit": "手",
    "price_quote": "元/桶",
    "min_price_change": 0.1,
    "is_active": true
  }
]
```

### 3. 获取历史数据

获取指定期货品种的历史价格数据。

**请求:**
```
GET /api/v1/market-data/history?symbol={symbol}&start_date={start_date}&end_date={end_date}
```

**参数:**
- `symbol` (必需): 期货代码，如 "CU"、"SC" 等
- `start_date` (必需): 开始日期，格式 YYYY-MM-DD
- `end_date` (必需): 结束日期，格式 YYYY-MM-DD

**限制:**
- 查询时间范围不能超过1年
- 开始日期不能晚于结束日期

**响应示例:**
```json
[
  {
    "symbol": "CU",
    "date": "2023-01-01T00:00:00",
    "open_price": 100.0,
    "high_price": 105.0,
    "low_price": 95.0,
    "close_price": 104.0,
    "volume": 1000,
    "turnover": 104000.0,
    "settlement_price": 104.0,
    "open_interest": 5000
  },
  {
    "symbol": "CU",
    "date": "2023-01-02T00:00:00",
    "open_price": 104.0,
    "high_price": 109.0,
    "low_price": 99.0,
    "close_price": 108.0,
    "volume": 1100,
    "turnover": 118800.0,
    "settlement_price": 108.0,
    "open_interest": 5200
  }
]
```

### 4. 刷新数据缓存

清除指定品种的缓存并重新获取最新数据。

**请求:**
```
POST /api/v1/market-data/refresh
```

**请求体:**
```json
{
  "symbol": "CU",
  "start_date": "2023-01-01",
  "end_date": "2023-01-02",
  "force_refresh": false
}
```

**参数:**
- `symbol` (必需): 期货代码
- `start_date` (可选): 开始日期，不提供则默认为1年前
- `end_date` (可选): 结束日期，不提供则默认为今天
- `force_refresh` (可选): 是否强制刷新，默认false

**响应示例:**
```json
{
  "success": true,
  "message": "品种 CU 数据刷新成功",
  "data_count": 2,
  "symbol": "CU",
  "refresh_time": "2023-12-01T10:30:00",
  "cache_hit": false
}
```

## 数据字段说明

### MarketData (市场数据)

| 字段 | 类型 | 说明 |
|------|------|------|
| symbol | string | 期货代码 |
| date | datetime | 交易日期 |
| open_price | float | 开盘价 |
| high_price | float | 最高价 |
| low_price | float | 最低价 |
| close_price | float | 收盘价 |
| volume | integer | 成交量 |
| turnover | float | 成交额（可选） |
| settlement_price | float | 结算价（可选） |
| open_interest | integer | 持仓量（可选） |

### SymbolInfo (品种信息)

| 字段 | 类型 | 说明 |
|------|------|------|
| symbol | string | 期货代码 |
| name | string | 品种名称 |
| exchange | string | 交易所代码 |
| sector | string | 所属版块 |
| contract_size | integer | 合约乘数 |
| trading_unit | string | 交易单位 |
| price_quote | string | 报价单位 |
| min_price_change | float | 最小变动价位 |
| is_active | boolean | 是否活跃交易 |

## 缓存策略

- **市场数据缓存**: 24小时TTL
- **品种信息缓存**: 1小时TTL
- **缓存键**: 基于品种代码和日期范围生成唯一键
- **缓存清理**: 支持按品种清理和全量清理

## 错误处理

### 错误响应格式

```json
{
  "success": false,
  "error": {
    "type": "ERROR_TYPE",
    "message": "错误描述",
    "details": {
      "field": "相关字段",
      "additional_info": "额外信息"
    }
  }
}
```

### 常见错误类型

| 错误类型 | HTTP状态码 | 说明 |
|----------|------------|------|
| VALIDATION_ERROR | 400 | 请求参数验证失败 |
| API_ERROR | 400 | 业务逻辑错误 |
| DATA_ERROR | 400 | 数据获取或处理错误 |
| EXTERNAL_API_ERROR | 503 | 外部API服务不可用 |
| RATE_LIMIT_ERROR | 429 | 请求频率限制 |

### 示例错误

**参数验证错误:**
```json
{
  "success": false,
  "error": {
    "type": "VALIDATION_ERROR",
    "message": "开始日期不能晚于结束日期",
    "details": {
      "field": "start_date"
    }
  }
}
```

**日期范围过长:**
```json
{
  "success": false,
  "error": {
    "type": "VALIDATION_ERROR",
    "message": "查询时间范围不能超过1年",
    "details": {
      "field": "end_date"
    }
  }
}
```

## 使用示例

### Python 示例

```python
import requests
from datetime import date, timedelta

# 获取支持的版块
response = requests.get("http://localhost:8000/api/v1/market-data/sectors")
sectors = response.json()
print("支持的版块:", sectors)

# 获取金属版块的品种
response = requests.get("http://localhost:8000/api/v1/market-data/symbols?sector=metal")
symbols = response.json()
print("金属品种:", [s["symbol"] for s in symbols])

# 获取铜的历史数据
end_date = date.today()
start_date = end_date - timedelta(days=30)

response = requests.get(
    f"http://localhost:8000/api/v1/market-data/history",
    params={
        "symbol": "CU",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat()
    }
)

if response.status_code == 200:
    data = response.json()
    print(f"获取到 {len(data)} 条铜的历史数据")
    for item in data[:5]:  # 显示前5条
        print(f"{item['date']}: 开盘 {item['open_price']}, 收盘 {item['close_price']}")
else:
    print("获取数据失败:", response.json())
```

### JavaScript 示例

```javascript
// 获取版块列表
async function getSectors() {
  const response = await fetch('/api/v1/market-data/sectors');
  const sectors = await response.json();
  console.log('支持的版块:', sectors);
  return sectors;
}

// 获取历史数据
async function getMarketData(symbol, startDate, endDate) {
  const params = new URLSearchParams({
    symbol: symbol,
    start_date: startDate,
    end_date: endDate
  });

  const response = await fetch(`/api/v1/market-data/history?${params}`);

  if (response.ok) {
    const data = await response.json();
    console.log(`获取到 ${data.length} 条 ${symbol} 的历史数据`);
    return data;
  } else {
    const error = await response.json();
    console.error('获取数据失败:', error);
    throw new Error(error.error.message);
  }
}

// 刷新缓存
async function refreshData(symbol) {
  const response = await fetch('/api/v1/market-data/refresh', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      symbol: symbol,
      force_refresh: true
    })
  });

  const result = await response.json();
  console.log('刷新结果:', result);
  return result;
}
```

## 性能说明

- **缓存命中**: 从缓存获取数据，响应时间 < 50ms
- **API调用**: 从AKShare获取数据，响应时间 1-5s
- **并发支持**: 支持多个并发请求
- **数据量限制**: 单次查询最多返回1年数据
- **频率限制**: 建议单个品种每分钟不超过10次请求

## 版本历史

- **v1.0.0** (2023-12-01): 初始版本
  - 基础市场数据获取功能
  - 多版块支持
  - Redis缓存机制
  - 完整的错误处理

## 注意事项

1. **数据来源**: 数据来源于AKShare，请确保网络连接正常
2. **交易时间**: 数据获取可能受到交易所交易时间影响
3. **缓存时效**: 缓存数据可能不是最新的实时数据
4. **数据完整性**: 建议在使用前验证数据的完整性和准确性
5. **频率限制**: 避免过于频繁的API调用，以免触发限制

## 技术支持

如有问题或建议，请联系开发团队或查看项目文档。

## 更新日志

### 2023-12-01
- 实现基础的期货数据获取功能
- 支持能源、金属、农产品、化工四个版块
- 添加Redis缓存机制
- 完善错误处理和日志记录
- 提供完整的单元测试和集成测试