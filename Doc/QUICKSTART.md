# TaiwanStockBot Quickstart

This is the short handoff version. It is not a time limit. It only keeps the minimum steps needed to resume the workflow quickly.

## If you only have a few minutes

1. Read `WORKFLOW_HANOFF.md` for the full context.
2. Run `run_bot.ps1`. It will create and use `.venv`, `tools\nodejs`, and local `node_modules` automatically if needed.
3. Check the generated artifacts:
   - `market_data.txt`
   - `sheet_trade_context.json`
   - `final_article.txt`
4. Open the latest HTML report in `Reports\Report_*.html`.
5. If the public page should be updated, verify the Firebase site:
   - `https://vinson-stock-bot.web.app`
   - [FIREBASE_MAPPING.md](FIREBASE_MAPPING.md)
6. If the Google Doc / Sheet output is wrong, inspect:
   - `publish_google_workspace.py`
   - [CREDENTIALS_AND_PERMISSIONS.md](CREDENTIALS_AND_PERMISSIONS.md)
7. If the data universe or prompts need changes, inspect:
   - `manage_symbols.py`
   - `fetch_stock_data.py`
   - `run_bot.ps1`
   - `Agents.md`

## Add or update a symbol

The active report universe lives in SQLite `symbol_master`, not only in prompts. Classifications should be source-backed; if the current buckets are too broad, add a precise category to ot_database.py first, seed the database, then update symbol_master.

```powershell
python manage_symbols.py categories
python manage_symbols.py list
python manage_symbols.py add --symbol 2376.TW --name 2376技嘉 --asset-type stock --market taiwan --category AIPC手機概念股
python manage_symbols.py add --symbol 2301.TW --name 2301光寶科 --asset-type stock --market taiwan --category '電腦週邊&電源供應'
python manage_symbols.py add --symbol 7610.TW --name 7610聯友金屬 --asset-type stock --market taiwan --category '再生循環&稀有金屬'
python manage_symbols.py deactivate 9999.TW
```

Use `--ma-proxy-symbol` when a row should borrow another ticker's moving averages, for example `^SOX` using `SOXX`.
## What this project currently does

- Pulls live market data.
- Reads Google Sheet moving averages for trade context.
- Generates an analyzer pass and a writer pass.
- Publishes a news-style report as HTML.
- Syncs the result to Google Docs / Sheets.
- Deploys the web version.
- Emails the final output to `vinson_hsieh@cyberlink.com`.

## Current coverage snapshot

The current active list is generated from `symbol_master`; run `python manage_symbols.py list` for the live source of truth.

- Bootstrap Taiwan stocks and ETFs: 2330, 3711, 2303, 2454, 2317, 2382, 2308, 2383, 3008, 2313, 2357, 2344, 6196, 2408, 5203, 2301, 3702, 3034, 2376, 5274, 3443, 8299, 2327, 3037, 3653, 2449, 6274, 3017, 7610, 3481, 6770, 6409, 8046, 3189, 6213, 6223, 3035, 2049, 6139, 1560, 2458, 6446, 2312, 6239, 6176, 2059, 3231, 2392, 2377, 0050, 0052, 00947, 00631L, 00830, 00876, 00909, 009805, 00910, 0056, 00919, 00878, 00922, 00991A, 00981A, 00735, 00990A, 00988A, 00982A, 00900, 00891, 00403A, 009816, 00646, 00911, 00895, 00757, 00713, 00915, 00918, 00924, 00635U, 00738U, 00763U, 00642U, 00917
- Financial stocks: 2801, 2892, 2886, 2834, 2812, 2890, 2880, 2883, 2884, 2885, 2881, 2882, 2855
- Cross-market: Vietnam, Japan, Korea, US indices, semiconductor index (SOXX proxy), JPY, TLT, Bitcoin, gold, oil, Samsung, SK Hynix

## Related Files

- [CREDENTIALS_AND_PERMISSIONS.md](CREDENTIALS_AND_PERMISSIONS.md)
- [FIREBASE_MAPPING.md](FIREBASE_MAPPING.md)
