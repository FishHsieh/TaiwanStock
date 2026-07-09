from __future__ import annotations

import argparse
import sqlite3
from typing import Any

from bot_database import DATABASE_PATH, connect, ensure_database, upsert_symbol


def list_categories() -> None:
    ensure_database()
    with connect() as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT category, parent_group, display_order
            FROM category_master
            WHERE is_active = 1
            ORDER BY display_order, category
            """
        ).fetchall()
    for row in rows:
        print(f"{row['display_order']:>3}  {row['parent_group']}  {row['category']}")


def list_symbols() -> None:
    ensure_database()
    with connect() as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT symbol, display_name, asset_type, market, category, ma_proxy_symbol, is_active
            FROM symbol_master
            ORDER BY market, asset_type, category, symbol
            """
        ).fetchall()
    for row in rows:
        status = "active" if row["is_active"] else "inactive"
        proxy = f" proxy={row['ma_proxy_symbol']}" if row["ma_proxy_symbol"] else ""
        print(
            f"{row['symbol']:<12} {status:<8} {row['market']:<8} "
            f"{row['asset_type']:<14} {row['category'] or '-':<18} "
            f"{row['display_name']}{proxy}"
        )


def category_exists(category: str) -> bool:
    ensure_database()
    with connect() as connection:
        row = connection.execute(
            "SELECT 1 FROM category_master WHERE category = ? AND is_active = 1",
            (category,),
        ).fetchone()
    return row is not None


def add_symbol(args: argparse.Namespace) -> None:
    if args.category and not category_exists(args.category):
        raise SystemExit(f"Unknown category: {args.category}. Run `python manage_symbols.py categories`.")
    upsert_symbol(
        symbol=args.symbol,
        yahoo_ticker=args.yahoo_ticker or args.symbol,
        display_name=args.name,
        asset_type=args.asset_type,
        market=args.market,
        category=args.category,
        ma_proxy_symbol=args.ma_proxy_symbol,
        is_active=not args.inactive,
    )
    print(f"Upserted {args.symbol} into {DATABASE_PATH}")


def set_active(symbol: str, active: bool) -> None:
    ensure_database()
    with connect() as connection:
        cursor = connection.execute(
            """
            UPDATE symbol_master
            SET is_active = ?, updated_at = datetime('now')
            WHERE symbol = ?
            """,
            (1 if active else 0, symbol),
        )
    if cursor.rowcount == 0:
        raise SystemExit(f"Symbol not found: {symbol}")
    state = "activated" if active else "deactivated"
    print(f"{state}: {symbol}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Maintain TaiwanStockBot symbol/category database.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("categories", help="List active categories.")
    subparsers.add_parser("list", help="List symbols in symbol_master.")

    add_parser = subparsers.add_parser("add", help="Add or update a symbol.")
    add_parser.add_argument("--symbol", required=True, help="Canonical symbol, usually Yahoo ticker such as 2330.TW.")
    add_parser.add_argument("--yahoo-ticker", default=None, help="Yahoo ticker if different from --symbol.")
    add_parser.add_argument("--name", required=True, help="Display name used in reports.")
    add_parser.add_argument("--asset-type", required=True, choices=[
        "stock", "financial", "etf", "index", "commodity", "fx", "crypto", "overseas_stock", "market"
    ])
    add_parser.add_argument("--market", required=True, choices=[
        "taiwan", "korea", "japan", "vietnam", "us", "all_day", "global"
    ])
    add_parser.add_argument("--category", default=None, help="Category from category_master.")
    add_parser.add_argument("--ma-proxy-symbol", default=None, help="Optional MA proxy symbol, e.g. SOXX for ^SOX.")
    add_parser.add_argument("--inactive", action="store_true", help="Insert as inactive.")

    deactivate_parser = subparsers.add_parser("deactivate", help="Deactivate a symbol.")
    deactivate_parser.add_argument("symbol")

    activate_parser = subparsers.add_parser("activate", help="Activate a symbol.")
    activate_parser.add_argument("symbol")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "categories":
        list_categories()
    elif args.command == "list":
        list_symbols()
    elif args.command == "add":
        add_symbol(args)
    elif args.command == "deactivate":
        set_active(args.symbol, False)
    elif args.command == "activate":
        set_active(args.symbol, True)
    else:
        parser.error(f"Unsupported command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
