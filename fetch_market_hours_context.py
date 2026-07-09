from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Iterable

DEFAULT_ROWS = [
    {
        "sort_order": 1,
        "country": "\u53f0\u7063",
        "market": "\u53f0\u80a1 (\u96c6\u4e2d\u5e02\u5834)",
        "taiwan_open": "09:00",
        "taiwan_close": "13:30",
        "notes": "\u96f6\u80a1\u4ea4\u6613\u6642\u9593\u70ba 09:00~14:30",
    },
    {
        "sort_order": 2,
        "country": "\u7f8e\u570b",
        "market": "\u7f8e\u80a1 (\u590f\u4ee4 / 3\u6708~11\u6708)",
        "taiwan_open": "21:30",
        "taiwan_close": "04:00",
        "notes": "\u5305\u542b\u7d10\u7d04\u8b49\u4ea4\u6240\u8207\u7d0d\u65af\u9054\u514b",
    },
    {
        "sort_order": 3,
        "country": "\u7f8e\u570b",
        "market": "\u7f8e\u80a1 (\u51ac\u4ee4 / 11\u6708~3\u6708)",
        "taiwan_open": "22:30",
        "taiwan_close": "05:00",
        "notes": "\u590f\u4ee4 / \u51ac\u4ee4\u5207\u63db\u901a\u5e38\u65bc\u4e09\u6708\u53ca\u5341\u4e00\u6708",
    },
    {
        "sort_order": 4,
        "country": "\u65e5\u672c",
        "market": "\u65e5\u80a1 (\u6771\u4eac\u8b49\u4ea4\u6240)",
        "taiwan_open": "08:00",
        "taiwan_close": "14:00",
        "notes": "\u7576\u5730\u6642\u9593\u70ba 09:00\uff0c\u4e2d\u9593 11:30~12:30 \u4f11\u606f",
    },
    {
        "sort_order": 5,
        "country": "\u5357\u97d3",
        "market": "\u97d3\u80a1 (\u97d3\u570b\u4ea4\u6613\u6240)",
        "taiwan_open": "08:00",
        "taiwan_close": "14:30",
        "notes": "\u7576\u5730\u6642\u9593\u70ba 09:00\uff0c\u7121\u4e2d\u5348\u4f11\u5e02",
    },
    {
        "sort_order": 6,
        "country": "\u8d8a\u5357",
        "market": "\u8d8a\u5357\u80a1\u5e02 (\u80e1\u5fd7\u660e/\u6cb3\u5167)",
        "taiwan_open": "10:00",
        "taiwan_close": "15:45",
        "notes": "\u7576\u5730\u6642\u9593\u70ba 09:00\uff0c\u4e2d\u9593 11:30~13:00 \u4f11\u606f",
    },
]


def ensure_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS market_hours_reference (
                sort_order INTEGER PRIMARY KEY,
                country TEXT NOT NULL,
                market TEXT NOT NULL,
                taiwan_open TEXT NOT NULL,
                taiwan_close TEXT NOT NULL,
                notes TEXT NOT NULL
            )
            """
        )
        existing_count = connection.execute(
            "SELECT COUNT(*) FROM market_hours_reference"
        ).fetchone()[0]
        if existing_count == 0:
            connection.executemany(
                """
                INSERT INTO market_hours_reference (
                    sort_order, country, market, taiwan_open, taiwan_close, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        row["sort_order"],
                        row["country"],
                        row["market"],
                        row["taiwan_open"],
                        row["taiwan_close"],
                        row["notes"],
                    )
                    for row in DEFAULT_ROWS
                ],
            )
            connection.commit()


def load_rows(db_path: Path) -> list[sqlite3.Row]:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT country, market, taiwan_open, taiwan_close, notes
            FROM market_hours_reference
            ORDER BY sort_order ASC
            """
        ).fetchall()
    return list(rows)


def build_markdown(rows: Iterable[sqlite3.Row]) -> str:
    lines = [
        "### \u56fa\u5b9a\u5e02\u5834\u4ea4\u6613\u6642\u9593\u8cc7\u6599\u5eab",
        "| \u570b\u5bb6 | \u5e02\u5834 / \u4ea4\u6613\u6240 | \u53f0\u7063\u958b\u76e4\u6642\u9593 | \u53f0\u7063\u6536\u76e4\u6642\u9593 | \u5099\u8a3b |",
        "|---|---|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['country']} | {row['market']} | {row['taiwan_open']} | {row['taiwan_close']} | {row['notes']} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build fixed market-hours context from a local SQLite database.")
    parser.add_argument("--db", required=True, help="Path to the SQLite database file.")
    parser.add_argument("--output", help="Optional output file path. If omitted, print to stdout.")
    args = parser.parse_args()

    db_path = Path(args.db)
    ensure_database(db_path)
    rows = load_rows(db_path)
    markdown = build_markdown(rows)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown + "\n", encoding="utf-8")
    else:
        print(markdown)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
