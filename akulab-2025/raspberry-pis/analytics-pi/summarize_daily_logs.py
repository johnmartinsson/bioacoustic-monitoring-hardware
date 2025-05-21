#!/usr/bin/env python3
"""
summarize_daily_logs.py

Generates an HTML daily summary for each Raspberry Pi in the system.
It scans pooled logs under
  /home/analyticspi/logs/pooled/<pi_name>/
    backup_recordings/<DATE>_backup_recordings.log
    rpi_health_snapshot/<DATE>_rpi_health.csv
    mount_watchdog/<DATE>_mount_watchdog.log   (analytics‑pi only)

🆕 2025‑04‑17
----------------
* **Chrony section split into two parts**
  1. **Time‑sync metrics table** – min / max / average of every *numeric*
     chrony column (e.g. `chrony_last_offset_s`, `chrony_rms_offset_s`,
     `chrony_freq_skew_ppm`).
  2. **Clock‑source usage line** –   `clockpi : 96, time.cloudflare.com : 4`.
     It counts unique values in column `chrony_src` (or the legacy
     `chrony_selected_refid` if present).

The rest of the script is unchanged from the original version you sent.
"""

import sys
import os
import re
import csv
import statistics
import collections
from datetime import datetime
from pathlib import Path
from typing import List, Dict

PI_NAMES = ["clockpi", "analyticspi", "recordingpi"]

# ----------------------------------------------------------------------------
# Entry‑point
# ----------------------------------------------------------------------------

def main() -> None:
    log_date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")

    LOG_BASE = "/home/analyticspi/logs/pooled"
    DAILY_SUM_DIR = "/home/analyticspi/logs/daily_summaries"
    os.makedirs(DAILY_SUM_DIR, exist_ok=True)

    html_parts: List[str] = [
        "<html><head><meta charset='utf-8'><title>Daily Summary – "
        f"{log_date}</title></head><body>",
        f"<h1>Daily Summary for {log_date}</h1>"
    ]

    for pi in PI_NAMES:
        html_parts.append(f"<h2>{pi.title().replace('pi', ' Pi')}</h2>")
        pi_folder = os.path.join(LOG_BASE, pi)
        if not os.path.isdir(pi_folder):
            html_parts.append(f"<p>No logs found for <b>{pi}</b> in {pi_folder}</p>")
            continue

        # -------- health snapshot --------
        health_csv = os.path.join(pi_folder, "rpi_health_snapshot", f"{log_date}_rpi_health.csv")
        html_parts.append(parse_health_csv(health_csv, pi, log_date))

        # -------- backup recordings -------
        backup_log = os.path.join(pi_folder, "backup_recordings", f"{log_date}_backup_recordings.log")
        html_parts.extend(parse_backup_log(backup_log, pi, log_date))
        #synced_file_log = os.path.join(pi_folder, "backup_recordings/synced_files/synced_files.log")
        #html_parts.extend(parse_synced_files_log(synced_file_log, log_date))

        # -------- mount watchdog ----------
        watchdog_log = os.path.join(pi_folder, "mount_watchdog", f"{log_date}_mount_watchdog.log")
        html_parts.append(parse_mount_watchdog(watchdog_log, log_date))

    html_parts.append("</body></html>")

    out_file = os.path.join(DAILY_SUM_DIR, f"{log_date}_summary.html")
    with open(out_file, "w", encoding="utf-8") as fh:
        fh.write("\n".join(html_parts))
    print(f"Summary generated: {out_file}")

# ----------------------------------------------------------------------------
# Health‑snapshot → HTML
# ----------------------------------------------------------------------------

def parse_health_csv(csv_path: str, pi_name: str, log_date: str) -> str:
    """Return HTML snippet summarising a single Pi's health CSV."""
    if not os.path.isfile(csv_path):
        return f"<p>No rpi_health_snapshot found for <b>{pi_name}</b> on {log_date}.</p>"

    with open(csv_path, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        if not rows:
            return f"<p>Empty rpi_health_snapshot CSV for <b>{pi_name}</b> on {log_date}.</p>"
        cols: List[str] = reader.fieldnames or []

    # Gather column → list‑of‑values
    col_vals: Dict[str, List[str]] = {c: [r[c] for r in rows] for c in cols}

    html: List[str] = [
        f"<h4>Health Snapshot for {pi_name}</h4>",
        "<table border='1' cellpadding='4' cellspacing='0'>",
        "<tr><th>Column</th><th>Min</th><th>Max</th><th>Average / Stats</th></tr>"
    ]

    for col in cols:
        vals = col_vals[col]
        num_vals: List[float] = []
        bool_vals: List[bool] = []
        for v in vals:
            if isinstance(v, str) and v.lower() in {"true", "false"}:
                bool_vals.append(v.lower() == "true")
            else:
                try:
                    num_vals.append(float(v))
                except (ValueError, TypeError):
                    pass

        min_s = max_s = avg_s = "N/A"
        if col.lower().startswith("timestamp"):
            min_s = f"first: {vals[0]}"
            max_s = f"last: {vals[-1]}"
        elif bool_vals and len(bool_vals) == len(vals):
            t_cnt = sum(bool_vals)
            min_s, max_s = f"True: {t_cnt}", f"False: {len(vals) - t_cnt}"
        elif num_vals and len(num_vals) == len(vals):
            min_s = f"{min(num_vals):.2f}"
            max_s = f"{max(num_vals):.2f}"
            avg_s = f"{statistics.mean(num_vals):.2f}"
        else:
            min_s, max_s = vals[0], vals[-1]
            avg_s = f"{len(vals)} rows"

        html.append(f"<tr><td>{col}</td><td>{min_s}</td><td>{max_s}</td><td>{avg_s}</td></tr>")

    html.append("</table>")

    # ---------------- Chrony extras ----------------
    chrony_cols = [c for c in cols if c.startswith("chrony_")]
    if chrony_cols:
        html.extend(build_chrony_section(chrony_cols, col_vals))

    return "\n".join(html)

# ----------------------------------------------------------------------------
# Chrony helpers
# ----------------------------------------------------------------------------

def build_chrony_section(chrony_cols: List[str], col_vals: Dict[str, List[str]]) -> List[str]:
    """Return HTML lines for Chrony metrics + source counts."""
    out: List[str] = ["<h5>Chrony Time‑Sync</h5>"]

    # ---- numeric table ----
    numeric_cols = [c for c in chrony_cols if c not in {"chrony_src", "chrony_selected_refid"}]
    numeric_cols = [c for c in numeric_cols if all(_is_float(v) for v in col_vals[c])]
    if numeric_cols:
        out.append("<table border='1' cellpadding='3' cellspacing='0'>")
        out.append("<tr><th>Metric</th><th>Min</th><th>Max</th><th>Average</th></tr>")
        for col in numeric_cols:
            nums = [float(v) for v in col_vals[col]]
            out.append(
                f"<tr><td>{col}</td><td>{min(nums):.6g}</td><td>{max(nums):.6g}</td><td>{statistics.mean(nums):.6g}</td></tr>"
            )
        out.append("</table>")

    # ---- clock‑source counts ----
    ref_col = "chrony_src" if "chrony_src" in col_vals else "chrony_selected_refid" if "chrony_selected_refid" in col_vals else None
    if ref_col:
        counts = collections.Counter(col_vals[ref_col])
        pretty = ", ".join(f"{src} : {cnt}" for src, cnt in counts.most_common())
        out.append(f"<p><b>Clock Source Usage</b>: {pretty}</p>")

    return out


def _is_float(x: str) -> bool:
    try:
        float(x)
        return True
    except (ValueError, TypeError):
        return False

# ----------------------------------------------------------------------------
# Backup recordings, watchdog – unchanged
# ----------------------------------------------------------------------------

def parse_synced_files_log(log_path: str, log_date: str) -> List[str]:
    """
    Parse ~/logs/backup_recordings/synced_files/synced_files.log and build an
    HTML snippet containing every .wav file whose embedded date matches
    `log_date` (YYYY-MM-DD).

    Example filename matched:
        auklab_20250428T111831.wav
    """
    if not os.path.isfile(log_path):
        return [f"<p>No synced_files.log found at {log_path}.</p>"]

    # Convert 2025-04-28 → 20250428 for pattern-matching
    date_compact = log_date.replace("-", "")

    # Example file: auklab_20250428T111831.wav
    wav_re = re.compile(
        rf"auklab_{date_compact}T"   # date part plus literal “T”
        r"\d{6}\.wav$"               # HHMMSS.wav
    )

    synced: List[str] = []
    with open(log_path, "r", encoding="utf-8") as fh:
        for raw in fh:
            fname = os.path.basename(raw.strip())
            if wav_re.match(fname):
                synced.append(fname)

    if synced:
        html = [f"<h4>Successfully Synced Files ({len(synced)} total)</h4><ol>"]
        html.extend(f"<li>{f}</li>" for f in synced)
        html.append("</ol>")
    else:
        html = [f"<p>No .wav files synced on {log_date}.</p>"]

    return html

def parse_backup_log(log_path: str, pi_name: str, log_date: str):
    if not os.path.isfile(log_path):
        return [f"<p>No backup_recordings log found for <b>{pi_name}</b> on {log_date}.</p>"]

    errors, synced, verified = [], [], []
    capturing = False
    # matches e.g.                     auklab_20250520T171000.wav
    #           and (legacy)           auklab_zoom_f8_pro_20240210_120015_0001.wav
    wav_re = re.compile(
        r"("
        r"auklab_"                         # mandatory prefix
        r"(?:zoom_f8_pro_)?"               # optional legacy recorder tag
        r"\d{8}"                           # YYYYMMDD
        r"(?:T|_)"                         # either “T” or “_” as date/time separator
        r"\d{6}"                           # HHMMSS
        r"(?:_\d{4})?"                     # optional Zoom file-counter
        r"\.wav"
        r")"
    )

    with open(log_path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if "[WARNING]" in line or "[ERROR]" in line:
                errors.append(line)
            if "rsync stdout:" in line:
                capturing = True
                continue
            if capturing:
                if not line or "[INFO]" in line:
                    capturing = False
                else:
                    m = wav_re.search(line)
                    if m:
                        synced.append(m.group(1))
            if pi_name == "analyticspi" and "verified successfully (sha256)" in line.lower():
                m = re.search(r"file\s+(.+?)\s+verified successfully \(sha256\)", line, re.IGNORECASE)
                if m:
                    verified.append(m.group(1))

    html: List[str] = []
    if errors:
        html.append("<h4>Backup Errors/Warnings</h4><ul>")
        html.extend(f"<li>{e}</li>" for e in errors)
        html.append("</ul>")
    else:
        html.append("<p>No backup errors or warnings found.</p>")

    if synced:
        html.append(f"<h4>Successfully Synced Files ({len(synced)} total)</h4><ol>")
        html.extend(f"<li>{f}</li>" for f in synced)
        html.append("</ol>")
    else:
        html.append("<p>No .wav files synced today.</p>")

    if pi_name == "analyticspi" and verified:
        html.append(f"<h4>Verified Files (sha256) ({len(verified)} total)</h4><ul>")
        html.extend(f"<li>{v}</li>" for v in verified)
        html.append("</ul>")

    return html


def parse_mount_watchdog(log_path: str, log_date: str) -> str:
    if not os.path.isfile(log_path):
        return f"<p>No mount_watchdog log found for analytics-pi on {log_date}.</p>"

    ok = fail = 0
    fails: List[str] = []
    with open(log_path, "r", encoding="utf-8") as fh:
        for line in fh:
            if "❌" in line:
                fail += 1
                fails.append(line.strip())
            elif "✅" in line:
                ok += 1

    html: List[str] = ["<h4>Mount Watchdog</h4>", f"<p>Mount OK count: {ok}<br>Mount Fail count: {fail}</p>"]
    if fails:
        html.append("<ul>")
        html.extend(f"<li>{d}</li>" for d in fails)
        html.append("</ul>")
    return "\n".join(html)


if __name__ == "__main__":
    main()

