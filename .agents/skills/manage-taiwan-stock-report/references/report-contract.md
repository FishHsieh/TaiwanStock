# TaiwanStockBot report contract

Use this contract when changing prompts, validation, or reviewing a generated report.

## Required index analysis

Include exact point level, daily change, 5-day/10-day/monthly/quarterly/half-year/yearly moving-average position, volume context when available, and a technical conclusion:

- 台灣指數: Taiwan Weighted Index and TPEx/OTC Index.
- 韓日股市: Korea KOSPI and Japan Nikkei 225.
- 美國股市: S&P 500, NASDAQ Composite, and Philadelphia Semiconductor Index.
- Use SOXX only as the Philadelphia Semiconductor Index moving-average proxy and label it explicitly.

Keep the established market overview coverage for Taiwan/OTC, Korea, Japan, semiconductor index, NASDAQ, S&P 500, TLT, Vietnam, DXY, JPY, gold, oil, and Bitcoin. If comparable moving averages remain unavailable after fallback, omit the table row and explain it in narrative.

## Required industry leaders

The `產業龍頭觀察` section must cover these leaders whenever current input exists:

- 2330台積電 — 晶圓代工
- 2454聯發科 — IC 設計
- 2308台達電 — 電源／資料中心基礎設施
- 2383台光電 — 高階 CCL
- 2327國巨 — 被動元件
- 3711日月光投控 — 封裝測試
- 2317鴻海 — 電子代工／AI 伺服器

For each, use 2–4 substantive sentences covering price and moving averages, volume versus prior day and 5-day average, latest revenue MoM/YoY/YTD YoY, industry role, relevant supplied demand/cross-market signal, and a short-term conclusion. Separate long-term leadership from current technical strength.

## Required ETF grouping

Use full Chinese display names. Keep these groups in this order in `ETF 分組觀察` and `ETF 操作表`:

1. 市值型 ETF: 0050, 009816
2. 主動型國內 ETF: 00981A, 00403A, 00991A
3. 主動型國外 ETF: 00988A, 00990A
4. 國外 ETF: 00909, 00895, 00830, 00757, 00735, 00924, 00876, 00910
5. 高股息 ETF: 0056, 00919, 00878, 00900, 00713

For each named ETF with data, include latest price/change, full moving-average position, volume context, and conclusion. Append other active ETFs after the required groups; do not omit valid active rows.

## Required sections and tables

Narrative sections:

- 台灣指數
- 韓日股市
- 美國股市
- 產業龍頭觀察
- ETF 分組觀察

Markdown tables:

- 市場總覽
- ETF 操作表
- 金融股操作表
- 個股操作表

## Interpretation rules

- Do not call a same-day decline near or worse than -3% “相對抗跌” merely because long moving averages remain intact.
- Interpret higher `JPY=X` as a weaker yen.
- Label Cleveland Fed CPI values as nowcasts, not official BLS CPI.
- Explain FINI net position and day-over-day change, financing/short balance changes, margin ratio, gold, oil, and Taiwan's latest three export months.
- Use the full moving-average wording in narrative. Compact notation in a table is acceptable only if its legend is unambiguous.
- Never invent missing fundamental or corporate-event facts.
