# Local CSV and watchlist format

Place daily bars in `collected_stocks/SYMBOL.csv`. Use UTF-8, a header row and these exact column names. Dates must use `YYYY-MM-DD`; prices must be positive finite numbers, and volume must be nonnegative. Duplicate dates and invalid OHLC ranges are rejected.

<sub>文件名对应股票代码，使用 UTF-8 和下列字段名。日期格式为年—月—日，价格必须为有限正数，成交量不得为负；重复日期及无效高低价范围会被拒绝。</sub>

```csv
Date,Open,High,Low,Close,Volume
2025-12-29,10,11,9,10.5,100000
2025-12-30,10.5,12,10,11.5,120000
```

The viewer displays the prices supplied. It does not adjust for corporate actions, convert currencies or verify a provider's data. Use consistent price and volume units in each file. The sample data uses weekdays rather than an exchange holiday calendar.

<sub>查看器直接展示所提供的价格，不进行复权、货币转换或数据源核验。同一文件须保持单位一致；虚构数据仅按工作日生成，不代表真实交易所日历。</sub>

In `picks.json`, each month maps to a list of objects containing `symbol`, `name` and `cutoff`. Symbol names support letters, numbers, underscores and hyphens. The cutoff must fall within its watchlist month. Data after that cutoff is discarded before weekly or monthly aggregation; a request cannot override the saved cutoff.

<sub>观察名单按月份组织，每行包含代码、名称及截止日。代码支持字母、数字、下划线和连字符；截止日必须属于该月。周线和月线在历史截取后聚合，请求不能覆盖保存的截止日。</sub>

Weekly and monthly bars use the first visible open, highest high, lowest low, last visible close and summed volume. Their timestamp is the last visible daily bar in that period. An incomplete final period remains partial.

<sub>聚合使用首日开盘、最高价、最低价、末日收盘及成交量合计，以该周期最后一个可见交易日标记；未结束的周期仍为部分周期。</sub>
