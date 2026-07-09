from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
DOCS_SCOPE = "https://www.googleapis.com/auth/documents"

REPORT_SHEET = "Report"
DATA_SHEET = "Data"


@dataclass(frozen=True)
class MarketRow:
    label: str
    ticker: str
    price: float
    change: float
    pct: float

    @property
    def previous_close(self) -> float:
        return self.price - self.change


@dataclass(frozen=True)
class ParsedMarketData:
    timestamp: str
    rows: list[MarketRow]

MARKET_TICKER_MAP: dict[str, str] = {
    "台股": "^TWII",
    "韓股": "^KS11",
    "日股": "^N225",
    "NASDAQ 綜合指數": "^IXIC",
    "S&P 500": "^GSPC",
    "越南大盤": "^VNI",
    "櫃買指數": "^TWOII",
    "美元指數": "DX-Y.NYB",
    "費城半導體指數": "^SOX",
    "台積電": "2330.TW",
    "日月光投控": "3711.TW",
    "聯電": "2303.TW",
    "聯發科": "2454.TW",
    "0050": "0050.TW",
    "0052": "0052.TW",
    "00947": "00947.TW",
    "00631L": "00631L.TW",
    "00830": "00830.TW",
    "00876": "00876.TW",
    "00909": "00909.TW",
    "009805": "009805.TW",
    "00910": "00910.TW",
    "00991A": "00991A.TW",
    "00981A": "00981A.TW",
    "00735": "00735.TW",
    "00990A": "00990A.TW",
    "00988A": "00988A.TW",
    "0056": "0056.TW",
    "00919": "00919.TW",
    "00878": "00878.TW",
    "00922": "00922.TW",
    '00900富邦特選高股息30': '00900.TW',
    '00891中信關鍵半導體': '00891.TW',
    '00403A主動統一升級50': '00403A.TW',
    '009816凱基台灣TOP50': '009816.TW',
    '00646元大S&P500': '00646.TW',
    '00911兆豐洲際半導體': '00911.TW',
    '00895富邦未來車': '00895.TW',
    '00757統一FANG+': '00757.TW',
    '00713元大台灣高息低波': '00713.TW',
    '00915凱基優選高股息30': '00915.TW',
    '00918大華優利高填息30': '00918.TW',
    '2801彰銀': '2801.TW',
    '2892第一金': '2892.TW',
    '2886兆豐金': '2886.TW',
    '2834臺企銀': '2834.TW',
    '2812台中銀': '2812.TW',
    '2890永豐金': '2890.TW',
    '2880華南金': '2880.TW',
    '2883凱基金': '2883.TW',
    '2884玉山金': '2884.TW',
    '2885元大金': '2885.TW',
    '2881富邦金': '2881.TW',
    '2882國泰金': '2882.TW',
    '2855統一證': '2855.TW',
    '2376技嘉': '2376.TW',
    '5274信驊': '5274.TWO',
    '8299群聯': '8299.TWO',
    '6274台耀': '6274.TWO',
    '6223旺矽': '6223.TWO',
    '00917中信特選金融': '00917.TW',
    "Samsung Electronics": "005930.KS",
    "SK Hynix": "000660.KS",
    "比特幣": "BTC-USD",
    "黃金期貨": "GC=F",
    "石油期貨": "CL=F",
}

def clean_markdown_text(text: str) -> str:
    text = text.replace("**", "")

    def replace_link(match: re.Match[str]) -> str:
        label = match.group(1).strip()
        url = match.group(2).strip()
        return f"{label} ({url})"

    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", replace_link, text)
    return text.strip()


TABLE_CELL_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")


def is_markdown_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def is_markdown_table_separator_line(line: str) -> bool:
    stripped = line.strip().strip("|")
    if not stripped:
        return False
    cells = [cell.strip() for cell in stripped.split("|")]
    if len(cells) < 2:
        return False
    return all(TABLE_CELL_SEPARATOR_RE.fullmatch(cell) for cell in cells)


def split_markdown_table_cells(line: str) -> list[str]:
    return [clean_markdown_text(cell.strip()) for cell in line.strip().strip("|").split("|")]


def display_width(text: str) -> int:
    width = 0
    for ch in text:
        if ch == "	":
            width += 4
        elif unicodedata.combining(ch):
            continue
        elif unicodedata.east_asian_width(ch) in {"F", "W"}:
            width += 2
        else:
            width += 1
    return width


def pad_table_cell(text: str, width: int, alignment: str) -> str:
    current = display_width(text)
    if current >= width:
        return text

    padding = width - current
    if alignment == "right":
        return (" " * padding) + text
    if alignment == "center":
        left = padding // 2
        right = padding - left
        return (" " * left) + text + (" " * right)
    return text + (" " * padding)


def format_markdown_table_block(lines: list[str]) -> list[str]:
    rows: list[list[str]] = []
    alignments: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if is_markdown_table_separator_line(stripped):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            alignments = []
            for cell in cells:
                if cell.startswith(":") and cell.endswith(":"):
                    alignments.append("center")
                elif cell.startswith(":"):
                    alignments.append("left")
                elif cell.endswith(":"):
                    alignments.append("right")
                else:
                    alignments.append("left")
            continue
        if is_markdown_table_line(stripped):
            rows.append(split_markdown_table_cells(stripped))

    if len(rows) < 2:
        return []

    column_count = max(max(len(row) for row in rows), len(alignments))
    if column_count <= 0:
        return []

    while len(alignments) < column_count:
        alignments.append("left")

    widths = [3] * column_count
    for row in rows:
        for index in range(column_count):
            cell_text = row[index] if index < len(row) else ""
            widths[index] = max(widths[index], display_width(cell_text))

    formatted_rows: list[str] = []
    for row in rows:
        padded_cells: list[str] = []
        for index in range(column_count):
            cell_text = row[index] if index < len(row) else ""
            padded_cells.append(pad_table_cell(cell_text, widths[index], alignments[index]))
        formatted_rows.append("| " + " | ".join(padded_cells) + " |")

    separator_cells = ["-" * widths[index] for index in range(column_count)]
    if separator_cells:
        formatted_rows.insert(1, "| " + " | ".join(separator_cells) + " |")

    return formatted_rows


@dataclass(frozen=True)
class DocLine:
    text: str
    kind: str


def build_google_doc_lines(article_text: str) -> list[DocLine]:
    doc_lines: list[DocLine] = []
    in_code_block = False
    saw_title = False
    table_lines: list[str] = []

    def flush_table_lines() -> None:
        nonlocal table_lines
        if not table_lines:
            return

        formatted_table = format_markdown_table_block(table_lines)
        if formatted_table:
            for table_line in formatted_table:
                doc_lines.append(DocLine(text=table_line, kind="code"))
        else:
            for table_line in table_lines:
                doc_lines.append(DocLine(text=clean_markdown_text(table_line), kind="code"))
        table_lines = []

    for raw_line in article_text.splitlines():
        stripped = raw_line.strip()

        if stripped.startswith("```"):
            flush_table_lines()
            in_code_block = not in_code_block
            continue

        if in_code_block:
            doc_lines.append(DocLine(text=raw_line.rstrip(), kind="code"))
            continue

        if not stripped:
            flush_table_lines()
            doc_lines.append(DocLine(text="", kind="blank"))
            continue

        if is_markdown_table_line(stripped) or is_markdown_table_separator_line(stripped):
            table_lines.append(raw_line.rstrip())
            continue

        flush_table_lines()

        heading_match = re.match(r"^\*\*(.+)\*\*$", stripped)
        if heading_match:
            kind = "title" if not saw_title else "heading"
            saw_title = True
            doc_lines.append(DocLine(text=clean_markdown_text(heading_match.group(1)), kind=kind))
            continue

        bullet_match = re.match(r"^-\s+(.*)$", stripped)
        if bullet_match:
            doc_lines.append(DocLine(text=clean_markdown_text(bullet_match.group(1)), kind="bullet"))
            continue

        doc_lines.append(DocLine(text=clean_markdown_text(stripped), kind="paragraph"))

    flush_table_lines()
    return doc_lines

def parse_market_data(text: str) -> ParsedMarketData:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    timestamp = ""
    if len(lines) > 1 and ":" in lines[1]:
        timestamp = lines[1].split(":", 1)[1].strip()

    open_bracket = chr(12304)
    close_bracket = chr(12305)
    rows: list[MarketRow] = []
    current: dict[str, str | float | None] | None = None

    def parse_number(value: str) -> float:
        return float(value.replace(",", "").replace(" ", ""))

    def resolve_label_and_ticker(raw_header: str) -> tuple[str, str]:
        raw_header = raw_header.strip()
        mapped_ticker = MARKET_TICKER_MAP.get(raw_header)
        if mapped_ticker:
            return raw_header, mapped_ticker

        if raw_header.endswith(")") and "(" in raw_header:
            label, inner = raw_header.rsplit("(", 1)
            label = label.strip()
            inner = inner[:-1].strip()

            mapped_ticker = MARKET_TICKER_MAP.get(label)
            if mapped_ticker:
                return label, mapped_ticker

            mapped_ticker = MARKET_TICKER_MAP.get(inner)
            if mapped_ticker:
                return label, mapped_ticker

            ticker_like = inner and " " not in inner and all(ch.isalnum() or ch in ".^=:-" for ch in inner)
            if ticker_like:
                return label, inner

            return label, ""

        code_match = re.match(r'^([0-9]{4,6}[A-Z]?)([^\s().].*)$', raw_header)
        if code_match:
            code = code_match.group(1)
            return raw_header, f'{code}.TW'

        return raw_header, ""

    def flush_current() -> None:
        nonlocal current
        if not current:
            return
        if current.get("label") is None or current.get("ticker") is None:
            current = None
            return
        if current.get("price") is None or current.get("change") is None or current.get("pct") is None:
            current = None
            return
        rows.append(
            MarketRow(
                label=str(current["label"]),
                ticker=str(current["ticker"]),
                price=float(current["price"]),
                change=float(current["change"]),
                pct=float(current["pct"]),
            )
        )
        current = None

    previous_separator = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if set(line) == {"-"}:
            previous_separator = True
            continue

        header_text = None
        if line[0] == open_bracket and line[-1] == close_bracket:
            header_text = line[1:-1].strip()
        elif previous_separator and line.startswith("?") and line.endswith("?") and ":" not in line:
            # PowerShell 5 redirection can turn full-width brackets into question marks.
            header_text = line.strip("?").strip()
        previous_separator = False

        if header_text:
            flush_current()
            label, ticker = resolve_label_and_ticker(header_text)
            current = {"label": label, "ticker": ticker, "price": None, "change": None, "pct": None}
            continue

        if current is None:
            continue
        if current["price"] is None:
            current["price"] = parse_number(line.split(":", 1)[1].strip())
            continue

        if current["change"] is None:
            current["change"] = parse_number(line.split(":", 1)[1].strip())
            continue

        if current["pct"] is None:
            pct_value = line.split(":", 1)[1].strip()
            if pct_value.endswith("%"):
                pct_value = pct_value[:-1].strip()
            current["pct"] = parse_number(pct_value)
            continue

    flush_current()

    if not rows:
        raise ValueError("No market rows found in market data text")

    return ParsedMarketData(timestamp=timestamp, rows=rows)

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_credentials(credentials_path: Path):
    scopes = [SHEETS_SCOPE, DOCS_SCOPE]
    return service_account.Credentials.from_service_account_file(
        str(credentials_path),
        scopes=scopes,
    )


def build_services(credentials_path: Path):
    creds = load_credentials(credentials_path)
    sheets_service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    docs_service = build("docs", "v1", credentials=creds, cache_discovery=False)
    return sheets_service, docs_service


def get_sheet_map(sheets_service, spreadsheet_id: str) -> dict[str, dict[str, int | str]]:
    response = (
        sheets_service.spreadsheets()
        .get(
            spreadsheetId=spreadsheet_id,
            fields="sheets.properties(sheetId,title,index)",
        )
        .execute()
    )
    sheet_map: dict[str, dict[str, int | str]] = {}
    for sheet in response.get("sheets", []):
        props = sheet["properties"]
        sheet_map[str(props["title"])] = {
            "sheetId": int(props["sheetId"]),
            "title": str(props["title"]),
            "index": int(props.get("index", 0)),
        }
    return sheet_map


def ensure_sheet_tabs(sheets_service, spreadsheet_id: str, required_titles: Iterable[str]) -> dict[str, dict[str, int | str]]:
    sheet_map = get_sheet_map(sheets_service, spreadsheet_id)
    requests = []

    required_titles = list(required_titles)
    if REPORT_SHEET not in sheet_map:
        if len(sheet_map) == 1 and "Sheet1" in sheet_map:
            requests.append(
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_map["Sheet1"]["sheetId"],
                            "title": REPORT_SHEET,
                        },
                        "fields": "title",
                    }
                }
            )
        else:
            requests.append({"addSheet": {"properties": {"title": REPORT_SHEET}}})

    updated_sheet_map = dict(sheet_map)
    if REPORT_SHEET not in updated_sheet_map:
        updated_sheet_map[REPORT_SHEET] = {"sheetId": -1, "title": REPORT_SHEET, "index": 0}

    if DATA_SHEET not in sheet_map and DATA_SHEET not in required_titles:
        required_titles.append(DATA_SHEET)

    if DATA_SHEET not in sheet_map and len(requests) == 0:
        requests.append({"addSheet": {"properties": {"title": DATA_SHEET}}})
    elif DATA_SHEET not in sheet_map and REPORT_SHEET in sheet_map and len(sheet_map) == 1:
        requests.append({"addSheet": {"properties": {"title": DATA_SHEET}}})
    elif DATA_SHEET not in sheet_map and REPORT_SHEET not in sheet_map:
        # Report sheet will be created above; Data is created here as a second tab.
        requests.append({"addSheet": {"properties": {"title": DATA_SHEET}}})

    if requests:
        (
            sheets_service.spreadsheets()
            .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            .execute()
        )
        sheet_map = get_sheet_map(sheets_service, spreadsheet_id)

    return sheet_map


def build_report_rows(title: str, timestamp: str, parsed: ParsedMarketData, article_text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    rows.append([title])
    rows.append([f"Generated at: {timestamp}"])
    rows.append([""])
    rows.append(["Market Snapshot"])
    rows.append(["Market", "Ticker", "Price", "Change", "Change %", "Previous Close"])
    for row in parsed.rows:
        rows.append(
            [
                row.label,
                row.ticker,
                f"{row.price:.2f}",
                f"{row.change:+.2f}",
                f"{row.pct:+.2f}%",
                f"{row.previous_close:.2f}",
            ]
        )
    rows.append([""])
    rows.append(["Full Article"])
    rows.append([""])
    clean_text = clean_markdown_text(article_text)
    for line in clean_text.splitlines():
        rows.append([line])
    return rows


def build_data_rows(parsed: ParsedMarketData) -> list[list[str]]:
    rows: list[list[str]] = [["Market", "Ticker", "Price", "Change", "Change %", "Previous Close"]]
    for row in parsed.rows:
        rows.append(
            [
                row.label,
                row.ticker,
                f"{row.price:.2f}",
                f"{row.change:+.2f}",
                f"{row.pct:+.2f}%",
                f"{row.previous_close:.2f}",
            ]
        )
    return rows


def clear_sheet_ranges(sheets_service, spreadsheet_id: str, ranges: list[str]) -> None:
    (
        sheets_service.spreadsheets()
        .values()
        .batchClear(spreadsheetId=spreadsheet_id, body={"ranges": ranges})
        .execute()
    )


def write_sheet_values(sheets_service, spreadsheet_id: str, sheet_name: str, rows: list[list[str]]) -> None:
    (
        sheets_service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption="RAW",
            body={"values": rows},
        )
        .execute()
    )


def style_first_row(sheets_service, spreadsheet_id: str, sheet_id: int) -> None:
    requests = [
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True}
                    }
                },
                "fields": "userEnteredFormat.textFormat.bold",
            }
        },
    ]
    (
        sheets_service.spreadsheets()
        .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
        .execute()
    )


def update_google_doc(docs_service, document_id: str, title: str, timestamp: str, article_text: str) -> None:
    document = docs_service.documents().get(documentId=document_id).execute()
    content = document.get("body", {}).get("content", [])
    end_index = content[-1].get("endIndex", 1) if content else 1

    requests = []
    if end_index > 2:
        requests.append(
            {
                "deleteContentRange": {
                    "range": {
                        "startIndex": 1,
                        "endIndex": end_index - 1,
                    }
                }
            }
        )

    doc_lines = [
        DocLine(text=title, kind="title"),
        DocLine(text=f"Generated at: {timestamp}", kind="meta"),
        DocLine(text="", kind="blank"),
        *build_google_doc_lines(article_text),
    ]
    if len(doc_lines) <= 3:
        doc_lines = [
            DocLine(text=title, kind="title"),
            DocLine(text=f"Generated at: {timestamp}", kind="meta"),
            DocLine(text="", kind="blank"),
            DocLine(text=clean_markdown_text(article_text), kind="paragraph"),
        ]

    full_text = "\n".join(line.text for line in doc_lines)
    if full_text:
        full_text += "\n"
    requests.append(
        {
            "insertText": {
                "location": {"index": 1},
                "text": full_text,
            }
        }
    )

    cursor = 1
    bullet_ranges = []
    for doc_line in doc_lines:
        start_index = cursor
        end_index = start_index + len(doc_line.text)
        paragraph_end_index = end_index + 1
        text_range = {"startIndex": start_index, "endIndex": end_index}
        paragraph_range = {"startIndex": start_index, "endIndex": paragraph_end_index}

        if doc_line.kind == "title":
            requests.append(
                {
                    "updateParagraphStyle": {
                        "range": paragraph_range,
                        "paragraphStyle": {"namedStyleType": "TITLE"},
                        "fields": "namedStyleType",
                    }
                }
            )
            requests.append(
                {
                    "updateTextStyle": {
                        "range": text_range,
                        "textStyle": {"bold": True, "fontSize": {"magnitude": 22, "unit": "PT"}},
                        "fields": "bold,fontSize",
                    }
                }
            )
        elif doc_line.kind == "heading":
            requests.append(
                {
                    "updateParagraphStyle": {
                        "range": paragraph_range,
                        "paragraphStyle": {"namedStyleType": "HEADING_2"},
                        "fields": "namedStyleType",
                    }
                }
            )
            requests.append(
                {
                    "updateTextStyle": {
                        "range": text_range,
                        "textStyle": {"bold": True, "fontSize": {"magnitude": 14, "unit": "PT"}},
                        "fields": "bold,fontSize",
                    }
                }
            )
        elif doc_line.kind == "meta":
            requests.append(
                {
                    "updateTextStyle": {
                        "range": text_range,
                        "textStyle": {"italic": True, "fontSize": {"magnitude": 10, "unit": "PT"}},
                        "fields": "italic,fontSize",
                    }
                }
            )
        elif doc_line.kind == "bullet":
            bullet_ranges.append(paragraph_range)
        elif doc_line.kind == "code":
            requests.append(
                {
                    "updateTextStyle": {
                        "range": text_range,
                        "textStyle": {
                            "weightedFontFamily": {"fontFamily": "Courier New"},
                            "fontSize": {"magnitude": 10, "unit": "PT"},
                        },
                        "fields": "weightedFontFamily,fontSize",
                    }
                }
            )

        cursor = paragraph_end_index

    for bullet_range in bullet_ranges:
        requests.append(
            {
                "createParagraphBullets": {
                    "range": bullet_range,
                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                }
            }
        )

    docs_service.documents().batchUpdate(documentId=document_id, body={"requests": requests}).execute()


def write_state_file(path: Path, payload: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Push the market report into Google Sheets and Google Docs.")
    parser.add_argument("--market-data", required=True, type=Path)
    parser.add_argument("--final-article", required=True, type=Path)
    parser.add_argument("--title", default="TaiwanStockBot 盤中市場報告")
    parser.add_argument("--credentials", type=Path, default=None)
    parser.add_argument("--sheet-id", default=None)
    parser.add_argument("--doc-id", default=None)
    parser.add_argument("--state-file", type=Path, default=Path("google_workspace_state.json"))
    args = parser.parse_args()

    credentials_value = args.credentials or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    sheet_id = args.sheet_id or os.environ.get("GOOGLE_SHEETS_ID") or os.environ.get("GOOGLE_SHEET_ID")
    doc_id = args.doc_id or os.environ.get("GOOGLE_DOC_ID")

    if isinstance(credentials_value, Path):
        credentials_path = credentials_value
    elif credentials_value:
        credentials_path = Path(credentials_value)
    else:
        credentials_path = None

    if credentials_path is None or not credentials_path.exists():
        print("[GoogleSync] Skipped: missing service account credentials path.")
        return 0

    if not sheet_id and not doc_id:
        print("[GoogleSync] Skipped: no Google Sheets or Docs target ID provided.")
        return 0

    parsed_market = parse_market_data(read_text(args.market_data))
    article_text = read_text(args.final_article)
    timestamp = parsed_market.timestamp or "(timestamp unavailable)"

    try:
        sheets_service, docs_service = build_services(credentials_path)
    except Exception as exc:  # pragma: no cover - setup issue
        print(f"[GoogleSync] Failed to create Google API clients: {exc}")
        return 1

    output: dict[str, str] = {}

    try:
        if sheet_id:
            sheet_map = ensure_sheet_tabs(sheets_service, sheet_id, [REPORT_SHEET, DATA_SHEET])
            report_rows = build_report_rows(args.title, timestamp, parsed_market, article_text)
            data_rows = build_data_rows(parsed_market)

            clear_sheet_ranges(
                sheets_service,
                sheet_id,
                [f"{REPORT_SHEET}!A1:F500", f"{DATA_SHEET}!A1:F100"],
            )
            write_sheet_values(sheets_service, sheet_id, REPORT_SHEET, report_rows)
            write_sheet_values(sheets_service, sheet_id, DATA_SHEET, data_rows)
            style_first_row(sheets_service, sheet_id, int(sheet_map[REPORT_SHEET]["sheetId"]))
            style_first_row(sheets_service, sheet_id, int(sheet_map[DATA_SHEET]["sheetId"]))

            sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
            output["sheet_url"] = sheet_url
            print(f"[GoogleSync] Updated sheet: {sheet_url}")

        if doc_id:
            update_google_doc(docs_service, doc_id, args.title, timestamp, article_text)
            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            output["doc_url"] = doc_url
            print(f"[GoogleSync] Updated doc: {doc_url}")

        if output:
            write_state_file(args.state_file, output)
        else:
            print("[GoogleSync] Nothing to update.")
        return 0
    except HttpError as exc:
        print(f"[GoogleSync] Google API error: {exc}")
        return 1
    except Exception as exc:
        print(f"[GoogleSync] Unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())





