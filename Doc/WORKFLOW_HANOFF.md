# TaiwanStockBot Workflow Handoff

Last updated: 2026-07-15

## Purpose

This project generates a daily market report, publishes it as HTML, syncs it to Google Docs / Sheets, updates the Firebase-hosted site, and emails the result.

## Completed Log

Use this section as the durable record of what has already been finished. Check it before repeating work.

- 2026-07-15: Full report flow reran successfully via `run_bot.ps1`; generated `Reports\Report_20260715_1411.html`, wrote transcript `Reports\run_bot_20260715_140705.log`, and emailed `vinson_hsieh@cyberlink.com`.
- 2026-07-15: The repository was committed and pushed to `origin/main` at `597f4cefbb8336d6e69e1e8cbefda64bbf353651`; working tree was clean after the push.
- 2026-07-15: The current session handoff state is now recorded here so the next run can continue from the latest working report pipeline without re-deriving the same fixes.
- 2026-07-07: Web report auto-refresh is now 5 seconds, with an immediate first check on load.
- 2026-07-07: Individual Taiwan stocks now include the latest monthly revenue and YoY revenue growth when available.
- 2026-07-07: ETFs and indices skip the monthly revenue field instead of showing misleading blanks.
- 2026-07-07: `fetch_sheet_trade_context.py` now falls back to Yahoo historical data when Google Sheet moving-average cells are missing or `#N/A`.
- 2026-07-07: The latest verified run completed successfully and produced `Reports\Report_20260707_1450.html`.
- 2026-07-07: TAIFEX futures wording was changed from "short open interest" to "net position" in the prompts and current visible report/web artifacts.
- 2026-07-08: Revenue context now reports latest month MoM/YoY and year-to-date YoY, without listing revenue amount.
- 2026-07-08: Added `data\taiwanstockbot.sqlite3` schema bootstrap via `bot_database.py`; live market snapshots now persist to `daily_ohlcv`, and revenue fetches persist to `monthly_revenue`.
- 2026-07-08: Added `symbol_master` / `category_master` maintenance workflow via `manage_symbols.py`; `fetch_stock_data.py` now loads active report symbols from SQLite instead of relying only on the hard-coded `MARKETS` list.

- 2026-07-08: Completed full workflow run and generated `Reports\Report_20260708_1624.html`; email was sent to `vinson_hsieh@cyberlink.com`.
- 2026-07-08: Fixed `run_bot.ps1` duplicate UTF-8 BOM at file start; this prevents PowerShell from treating `﻿#` as a command and helps avoid Scheduler `0x1` false failures.
- 2026-07-08: Added UTF-8 Python output environment variables in `run_bot.ps1` / `post_report_sync.ps1` and added a resilient `?symbol?` fallback in `publish_google_workspace.py` so Google Workspace sync can parse market data even if PowerShell redirection corrupts full-width brackets.
- 2026-07-08: Google Workspace sync was rerun successfully after parser fix; updated Sheet and Doc URLs remain in `google_workspace_state.json`, and Firebase Hosting deployed to `https://vinson-stock-bot.web.app`.
- 2026-07-08: Added active symbols `6239力成`, `6176瑞儀`, `2059川湖`, `3231緯創`, `2392正崴`, and `2377微星` to `symbol_master` and bootstrap metadata; active universe count is now 114.
- 2026-07-08: Analyzer prompt now explicitly says not to summarize away active Taiwan securities that have valid moving-average context.
- 2026-07-08: Reran full workflow with `TAIWANSTOCKBOT_SKIP_EMAIL=1` after sheet-context/parser fixes; generated `Reports\Report_20260708_1624.html`, updated Google Sheet/Doc, deployed Firebase, and intentionally did not send a duplicate email.
- 2026-07-08: Added `TAIWANSTOCKBOT_SKIP_EMAIL=1` support to `run_bot.ps1` for safe no-email reruns.
- 2026-07-08: Rewrote `run_bot.ps1` and `post_report_sync.ps1` with exactly one UTF-8 BOM so Windows PowerShell 5 `-File` reads Chinese strings correctly without leaving a duplicate BOM command.
- 2026-07-08: Restored core `fetch_stock_data.py` market-data output labels to readable Chinese brackets/field names (`【標的】`, 最新價格, 漲跌, 漲跌幅, 成交量, 量能, 資料來源).
- 2026-07-09: Institutional futures / foreign open-interest now reads from the SQLite cache seeded with WantGoo net open interest (foreign `-81,268` on 2026-07-08); the report no longer depends on live TAIFEX open-interest scraping.
- 2026-07-08: Refined classification taxonomy: added 再生循環&稀有金屬 and 電腦週邊&電源供應, moved 7610聯友金屬 out of 貴金屬, and moved 2301光寶科 out of BBU&HVDC.
## Do Not Re-Do

- Do not reintroduce manual page refresh for the report site; auto-refresh is already in place.
- Do not force monthly revenue onto ETFs or indices; it only applies to individual stocks.
- Do not assume Google Sheet moving averages are missing just because the API returned #N/A; the code already has a Yahoo fallback.
- Do not read the `Trading Volume and Trading Value` table on TAIFEX `totalTableDate` as foreign futures open interest; the report now uses the SQLite-cached WantGoo net open-interest snapshot instead.


## Data Lifecycle Rules

Use these rules when changing cache, database, or report generation behavior.

- On startup, if the database has no usable data for the current report date and source, fetch live data once and store it before generating the report.
- During active trading sessions, always fetch live market data for the markets that are currently trading; do not rely only on yesterday's database snapshot.
- For closed markets, reuse the latest database snapshot for that market unless the current report date has no stored snapshot yet.
- Report generation should combine fresh live snapshots with persisted database data, then derive conclusions from the merged state.
- Monthly revenue applies only to individual Taiwan stocks. Show the latest revenue month, MoM, YoY, and year-to-date YoY; do not list revenue amount in the report.
- ETFs, indices, commodities, FX, crypto, and overseas index rows should skip monthly revenue fields.
- Long-lived reference data belongs in SQLite: symbol master, ETF Chinese names, category mapping, market hours, source metadata, and manual overrides.
- Taiwan stock classification is source-backed reference data. Prefer company main business, exchange/Yahoo industry, official company product lines, and CMoney concept pages; do not let the Analyzer invent a category when symbol_master already has one.
- The canonical report universe is `symbol_master`; `MARKETS` in `fetch_stock_data.py` is now only the bootstrap fallback when the database is empty.
- The shared runtime database path is data\taiwanstockbot.sqlite3; it is generated locally and ignored by git.
- Rebuildable intermediate results can stay as cache: Google Sheet response cache, Yahoo history MA cache, latest live snapshot fallback, and generated report-version metadata.
## Symbol Maintenance Workflow

Use this workflow whenever adding or changing a tracked symbol.

1. Check valid categories: `python manage_symbols.py categories`.
1. Decide the symbol metadata before adding it: canonical Yahoo ticker, Chinese display name, asset type, market, category, and optional MA proxy.
1. Add or update the symbol with `python manage_symbols.py add --symbol <ticker> --name <display name> --asset-type <type> --market <market> --category <category>`.
1. Use `--ma-proxy-symbol <ticker>` when one instrument should use another instrument's moving averages, for example `^SOX` using `SOXX`.
1. If the existing category list is too broad or misleading, add a precise durable category in `bot_database.py` `DEFAULT_CATEGORIES`, run `python -c "from bot_database import ensure_database; ensure_database()"`, then update the symbol in `symbol_master`.
1. If a new Taiwan stock category is uncertain, add it as `待分類` first, then classify it before relying on the report table.
1. Use `python manage_symbols.py list` to verify the active universe and category grouping.
1. Use `python manage_symbols.py deactivate <symbol>` instead of deleting rows when a symbol should stop appearing in reports.

Examples:

```powershell
python manage_symbols.py categories
python manage_symbols.py add --symbol 2376.TW --name 2376技嘉 --asset-type stock --market taiwan --category AIPC手機概念股
python manage_symbols.py add --symbol 2301.TW --name 2301光寶科 --asset-type stock --market taiwan --category '電腦週邊&電源供應'
python manage_symbols.py add --symbol 7610.TW --name 7610聯友金屬 --asset-type stock --market taiwan --category '再生循環&稀有金屬'
python manage_symbols.py add --symbol ^SOX --name 費城半導體指數 --asset-type index --market us --category 指數 --ma-proxy-symbol SOXX
python manage_symbols.py deactivate 9999.TW
```
## End-to-End Flow

1. `run_bot.ps1` is the main entry point.
1. `fetch_stock_data.py` collects live market prices and writes `market_data.txt`.
1. `fetch_sheet_trade_context.py` reads the Google Sheet moving-average data and writes `sheet_trade_context.json`.
1. The Analyzer agent reads `market_data.txt` plus `sheet_trade_context.json` and writes `final_article.txt`.
1. `run_bot.ps1` converts the article into HTML and writes the latest report to `Reports\Report_YYYYMMDD_HHMM.html`.
1. `publish_google_workspace.py` syncs the article/report into Google Docs and Google Sheets.
1. `run_bot.ps1` updates `web\index.html` and deploys the site to Firebase Hosting.
1. The bot emails the final output to `vinson_hsieh@cyberlink.com`.

## Current Output Targets

- `market_data.txt`
- `sheet_trade_context.json`
- `final_article.txt`
- `Reports\Report_*.html`
- `web\index.html`
- Google Sheet and Google Doc synced by the pipeline

## Key Roles

- Analyzer: market interpretation, cross-market relationships, and buy/hold/sell style guidance.
- Writer: turns the analysis into a publishable market update with a news style.

## Current Market Coverage

The pipeline now covers:

- Taiwan
- Vietnam (`越南大盤 (VNINDEX)`)
- Japan
- Korea
- US indices
- Semiconductor index
- JPY
- TLT
- Bitcoin
- Gold
- Oil
- Samsung
- SK Hynix

Active Taiwan stocks and ETFs are maintained in `symbol_master`; use `python manage_symbols.py list` for the live list. The bootstrap snapshot currently includes:

- 2330, 3711, 2303, 2454, 2317, 2382, 2308, 2383, 3008, 2313, 2357, 2344, 6196, 2408, 5203, 2301, 3702, 3034, 2376, 5274, 3443, 8299, 2327, 3037, 3653, 2449, 6274, 3017, 7610, 3481, 6770, 6409, 8046, 3189, 6213, 6223, 3035, 2049, 6139, 1560, 2458, 6446, 2312, 6239, 6176, 2059, 3231, 2392, 2377
- 0050, 0052, 00947, 00631L, 00830, 00876, 00909, 009805, 00910, 0056, 00919, 00878, 00922, 00991A, 00981A, 00735, 00990A, 00988A, 00982A, 00900, 00891, 00403A, 009816, 00646, 00911, 00895, 00757, 00713, 00915, 00918, 00924, 00635U, 00738U, 00763U, 00642U, 00917
- 2801, 2892, 2886, 2834, 2812, 2890, 2880, 2883, 2884, 2885, 2881, 2882, 2855
- Semiconductor index uses SOXX as the moving-average proxy for its annotation.
- Sheet gaps or #N/A values now fall back to Yahoo history before a row is omitted.

## Google Sheet Moving Averages

The sheet-based trade context compares live prices against the Google Sheet first and falls back to Yahoo history when a row or MA is missing.

- 5-day MA
- 10-day MA
- Monthly MA
- Quarterly MA
- Half-year MA
- Yearly MA

The canonical source sheet is:

- `1WQNCHJfK5CXluCeWsSee64NczdG6DapcbBkI7C8OuFI`

## Important Files

- [run_bot.ps1](run_bot.ps1)
- [bot_database.py](bot_database.py)
- [manage_symbols.py](manage_symbols.py)
- [fetch_stock_data.py](fetch_stock_data.py)
- [fetch_sheet_trade_context.py](fetch_sheet_trade_context.py)
- [publish_google_workspace.py](publish_google_workspace.py)
- [Agents.md](Agents.md)
- [GOOGLE_SITES_EMBED.md](GOOGLE_SITES_EMBED.md)
- [CREDENTIALS_AND_PERMISSIONS.md](CREDENTIALS_AND_PERMISSIONS.md)
- [FIREBASE_MAPPING.md](FIREBASE_MAPPING.md)

## Google Sites / Hosting Notes

- Google Sites does not live-watch local `index.html`.
- The live content comes from the Google Doc / Google Sheet and the Firebase-hosted web page.
- Firebase Hosting URL: `https://vinson-stock-bot.web.app`
- For Windows Task Scheduler, prefer launching `run_bot.ps1` with `powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "F:\TaiwanStockBot\run_bot.ps1"`.
- Each run now writes a transcript log to `Reports\run_bot_YYYYMMDD_HHMMSS.log`.


## Scheduler Troubleshooting Notes

- If Scheduler shows `0x1`, first check `Reports\run_bot_*.log` and confirm the first line of `run_bot.ps1` starts with `#`, not a hidden BOM character before `#`.
- If Google Workspace sync says `No market rows found`, check whether `market_data.txt` section headers became `?標的?`; `publish_google_workspace.py` now supports this fallback, but future output should be protected by `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1`.
- `post_report_sync.ps1` now loads `google_workspace.local.ps1` directly, so manual reruns should have the same Google env as `run_bot.ps1`.
## Resume Checklist

When continuing next time:

1. Start from `F:\TaiwanStockBot` and run `run_bot.ps1` for the full pipeline.
1. Confirm the latest `Reports\Report_*.html` and `Reports\run_bot_*.log`.
1. Check whether `origin/main` still points to `597f4cefbb8336d6e69e1e8cbefda64bbf353651` before making new changes.
1. Add/update symbols through `manage_symbols.py` and verify `symbol_master`; avoid editing prompt-only ticker lists.
1. Confirm `market_data.txt`, `sheet_trade_context.json`, and `final_article.txt`.
1. Check Firebase deployment status if the site should be public.
1. Confirm email delivery if needed.

## Recent Stable State

As of 2026-06-29, the pipeline already includes:

- Vietnam index via official HOSE source
- JPY and TLT coverage
- Google Sheet MA comparison
- News-style article rendering
- Python execution through project-local `.venv`
- Node runtime through project-local `tools\nodejs`
- Firebase CLI through project-local `node_modules`
- Firebase Hosting deployment
- Email delivery to the configured recipient

## Related Files

- [CREDENTIALS_AND_PERMISSIONS.md](CREDENTIALS_AND_PERMISSIONS.md)
- [FIREBASE_MAPPING.md](FIREBASE_MAPPING.md)
