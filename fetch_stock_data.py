import sys







import time



import re







from datetime import datetime, timedelta, timezone

from html import unescape

import io
import json
from functools import lru_cache
import zipfile
import xml.etree.ElementTree as ET





import sqlite3



from concurrent.futures import ThreadPoolExecutor, as_completed



from dataclasses import asdict, dataclass, replace



from pathlib import Path



from statistics import mean



from typing import Optional



from zoneinfo import ZoneInfo







from urllib.parse import quote, urljoin

from bot_database import count_active_symbols, ensure_database, load_active_symbols, load_latest_institutional_futures_snapshot, seed_category_master, upsert_daily_ohlcv, upsert_symbol















import requests















# 設定 Yahoo Finance 的代號 (Ticker)







MARKETS = [







    ("台股 (TAIEX)", "^TWII"),



    ("\u6ac3\u8cb7\u6307\u6578", "^TWOII"),







    ("台積電 (2330.TW)", "2330.TW"),







    ("日月光投控 (3711.TW)", "3711.TW"),







    ("聯電 (2303.TW)", "2303.TW"),







    ("聯發科 (2454.TW)", "2454.TW"),







    ("鴻海 (2317.TW)", "2317.TW"),







    ("廣達 (2382.TW)", "2382.TW"),







    ("台達電 (2308.TW)", "2308.TW"),







    ("台光電 (2383.TW)", "2383.TW"),







    ("大立光 (3008.TW)", "3008.TW"),







    ("華通 (2313.TW)", "2313.TW"),







    ("華碩 (2357.TW)", "2357.TW"),







    ("華邦電 (2344.TW)", "2344.TW"),







    ("帆宣 (6196.TW)", "6196.TW"),







    ("南亞科 (2408.TW)", "2408.TW"),







    ("訊連 (5203.TW)", "5203.TW"),







    ("2301光寶科", "2301.TW"),







    ("大聯大 (3702.TW)", "3702.TW"),







    ("3034聯詠", "3034.TW"),







    ("2376技嘉", "2376.TW"),







    ("5274信驊", "5274.TWO"),







    ("3443創意", "3443.TW"),







    ("8299群聯", "8299.TWO"),







    ("2327國巨", "2327.TW"),







    ("3037欣興", "3037.TW"),







    ("3653健策", "3653.TW"),







    ("2449京元電子", "2449.TW"),







    ("6274台燿", "6274.TWO"),







    ("3017奇鋐", "3017.TW"),







    ("7610聯友金屬", "7610.TW"),







    ("3481群創", "3481.TW"),







    ("6770力積電", "6770.TW"),







    ("6409旭隼科技", "6409.TW"),







    ("8046南電", "8046.TW"),







    ("3189景碩", "3189.TW"),







    ("6213聯茂", "6213.TW"),







    ("6223旺矽", "6223.TWO"),







    ("3035智原", "3035.TW"),







    ("2049上銀", "2049.TW"),







    ("6139亞翔", "6139.TW"),







    ("1560中砂", "1560.TW"),







    ("2458義隆", "2458.TW"),







    ("6446藥華藥", "6446.TW"),







    ("2312金寶電子", "2312.TW"),


    ("6239力成", "6239.TW"),



    ("6176瑞儀", "6176.TW"),



    ("2059川湖", "2059.TW"),



    ("3231緯創", "3231.TW"),



    ("2392正崴", "2392.TW"),



    ("2377微星", "2377.TW"),






    ("00991A主動復華未來50", "00991A.TW"),







    ("00981A主動統一台股增長", "00981A.TW"),







    ("00735國泰臺韓科技", "00735.TW"),







    ("00990A主動元大AI新經濟", "00990A.TW"),







    ("00988A主動統一全球創新", "00988A.TW"),







    ("00982A主動群益台灣強棒", "00982A.TW"),







    ("0050????50", "0050.TW"),







    ("0052????", "0052.TW"),







    ("00947????IC??", "00947.TW"),







    ("00631L????50?2", "00631L.TW"),







    ("00830???????", "00830.TW"),







    ("00876????5G", "00876.TW"),







    ("00909????????", "00909.TW"),







    ("009805????????", "009805.TW"),







    ("00910???????", "00910.TW"),







    ("0056?????", "0056.TW"),







    ("00919????????", "00919.TW"),







    ("00878???????", "00878.TW"),







    ("00922??????50", "00922.TW"),







    ("00900富邦特選高股息30", "00900.TW"),







    ("00891中信關鍵半導體", "00891.TW"),







    ("00403A主動統一升級50", "00403A.TW"),







    ("009816凱基台灣TOP50", "009816.TW"),







    ("00646元大S&P500", "00646.TW"),







    ("00911兆豐洲際半導體", "00911.TW"),







    ("00895富邦未來車", "00895.TW"),







    ("00757統一FANG+", "00757.TW"),







    ("00713元大台灣高息低波", "00713.TW"),







    ("00915凱基優選高股息30", "00915.TW"),







    ("00918大華優利高填息30", "00918.TW"),







    ("00924復華S&P500", "00924.TW"),







    ("00635U期元大S&P黃金", "00635U.TW"),







    ("00738U期元大道瓊白銀", "00738U.TW"),







    ("00763U期街口道瓊銅", "00763U.TW"),







    ("00642U元大石油", "00642U.TW"),







    ("2801彰銀", "2801.TW"),







    ("2892第一金", "2892.TW"),







    ("2886兆豐金", "2886.TW"),







    ("2834臺企銀", "2834.TW"),







    ("2812台中銀", "2812.TW"),







    ("2890永豐金", "2890.TW"),







    ("2880華南金", "2880.TW"),







    ("2883凱基金", "2883.TW"),







    ("2884玉山金", "2884.TW"),







    ("2885元大金", "2885.TW"),







    ("2881富邦金", "2881.TW"),







    ("2882國泰金", "2882.TW"),







    ("2855統一證", "2855.TW"),







    ("00917中信特選金融", "00917.TW"),







    ("越南大盤 (VNINDEX)", "VNINDEX"),







    ("日圓匯率", "JPY=X"),



    ("\u7f8e\u5143\u6307\u6578", "DX-Y.NYB"),







    ("美國長債 ETF (TLT)", "TLT"),







    ("韓股 (KOSPI)", "^KS11"),







    ("日股 (NIKKEI)", "^N225"),







    ("NASDAQ 綜合指數", "^IXIC"),







    ("S&P 500", "^GSPC"),







    ("費城半導體指數 (^SOX)", "^SOX"),







    ("比特幣 (BTC-USD)", "BTC-USD"),







    ("黃金期貨 (GC=F)", "GC=F"),







    ("石油期貨 (CL=F)", "CL=F"),







    ("Samsung Electronics (005930.KS)", "005930.KS"),







    ("SK Hynix (000660.KS)", "000660.KS"),







]



















VIETNAM_INDEX_TICKERS = {"^VNI", "VNINDEX"}







WORK_DIR = Path(__file__).resolve().parent



DATA_DIR = WORK_DIR / "data"

REPORT_DIR = WORK_DIR / "Reports"



MARKET_CACHE_DB = DATA_DIR / "market_snapshots.sqlite3"



TAIPEI_TZ = timezone(timedelta(hours=8))



LIVE_WORKER_LIMIT = 6



YAHOO_HEADERS = {



    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"



}







YAHOO_MARGIN_BALANCE_URL = "https://tw.stock.yahoo.com/margin-balance"

TAIFEX_INSTITUTIONAL_TRADERS_URL = "https://www.taifex.com.tw/enl/eng3/totalTableDate"

TAIFEX_HEADERS = {

    "User-Agent": (

        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "

        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    ),

    "Referer": "https://www.taifex.com.tw/enl/eIndex",

}

CUSTOMS_EXPORT_CHART_URL = "https://portal.sw.nat.gov.tw/APGA/GA28_getChartData"

CUSTOMS_EXPORT_HEADERS = {
    "User-Agent": TAIFEX_HEADERS["User-Agent"],
    "Referer": "https://portal.sw.nat.gov.tw/APGA/GA28",
}






SESSION_KIND_DISPLAY = {



    "taiwan": "\u53f0\u80a1/\u6ac3\u8cb7",



    "korea": "\u97d3\u80a1",



    "japan": "\u65e5\u80a1",



    "vietnam": "\u8d8a\u5357",



    "us": "\u7f8e\u80a1",



    "all_day": "\u5168\u5929\u5831\u50f9",



}







SESSION_KIND_TZ = {



    "taiwan": "Asia/Taipei",



    "korea": "Asia/Seoul",



    "japan": "Asia/Tokyo",



    "vietnam": "Asia/Ho_Chi_Minh",



    "us": "America/New_York",



    "all_day": "Asia/Taipei",



}







SESSION_WINDOWS = {



    "taiwan": ((9, 0), (13, 30)),



    "korea": ((9, 0), (15, 30)),



    "japan": ((9, 0), (11, 30), (12, 30), (15, 0)),



    "vietnam": ((9, 0), (11, 30), (13, 0), (15, 0)),



    "us": ((9, 30), (16, 0)),



}







ALL_DAY_TICKERS = {"JPY=X", "DX-Y.NYB", "BTC-USD", "GC=F", "CL=F"}



US_TICKERS = {"^IXIC", "^GSPC", "^SOX", "TLT"}



KOREA_TICKERS = {"^KS11", "005930.KS", "000660.KS"}



JAPAN_TICKERS = {"^N225"}



TAIWAN_SUFFIXES = (".TW", ".TWO")

FINANCIAL_TICKERS = {
    "2801.TW", "2892.TW", "2886.TW", "2834.TW", "2812.TW", "2890.TW",
    "2880.TW", "2883.TW", "2884.TW", "2885.TW", "2881.TW", "2882.TW",
    "2855.TW", "00917.TW",
}

COMMODITY_TICKERS = {"GC=F", "CL=F"}
FX_TICKERS = {"JPY=X", "DX-Y.NYB"}
CRYPTO_TICKERS = {"BTC-USD"}
INDEX_TICKERS = {"^TWII", "^TWOII", "VNINDEX", "^KS11", "^N225", "^IXIC", "^GSPC", "^SOX"}

CATEGORY_OVERRIDES = {
    "2330.TW": "矽晶圓與晶片代工",
    "3711.TW": "先進封裝CoWoS概念",
    "2303.TW": "矽晶圓與晶片代工",
    "2454.TW": "IC設計&IP概念",
    "2317.TW": "電子代工/EMS",
    "2382.TW": "AIPC手機概念股",
    "2308.TW": "重電&綠能概念",
    "2383.TW": "PCB載板&SiC",
    "3008.TW": "AIPC手機概念股",
    "2313.TW": "PCB載板&SiC",
    "2357.TW": "AIPC手機概念股",
    "2344.TW": "記憶體",
    "6196.TW": "半導體廠房",
    "2408.TW": "記憶體",
    "5203.TW": "AIPC手機概念股",
    "2301.TW": "電腦週邊&電源供應",
    "3702.TW": "電子通路",
    "3034.TW": "IC設計&IP概念",
    "2376.TW": "AIPC手機概念股",
    "5274.TWO": "IC設計&IP概念",
    "3443.TW": "IC設計&IP概念",
    "8299.TWO": "記憶體",
    "2327.TW": "被動元件",
    "3037.TW": "PCB載板&SiC",
    "3653.TW": "液冷散熱概念",
    "2449.TW": "先進封裝CoWoS概念",
    "6274.TWO": "PCB載板&SiC",
    "3017.TW": "液冷散熱概念",
    "7610.TW": "再生循環&稀有金屬",
    "3481.TW": "面板",
    "6770.TW": "矽晶圓與晶片代工",
    "6409.TW": "BBU&HVDC",
    "8046.TW": "PCB載板&SiC",
    "3189.TW": "PCB載板&SiC",
    "6213.TW": "PCB載板&SiC",
    "6223.TWO": "先進封裝CoWoS概念",
    "3035.TW": "IC設計&IP概念",
    "2049.TW": "機器人與自動化",
    "6139.TW": "半導體廠房",
    "1560.TW": "半導體材料",
    "2458.TW": "IC設計&IP概念",
    "6446.TW": "生技醫療",
    "2312.TW": "電子代工/EMS",
    "6239.TW": "先進封裝CoWoS概念",
    "6176.TW": "面板",
    "2059.TW": "AIPC手機概念股",
    "3231.TW": "電子代工/EMS",
    "2392.TW": "電子代工/EMS",
    "2377.TW": "AIPC手機概念股",
}

DISPLAY_NAME_OVERRIDES = {
    "^TWOII": "櫃買指數",
    "DX-Y.NYB": "美元指數",
    "0050.TW": "0050元大台灣50",
    "0052.TW": "0052富邦科技",
    "00947.TW": "00947台新臺灣IC設計",
    "00631L.TW": "00631L元大台灣50正2",
    "00830.TW": "00830國泰費城半導體",
    "00876.TW": "00876元大全球5G",
    "00909.TW": "00909國泰數位支付服務",
    "009805.TW": "009805新光美國電力基建",
    "00910.TW": "00910第一金太空衛星",
    "0056.TW": "0056元大高股息",
    "00919.TW": "00919群益台灣精選高息",
    "00878.TW": "00878國泰永續高股息",
    "00922.TW": "00922國泰台灣領袖50",
}










@dataclass(frozen=True)



class MarketSnapshot:



    label: str



    ticker: str



    market_kind: str



    session_state: str



    price: float



    change: float



    pct: float



    volume: Optional[float]



    previous_volume: Optional[float]



    avg5_volume: Optional[float]



    fetched_at_local: str



    fetched_at_utc: str



    data_source: str











@dataclass(frozen=True)



class MarketDefinition:



    label: str



    ticker: str











@dataclass(frozen=True)



class MarginBalanceSnapshot:



    asof_date: str



    financing_change: float



    financing_balance: float



    short_change: float



    short_balance: float



    margin_ratio: float



    day_trade_change: float



    day_trade_total: float



    fetched_at_local: str



    fetched_at_utc: str



    data_source: str





@dataclass(frozen=True)
class TaifexInstitutionalTraderSnapshot:
    asof_date: str
    foreign_net: int
    foreign_change: int
    small_foreign_net: int
    small_foreign_change: int
    investment_trust_net: int
    investment_trust_change: int
    dealer_net: int
    dealer_change: int
    total_net: int
    total_change: int
    fetched_at_local: str
    fetched_at_utc: str
    data_source: str


@dataclass(frozen=True)
class TaiwanExportTrendPoint:
    period_label: str
    export_value_billion_usd: float
    yoy_pct: float


@dataclass(frozen=True)
class TaiwanExportTrendSnapshot:
    article_title: str
    article_date: str
    points: tuple[TaiwanExportTrendPoint, ...]
    fetched_at_local: str
    fetched_at_utc: str
    data_source: str


TAIWAN_EXPORT_REFERENCE_LIST_URL = "https://www.trade.gov.tw/App_Ashx/getDataByNodeid.ashx"
TAIWAN_EXPORT_REFERENCE_BASE_URL = "https://www.trade.gov.tw"
TAIWAN_EXPORT_TREND_CACHE_PATH = Path(__file__).resolve().parent / "Data" / "taiwan_export_trend_cache.json"
_ODS_NS = {
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}


MARKET_DEFINITIONS = [MarketDefinition(label=name, ticker=ticker) for name, ticker in MARKETS]











def classify_market_kind(ticker_symbol: str) -> str:



    if ticker_symbol in VIETNAM_INDEX_TICKERS:



        return "vietnam"



    if ticker_symbol in ALL_DAY_TICKERS:



        return "all_day"



    if ticker_symbol in US_TICKERS:



        return "us"



    if ticker_symbol in KOREA_TICKERS or ticker_symbol.endswith(".KS"):



        return "korea"



    if ticker_symbol in JAPAN_TICKERS:



        return "japan"



    if ticker_symbol in {"^TWII", "^TWOII"} or ticker_symbol.endswith(TAIWAN_SUFFIXES):



        return "taiwan"



    return "global"












def infer_asset_type(ticker_symbol: str) -> str:
    if ticker_symbol in INDEX_TICKERS:
        return "index"
    if ticker_symbol in COMMODITY_TICKERS:
        return "commodity"
    if ticker_symbol in FX_TICKERS:
        return "fx"
    if ticker_symbol in CRYPTO_TICKERS:
        return "crypto"
    if ticker_symbol in FINANCIAL_TICKERS:
        return "financial"
    if ticker_symbol == "TLT":
        return "etf"
    if ticker_symbol.endswith(".KS"):
        return "overseas_stock"
    if ticker_symbol.endswith(TAIWAN_SUFFIXES):
        code = ticker_symbol.split(".")[0]
        if code.startswith("00"):
            return "etf"
        return "stock"
    return "market"


def infer_symbol_category(ticker_symbol: str, asset_type: str) -> str | None:
    if ticker_symbol in CATEGORY_OVERRIDES:
        return CATEGORY_OVERRIDES[ticker_symbol]
    if asset_type == "etf":
        return "ETF"
    if asset_type == "financial":
        return "金融"
    if asset_type == "index":
        return "指數"
    if asset_type == "commodity":
        return "商品"
    if asset_type == "fx":
        return "外匯"
    if asset_type == "crypto":
        return "加密貨幣"
    if asset_type == "overseas_stock":
        return "海外股票"
    if asset_type == "stock":
        return "待分類"
    return None


def infer_symbol_metadata(label: str, ticker_symbol: str) -> dict[str, str | None]:
    asset_type = infer_asset_type(ticker_symbol)
    return {
        "symbol": ticker_symbol,
        "yahoo_ticker": ticker_symbol,
        "display_name": DISPLAY_NAME_OVERRIDES.get(ticker_symbol, label),
        "asset_type": asset_type,
        "market": classify_market_kind(ticker_symbol),
        "category": infer_symbol_category(ticker_symbol, asset_type),
        "ma_proxy_symbol": "SOXX" if ticker_symbol == "^SOX" else None,
    }


def bootstrap_symbol_master_from_markets() -> None:
    ensure_database()
    seed_category_master()
    if count_active_symbols() > 0:
        return
    for label, ticker_symbol in MARKETS:
        metadata = infer_symbol_metadata(label, ticker_symbol)
        upsert_symbol(
            symbol=str(metadata["symbol"]),
            yahoo_ticker=str(metadata["yahoo_ticker"]),
            display_name=str(metadata["display_name"]),
            asset_type=str(metadata["asset_type"]),
            market=str(metadata["market"]),
            category=metadata["category"],
            ma_proxy_symbol=metadata["ma_proxy_symbol"],
        )


def load_market_definitions() -> list[MarketDefinition]:
    try:
        bootstrap_symbol_master_from_markets()
        rows = load_active_symbols()
        if rows:
            return [MarketDefinition(label=row["display_name"], ticker=row["yahoo_ticker"]) for row in rows]
    except Exception as exc:
        print(f"[DB] symbol_master load failed, using MARKETS fallback: {exc}", file=sys.stderr)
    return MARKET_DEFINITIONS
def _nth_weekday_of_month(year: int, month: int, weekday: int, occurrence: int) -> int:



    import calendar







    month_calendar = calendar.monthcalendar(year, month)



    matches = [week[weekday] for week in month_calendar if week[weekday] != 0]



    return matches[occurrence - 1]











def _is_us_dst(utc_now: datetime) -> bool:



    year = utc_now.year



    dst_start_day = _nth_weekday_of_month(year, 3, 6, 2)



    dst_end_day = _nth_weekday_of_month(year, 11, 6, 1)



    dst_start = datetime(year, 3, dst_start_day, 7, 0, tzinfo=timezone.utc)



    dst_end = datetime(year, 11, dst_end_day, 6, 0, tzinfo=timezone.utc)



    return dst_start <= utc_now < dst_end











def get_market_local_now(market_kind: str, now_taipei: Optional[datetime] = None) -> datetime:



    reference_utc = (now_taipei or datetime.now(TAIPEI_TZ)).astimezone(timezone.utc)



    if market_kind == "us":



        offset_hours = -4 if _is_us_dst(reference_utc) else -5



    else:



        offset_hours = {



            "taiwan": 8,



            "korea": 9,



            "japan": 9,



            "vietnam": 7,



            "all_day": 8,



            "global": 8,



        }.get(market_kind, 8)



    return reference_utc.astimezone(timezone(timedelta(hours=offset_hours)))







def get_session_state_for_kind(market_kind: str, now_taipei: Optional[datetime] = None) -> str:



    if market_kind in {"all_day", "global"}:



        return "\u5168\u5929\u5831\u50f9"







    local_now = get_market_local_now(market_kind, now_taipei)







    if local_now.weekday() >= 5:



        return "\u6536\u76e4"







    minute_of_day = local_now.hour * 60 + local_now.minute



    windows = SESSION_WINDOWS[market_kind]







    def to_minutes(pair: tuple[int, int]) -> int:



        return pair[0] * 60 + pair[1]







    if market_kind in {"taiwan", "korea", "us"}:



        open_minute = to_minutes(windows[0])



        close_minute = to_minutes(windows[1])



        if minute_of_day < open_minute:



            return "\u672a\u958b\u76e4"



        if minute_of_day < close_minute:



            return "\u76e4\u4e2d"



        return "\u6536\u76e4"







    if market_kind in {"japan", "vietnam"}:



        open_1 = to_minutes(windows[0])



        close_1 = to_minutes(windows[1])



        open_2 = to_minutes(windows[2])



        close_2 = to_minutes(windows[3])



        if minute_of_day < open_1:



            return "\u672a\u958b\u76e4"



        if minute_of_day < close_1:



            return "\u76e4\u4e2d"



        if minute_of_day < open_2:



            return "\u5348\u4f11"



        if minute_of_day < close_2:



            return "\u76e4\u4e2d"



        return "\u6536\u76e4"







    return "\u6536\u76e4"











def ensure_cache_database() -> None:



    REPORT_DIR.mkdir(parents=True, exist_ok=True)



    with sqlite3.connect(MARKET_CACHE_DB, timeout=30) as connection:



        connection.execute("PRAGMA journal_mode=WAL")



        connection.execute(



            """



            CREATE TABLE IF NOT EXISTS latest_market_snapshot (



                ticker TEXT PRIMARY KEY,



                label TEXT NOT NULL,



                market_kind TEXT NOT NULL,



                session_state TEXT NOT NULL,



                price REAL NOT NULL,



                change_value REAL NOT NULL,



                pct REAL NOT NULL,



                volume REAL,



                previous_volume REAL,



                avg5_volume REAL,



                fetched_at_local TEXT NOT NULL,



                fetched_at_utc TEXT NOT NULL,



                data_source TEXT NOT NULL



            )



            """



        )











def row_to_snapshot(row: sqlite3.Row) -> MarketSnapshot:



    return MarketSnapshot(



        label=str(row["label"]),



        ticker=str(row["ticker"]),



        market_kind=str(row["market_kind"]),



        session_state=str(row["session_state"]),



        price=float(row["price"]),



        change=float(row["change_value"]),



        pct=float(row["pct"]),



        volume=float(row["volume"]) if row["volume"] is not None else None,



        previous_volume=float(row["previous_volume"]) if row["previous_volume"] is not None else None,



        avg5_volume=float(row["avg5_volume"]) if row["avg5_volume"] is not None else None,



        fetched_at_local=str(row["fetched_at_local"]),



        fetched_at_utc=str(row["fetched_at_utc"]),



        data_source=str(row["data_source"]),



    )











def load_cached_snapshot(ticker_symbol: str) -> Optional[MarketSnapshot]:



    ensure_cache_database()



    with sqlite3.connect(MARKET_CACHE_DB, timeout=30) as connection:



        connection.row_factory = sqlite3.Row



        row = connection.execute(



            "SELECT * FROM latest_market_snapshot WHERE ticker = ?",



            (ticker_symbol,),



        ).fetchone()



        if row is None:



            return None



        return row_to_snapshot(row)











def store_snapshot(snapshot: MarketSnapshot) -> None:



    ensure_cache_database()



    with sqlite3.connect(MARKET_CACHE_DB, timeout=30) as connection:



        connection.execute("PRAGMA journal_mode=WAL")



        connection.execute(



            """



            INSERT INTO latest_market_snapshot (



                ticker, label, market_kind, session_state, price, change_value, pct,



                volume, previous_volume, avg5_volume, fetched_at_local, fetched_at_utc, data_source



            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)



            ON CONFLICT(ticker) DO UPDATE SET



                label = excluded.label,



                market_kind = excluded.market_kind,



                session_state = excluded.session_state,



                price = excluded.price,



                change_value = excluded.change_value,



                pct = excluded.pct,



                volume = excluded.volume,



                previous_volume = excluded.previous_volume,



                avg5_volume = excluded.avg5_volume,



                fetched_at_local = excluded.fetched_at_local,



                fetched_at_utc = excluded.fetched_at_utc,



                data_source = excluded.data_source



            """,



            (



                snapshot.ticker,



                snapshot.label,



                snapshot.market_kind,



                snapshot.session_state,



                snapshot.price,



                snapshot.change,



                snapshot.pct,



                snapshot.volume,



                snapshot.previous_volume,



                snapshot.avg5_volume,



                snapshot.fetched_at_local,



                snapshot.fetched_at_utc,



                snapshot.data_source,



            ),



        )












def store_daily_ohlcv_snapshot(snapshot: MarketSnapshot) -> None:
    trade_date = str(snapshot.fetched_at_local or "")[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", trade_date):
        trade_date = datetime.now(TAIPEI_TZ).strftime("%Y-%m-%d")
    upsert_daily_ohlcv(
        symbol=snapshot.ticker,
        trade_date=trade_date,
        close=snapshot.price,
        change_value=snapshot.change,
        pct=snapshot.pct,
        volume=snapshot.volume,
        previous_volume=snapshot.previous_volume,
        avg5_volume=snapshot.avg5_volume,
        source=snapshot.data_source,
        fetched_at=snapshot.fetched_at_local,
    )

def fetch_json_with_retry(session: requests.Session, url: str, *, timeout: int = 15, retries: int = 4) -> dict:



    last_error: Exception | None = None



    for attempt in range(1, retries + 1):



        try:



            response = session.get(url, headers=YAHOO_HEADERS, timeout=timeout)



            response.raise_for_status()



            return response.json()



        except requests.exceptions.HTTPError as exc:



            status_code = getattr(exc.response, "status_code", None)



            if status_code is not None and int(status_code) < 500:



                raise



            last_error = exc



        except (requests.exceptions.RequestException, ValueError) as exc:



            last_error = exc







        if attempt < retries:



            time.sleep(min(2 ** (attempt - 1), 5))







    raise RuntimeError(f"Yahoo Finance request failed for {url}") from last_error















def fetch_text_with_retry(session: requests.Session, url: str, *, timeout: int = 15, retries: int = 4) -> str:



    last_error: Exception | None = None



    for attempt in range(1, retries + 1):



        try:



            response = session.get(url, headers=YAHOO_HEADERS, timeout=timeout)



            response.raise_for_status()



            return response.text



        except requests.exceptions.HTTPError as exc:



            status_code = getattr(exc.response, "status_code", None)



            if status_code is not None and int(status_code) < 500:



                raise



            last_error = exc



        except requests.exceptions.RequestException as exc:



            last_error = exc



        if attempt < retries:



            time.sleep(min(2 ** (attempt - 1), 5))



    raise RuntimeError(f"Yahoo Finance request failed for {url}") from last_error











def _parse_margin_balance_number(value: str) -> float:



    return float(value.replace(",", "").replace("%", ""))











def _parse_taifex_integer(value: str) -> int:



    text = value.replace(",", "").strip()



    if not text or text == "-":



        return 0



    return int(text)







def _fetch_taifex_institutional_rows_for_date(session: requests.Session, query_date: str) -> tuple[str, dict[str, dict[str, int]]]:
    payload = {
        "queryDate": query_date,
        "queryType": "",
        "goDay": "",
        "doQuery": "",
        "dateaddcnt": "",
        "button": "Send Query",
    }

    response = session.post(TAIFEX_INSTITUTIONAL_TRADERS_URL, headers=TAIFEX_HEADERS, data=payload, timeout=20)
    response.raise_for_status()

    html_text = response.text
    text = re.sub(r"<[^>]+>", " ", html_text)
    text = unescape(re.sub(r"\s+", " ", text))

    date_match = re.search(r"Date:(\d{4}/\d{2}/\d{2})", text)
    if not date_match:
        raise RuntimeError("TAIFEX institutional trader date not found")

    target_table_html = None
    fallback_table_html = None
    for table_html in re.findall(r"<table\b[^>]*>.*?</table>", html_text, flags=re.S | re.I):
        table_text = unescape(re.sub(r"<[^>]+>", " ", table_html))
        if all(token in table_text for token in ("Dealers", "Investment Trust", "FINI")) and fallback_table_html is None:
            fallback_table_html = table_html
        if "Open Interest and Contract Value" in table_text and all(token in table_text for token in ("Dealers", "Investment Trust", "FINI")):
            target_table_html = table_html
            break

    if target_table_html is None:
        target_table_html = fallback_table_html

    if target_table_html is None:
        raise RuntimeError("TAIFEX open interest table not found")

    rows: dict[str, dict[str, int]] = {}
    for tr_html in re.findall(r"<tr\b[^>]*>.*?</tr>", target_table_html, flags=re.S | re.I):
        cell_htmls = re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", tr_html, flags=re.S | re.I)
        cells = [re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", cell))).strip() for cell in cell_htmls]
        if len(cells) == 7 and cells[0] in {"Dealers", "Investment Trust", "FINI", "Total"}:
            rows[cells[0]] = {
                "long_volume": _parse_taifex_integer(cells[1]),
                "long_value": _parse_taifex_integer(cells[2]),
                "short_volume": _parse_taifex_integer(cells[3]),
                "short_value": _parse_taifex_integer(cells[4]),
                "net_volume": _parse_taifex_integer(cells[5]),
                "net_value": _parse_taifex_integer(cells[6]),
            }

    if "FINI" not in rows:
        raise RuntimeError("TAIFEX FINI row not found")

    return date_match.group(1), rows
def _fetch_taifex_institutional_rows(session: requests.Session, reference_now: datetime) -> tuple[str, dict[str, dict[str, int]], str, dict[str, dict[str, int]]]:



    def find_trading_date(start_date: datetime.date) -> tuple[str, dict[str, dict[str, int]]]:



        for lookback in range(0, 16):



            candidate = (start_date - timedelta(days=lookback)).strftime("%Y/%m/%d")



            try:



                return _fetch_taifex_institutional_rows_for_date(session, candidate)



            except Exception:



                continue



        raise RuntimeError("Unable to locate a TAIFEX institutional trader trading day")



    current_date, current_rows = find_trading_date(reference_now.date())

    previous_date_obj = datetime.strptime(current_date, "%Y/%m/%d").date()

    previous_date, previous_rows = find_trading_date(previous_date_obj - timedelta(days=1))

    return current_date, current_rows, previous_date, previous_rows







def fetch_taifex_institutional_traders(reference_now: Optional[datetime] = None, session: Optional[requests.Session] = None) -> TaifexInstitutionalTraderSnapshot:
    row = load_latest_institutional_futures_snapshot()
    if row is None:
        raise RuntimeError('institutional futures cache is empty; seed institutional_futures_snapshot first')
    return TaifexInstitutionalTraderSnapshot(**row)

def fetch_yahoo_margin_balance(session: Optional[requests.Session] = None) -> MarginBalanceSnapshot:
    if session is None:
        with requests.Session() as auto_session:
            return fetch_yahoo_margin_balance(auto_session)

    html_text = fetch_text_with_retry(session, YAHOO_MARGIN_BALANCE_URL, timeout=20, retries=4)

    table_anchor = html_text.find("table-body-wrapper")
    if table_anchor == -1:
        raise RuntimeError("Yahoo margin balance table body not found")

    row_start = html_text.find('<li class="List(n)">', table_anchor)
    if row_start == -1:
        raise RuntimeError("Yahoo margin balance latest row not found")

    next_row_start = html_text.find('</li><li class="List(n)">', row_start)
    if next_row_start == -1:
        raise RuntimeError("Yahoo margin balance row boundary not found")

    row_html = html_text[row_start:next_row_start]

    date_match = re.search(r'<div class="W\(112px\) Ta\(start\)">(.*?)</div>', row_html)
    if not date_match:
        raise RuntimeError("Yahoo margin balance date not found")

    numbers = re.findall(r'>([-+]?\d[\d,]*(?:\.\d+)?%?)<', row_html)
    if len(numbers) < 7:
        raise RuntimeError(f"Yahoo margin balance row did not contain enough numeric fields: {numbers}")

    local_now = datetime.now(TAIPEI_TZ)

    return MarginBalanceSnapshot(
        asof_date=unescape(date_match.group(1)).strip(),
        financing_change=_parse_margin_balance_number(numbers[0]),
        financing_balance=_parse_margin_balance_number(numbers[1]),
        short_change=_parse_margin_balance_number(numbers[2]),
        short_balance=_parse_margin_balance_number(numbers[3]),
        margin_ratio=_parse_margin_balance_number(numbers[4]),
        day_trade_change=_parse_margin_balance_number(numbers[5]),
        day_trade_total=_parse_margin_balance_number(numbers[6]),
        fetched_at_local=local_now.strftime("%Y-%m-%d %H:%M:%S"),
        fetched_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        data_source="live-yahoo",
    )
def fetch_yahoo_snapshot(



    session: requests.Session,



    label: str,



    ticker_symbol: str,



    market_kind: str,



    session_state: str,



) -> MarketSnapshot:



    encoded_ticker = quote(ticker_symbol, safe="")



    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded_ticker}?range=1mo&interval=1d"



    data = fetch_json_with_retry(session, url, timeout=15, retries=4)







    chart = data.get("chart", {})



    error = chart.get("error")



    if error:



        raise RuntimeError(error.get("description") or error.get("code") or "Yahoo Finance returned an error")







    results = chart.get("result") or []



    if not results:



        raise RuntimeError("Yahoo Finance returned empty data")







    result = results[0]



    meta = result.get("meta") or {}



    indicators = result.get("indicators") or {}



    quote_data = (indicators.get("quote") or [{}])[0]



    close_history = [float(value) for value in (quote_data.get("close") or []) if value is not None]



    volume_history = [float(value) for value in (quote_data.get("volume") or []) if value is not None]







    price = meta.get("regularMarketPrice")
    if session_state == "收盤" and close_history:
        price = close_history[-1]
    if price in (None, "") and close_history:
        price = close_history[-1]

    prev_close = None



    if len(close_history) >= 2:



        prev_close = close_history[-2]



    if prev_close in (None, ""):



        prev_close = meta.get("previousClose")



    if prev_close in (None, ""):



        prev_close = meta.get("chartPreviousClose")







    if price in (None, "") or prev_close in (None, ""):



        raise RuntimeError("Yahoo Finance did not return usable price data")







    price = float(price)



    prev_close = float(prev_close)



    change = price - prev_close



    pct = (change / prev_close * 100) if prev_close else 0.0







    current_volume = meta.get("regularMarketVolume")



    if session_state == "收盤" and volume_history:



        current_volume = volume_history[-1]



    if current_volume in (None, "") and volume_history:



        current_volume = volume_history[-1]



    current_volume = float(current_volume) if current_volume not in (None, "") else None







    previous_volume = float(volume_history[-2]) if len(volume_history) >= 2 else None



    prior_history = volume_history[:-1]



    avg5_volume = float(mean(prior_history[-5:])) if prior_history else None







    local_now = datetime.now(TAIPEI_TZ)



    return MarketSnapshot(



        label=label,



        ticker=ticker_symbol,



        market_kind=market_kind,



        session_state=session_state,



        price=price,



        change=change,



        pct=pct,



        volume=current_volume,



        previous_volume=previous_volume,



        avg5_volume=avg5_volume,



        fetched_at_local=local_now.strftime("%Y-%m-%d %H:%M:%S"),



        fetched_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),



        data_source="live",



    )





def print_taifex_institutional_trader_snapshot(snapshot: TaifexInstitutionalTraderSnapshot) -> None:
    def signed(value: int) -> str:
        return f"+{value:,}" if value >= 0 else f"{value:,}"

    print("台指期貨法人未平倉淨部位（快取）")
    print(f"  數據日期: {snapshot.asof_date}")
    print(f"  外資: {snapshot.foreign_net:,} ({signed(snapshot.foreign_change)})")
    print(f"  小外資: {snapshot.small_foreign_net:,} ({signed(snapshot.small_foreign_change)})")
    print(f"  投信: {snapshot.investment_trust_net:,} ({signed(snapshot.investment_trust_change)})")
    print(f"  自營商: {snapshot.dealer_net:,} ({signed(snapshot.dealer_change)})")
    print(f"  合計: {snapshot.total_net:,} ({signed(snapshot.total_change)})")
    if snapshot.foreign_net < 0:
        print(f"  外資方向: 空單 {abs(snapshot.foreign_net):,} 口")
    else:
        print(f"  外資方向: 多單 {snapshot.foreign_net:,} 口")
    print(f"  擷取時間: {snapshot.fetched_at_local}")
    print(f"  資料來源: {snapshot.data_source}")

def _parse_taiwan_export_float(value: str) -> float:
    cleaned = value.replace(',', '').replace('%', '').replace('?', '-').replace('?', '-').replace(' ', '').strip()
    if not cleaned:
        raise ValueError('empty numeric value')
    return float(cleaned)



def _read_ods_table_rows(table: ET.Element) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.findall('./table:table-row', _ODS_NS):
        values: list[str] = []
        for cell in row.findall('./table:table-cell', _ODS_NS):
            repeat = int(cell.get(f"{{{_ODS_NS['table']}}}number-columns-repeated") or '1')
            text = ''.join(cell.itertext()).replace(' ', ' ').strip()
            for _ in range(repeat):
                values.append(text)
                if len(values) >= 9:
                    break
            if len(values) >= 9:
                break
        rows.append(values)
    return rows



def _extract_taiwan_export_month_rows(ods_blob: bytes) -> list[TaiwanExportTrendPoint]:
    with zipfile.ZipFile(io.BytesIO(ods_blob)) as archive:
        content = archive.read('content.xml')

    root = ET.fromstring(content)
    tables = root.findall('.//table:table', _ODS_NS)
    target_table = None
    for table in tables:
        name = table.get(f"{{{_ODS_NS['table']}}}name", '')
        if '二1我國整體進出口貿易' in name or '我國整體進出口貿易' in name:
            target_table = table
            break
    if target_table is None:
        raise RuntimeError('trade reference indicator table not found in ODS')

    rows = _read_ods_table_rows(target_table)
    current_year = None
    monthly_rows: list[tuple[int, int, float, float]] = []
    for row in rows:
        if not row:
            continue
        label = row[0].strip()
        year_match = re.match(r'^(\d+)年$', label)
        if year_match:
            current_year = int(year_match.group(1))
            continue
        month_match = re.match(r'^(\d+)月(?:\([^)]+\))?$', label)
        if current_year is None or month_match is None:
            continue
        if len(row) < 5:
            continue
        month = int(month_match.group(1))
        export_value = _parse_taiwan_export_float(row[3])
        yoy_pct = _parse_taiwan_export_float(row[4])
        monthly_rows.append((current_year, month, export_value, yoy_pct))

    if len(monthly_rows) < 3:
        raise RuntimeError('not enough monthly export rows found in ODS')

    latest_rows = monthly_rows[-3:]
    points = []
    for roc_year, month, export_value, yoy_pct in latest_rows:
        gregorian_year = roc_year + 1911
        points.append(
            TaiwanExportTrendPoint(
                period_label=f'{gregorian_year}年{month}月',
                export_value_billion_usd=export_value,
                yoy_pct=yoy_pct,
            )
        )
    return points



def _load_taiwan_export_trend_cache() -> TaiwanExportTrendSnapshot | None:
    if not TAIWAN_EXPORT_TREND_CACHE_PATH.exists():
        return None
    try:
        payload = json.loads(TAIWAN_EXPORT_TREND_CACHE_PATH.read_text(encoding='utf-8'))
        points = tuple(TaiwanExportTrendPoint(**item) for item in payload['points'])
        return TaiwanExportTrendSnapshot(
            article_title=payload['article_title'],
            article_date=payload['article_date'],
            points=points,
            fetched_at_local=payload['fetched_at_local'],
            fetched_at_utc=payload['fetched_at_utc'],
            data_source=payload['data_source'],
        )
    except Exception:
        return None



def _save_taiwan_export_trend_cache(snapshot: TaiwanExportTrendSnapshot) -> None:
    payload = {
        'article_title': snapshot.article_title,
        'article_date': snapshot.article_date,
        'points': [asdict(point) for point in snapshot.points],
        'fetched_at_local': snapshot.fetched_at_local,
        'fetched_at_utc': snapshot.fetched_at_utc,
        'data_source': snapshot.data_source,
    }
    TAIWAN_EXPORT_TREND_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TAIWAN_EXPORT_TREND_CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')



def _month_only(period_label: str) -> str:
    return period_label.split('年', 1)[1] if '年' in period_label else period_label



def _describe_taiwan_export_trend(points: tuple[TaiwanExportTrendPoint, ...]) -> str:
    if len(points) < 3:
        return '資料不足'
    first, second, third = points[-3:]
    middle_month = _month_only(second.period_label)
    latest_month = _month_only(third.period_label)
    middle_phrase = f'{middle_month}回落' if second.export_value_billion_usd < first.export_value_billion_usd else f'{middle_month}反彈'
    if third.export_value_billion_usd > second.export_value_billion_usd:
        latest_phrase = f'{latest_month}反彈' if second.export_value_billion_usd < first.export_value_billion_usd else f'{latest_month}繼強'
    elif third.export_value_billion_usd < second.export_value_billion_usd:
        latest_phrase = f'{latest_month}回落'
    else:
        latest_phrase = f'{latest_month}持平'
    return f'{middle_phrase}、{latest_phrase}'



def _format_taiwan_export_trend_summary(snapshot: TaiwanExportTrendSnapshot) -> str:
    points = snapshot.points[-3:]
    if len(points) < 3:
        return '台灣出口資料不足。'
    p1, p2, p3 = points
    return (
        f'台灣出口近三個月仍強：{p1.period_label} {p1.export_value_billion_usd:.2f} 億美元、年增 {p1.yoy_pct:.2f}%；'
        f'{_month_only(p2.period_label)} {p2.export_value_billion_usd:.2f} 億美元、年增 {p2.yoy_pct:.2f}%；'
        f'{_month_only(p3.period_label)} {p3.export_value_billion_usd:.2f} 億美元、年增 {p3.yoy_pct:.2f}%。'
    )



@lru_cache(maxsize=1)
def fetch_taiwan_export_trend() -> TaiwanExportTrendSnapshot:
    cache_snapshot = _load_taiwan_export_trend_cache()

    params = {
        'nodeID': '1374',
        'keyword': '',
        'calendarTo': '',
        'calendarFrom': '',
        'history': 'y',
        'datatime': 'all',
        'pageindex': '1',
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': 'https://www.trade.gov.tw/Pages/List.aspx?nodeID=1374',
    }

    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = requests.get(TAIWAN_EXPORT_REFERENCE_LIST_URL, params=params, headers=headers, timeout=45)
            response.raise_for_status()
            payload = response.json()
            html_payload = payload.get('Html') or ''
            matches = re.findall(r'<a href="([^"]+)" title="([^"]+)">([^<]+)</a>', html_payload)
            if not matches:
                raise RuntimeError('trade reference indicator list is empty')

            latest_article_title = unescape(matches[0][1]).replace('\xa0', ' ').strip()
            if cache_snapshot is not None and cache_snapshot.article_title == latest_article_title:
                return cache_snapshot


            detail_href = matches[0][0]
            detail_url = urljoin(TAIWAN_EXPORT_REFERENCE_BASE_URL, detail_href)
            detail_response = requests.get(detail_url, headers=headers, timeout=45)
            detail_response.raise_for_status()
            detail_html = detail_response.text

            title_match = re.search(r'<h2 class="tender-title">\s*(.*?)\s*</h2>', detail_html, re.S)
            date_match = re.search(r'<span class="date">\s*([0-9-]+)\s*</span>', detail_html, re.S)
            if not title_match or not date_match:
                raise RuntimeError('trade reference indicator detail page is missing the expected article header')

            article_title = unescape(title_match.group(1)).replace(' ', ' ').strip()
            article_date = date_match.group(1).strip()
            attachment_hrefs = re.findall(r"href=[\"'](?P<href>/App_Ashx/File\.ashx\?FileID=[^\"']+)[\"']", detail_html, re.S)
            if not attachment_hrefs:
                raise RuntimeError('trade reference indicator detail page is missing downloadable attachments')

            for attachment_href in attachment_hrefs:
                attachment_url = urljoin(TAIWAN_EXPORT_REFERENCE_BASE_URL, attachment_href)
                ods_response = requests.get(attachment_url, headers=headers, timeout=60)
                ods_response.raise_for_status()
                try:
                    points = tuple(_extract_taiwan_export_month_rows(ods_response.content))
                except Exception:
                    last_error = sys.exc_info()[1]
                    continue

                snapshot = TaiwanExportTrendSnapshot(
                    article_title=article_title,
                    article_date=article_date,
                    points=points,
                    fetched_at_local=datetime.now(ZoneInfo('Asia/Taipei')).isoformat(timespec='seconds'),
                    fetched_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                    data_source=f'{article_title} | trade.gov.tw reference indicator attachment',
                )
                _save_taiwan_export_trend_cache(snapshot)
                return snapshot

            raise RuntimeError('no downloadable attachment on the trade reference indicator page produced an export table')
        except Exception as exc:
            last_error = exc
            if attempt >= 3:
                break
            delay_seconds = min(2 ** (attempt - 1), 5)
            print(f'[WARN] Taiwan export trend fetch attempt {attempt}/3 failed: {exc}; retrying in {delay_seconds}s...', file=sys.stderr)
            time.sleep(delay_seconds)

    if cache_snapshot is not None:
        return cache_snapshot
    raise RuntimeError('Taiwan export trend fetch failed') from last_error



def print_taiwan_export_trend_snapshot(snapshot: TaiwanExportTrendSnapshot) -> None:
    print('【台灣出口近三月】')
    print(f'  來源: {snapshot.article_title} | {snapshot.article_date}')
    summary_line = _format_taiwan_export_trend_summary(snapshot)
    print(f'  摘要: {summary_line}')
    trend_desc = _describe_taiwan_export_trend(snapshot.points)
    print(f'  月度趨勢: {trend_desc}')
    print(f'  發布日: {snapshot.article_date}')
    print(f'  資料來源: {snapshot.data_source}')


def fetch_vietnam_index_via_hose(session: requests.Session) -> tuple[float, float, float]:



    headers = {



        "User-Agent": YAHOO_HEADERS["User-Agent"],



    }



    url = "https://api.hsx.vn/l/api/v1/indicies/hoseindexinfo/homepage?type=VNINDEX"



    max_attempts = 4



    data = None







    for attempt in range(1, max_attempts + 1):



        try:



            response = session.get(url, headers=headers, timeout=45)



            response.raise_for_status()



            data = response.json()



            break



        except requests.exceptions.Timeout as exc:



            if attempt >= max_attempts:



                raise RuntimeError(f"HOSE VNINDEX timed out after {max_attempts} attempts") from exc



            delay_seconds = min(2 ** (attempt - 1), 5)



            print(f"[VNINDEX] timeout on attempt {attempt}/{max_attempts}; retrying in {delay_seconds}s...")



            time.sleep(delay_seconds)



        except requests.exceptions.RequestException as exc:



            if attempt >= max_attempts:



                raise RuntimeError(f"HOSE VNINDEX request failed after {max_attempts} attempts") from exc



            delay_seconds = min(2 ** (attempt - 1), 5)



            print(f"[VNINDEX] request failed on attempt {attempt}/{max_attempts}; retrying in {delay_seconds}s...")



            time.sleep(delay_seconds)







    if data is None:



        raise RuntimeError("HOSE VNINDEX request failed")







    items = data.get("data") or []



    if not items:



        raise RuntimeError("HOSE VNINDEX returned empty data")







    item = items[0] or {}



    current_price_raw = item.get("value")



    percent_raw = item.get("percent")



    if current_price_raw in (None, ""):



        raise RuntimeError("HOSE VNINDEX did not return a live price")



    if percent_raw in (None, ""):



        raise RuntimeError("HOSE VNINDEX did not return a percent change")







    current_price = float(str(current_price_raw).replace(",", ""))



    change_percent = float(str(percent_raw).replace("%", "").replace(",", ""))



    if change_percent <= -100:



        raise RuntimeError("HOSE VNINDEX percent change cannot be converted to a previous close")







    prev_close = current_price / (1 + (change_percent / 100))



    change = current_price - prev_close



    return current_price, change, change_percent











def fetch_vietnam_snapshot(



    session: requests.Session,



    label: str,



    ticker_symbol: str,



    market_kind: str,



    session_state: str,



) -> MarketSnapshot:



    yahoo_snapshot: Optional[MarketSnapshot] = None



    yahoo_error: Optional[Exception] = None



    try:



        yahoo_snapshot = fetch_yahoo_snapshot(session, label, "^VNI", market_kind, session_state)



    except Exception as exc:



        yahoo_error = exc







    hose_error: Optional[Exception] = None



    hose_price: Optional[tuple[float, float, float]] = None



    try:



        hose_price = fetch_vietnam_index_via_hose(session)



    except Exception as exc:



        hose_error = exc







    if hose_price is not None and yahoo_snapshot is not None:



        current_price, change, pct = hose_price



        return replace(



            yahoo_snapshot,



            ticker=ticker_symbol,



            price=current_price,



            change=change,



            pct=pct,



            data_source="live",



        )







    if hose_price is not None:



        current_price, change, pct = hose_price



        local_now = datetime.now(TAIPEI_TZ)



        return MarketSnapshot(



            label=label,



            ticker=ticker_symbol,



            market_kind=market_kind,



            session_state=session_state,



            price=current_price,



            change=change,



            pct=pct,



            volume=None,



            previous_volume=None,



            avg5_volume=None,



            fetched_at_local=local_now.strftime("%Y-%m-%d %H:%M:%S"),



            fetched_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),



            data_source="live",



        )







    if yahoo_snapshot is not None:



        return replace(



            yahoo_snapshot,



            ticker=ticker_symbol,



            data_source="live-yahoo-fallback",



        )







    raise RuntimeError(f"Vietnam data fetch failed: hose={hose_error}; yahoo={yahoo_error}")











def fetch_market_snapshot_live(



    label: str,



    ticker_symbol: str,



    market_kind: str,



    session_state: str,



) -> MarketSnapshot:



    with requests.Session() as session:



        if market_kind == "vietnam":



            return fetch_vietnam_snapshot(session, label, ticker_symbol, market_kind, session_state)



        return fetch_yahoo_snapshot(session, label, ticker_symbol, market_kind, session_state)















def fetch_market_snapshot(



    label: str,



    ticker_symbol: str,



    *,



    reference_now: Optional[datetime] = None,



) -> MarketSnapshot:



    market_kind = classify_market_kind(ticker_symbol)



    session_state = get_session_state_for_kind(market_kind, reference_now or datetime.now(TAIPEI_TZ))



    cached_snapshot = load_cached_snapshot(ticker_symbol)





    try:



        live_snapshot = fetch_market_snapshot_live(label, ticker_symbol, market_kind, session_state)



        return live_snapshot



    except Exception as exc:



        if cached_snapshot is not None:



            return replace(cached_snapshot, session_state=session_state, data_source="cache-fallback")



        raise RuntimeError(f"{label} ??????????????: {exc}") from exc





def format_volume_value(value: Optional[float]) -> str:



    if value in (None, 0):



        return "N/A"



    return f"{value:,.0f}"











def format_volume_delta(current_volume: Optional[float], reference_volume: Optional[float]) -> str:



    if current_volume in (None, 0) or reference_volume in (None, 0):



        return "N/A"



    delta = (current_volume - reference_volume) / reference_volume * 100



    return f"{delta:+.1f}%"











def build_session_title(session_states: dict[str, str], has_all_day_quotes: bool) -> str:



    parts: list[str] = []



    for kind in ("taiwan", "korea", "japan", "vietnam", "us"):



        state = session_states.get(kind)



        if state:



            parts.append(f"{SESSION_KIND_DISPLAY[kind]}{state}")



    if has_all_day_quotes:



        parts.append(SESSION_KIND_DISPLAY["all_day"])



    if not parts:



        return "\u5168\u7403\u5e02\u5834"



    return "\uff5c".join(parts)











def build_session_summary(session_states: dict[str, str], has_all_day_quotes: bool) -> str:



    parts: list[str] = []



    for kind in ("taiwan", "korea", "japan", "vietnam", "us"):



        state = session_states.get(kind)



        if state:



            parts.append(f"{SESSION_KIND_DISPLAY[kind]}{state}")



    summary = "\u3001".join(parts) if parts else "\u5168\u7403\u5e02\u5834"



    if has_all_day_quotes:



        suffix = "\u5916\u532f/\u5546\u54c1/\u52a0\u5bc6\u70ba\u5168\u5929\u5831\u50f9"



        summary = f"{summary}\uff1b{suffix}" if summary else suffix



    return summary











def print_market_snapshot(snapshot: MarketSnapshot) -> None:



    change_sign = "+" if snapshot.change >= 0 else ""



    pct_sign = "+" if snapshot.pct >= 0 else ""



    print(f"【{snapshot.label}】")



    print(f"  最新價格: {snapshot.price:.2f}")



    print(f"  漲跌: {change_sign}{snapshot.change:.2f}")



    print(f"  漲跌幅: {pct_sign}{snapshot.pct:.2f}%")



    print(f"  交易狀態: {snapshot.session_state}")



    print(f"  擷取時間: {snapshot.fetched_at_local}")



    print(f"  成交量: {format_volume_value(snapshot.volume)}")



    print(f"  前日成交量: {format_volume_value(snapshot.previous_volume)}")



    print(f"  5日均量: {format_volume_value(snapshot.avg5_volume)}")



    print(



        f"  量能: 較前日 {format_volume_delta(snapshot.volume, snapshot.previous_volume)}"



        f"，較5日 {format_volume_delta(snapshot.volume, snapshot.avg5_volume)}"



    )



    print(f"  資料來源: {snapshot.data_source}")











def print_margin_balance_snapshot(snapshot: MarginBalanceSnapshot) -> None:



    financing_change_sign = "+" if snapshot.financing_change >= 0 else ""



    short_change_sign = "+" if snapshot.short_change >= 0 else ""



    day_trade_change_sign = "+" if snapshot.day_trade_change >= 0 else ""



    print("【Yahoo 融資融券】")



    print(f"  日期: {snapshot.asof_date}")



    print(f"  融資餘額: {snapshot.financing_balance:,.2f} 億元，增減 {financing_change_sign}{snapshot.financing_change:.2f} 億")



    print(f"  融券餘額: {snapshot.short_balance:,.0f} 張，增減 {short_change_sign}{snapshot.short_change:,.0f} 張")



    print(f"  券資比: {snapshot.margin_ratio:.2f}%")



    print(f"  當沖總量: {snapshot.day_trade_total:,.0f} 張，增減 {day_trade_change_sign}{snapshot.day_trade_change:,.0f} 張")



    print(f"  擷取時間: {snapshot.fetched_at_local}")



    print(f"  資料來源: {snapshot.data_source}")









def get_market_data() -> None:



    run_started = datetime.now(TAIPEI_TZ)

    market_definitions = load_market_definitions()



    market_states: dict[str, str] = {}



    for kind in ("taiwan", "korea", "japan", "vietnam", "us"):



        market_states[kind] = get_session_state_for_kind(kind, run_started)







    has_all_day_quotes = any(defn.ticker in ALL_DAY_TICKERS for defn in market_definitions)



    title = build_session_title(market_states, has_all_day_quotes=has_all_day_quotes)



    summary = build_session_summary(market_states, has_all_day_quotes=has_all_day_quotes)







    print(f"=== 市場快訊：{title} ===")



    print(f"時間 (台北): {run_started.strftime('%Y-%m-%d %H:%M:%S')}")



    print(f"交易狀態: {summary}")



    print("快取說明: 非交易中市場可使用 SQLite 快取資料")



    print(f"快取資料庫: {MARKET_CACHE_DB}")







    started_at = time.perf_counter()



    results = [None] * len(market_definitions)



    margin_snapshot: MarginBalanceSnapshot | None = None

    taifex_snapshot: TaifexInstitutionalTraderSnapshot | None = None







    with ThreadPoolExecutor(max_workers=min(LIVE_WORKER_LIMIT, len(market_definitions))) as executor:



        futures = {



            executor.submit(fetch_yahoo_margin_balance): "margin",



            executor.submit(fetch_taifex_institutional_traders, reference_now=run_started): "taifex",



            **{



                executor.submit(fetch_market_snapshot, definition.label, definition.ticker, reference_now=run_started): index



                for index, definition in enumerate(market_definitions)



            },



        }



        for future in as_completed(futures):



            token = futures[future]



            if token == "margin":



                try:



                    margin_snapshot = future.result()



                except Exception as exc:



                    print(f"[WARN] Yahoo ???????????: {exc}", file=sys.stderr)



                continue







            if token == "taifex":



                try:



                    taifex_snapshot = future.result()



                except Exception as exc:



                    print(f"[WARN] TAIFEX ???????????: {exc}", file=sys.stderr)



                continue







            index = token



            definition = market_definitions[index]



            try:



                results[index] = ("ok", future.result())



            except Exception as exc:



                results[index] = ("error", f"{definition.label} ??????????????: {exc}")







    if margin_snapshot is not None:



        print_margin_balance_snapshot(margin_snapshot)



    if taifex_snapshot is not None:



        print_taifex_institutional_trader_snapshot(taifex_snapshot)



    
    try:
        export_trend_snapshot = fetch_taiwan_export_trend()
    except Exception as exc:
        print(f"[WARN] Taiwan export trend fetch failed: {exc}", file=sys.stderr)
    else:
        print_taiwan_export_trend_snapshot(export_trend_snapshot)

    print("-" * 40)







    for entry in results:



        if not entry:



            continue



        status, payload = entry



        if status == "ok" and isinstance(payload, MarketSnapshot):



            if payload.data_source.startswith("live"):



                try:



                    store_snapshot(payload)
                    store_daily_ohlcv_snapshot(payload)



                except Exception as exc:



                    print(f"[CACHE] ?????????: {payload.label} - {exc}")



            print_market_snapshot(payload)



        else:



            print(f"?{payload}?")



        print("-" * 40)







    elapsed_seconds = time.perf_counter() - started_at



    print(f"???: {elapsed_seconds:.1f} ?")







if __name__ == "__main__":



    sys.stdout.reconfigure(encoding="utf-8")



    get_market_data()








