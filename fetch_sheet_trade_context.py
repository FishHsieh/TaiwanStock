from __future__ import annotations



import argparse

import hashlib

import json

import re

import os

import sys
import time

from concurrent.futures import ThreadPoolExecutor, as_completed

from datetime import datetime

from pathlib import Path

from typing import Any

from urllib.parse import quote



import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



from google.oauth2 import service_account

from googleapiclient.discovery import build



from publish_google_workspace import parse_market_data
from bot_database import log_source_fetch, upsert_monthly_revenue



DEFAULT_SHEET_ID = "1WQNCHJfK5CXluCeWsSee64NczdG6DapcbBkI7C8OuFI"

SHEET_RANGE = "A1:ZZ31"

PREFERRED_MA_SHEET_TITLE = "????"

CACHE_SCHEMA_VERSION = 4

READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"

DRIVE_METADATA_SCOPE = "https://www.googleapis.com/auth/drive.metadata.readonly"

CACHE_FILENAME = "sheet_trade_context_cache.json"

HISTORICAL_MA_WINDOWS = {

    "ma5": 5,

    "ma10": 10,

    "ma_month": 20,

    "ma_quarter": 60,

    "ma_half": 120,

    "ma_year": 240,

}

YAHOO_HISTORY_RANGE = "1y"

YAHOO_HISTORY_INTERVAL = "1d"

YAHOO_HEADERS = {

    "User-Agent": (

        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "

        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    )

}

TAIWAN_EQUITY_TICKER_RE = re.compile(r"^\d{4,6}[A-Z]?\.(TW|TWO)$", re.IGNORECASE)





def parse_float(value: Any) -> float | None:

    if value is None:

        return None

    text = str(value).strip().replace(",", "")

    if not text or text == "-":

        return None

    try:

        return float(text)

    except ValueError:

        return None





def sheet_code_to_ticker(code: str) -> str | None:

    code = code.strip()

    if not code:

        return None



    aliases = {

        "TPE:IX0001": "^TWII",

        "KRX:KOSPI": "^KS11",

        "INDEXNIKKEI:NI225": "^N225",

        "NDX": "^NDX",

        ".IXIC": "^IXIC",

        ".INX": "^GSPC",

        "NASDAQ:SOXX": "SOXX",

        "INDEXNASDAQ:SOX": "^SOX",

        "CURRENCY:BTCUSD": "BTC-USD",

    }

    if code in aliases:

        return aliases[code]



    if code.startswith("TPE:"):

        return f"{code.split(':', 1)[1]}.TW"

    if code.startswith("OTC:"):

        return f"{code.split(':', 1)[1]}.TWO"

    if code.startswith("KRX:"):

        return f"{code.split(':', 1)[1]}.KS"

    if code.startswith("INDEXNIKKEI:"):

        base = code.split(":", 1)[1]

        if base == "NI225":

            return "^N225"

        return base

    if code.startswith("INDEXNASDAQ:"):

        base = code.split(":", 1)[1]

        if base == "SOX":

            return "^SOX"

        return base

    if code.startswith("CURRENCY:"):

        base = code.split(":", 1)[1]

        if base == "BTCUSD":

            return "BTC-USD"

        return base

    if re.fullmatch(r"\d{4,6}[A-Z]?", code):

        return f"{code}.TW"

    if code.startswith("."):

        return code

    return code





def load_market_rows(market_data_path: Path):

    text = market_data_path.read_text(encoding="utf-8-sig")

    return parse_market_data(text)





def fetch_yahoo_history_closes(ticker_symbol: str) -> list[float]:

    encoded_ticker = quote(ticker_symbol, safe="")

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded_ticker}"

    params = {

        "range": YAHOO_HISTORY_RANGE,

        "interval": YAHOO_HISTORY_INTERVAL,

        "includePrePost": "false",

        "events": "div,splits",

    }

    response = requests.get(url, headers=YAHOO_HEADERS, params=params, timeout=20)

    response.raise_for_status()

    data = response.json()

    chart = data.get("chart", {})

    error = chart.get("error")

    if error:

        raise RuntimeError(error.get("description") or error.get("code") or "Yahoo Finance history error")

    results = chart.get("result") or []

    if not results:

        raise RuntimeError("Yahoo Finance returned empty historical data")

    result = results[0]

    quote_rows = result.get("indicators", {}).get("quote") or []

    if not quote_rows:

        raise RuntimeError("Yahoo Finance returned no quote history")

    closes = quote_rows[0].get("close") or []

    cleaned = [float(str(value).replace(",", "")) for value in closes if value not in (None, "")]

    if not cleaned:

        raise RuntimeError("Yahoo Finance returned empty close series")

    return cleaned





def compute_history_mas(closes: list[float]) -> dict[str, float | None]:

    ma_values: dict[str, float | None] = {}

    if not closes:

        for name in HISTORICAL_MA_WINDOWS:

            ma_values[name] = None

        return ma_values



    for name, window in HISTORICAL_MA_WINDOWS.items():

        # Match GOOGLEFINANCE-style behavior more closely:

        # if fewer than N closes exist, average the available closes

        # instead of dropping the MA entirely.

        usable_closes = closes[-min(window, len(closes)):]

        ma_values[name] = sum(usable_closes) / len(usable_closes)

    return ma_values





def fetch_history_ma_values(ticker_symbol: str) -> dict[str, float | None]:

    return compute_history_mas(fetch_yahoo_history_closes(ticker_symbol))







def extract_balanced_json_array(text: str) -> str:

    start = text.find("[")

    if start == -1:

        raise RuntimeError("Yahoo revenue chart data array not found")

    depth = 0

    in_string = False

    escape = False

    for index in range(start, len(text)):

        char = text[index]

        if in_string:

            if escape:

                escape = False

            elif char == "\\":

                escape = True

            elif char == '"':

                in_string = False

        else:

            if char == '"':

                in_string = True

            elif char == '[':

                depth += 1

            elif char == ']':

                depth -= 1

                if depth == 0:

                    return text[start : index + 1]

    raise RuntimeError("Unbalanced Yahoo revenue chart data array")


def fetch_text_with_retry(session: requests.Session, url: str, *, timeout: int = 20, retries: int = 4) -> str:

    last_error: Exception | None = None

    for attempt in range(retries):

        try:

            response = session.get(url, headers=YAHOO_HEADERS, timeout=timeout, verify=False)

            response.raise_for_status()

            return response.text

        except Exception as exc:

            last_error = exc

            if attempt + 1 < retries:

                time.sleep(min(2 ** attempt, 4))

    if last_error is not None:

        raise last_error

    raise RuntimeError("Yahoo request failed")


def parse_revenue_period(period: str) -> tuple[int, int] | None:
    match = re.fullmatch(r"(\d{4})/(\d{1,2})", str(period or "").strip())
    if not match:
        return None
    year = int(match.group(1))
    month = int(match.group(2))
    if month < 1 or month > 12:
        return None
    return year, month


def calculate_ytd_revenue_yoy(entries: list[dict[str, Any]], latest_period: str) -> float | None:
    parsed_latest = parse_revenue_period(latest_period)
    if parsed_latest is None:
        return None
    latest_year, latest_month = parsed_latest

    current_total = 0.0
    previous_total = 0.0
    for entry in entries:
        parsed_period = parse_revenue_period(str(entry.get("date") or ""))
        if parsed_period is None:
            continue
        year, month = parsed_period
        if month > latest_month:
            continue
        revenue_value = parse_float(entry.get("currentPeriodRevenue"))
        if revenue_value is None:
            continue
        if year == latest_year:
            current_total += revenue_value
        elif year == latest_year - 1:
            previous_total += revenue_value

    if previous_total <= 0 or current_total <= 0:
        return None
    return round(((current_total / previous_total) - 1.0) * 100.0, 2)


def format_pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.2f}%"


def fetch_yahoo_revenue_summary(ticker_symbol: str) -> dict[str, Any] | None:
    if not TAIWAN_EQUITY_TICKER_RE.fullmatch(ticker_symbol):
        return None

    encoded_ticker = quote(ticker_symbol, safe="")
    url = f"https://tw.stock.yahoo.com/quote/{encoded_ticker}/revenue"
    with requests.Session() as session:
        html_text = fetch_text_with_retry(session, url, timeout=20, retries=4)

    key_match = re.search(r'"revenueChartDataKey":"([^"]+)"', html_text)
    if not key_match:
        return None

    revenue_key = key_match.group(1)
    marker = f'"{revenue_key}":{{"data":'
    marker_index = html_text.find(marker)
    if marker_index == -1:
        return None

    array_text = extract_balanced_json_array(html_text[marker_index + len(marker) :])
    try:
        entries = json.loads(array_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Yahoo revenue chart decode failed for {ticker_symbol}: {exc}") from exc

    if not entries:
        return None

    latest = None
    for entry in reversed(entries):
        if parse_float(entry.get("revenueYoY")) is not None:
            latest = entry
            break
    if latest is None:
        return None

    revenue_yoy = parse_float(latest.get("revenueYoY"))
    if revenue_yoy is None:
        return None

    revenue_mom = parse_float(latest.get("currentPeriodGrowthRate"))
    revenue_month = str(latest.get("date") or "").strip()
    revenue_ytd_yoy = calculate_ytd_revenue_yoy(entries, revenue_month)
    month_label = revenue_month or "最新月份"
    summary = (
        f"{month_label} 營收 MoM {format_pct(revenue_mom)}，"
        f"YoY {format_pct(revenue_yoy)}，"
        f"今年累計 YoY {format_pct(revenue_ytd_yoy)}"
    )

    return {
        "revenue_month": revenue_month,
        "revenue_yoy": revenue_yoy,
        "revenue_mom": revenue_mom,
        "revenue_ytd_yoy": revenue_ytd_yoy,
        "revenue_summary": summary,
        "revenue_source": "Yahoo Finance revenue page",
    }

def enrich_ma_info(info: dict[str, Any], history_values: dict[str, float | None] | None) -> dict[str, Any]:

    merged = dict(info)

    history_values = history_values or {}

    used_sheet = False

    used_history = False

    for key in HISTORICAL_MA_WINDOWS:

        if merged.get(key) is not None:

            used_sheet = True

            continue

        if history_values.get(key) is not None:

            merged[key] = history_values[key]

            used_history = True

    if used_sheet and used_history:

        merged["ma_source"] = "google_sheet+yahoo_history"

    elif used_history:

        merged["ma_source"] = "yahoo_history"

    elif used_sheet:

        merged["ma_source"] = "google_sheet"

    else:

        merged["ma_source"] = "missing"

    return merged





def load_google_credentials(credentials_path: Path):

    return service_account.Credentials.from_service_account_file(

        str(credentials_path),

        scopes=[READONLY_SCOPE, DRIVE_METADATA_SCOPE],

    )





def compute_file_digest(path: Path) -> str:

    digest = hashlib.sha256()

    with path.open("rb") as handle:

        for chunk in iter(lambda: handle.read(1024 * 1024), b""):

            digest.update(chunk)

    return digest.hexdigest()





def read_json_file(path: Path) -> dict[str, Any] | None:

    if not path.exists():

        return None

    try:

        payload = json.loads(path.read_text(encoding="utf-8"))

    except Exception:

        return None

    return payload if isinstance(payload, dict) else None





def write_json_file(path: Path, payload: dict[str, Any]) -> None:

    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")





def get_default_cache_path() -> Path:

    return Path(__file__).resolve().parent / "Reports" / CACHE_FILENAME





def get_sheet_revision_signature(credentials_path: Path, spreadsheet_id: str) -> dict[str, Any]:

    creds = load_google_credentials(credentials_path)

    drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)

    metadata = (

        drive_service.files()

        .get(fileId=spreadsheet_id, fields="modifiedTime,version")

        .execute()

    )

    return {

        "modified_time": metadata.get("modifiedTime"),

        "version": metadata.get("version"),

    }





def load_cached_context(cache_path: Path, cache_key: dict[str, Any]) -> dict[str, Any] | None:

    payload = read_json_file(cache_path)

    if not payload:

        return None

    if payload.get("cache_key") != cache_key:

        return None

    context = payload.get("context")

    return context if isinstance(context, dict) else None





def store_cached_context(cache_path: Path, cache_key: dict[str, Any], context: dict[str, Any]) -> None:

    write_json_file(

        cache_path,

        {

            "cache_key": cache_key,

            "context": context,

            "updated_at": datetime.now().isoformat(timespec="seconds"),

        },

    )





def build_sheet_index(credentials_path: Path, spreadsheet_id: str) -> tuple[str, dict[str, dict[str, Any]]]:

    creds = load_google_credentials(credentials_path)

    service = build("sheets", "v4", credentials=creds, cache_discovery=False)

    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

    sheets = meta.get("sheets", [])

    if not sheets:

        raise RuntimeError("Google Sheet contains no sheets")



    preferred_title = None

    for sheet in sheets:

        title = sheet.get("properties", {}).get("title")

        if title == PREFERRED_MA_SHEET_TITLE:

            preferred_title = title

            break



    sheet_title = preferred_title or sheets[0].get("properties", {}).get("title") or PREFERRED_MA_SHEET_TITLE



    values = (

        service.spreadsheets()

        .values()

        .get(spreadsheetId=spreadsheet_id, range=f"'{sheet_title}'!{SHEET_RANGE}")

        .execute()

        .get("values", [])

    )



    max_cols = max((len(row) for row in values), default=0)



    def cell(row_number: int, col_number: int) -> str:

        row_index = row_number - 1

        col_index = col_number - 1

        if row_index >= len(values):

            return ""

        row = values[row_index]

        if col_index >= len(row):

            return ""

        return str(row[col_index]).strip()



    index: dict[str, dict[str, Any]] = {}

    for col in range(1, max_cols + 1):

        code = cell(2, col)

        ticker = sheet_code_to_ticker(code)

        if not ticker:

            continue



        index[ticker] = {

            "sheet_label": cell(1, col) or ticker,

            "sheet_code": code,

            "sheet_price": parse_float(cell(6, col)),

            "ma10_price": parse_float(cell(11, col)),

            "ma5": parse_float(cell(23, col)),

            "ma10": parse_float(cell(24, col)),

            "ma_month": parse_float(cell(25, col)),

            "ma_quarter": parse_float(cell(26, col)),

            "ma_half": parse_float(cell(27, col)),

            "ma_year": parse_float(cell(28, col)),

            "action": cell(31, col),

        }



    return sheet_title, index

def pct_gap(price: float, ma: float | None) -> float | None:

    if ma in (None, 0):

        return None

    return ((price / ma) - 1.0) * 100.0





def describe_position(price: float, info: dict[str, Any]) -> str:

    ma5 = info.get("ma5")

    ma10 = info.get("ma10")

    ma_month = info.get("ma_month")

    ma_quarter = info.get("ma_quarter")

    ma_half = info.get("ma_half")

    ma_year = info.get("ma_year")



    if all(v is not None for v in [ma5, ma10, ma_month, ma_quarter, ma_half, ma_year]):

        if price >= ma5 >= ma10 >= ma_month >= ma_quarter >= ma_half >= ma_year:

            return "above_all"

        if price >= ma10 >= ma_month >= ma_quarter:

            return "above_short_medium"

        if price >= ma_month and price < ma10:

            return "pullback_above_month"

        if price >= ma_quarter and price < ma_month:

            return "between_quarter_and_month"

        if price >= ma_year and price < ma_quarter:

            return "long_support_mid_weak"



    if ma_month is not None and price >= ma_month:

        return "above_month"

    if ma_quarter is not None and price >= ma_quarter:

        return "near_quarter"

    return "weak"





def build_bias(price: float, info: dict[str, Any]) -> str:

    ma5 = info.get("ma5")

    ma10 = info.get("ma10")

    ma_month = info.get("ma_month")

    ma_quarter = info.get("ma_quarter")

    ma_half = info.get("ma_half")

    ma_year = info.get("ma_year")



    if all(v is not None for v in [ma5, ma10, ma_month, ma_quarter, ma_half, ma_year]):

        if price >= ma5 >= ma10 >= ma_month >= ma_quarter >= ma_half >= ma_year:

            return "buy"

        if price >= ma10 >= ma_month >= ma_quarter:

            return "buy_on_pullback"

        if price >= ma_month >= ma_quarter:

            return "mild_buy"

        if price >= ma_quarter and price < ma_month:

            return "hold"

        return "sell_or_reduce"



    if ma10 is not None and ma_month is not None:

        if price >= ma10 and price >= ma_month:

            return "buy"

        if price < ma10 and price >= ma_month:

            return "hold"

        if price < ma_month:

            return "sell_or_reduce"



    return "hold"





def normalize_multiline(text: str) -> list[str]:

    return [line.strip() for line in str(text).splitlines() if line.strip()]





def build_context(

    market_rows,

    sheet_title: str,

    sheet_index: dict[str, dict[str, Any]],

    history_ma_cache: dict[str, dict[str, float | None]],
    revenue_cache: dict[str, dict[str, Any]],

) -> dict[str, Any]:

    rows: list[dict[str, Any]] = []

    for row in market_rows.rows:

        source_ticker = row.ticker

        info = None



        if row.ticker == "^SOX":

            source_ticker = "SOXX"

            info = sheet_index.get("SOXX") or sheet_index.get(row.ticker)

        else:

            info = sheet_index.get(row.ticker)



        history_key = source_ticker if source_ticker in history_ma_cache else row.ticker

        history_values = history_ma_cache.get(history_key)

        revenue_info = revenue_cache.get(row.ticker)



        if info is None:

            if not history_values or not any(value is not None for value in history_values.values()):

                continue

            info = {

                "sheet_label": row.label,

                "sheet_code": source_ticker,

                "sheet_price": row.price,

                "ma10_price": None,

                "ma5": None,

                "ma10": None,

                "ma_month": None,

                "ma_quarter": None,

                "ma_half": None,

                "ma_year": None,

                "action": "",

            }



        enriched_info = enrich_ma_info(info, history_values)

        price = row.price

        row_payload = {

            "label": row.label,

            "ticker": row.ticker,

            "price": round(price, 4),

            "sheet_label": enriched_info["sheet_label"],

            "sheet_code": enriched_info["sheet_code"],

            "sheet_source_ticker": source_ticker,

            "sheet_price": enriched_info["sheet_price"],

            "ma5": enriched_info["ma5"],

            "ma10": enriched_info["ma10"],

            "ma_month": enriched_info["ma_month"],

            "ma_quarter": enriched_info["ma_quarter"],

            "ma_half": enriched_info["ma_half"],

            "ma_year": enriched_info["ma_year"],

            "ma_source": enriched_info["ma_source"],

            "gaps_pct": {

                "ma5": pct_gap(price, enriched_info["ma5"]),

                "ma10": pct_gap(price, enriched_info["ma10"]),

                "ma_month": pct_gap(price, enriched_info["ma_month"]),

                "ma_quarter": pct_gap(price, enriched_info["ma_quarter"]),

                "ma_half": pct_gap(price, enriched_info["ma_half"]),

                "ma_year": pct_gap(price, enriched_info["ma_year"]),

            },

            "position": describe_position(price, enriched_info),

            "bias": build_bias(price, enriched_info),

            "action": normalize_multiline(enriched_info.get("action", "")),

        }

        if revenue_info:
            row_payload.update(revenue_info)

        rows.append(row_payload)



    return {

        "generated_at": datetime.now().isoformat(timespec="seconds"),

        "sheet_title": sheet_title,

        "rows": rows,

    }

def fallback_context(message: str) -> dict[str, Any]:

    return {

        "generated_at": datetime.now().isoformat(timespec="seconds"),

        "sheet_title": "",

        "rows": [],

        "warning": message,

    }





def main() -> int:

    parser = argparse.ArgumentParser(description="Build a sheet-backed trade context from live market data and Google Sheet MAs.")

    parser.add_argument("--market-data", required=True, type=Path)

    parser.add_argument("--output", type=Path, default=None)

    parser.add_argument("--credentials", type=Path, default=None)

    parser.add_argument("--sheet-id", default=None)

    parser.add_argument("--cache", type=Path, default=None)

    args = parser.parse_args()



    market_data_path = args.market_data

    if not market_data_path.exists():

        context = fallback_context(f"missing market data file: {market_data_path}")

    else:

        credentials_value = args.credentials or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

        if isinstance(credentials_value, Path):

            credentials_path = credentials_value

        elif credentials_value:

            credentials_path = Path(credentials_value)

        else:

            credentials_path = None



        sheet_id = args.sheet_id or os.environ.get("TAIWANSTOCK_MA_SHEET_ID") or DEFAULT_SHEET_ID



        if credentials_path is None or not credentials_path.exists():

            context = fallback_context("missing Google service account credentials")

        else:

            cache_path = args.cache or get_default_cache_path()

            cache_key: dict[str, Any] | None = None

            cached_context: dict[str, Any] | None = None

            try:

                market_hash = compute_file_digest(market_data_path)

                sheet_signature = get_sheet_revision_signature(credentials_path, sheet_id)

                cache_key = {

                    "cache_schema_version": CACHE_SCHEMA_VERSION,

                    "spreadsheet_id": sheet_id,

                    "preferred_sheet_title": PREFERRED_MA_SHEET_TITLE,

                    "sheet_range": SHEET_RANGE,

                    "market_data_sha256": market_hash,

                    "sheet_modified_time": sheet_signature.get("modified_time"),

                    "sheet_version": sheet_signature.get("version"),

                }

                cached_context = load_cached_context(cache_path, cache_key)

            except Exception:

                cache_key = None

                cached_context = None



            if cached_context is not None:

                print(f"[SheetContext] Cache hit: {cache_path}")

                context = cached_context

            else:

                try:

                    market_rows = load_market_rows(market_data_path)

                    sheet_title, sheet_index = build_sheet_index(credentials_path, sheet_id)

                    history_targets: set[str] = set()

                    for symbol, info in sheet_index.items():

                        history_symbol = "SOXX" if symbol == "^SOX" else symbol

                        if any(info.get(key) is None for key in HISTORICAL_MA_WINDOWS):

                            history_targets.add(history_symbol)

                    for row in market_rows.rows:

                        history_symbol = "SOXX" if row.ticker == "^SOX" else row.ticker

                        info = sheet_index.get(history_symbol) or sheet_index.get(row.ticker)

                        if info is None:

                            history_targets.add(history_symbol)

                    history_ma_cache: dict[str, dict[str, float | None]] = {}

                    if history_targets:

                        with ThreadPoolExecutor(max_workers=min(8, len(history_targets))) as executor:

                            futures = {}

                            for symbol in history_targets:

                                lookup_symbol = "SOXX" if symbol == "^SOX" else symbol

                                future = executor.submit(fetch_history_ma_values, lookup_symbol)

                                futures[future] = symbol

                            for future in as_completed(futures):

                                symbol = futures[future]

                                try:

                                    history_ma_cache[symbol] = future.result()

                                except Exception:

                                    history_ma_cache[symbol] = {}



                    revenue_targets: set[str] = set()
                    for row in market_rows.rows:
                        if TAIWAN_EQUITY_TICKER_RE.fullmatch(row.ticker):
                            revenue_targets.add(row.ticker)
                    revenue_cache: dict[str, dict[str, Any]] = {}
                    if revenue_targets:
                        with ThreadPoolExecutor(max_workers=min(8, len(revenue_targets))) as executor:
                            futures = {}
                            for symbol in revenue_targets:
                                future = executor.submit(fetch_yahoo_revenue_summary, symbol)
                                futures[future] = symbol
                            for future in as_completed(futures):
                                symbol = futures[future]
                                try:

                                    revenue_summary = future.result()

                                    if revenue_summary:

                                        revenue_cache[symbol] = revenue_summary

                                        try:

                                            upsert_monthly_revenue(symbol, revenue_summary)

                                            log_source_fetch(

                                                "Yahoo Finance revenue page",

                                                symbol,

                                                "ok",

                                                asof_key=str(revenue_summary.get("revenue_month") or ""),

                                            )

                                        except Exception:

                                            pass

                                except Exception:

                                    revenue_cache[symbol] = {}

                                    try:

                                        log_source_fetch("Yahoo Finance revenue page", symbol, "error")

                                    except Exception:

                                        pass
                    context = build_context(market_rows, sheet_title, sheet_index, history_ma_cache, revenue_cache)

                    if cache_key is not None and "warning" not in context:

                        store_cached_context(cache_path, cache_key, context)

                        print(f"[SheetContext] Cached: {cache_path}")

                except Exception as exc:

                    context = fallback_context(f"failed to read Google Sheet MAs: {exc}")



    payload = json.dumps(context, ensure_ascii=False, indent=2)

    if args.output:

        args.output.write_text(payload, encoding="utf-8")

        print(f"[SheetContext] Wrote {args.output}")

    else:

        print(payload)

    return 0





if __name__ == "__main__":

    raise SystemExit(main())

