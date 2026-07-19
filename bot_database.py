from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "taiwanstockbot.sqlite3"
SCHEMA_VERSION = 3

DEFAULT_CATEGORIES = [
    ("指數", 10, "市場總覽"),
    ("商品", 20, "市場總覽"),
    ("外匯", 30, "市場總覽"),
    ("加密貨幣", 40, "市場總覽"),
    ("海外股票", 50, "市場總覽"),
    ("ETF", 100, "ETF"),
    ("金融", 200, "金融"),
    ("AIPC手機概念股", 300, "個股"),
    ("光通訊與CPO", 310, "個股"),
    ("機器人與自動化", 320, "個股"),
    ("先進封裝CoWoS概念", 330, "個股"),
    ("矽晶圓與晶片代工", 340, "個股"),
    ("IC設計&IP概念", 350, "個股"),
    ("液冷散熱概念", 360, "個股"),
    ("重電&綠能概念", 370, "個股"),
    ("PCB載板&SiC", 380, "個股"),
    ("太空&低軌道衛星", 390, "個股"),
    ("傳產類股", 400, "個股"),
    ("貴金屬", 410, "個股"),
    ("再生循環&稀有金屬", 415, "個股"),
    ("記憶體", 420, "個股"),
    ("被動元件", 430, "個股"),
    ("BBU&HVDC", 440, "個股"),
    ("電腦週邊&電源供應", 445, "個股"),
    ("半導體廠房", 450, "個股"),
    ("能源", 460, "個股"),
    ("工業電腦", 470, "個股"),
    ("軍工&無人機", 480, "個股"),
    ("電子代工/EMS", 490, "個股"),
    ("電子通路", 500, "個股"),
    ("面板", 510, "個股"),
    ("半導體材料", 520, "個股"),
    ("生技醫療", 530, "個股"),
    ("待分類", 999, "個股"),
]

def connect(db_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=30)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def ensure_database(db_path: Path = DATABASE_PATH) -> None:
    with connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS category_master (
                category TEXT PRIMARY KEY,
                display_order INTEGER NOT NULL,
                parent_group TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS symbol_master (
                symbol TEXT PRIMARY KEY,
                yahoo_ticker TEXT NOT NULL,
                display_name TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                market TEXT NOT NULL,
                category TEXT,
                ma_proxy_symbol TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_ohlcv (
                symbol TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL NOT NULL,
                change_value REAL,
                pct REAL,
                volume REAL,
                previous_volume REAL,
                avg5_volume REAL,
                source TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                PRIMARY KEY (symbol, trade_date)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS monthly_revenue (
                symbol TEXT NOT NULL,
                revenue_month TEXT NOT NULL,
                revenue_mom REAL,
                revenue_yoy REAL,
                revenue_ytd_yoy REAL,
                source TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                PRIMARY KEY (symbol, revenue_month)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS report_runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                stage TEXT,
                report_path TEXT,
                email_status TEXT,
                deploy_status TEXT,
                error_message TEXT,
                duration_sec REAL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS source_fetch_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                scope TEXT NOT NULL,
                asof_key TEXT,
                status TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                error_message TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS institutional_futures_snapshot (
                asof_date TEXT PRIMARY KEY,
                foreign_net INTEGER NOT NULL,
                foreign_change INTEGER NOT NULL,
                small_foreign_net INTEGER NOT NULL,
                small_foreign_change INTEGER NOT NULL,
                investment_trust_net INTEGER NOT NULL,
                investment_trust_change INTEGER NOT NULL,
                dealer_net INTEGER NOT NULL,
                dealer_change INTEGER NOT NULL,
                total_net INTEGER NOT NULL,
                total_change INTEGER NOT NULL,
                fetched_at_local TEXT NOT NULL,
                fetched_at_utc TEXT NOT NULL,
                data_source TEXT NOT NULL
            )
            """
        )

        seed_category_master(connection)
        now = datetime.now().isoformat(timespec="seconds")
        connection.execute(
            """
            INSERT INTO metadata (key, value, updated_at)
            VALUES ('schema_version', ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (str(SCHEMA_VERSION), now),
        )



def seed_category_master(connection: sqlite3.Connection | None = None) -> None:
    owns_connection = connection is None
    if connection is None:
        connection = connect()
    try:
        now = datetime.now().isoformat(timespec="seconds")
        connection.executemany(
            """
            INSERT INTO category_master (
                category, display_order, parent_group, is_active, updated_at
            ) VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(category) DO UPDATE SET
                display_order = excluded.display_order,
                parent_group = excluded.parent_group,
                is_active = excluded.is_active,
                updated_at = excluded.updated_at
            """,
            [(category, order, group, now) for category, order, group in DEFAULT_CATEGORIES],
        )
        if owns_connection:
            connection.commit()
    finally:
        if owns_connection:
            connection.close()


def upsert_symbol(
    *,
    symbol: str,
    yahoo_ticker: str,
    display_name: str,
    asset_type: str,
    market: str,
    category: str | None = None,
    ma_proxy_symbol: str | None = None,
    is_active: bool = True,
    db_path: Path = DATABASE_PATH,
) -> None:
    ensure_database(db_path)
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO symbol_master (
                symbol, yahoo_ticker, display_name, asset_type, market,
                category, ma_proxy_symbol, is_active, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                yahoo_ticker = excluded.yahoo_ticker,
                display_name = excluded.display_name,
                asset_type = excluded.asset_type,
                market = excluded.market,
                category = excluded.category,
                ma_proxy_symbol = excluded.ma_proxy_symbol,
                is_active = excluded.is_active,
                updated_at = excluded.updated_at
            """,
            (
                symbol,
                yahoo_ticker,
                display_name,
                asset_type,
                market,
                category,
                ma_proxy_symbol,
                1 if is_active else 0,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )


def count_active_symbols(db_path: Path = DATABASE_PATH) -> int:
    ensure_database(db_path)
    with connect(db_path) as connection:
        return int(
            connection.execute(
                "SELECT COUNT(*) FROM symbol_master WHERE is_active = 1"
            ).fetchone()[0]
        )


def load_active_symbols(db_path: Path = DATABASE_PATH) -> list[dict[str, Any]]:
    ensure_database(db_path)
    with connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                s.symbol,
                s.yahoo_ticker,
                s.display_name,
                s.asset_type,
                s.market,
                s.category,
                s.ma_proxy_symbol,
                COALESCE(c.display_order, 9999) AS category_order
            FROM symbol_master s
            LEFT JOIN category_master c ON c.category = s.category
            WHERE s.is_active = 1
            ORDER BY
                CASE s.market
                    WHEN 'taiwan' THEN 10
                    WHEN 'korea' THEN 20
                    WHEN 'japan' THEN 30
                    WHEN 'vietnam' THEN 40
                    WHEN 'us' THEN 50
                    WHEN 'all_day' THEN 60
                    ELSE 99
                END,
                CASE s.asset_type
                    WHEN 'index' THEN 10
                    WHEN 'stock' THEN 20
                    WHEN 'financial' THEN 30
                    WHEN 'etf' THEN 40
                    ELSE 50
                END,
                category_order,
                s.symbol
            """
        ).fetchall()
        return [dict(row) for row in rows]

def upsert_monthly_revenue(
    symbol: str,
    revenue: dict[str, Any],
    db_path: Path = DATABASE_PATH,
) -> None:
    revenue_month = str(revenue.get("revenue_month") or "").strip()
    if not revenue_month:
        return

    ensure_database(db_path)
    fetched_at = datetime.now().isoformat(timespec="seconds")
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO monthly_revenue (
                symbol, revenue_month, revenue_mom, revenue_yoy,
                revenue_ytd_yoy, source, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, revenue_month) DO UPDATE SET
                revenue_mom = excluded.revenue_mom,
                revenue_yoy = excluded.revenue_yoy,
                revenue_ytd_yoy = excluded.revenue_ytd_yoy,
                source = excluded.source,
                fetched_at = excluded.fetched_at
            """,
            (
                symbol,
                revenue_month,
                revenue.get("revenue_mom"),
                revenue.get("revenue_yoy"),
                revenue.get("revenue_ytd_yoy"),
                revenue.get("revenue_source") or "unknown",
                fetched_at,
            ),
        )



def load_latest_monthly_revenue_cache(db_path: Path = DATABASE_PATH) -> dict[str, dict[str, Any]]:
    ensure_database(db_path)
    with connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                r.symbol,
                r.revenue_month,
                r.revenue_mom,
                r.revenue_yoy,
                r.revenue_ytd_yoy,
                r.source,
                r.fetched_at
            FROM monthly_revenue r
            JOIN (
                SELECT symbol, MAX(revenue_month) AS revenue_month
                FROM monthly_revenue
                GROUP BY symbol
            ) latest
            ON latest.symbol = r.symbol AND latest.revenue_month = r.revenue_month
            ORDER BY r.symbol
            """
        ).fetchall()

    def format_pct(value: Any) -> str:
        if value is None:
            return 'N/A'
        try:
            return f"{float(value):+.2f}%"
        except (TypeError, ValueError):
            return 'N/A'

    cache: dict[str, dict[str, Any]] = {}
    for row in rows:
        revenue_month = str(row['revenue_month'] or '').strip()
        month_label = revenue_month or '最新月份'
        revenue_mom = row['revenue_mom']
        revenue_yoy = row['revenue_yoy']
        revenue_ytd_yoy = row['revenue_ytd_yoy']
        cache[row['symbol']] = {
            'revenue_month': revenue_month,
            'revenue_mom': revenue_mom,
            'revenue_yoy': revenue_yoy,
            'revenue_ytd_yoy': revenue_ytd_yoy,
            'revenue_summary': (
                f"{month_label} 營收 MoM {format_pct(revenue_mom)}，"
                f"YoY {format_pct(revenue_yoy)}，"
                f"今年累計 YoY {format_pct(revenue_ytd_yoy)}"
            ),
            'revenue_source': f"SQLite cache ({str(row['source'] or 'unknown').strip() or 'unknown'})",
            'revenue_fetched_at': row['fetched_at'],
        }
    return cache


def upsert_daily_ohlcv(
    *,
    symbol: str,
    trade_date: str,
    close: float,
    source: str,
    fetched_at: str,
    open_value: float | None = None,
    high: float | None = None,
    low: float | None = None,
    change_value: float | None = None,
    pct: float | None = None,
    volume: float | None = None,
    previous_volume: float | None = None,
    avg5_volume: float | None = None,
    db_path: Path = DATABASE_PATH,
) -> None:
    ensure_database(db_path)
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO daily_ohlcv (
                symbol, trade_date, open, high, low, close, change_value, pct,
                volume, previous_volume, avg5_volume, source, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, trade_date) DO UPDATE SET
                open = COALESCE(excluded.open, daily_ohlcv.open),
                high = COALESCE(excluded.high, daily_ohlcv.high),
                low = COALESCE(excluded.low, daily_ohlcv.low),
                close = excluded.close,
                change_value = excluded.change_value,
                pct = excluded.pct,
                volume = excluded.volume,
                previous_volume = excluded.previous_volume,
                avg5_volume = excluded.avg5_volume,
                source = excluded.source,
                fetched_at = excluded.fetched_at
            """,
            (
                symbol,
                trade_date,
                open_value,
                high,
                low,
                close,
                change_value,
                pct,
                volume,
                previous_volume,
                avg5_volume,
                source,
                fetched_at,
            ),
        )

def log_source_fetch(
    source: str,
    scope: str,
    status: str,
    *,
    asof_key: str | None = None,
    error_message: str | None = None,
    db_path: Path = DATABASE_PATH,
) -> None:
    ensure_database(db_path)
    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO source_fetch_log (
                source, scope, asof_key, status, fetched_at, error_message
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                source,
                scope,
                asof_key,
                status,
                datetime.now().isoformat(timespec="seconds"),
                error_message,
            ),
        )

def upsert_institutional_futures_snapshot(snapshot: dict[str, Any], db_path: Path = DATABASE_PATH) -> None:
    asof_date = str(snapshot.get("asof_date") or "").strip()
    if not asof_date:
        return

    ensure_database(db_path)
    fetched_at_local = str(snapshot.get("fetched_at_local") or "").strip()
    fetched_at_utc = str(snapshot.get("fetched_at_utc") or "").strip()
    data_source = str(snapshot.get("data_source") or "WantGoo cache").strip() or "WantGoo cache"
    if not fetched_at_local:
        fetched_at_local = datetime.now().isoformat(timespec="seconds")
    if not fetched_at_utc:
        fetched_at_utc = fetched_at_local

    with connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO institutional_futures_snapshot (
                asof_date, foreign_net, foreign_change, small_foreign_net, small_foreign_change,
                investment_trust_net, investment_trust_change, dealer_net, dealer_change,
                total_net, total_change, fetched_at_local, fetched_at_utc, data_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(asof_date) DO UPDATE SET
                foreign_net = excluded.foreign_net,
                foreign_change = excluded.foreign_change,
                small_foreign_net = excluded.small_foreign_net,
                small_foreign_change = excluded.small_foreign_change,
                investment_trust_net = excluded.investment_trust_net,
                investment_trust_change = excluded.investment_trust_change,
                dealer_net = excluded.dealer_net,
                dealer_change = excluded.dealer_change,
                total_net = excluded.total_net,
                total_change = excluded.total_change,
                fetched_at_local = excluded.fetched_at_local,
                fetched_at_utc = excluded.fetched_at_utc,
                data_source = excluded.data_source
            """,
            (
                asof_date,
                snapshot.get("foreign_net"),
                snapshot.get("foreign_change"),
                snapshot.get("small_foreign_net"),
                snapshot.get("small_foreign_change"),
                snapshot.get("investment_trust_net"),
                snapshot.get("investment_trust_change"),
                snapshot.get("dealer_net"),
                snapshot.get("dealer_change"),
                snapshot.get("total_net"),
                snapshot.get("total_change"),
                fetched_at_local,
                fetched_at_utc,
                data_source,
            ),
        )


def load_latest_institutional_futures_snapshot(db_path: Path = DATABASE_PATH) -> dict[str, Any] | None:
    ensure_database(db_path)
    with connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT
                asof_date, foreign_net, foreign_change, small_foreign_net, small_foreign_change,
                investment_trust_net, investment_trust_change, dealer_net, dealer_change,
                total_net, total_change, fetched_at_local, fetched_at_utc, data_source
            FROM institutional_futures_snapshot
            ORDER BY asof_date DESC
            LIMIT 1
            """
        ).fetchone()
        return dict(row) if row else None
