---
name: manage-taiwan-stock-report
description: Control the TaiwanStockBot market-report workflow end to end. Use when Codex needs to refresh market data, enforce latest-date checks, generate or review the report, maintain the required Taiwan/Asia/US index analysis, industry-leader commentary and ETF group coverage, run without duplicate email, deploy Firebase Hosting, verify the public version, or diagnose stale report data.
---

# Manage TaiwanStockBot Report

Operate the report pipeline conservatively: prove data dates, preserve the report contract, deploy only validated output, and verify the public site.

## Load project context

1. Work from the repository root.
2. Read `Doc/WORKFLOW_HANOFF.md`, `Doc/Agents.md`, `Doc/QUICKSTART.md`, `firebase.json`, and `.firebaserc` as needed.
3. Read [references/report-contract.md](references/report-contract.md) before changing prompts, validation, report structure, or coverage.
4. Inspect `git status --short --branch`. Preserve unrelated user changes.
5. Treat `data/taiwanstockbot.sqlite3`, generated reports, caches, and logs as local runtime artifacts unless the repository says otherwise.

## Choose the operation

- For a question such as “is this data current?”, diagnose only. Inspect the generated input, SQLite row, source, and official/latest source. Do not modify or deploy unless asked.
- For a report-control change, edit the durable pipeline (`run_bot.ps1`, `fetch_stock_data.py`, `Doc/Agents.md`, validation) and verify syntax before running.
- For “update the website”, run the full pipeline, wait for its background Firebase deploy, and verify the public version.
- Do not commit or push unless the user asks. Always report modified tracked files.

## Enforce freshness

1. Never equate report generation time with source-data time.
2. For TAIFEX institutional futures, query the official TX open-interest table on every run. SQLite is failure fallback only. Require:
   - an explicit `資料日期`;
   - `live-taifex-tx-open-interest` for a successful live query;
   - FINI net position and change from the preceding trading day;
   - no substitution of trading-volume columns or the all-contract table.
3. For margin data, record the latest date returned by the live source. A prior trading date can still be current when the present-day official table is not published. Verify against the official TWSE daily margin endpoint before calling it stale.
4. For closed markets, allow the latest stored trading-day snapshot and label it. For trading markets, require a live attempt.
5. Never silently replace a failed live attempt with an undated cache. Print the cache date and source.
6. After a requested full refresh, require the report generation date to be the current Taipei calendar date. Source dates may be earlier only when the official source confirms that no newer trading-day row exists.

## Modify report controls

1. Put durable generation requirements in the Analyzer prompt in `run_bot.ps1` and the Analyzer instructions in `Doc/Agents.md`.
2. Add pre-publish validation for mandatory sections or named coverage. Fail before HTML/deployment if the contract is incomplete.
3. Keep narrative additive to the four established tables: 市場總覽, ETF 操作表, 金融股操作表, 個股操作表.
4. Require exact point/price, moving-average position, volume context, and a conclusion. Do not invent news, orders, customers, guidance, capacity plans, or market-share changes.
5. If tables use compact moving-average notation such as `5-、10+`, add an explicit legend explaining `+`, `-`, and `=`. Use each fixed display name once; reject duplicated labels such as `美元指數 美元指數`.
6. Parse-check edited PowerShell and AST-check edited Python. Run `git diff --check`.

## Run the full refresh

Unless the user explicitly requests email, prevent duplicate mail while retaining deployment:

```powershell
$env:TAIWANSTOCKBOT_SKIP_EMAIL='1'
Remove-Item Env:TAIWANSTOCKBOT_SKIP_SYNC -ErrorAction SilentlyContinue
& .\run_bot.ps1
```

Use a command timeout of at least 30 minutes. The Analyzer can take several minutes and may keep its output file at zero bytes until completion. Provide progress updates at least once per minute.

If the command runner times out, inspect the newest `Reports/run_bot_*.log`, process start times, and generated files. Do not start a duplicate run or kill a generic `codex`, `node`, or PowerShell process without proving it belongs to the abandoned run.

## Complete Firebase deployment

When deployment is in scope, also activate `firebase-hosting-basics` and follow its current Classic Hosting instructions.

1. Read the main run output for the background PID and `Reports/post_report_sync_*.log` path.
2. Wait for that exact background process to exit.
3. Require `release complete` and `Firebase deploy completed` in its log.
4. Verify `https://vinson-stock-bot.web.app/report-version.json` returns HTTP 200 and matches local `web/report-version.json`.
5. Verify the public HTML contains the required report sections and coverage tokens.

## Run deterministic validation

Run the bundled checker after local generation and again with the public URL after deployment. The strict flags query official TWSE/TAIFEX dates, require a report generated today, compare the archived HTML with `web/index.html`, and inspect the deployment log:

```powershell
.\.venv\Scripts\python.exe .agents\skills\manage-taiwan-stock-report\scripts\verify_report.py --check-official-dates --max-report-age-days 0
.\.venv\Scripts\python.exe .agents\skills\manage-taiwan-stock-report\scripts\verify_report.py --check-official-dates --max-report-age-days 0 --check-deploy-log --public-url https://vinson-stock-bot.web.app
```

Treat any nonzero result as a blocker. Do not claim success from a deploy log alone.

## Hand off

Report:

- report version and generated time;
- TAIFEX and margin source dates;
- local report and deployment log paths;
- public HTTP/version verification;
- whether email was skipped;
- tracked files left modified and whether Git remains uncommitted.

Use the timestamped article path reported by the run, normally `Reports/final_article_<runstamp>.txt`. Do not require a root-level `final_article.txt` when the current pipeline intentionally archives the article.
