#!/usr/bin/env python3
"""Download daily summary pages for a date range and parse key fields to JSON."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup


@dataclass
class FetchResult:
    day: date
    url: str
    status: str
    error: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    parser.add_argument(
        "--base-url",
        default="https://johnmartinsson.github.io/akulab2025/daily_summaries",
        help="Base URL that serves <YYYY-MM-DD>_summary.html",
    )
    parser.add_argument("--out-dir", default="./season_review_output", help="Output directory")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")
    return parser.parse_args()


def date_range(start: date, end: date) -> list[date]:
    days: list[date] = []
    cur = start
    while cur <= end:
        days.append(cur)
        cur += timedelta(days=1)
    return days


def normalize_pi_name(text: str) -> str:
    t = text.strip().lower()
    if "clock" in t:
        return "clockpi"
    if "analytics" in t:
        return "analyticspi"
    if "recording" in t:
        return "recordingpi"
    return re.sub(r"\s+", "_", t)


def table_to_dict(table) -> dict[str, Any]:
    rows = table.find_all("tr")
    if not rows:
        return {"headers": [], "rows": []}

    headers = [th.get_text(" ", strip=True) for th in rows[0].find_all(["th", "td"])]
    out_rows = []
    for tr in rows[1:]:
        cells = [td.get_text(" ", strip=True) for td in tr.find_all(["th", "td"])]
        if cells:
            out_rows.append(cells)
    return {"headers": headers, "rows": out_rows}


def parse_health_table(rows: list[list[str]]) -> dict[str, dict[str, str]]:
    health: dict[str, dict[str, str]] = {}
    for row in rows:
        if len(row) < 4:
            continue
        col = row[0]
        health[col] = {"min": row[1], "max": row[2], "stats": row[3]}
    return health


def parse_chrony_table(rows: list[list[str]]) -> dict[str, dict[str, str]]:
    chrony: dict[str, dict[str, str]] = {}
    for row in rows:
        if len(row) < 4:
            continue
        metric = row[0]
        chrony[metric] = {"min": row[1], "max": row[2], "avg": row[3]}
    return chrony


def parse_pi_section(h2_tag) -> dict[str, Any]:
    section: dict[str, Any] = {
        "health": {},
        "chrony": {},
        "clock_source_usage": None,
        "synced_files": [],
        "mount_watchdog": {},
        "paragraphs": [],
        "tables": [],
    }

    node = h2_tag.next_sibling
    while node is not None:
        if getattr(node, "name", None) == "h2":
            break
        name = getattr(node, "name", None)

        if name == "table":
            t = table_to_dict(node)
            section["tables"].append(t)
            headers = [h.lower() for h in t["headers"]]
            if headers == ["column", "min", "max", "average / stats"]:
                section["health"] = parse_health_table(t["rows"])
            elif headers == ["metric", "min", "max", "average"]:
                section["chrony"] = parse_chrony_table(t["rows"])

        elif name == "p":
            text = node.get_text(" ", strip=True)
            if text:
                section["paragraphs"].append(text)
                m = re.search(r"Clock Source Usage\s*:\s*(.*)$", text)
                if m:
                    section["clock_source_usage"] = m.group(1)

                if text.startswith("Mount OK count:"):
                    ok_m = re.search(r"Mount OK count:\s*(\d+)", text)
                    fail_m = re.search(r"Mount Fail count:\s*(\d+)", text)
                    section["mount_watchdog"] = {
                        "ok_count": int(ok_m.group(1)) if ok_m else None,
                        "fail_count": int(fail_m.group(1)) if fail_m else None,
                    }

        elif name == "h4":
            h4_text = node.get_text(" ", strip=True)
            if h4_text.startswith("Successfully Synced Files"):
                next_node = node.find_next_sibling()
                if next_node is not None and next_node.name == "ol":
                    section["synced_files"] = [li.get_text(" ", strip=True) for li in next_node.find_all("li")]

        node = node.next_sibling

    return section


def parse_html(day: date, url: str, html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    doc: dict[str, Any] = {
        "date": day.isoformat(),
        "url": url,
        "title": soup.title.get_text(strip=True) if soup.title else "",
        "sections": {},
    }

    for h2 in soup.find_all("h2"):
        pi_name = normalize_pi_name(h2.get_text(" ", strip=True))
        doc["sections"][pi_name] = parse_pi_section(h2)

    return doc


def fetch_text(url: str, timeout: int) -> str:
    req = Request(url, headers={"User-Agent": "season-summary-crawler/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def main() -> int:
    args = parse_args()
    start = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end = datetime.strptime(args.end_date, "%Y-%m-%d").date()
    if end < start:
        raise SystemExit("end-date must be >= start-date")

    out_dir = Path(args.out_dir).resolve()
    raw_dir = out_dir / "raw_html"
    parsed_dir = out_dir / "parsed_json"
    raw_dir.mkdir(parents=True, exist_ok=True)
    parsed_dir.mkdir(parents=True, exist_ok=True)

    results: list[FetchResult] = []

    for day in date_range(start, end):
        fname = f"{day.isoformat()}_summary.html"
        url = f"{args.base_url.rstrip('/')}/{fname}"
        print(f"[INFO] Fetching {url}")
        try:
            html = fetch_text(url, args.timeout)
            (raw_dir / fname).write_text(html, encoding="utf-8")
            parsed = parse_html(day, url, html)
            (parsed_dir / f"{day.isoformat()}_summary.json").write_text(
                json.dumps(parsed, indent=2) + "\n", encoding="utf-8"
            )
            results.append(FetchResult(day=day, url=url, status="ok"))
        except HTTPError as exc:
            results.append(FetchResult(day=day, url=url, status="http_error", error=f"{exc.code} {exc.reason}"))
            print(f"[WARN] HTTP error for {day}: {exc.code} {exc.reason}")
        except URLError as exc:
            results.append(FetchResult(day=day, url=url, status="url_error", error=str(exc.reason)))
            print(f"[WARN] URL error for {day}: {exc.reason}")
        except Exception as exc:
            results.append(FetchResult(day=day, url=url, status="error", error=str(exc)))
            print(f"[WARN] Unexpected error for {day}: {exc}")

    summary = {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "base_url": args.base_url,
        "fetched_ok": sum(1 for r in results if r.status == "ok"),
        "failed": sum(1 for r in results if r.status != "ok"),
        "results": [r.__dict__ | {"day": r.day.isoformat()} for r in results],
    }
    (out_dir / "crawl_report.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"[INFO] Done. ok={summary['fetched_ok']} failed={summary['failed']}")
    print(f"[INFO] Raw HTML: {raw_dir}")
    print(f"[INFO] Parsed JSON: {parsed_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
