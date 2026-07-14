# TaiwanStockBot

TaiwanStockBot is a daily market-report pipeline for Taiwan stocks, ETFs, and cross-market signals. It fetches market data, builds moving-average context from Google Sheets and Yahoo fallback data, generates a news-style report, publishes HTML and Google Workspace outputs, deploys the web page, and emails the final result.

## What it does

- Collects live market data for Taiwan, Japan, Korea, Vietnam, US indices, FX, commodities, crypto, and selected stocks/ETFs.
- Reads moving-average context from the canonical Google Sheet and falls back to Yahoo history when sheet cells are missing or `#N/A`.
- Maintains symbol metadata, categories, and market-hours references in SQLite.
- Generates a news-style analysis article and a web-friendly HTML report.
- Syncs outputs to Google Docs / Google Sheets, Firebase Hosting, and email.

## Main entry point

- `run_bot.ps1`

## Quick start

1. Open `Doc/QUICKSTART.md` for the shortest resume path.
2. Run `run_bot.ps1` from the project root.
3. Review the generated artifacts:
   - `market_data.txt`
   - `sheet_trade_context.json`
   - `final_article.txt`
   - `Reports/Report_*.html`
4. Check the web output at `https://vinson-stock-bot.web.app`.

## Prerequisites

The project is designed to bootstrap its own local runtime when needed:

- Python virtual environment in `.venv`
- Portable Node runtime in `tools/nodejs`
- Local Node modules in `node_modules`

You normally do not need a global Python or Node install once the project has been bootstrapped.

## Repository layout

- `run_bot.ps1` - orchestrates the full workflow
- `fetch_stock_data.py` - fetches live market data and writes `market_data.txt`
- `fetch_sheet_trade_context.py` - reads sheet moving averages and caches trade context
- `bot_database.py` - SQLite schema and cache helpers
- `manage_symbols.py` - maintains tracked symbols and categories
- `publish_google_workspace.py` - syncs to Google Docs / Sheets
- `post_report_sync.ps1` - post-processing and publish helper
- `web/` - Firebase Hosting site source
- `Doc/` - project documentation and handoff notes
- `Reports/` - generated reports and logs
- `data/` - local SQLite databases

## Data and cache rules

- `data/taiwanstockbot.sqlite3` is the shared local database.
- Generated reports and logs stay under `Reports/`.
- Runtime scratch files and old outputs are kept out of git by `.gitignore`.
- Symbol and category updates should go through `manage_symbols.py` instead of hard-coding lists in prompts.

## Tracking scope

The current tracked universe includes:

- Taiwan stocks and ETFs maintained in `symbol_master`
- Financial stocks
- Cross-market references such as Vietnam, Japan, Korea, NASDAQ, S&P 500, SOX proxy, TLT, JPY, Bitcoin, gold, oil, Samsung, and SK Hynix

Use this command to inspect the live tracked universe:

```powershell
python manage_symbols.py list
```

## Moving-average logic

The report compares live prices against these moving averages when available:

- 5-day
- 10-day
- Monthly
- Quarterly
- Half-year
- Yearly

If the Google Sheet cell is missing or not usable, the pipeline falls back to Yahoo history.

## Output targets

- `market_data.txt`
- `sheet_trade_context.json`
- `final_article.txt`
- `Reports/Report_*.html`
- `web/index.html`
- Google Docs / Google Sheets sync outputs

## References

- `Doc/QUICKSTART.md`
- `Doc/WORKFLOW_HANOFF.md`
- `Doc/CREDENTIALS_AND_PERMISSIONS.md`
- `Doc/FIREBASE_MAPPING.md`
- `Doc/GOOGLE_SITES_EMBED.md`

## GitHub

Project repository:

- https://github.com/FishHsieh/TaiwanStock
