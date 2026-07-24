#!/usr/bin/env python3
"""Validate local and optionally deployed TaiwanStockBot report artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


TAIPEI_TZ = timezone(timedelta(hours=8))
REQUIRED_SECTIONS = (
    "台灣指數", "韓日股市", "美國股市", "市場總覽", "產業龍頭觀察",
    "ETF 分組觀察", "ETF 操作表", "金融股操作表", "個股操作表",
)
REQUIRED_LEADERS = (
    "2330台積電", "2454聯發科", "2308台達電", "2383台光電",
    "2327國巨", "3711日月光投控", "2317鴻海",
)
REQUIRED_ETFS = (
    "0050", "009816", "00981A", "00403A", "00991A", "00988A",
    "00990A", "00909", "00895", "00830", "00757", "00735", "00924",
    "00876", "00910", "0056", "00919", "00878", "00900", "00713",
)
REQUIRED_ETF_GROUPS = (
    "市值型 ETF", "主動型國內 ETF", "主動型國外 ETF", "國外 ETF", "高股息 ETF",
)
DUPLICATE_LABELS = ("美元指數 美元指數", "日圓匯率 日圓匯率")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def load_version(path: Path) -> dict[str, str]:
    value = json.loads(read_text(path))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return {str(key): str(item) for key, item in value.items()}


def fetch_text(url: str) -> str:
    request = Request(url, headers={
        "User-Agent": "TaiwanStockBot-report-validator/1.0",
        "Cache-Control": "no-cache",
    })
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}: {url}")
        return response.read().decode("utf-8-sig")


def fetch_json(url: str) -> dict:
    value = json.loads(fetch_text(url))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object from {url}")
    return value


def require_tokens(text: str, tokens: tuple[str, ...], label: str, errors: list[str]) -> None:
    for token in tokens:
        if token not in text:
            errors.append(f"Missing {label}: {token}")


def require_order(text: str, tokens: tuple[str, ...], label: str, errors: list[str]) -> None:
    positions = [text.find(token) for token in tokens]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        errors.append(f"Missing or out-of-order {label}: {', '.join(tokens)}")


def extract_market_date(text: str, heading: str) -> str | None:
    pattern = rf"{re.escape(heading)}.*?資料日期:\s*(\d{{4}}/\d{{2}}/\d{{2}})"
    match = re.search(pattern, text, flags=re.S)
    return match.group(1) if match else None


def section_slice(text: str, start: str, end: str) -> str:
    start_index = text.find(start)
    end_index = text.find(end, start_index + len(start)) if start_index >= 0 else -1
    if start_index < 0:
        return ""
    return text[start_index:] if end_index < 0 else text[start_index:end_index]


def latest_twse_margin_date(reference_date: datetime) -> str:
    base = "https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN"
    for lookback in range(16):
        candidate = reference_date.date() - timedelta(days=lookback)
        query = urlencode({
            "date": candidate.strftime("%Y%m%d"), "selectType": "MS", "response": "json",
        })
        payload = fetch_json(f"{base}?{query}")
        if payload.get("stat") == "OK" and payload.get("date"):
            return datetime.strptime(str(payload["date"]), "%Y%m%d").strftime("%Y/%m/%d")
    raise RuntimeError("Unable to locate an official TWSE margin date within 16 days")


def latest_taifex_date(repo: Path, reference_date: datetime) -> str:
    sys.path.insert(0, str(repo))
    import requests  # type: ignore
    from fetch_stock_data import _fetch_taifex_institutional_rows  # type: ignore

    with requests.Session() as session:
        current_date, _, _, _ = _fetch_taifex_institutional_rows(session, reference_date)
    return current_date


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_content(text: str, prefix: str, errors: list[str]) -> None:
    require_tokens(text, REQUIRED_SECTIONS, f"{prefix}section", errors)
    leader_section = section_slice(text, "產業龍頭觀察", "ETF 分組觀察")
    require_tokens(leader_section, REQUIRED_LEADERS, f"{prefix}leader commentary", errors)
    require_tokens(text, REQUIRED_ETFS, f"{prefix}ETF", errors)
    require_order(text, REQUIRED_ETF_GROUPS, f"{prefix}ETF groups", errors)
    for label in DUPLICATE_LABELS:
        if label in text:
            errors.append(f"Duplicated {prefix}display label: {label}")
    compact_ma = re.search(r"(?:^|[>|\s])5[+\-=]、10[+\-=]", text)
    legend_tokens = ("均線簡寫", "+ 代表", "＋代表", "「+」代表", "「＋」代表")
    if compact_ma and not any(token in text for token in legend_tokens):
        errors.append(f"Compact {prefix}moving-average notation has no explicit legend")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=None, help="TaiwanStockBot repository root")
    parser.add_argument("--public-url", help="Firebase Hosting base URL to verify")
    parser.add_argument("--check-official-dates", action="store_true")
    parser.add_argument("--check-deploy-log", action="store_true")
    parser.add_argument("--max-report-age-days", type=int, default=None)
    args = parser.parse_args()

    repo = args.repo.resolve() if args.repo else Path(__file__).resolve().parents[4]
    version_path = repo / "web" / "report-version.json"
    index_path = repo / "web" / "index.html"
    market_path = repo / "market_data.txt"
    errors: list[str] = []

    for path in (version_path, index_path, market_path):
        if not path.is_file():
            errors.append(f"Missing artifact: {path}")
    if errors:
        print("\n".join(f"ERROR: {item}" for item in errors), file=sys.stderr)
        return 1

    version = load_version(version_path)
    index = read_text(index_path)
    market = read_text(market_path)
    validate_content(index, "", errors)

    version_value = version.get("version", "")
    report_path = repo / "Reports" / f"Report_{version_value}.html"
    if not report_path.is_file():
        errors.append(f"Missing version-matched archived report: {report_path}")
    elif sha256(report_path) != sha256(index_path):
        errors.append("Archived report content does not match web/index.html")

    now_taipei = datetime.now(TAIPEI_TZ)
    if args.max_report_age_days is not None:
        try:
            report_date = datetime.strptime(version_value[:8], "%Y%m%d").date()
            age = (now_taipei.date() - report_date).days
            if age < 0 or age > args.max_report_age_days:
                errors.append(f"Report age is {age} days; maximum is {args.max_report_age_days}")
        except ValueError:
            errors.append(f"Invalid report version date: {version_value}")

    taifex_date = extract_market_date(market, "台指期貨法人未平倉淨部位")
    margin_date = (
        extract_market_date(market, "【融資融券】")
        or extract_market_date(market, "【Yahoo 融資融券】")
    )
    if not taifex_date:
        errors.append("Missing TAIFEX data date")
    if "live-taifex-tx-open-interest" not in market:
        errors.append("TAIFEX source is not the official live TX open-interest source")
    if not margin_date:
        errors.append("Missing margin data date")
    if (
        "資料來源: live-twse-official" not in market
        and "資料來源: live-yahoo" not in market
    ):
        errors.append("Margin data did not record a live TWSE/Yahoo fetch")

    official_taifex_date = None
    official_margin_date = None
    if args.check_official_dates:
        official_taifex_date = latest_taifex_date(repo, now_taipei)
        official_margin_date = latest_twse_margin_date(now_taipei)
        if taifex_date != official_taifex_date:
            errors.append(f"TAIFEX date {taifex_date} != official latest {official_taifex_date}")
        if margin_date != official_margin_date:
            errors.append(f"Margin date {margin_date} != official latest {official_margin_date}")

    if args.check_deploy_log:
        logs = sorted((repo / "Reports").glob("post_report_sync_*.log"), key=lambda path: path.stat().st_mtime)
        if not logs:
            errors.append("Missing deployment log")
        else:
            deploy_log = read_text(logs[-1])
            for marker in ("release complete", "Firebase deploy completed"):
                if marker not in deploy_log:
                    errors.append(f"Latest deployment log is missing: {marker}")

    public_version = None
    if args.public_url:
        base = args.public_url.rstrip("/")
        public_version = json.loads(fetch_text(f"{base}/report-version.json"))
        public_index = fetch_text(f"{base}/")
        if str(public_version.get("version")) != version_value:
            errors.append(f"Public version {public_version.get('version')} != local {version_value}")
        validate_content(public_index, "public ", errors)

    summary = {
        "repo": str(repo), "version": version_value, "generatedAt": version.get("generatedAt"),
        "taifexDate": taifex_date, "officialTaifexDate": official_taifex_date,
        "marginDate": margin_date, "officialMarginDate": official_margin_date,
        "publicVersion": public_version.get("version") if public_version else None,
        "ok": not errors,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if errors:
        print("\n".join(f"ERROR: {item}" for item in errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
