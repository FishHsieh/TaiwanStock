from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


CLEVELAND_URL = "https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting"
TREASURY_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
    "?data=daily_treasury_yield_curve&field_tdr_date_value={year}"
)
EFFR_URL = "https://markets.newyorkfed.org/api/rates/unsecured/effr/last/1.json"
MACROMICRO_CPI_URL = "https://www.macromicro.me/charts/27688/us-cleveland-inflation-cpi"
MACROMICRO_RATE_URL = "https://www.macromicro.me/collections/9/us-market-relative/48/target-rate"
USER_AGENT = "TaiwanStockBot/1.0 (+https://github.com/FishHsieh/TaiwanStock)"


def _number(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    return float(value.strip())


def _table_rows(page: str, heading: str) -> list[list[str]]:
    start = page.lower().find(heading.lower())
    if start < 0:
        raise ValueError(f"Cleveland Fed table not found: {heading}")
    match = re.search(r"<tbody[^>]*>(.*?)</tbody>", page[start:], re.I | re.S)
    if not match:
        raise ValueError(f"Cleveland Fed table body not found: {heading}")
    rows: list[list[str]] = []
    for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", match.group(1), re.I | re.S):
        cells = []
        for cell_html in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.I | re.S):
            text = re.sub(r"<[^>]+>", " ", cell_html)
            cells.append(" ".join(html_lib.unescape(text).split()))
        if cells:
            rows.append(cells)
    return rows


def fetch_inflation_nowcast(session: requests.Session) -> dict[str, Any]:
    response = session.get(CLEVELAND_URL, timeout=30)
    response.raise_for_status()
    mom_rows = _table_rows(response.text, "Inflation, month-over-month percent change")
    yoy_rows = _table_rows(response.text, "Inflation, year-over-year percent change")
    mom = next((row for row in mom_rows if len(row) >= 6 and row[1] and row[2]), None)
    yoy = next((row for row in yoy_rows if len(row) >= 6 and row[1] and row[2]), None)
    if not mom or not yoy:
        raise ValueError("No current CPI nowcast row found")
    return {
        "period": mom[0],
        "updated": mom[5],
        "headline_cpi_mom_pct": _number(mom[1]),
        "core_cpi_mom_pct": _number(mom[2]),
        "headline_cpi_yoy_pct": _number(yoy[1]),
        "core_cpi_yoy_pct": _number(yoy[2]),
        "kind": "Cleveland Fed daily nowcast; not an official BLS CPI release",
        "source": "Federal Reserve Bank of Cleveland",
        "source_url": CLEVELAND_URL,
        "reference_url": MACROMICRO_CPI_URL,
    }


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _property_map(element: ET.Element) -> dict[str, str]:
    return {_local_name(child.tag): (child.text or "").strip() for child in element}


def fetch_treasury_yields(session: requests.Session) -> dict[str, Any]:
    year = datetime.now(timezone.utc).year
    response = session.get(TREASURY_URL.format(year=year), timeout=30)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    records: list[dict[str, str]] = []
    for element in root.iter():
        if _local_name(element.tag) == "properties":
            record = _property_map(element)
            if record.get("NEW_DATE"):
                records.append(record)
    if len(records) < 2:
        raise ValueError("Treasury yield feed returned fewer than two observations")
    records.sort(key=lambda item: item["NEW_DATE"])
    latest, previous = records[-1], records[-2]
    fields = {"2y": "BC_2YEAR", "10y": "BC_10YEAR", "30y": "BC_30YEAR"}
    rates = {label: _number(latest.get(field)) for label, field in fields.items()}
    previous_rates = {label: _number(previous.get(field)) for label, field in fields.items()}
    changes_bps = {
        label: round((rates[label] - previous_rates[label]) * 100, 1)
        if rates[label] is not None and previous_rates[label] is not None
        else None
        for label in fields
    }
    curve_10y_2y = (
        round((rates["10y"] - rates["2y"]) * 100, 1)
        if rates["10y"] is not None and rates["2y"] is not None
        else None
    )
    curve_change_bps = (
        round(changes_bps["10y"] - changes_bps["2y"], 1)
        if changes_bps["10y"] is not None and changes_bps["2y"] is not None
        else None
    )
    return {
        "date": latest["NEW_DATE"][:10],
        "previous_date": previous["NEW_DATE"][:10],
        "rates_pct": rates,
        "day_change_bps": changes_bps,
        "curve_10y_minus_2y_bps": curve_10y_2y,
        "curve_day_change_bps": curve_change_bps,
        "source": "U.S. Department of the Treasury daily par yield curve",
        "source_url": TREASURY_URL.format(year=year),
    }


def fetch_policy_rate(session: requests.Session) -> dict[str, Any]:
    response = session.get(EFFR_URL, timeout=30)
    response.raise_for_status()
    records = response.json().get("refRates") or []
    if not records:
        raise ValueError("New York Fed EFFR API returned no observations")
    item = records[0]
    return {
        "date": item.get("effectiveDate"),
        "effr_pct": item.get("percentRate"),
        "target_range_low_pct": item.get("targetRateFrom"),
        "target_range_high_pct": item.get("targetRateTo"),
        "source": "Federal Reserve Bank of New York EFFR",
        "source_url": EFFR_URL,
        "reference_url": MACROMICRO_RATE_URL,
    }


def _read_cache(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def build_context(cache_path: Path) -> dict[str, Any]:
    cached = _read_cache(cache_path)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json,text/html,application/xml"})
    sections = {
        "inflation_nowcast": fetch_inflation_nowcast,
        "policy_rate": fetch_policy_rate,
        "treasury_yields": fetch_treasury_yields,
    }
    payload: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "live",
        "errors": [],
    }
    for key, fetcher in sections.items():
        try:
            payload[key] = fetcher(session)
            payload[key]["data_state"] = "live"
        except Exception as exc:  # The report must degrade to cache instead of aborting.
            cached_section = cached.get(key)
            payload["errors"].append(f"{key}: {exc}")
            if isinstance(cached_section, dict) and cached_section:
                payload[key] = dict(cached_section)
                payload[key]["data_state"] = "cached"
            else:
                payload[key] = {"data_state": "unavailable"}
    if payload["errors"]:
        states = [payload[key].get("data_state") for key in sections]
        if all(state == "unavailable" for state in states):
            payload["status"] = "unavailable"
        elif all(state == "cached" for state in states):
            payload["status"] = "cached"
        else:
            payload["status"] = "partial"
    payload["interpretation_rules"] = [
        "CPI values are Cleveland Fed nowcasts, not official BLS releases; label them clearly.",
        "Translate CPI into plain Chinese: MoM determines whether prices are expected to rise/fall/stay flat next month; YoY describes the price level versus one year ago.",
        "Distinguish disinflation from deflation. Lower YoY inflation is not falling prices when MoM remains positive; near-zero headline MoM with positive core MoM means surface cooling but persistent underlying inflation.",
        "Sticky or rising core CPI and higher 2Y/10Y yields are headwinds for long-duration growth and technology valuations.",
        "Higher Treasury yields mean lower bond prices and are generally unfavorable for TLT; falling yields imply the reverse.",
        "Use the 2Y yield for policy expectations, the 10Y yield for discount-rate pressure, and the 10Y-2Y spread for curve shape.",
        "After discussing inflation and the yield curve, state plainly whether the combined signal is favorable, unfavorable, or mixed for Taiwan technology stocks, financials, and TLT.",
        "A positive 10Y-2Y spread is structurally healthier than inversion but is not automatically bullish; also explain whether the spread widened or narrowed that day and why.",
    ]
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch U.S. CPI nowcast, policy-rate, and Treasury-yield context.")
    parser.add_argument("--output", default="us_macro_context.json")
    parser.add_argument("--cache", default="data/us_macro_context_cache.json")
    args = parser.parse_args()
    output_path = Path(args.output)
    cache_path = Path(args.cache)
    payload = build_context(cache_path)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    if payload["status"] != "unavailable":
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(rendered, encoding="utf-8")
    print(f"[USMacro] Wrote {output_path} ({payload['status']})")
    for error in payload["errors"]:
        print(f"[USMacro][WARN] {error}", file=sys.stderr)
    return 0 if payload["status"] != "unavailable" else 1


if __name__ == "__main__":
    raise SystemExit(main())
