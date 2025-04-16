#!/usr/bin/env python3
"""
summarize_daily_logs.py

Generates one HTML summary for the given date (default = today), scanning:
  /home/analyticspi/logs/pooled/<pi_name>/
    backup_recordings/<DATE>_backup_recordings.log
    rpi_health_snapshot/<DATE>_rpi_health.csv
    mount_watchdog/<DATE>_mount_watchdog.log (analytics-pi only)

We add a new step: if pi == 'analyticspi', we parse lines like:
  "[INFO] File <filename> verified successfully (sha256)."
and present them in a separate bullet list titled "Verified Files (sha256)".
"""

import sys
import os
import re
import csv
import statistics
from datetime import datetime
from pathlib import Path

PI_NAMES = ["clockpi", "analyticspi", "recordingpi"]

def main():
    if len(sys.argv) > 1:
        log_date = sys.argv[1]
    else:
        log_date = datetime.now().strftime("%Y-%m-%d")

    LOG_BASE = "/home/analyticspi/logs/pooled"
    DAILY_SUM_DIR = os.path.join("/home/analyticspi/logs", "daily_summaries")
    os.makedirs(DAILY_SUM_DIR, exist_ok=True)

    html_lines = []
    html_lines.append("<html><head><meta charset='utf-8'><title>Daily Summary</title></head><body>")
    html_lines.append(f"<h1>Daily Summary for {log_date}</h1>")

    for pi in PI_NAMES:
        html_lines.append(f"<h2>{pi.title().replace('pi',' Pi')}</h2>")
        pi_folder = os.path.join(LOG_BASE, pi)

        if not os.path.isdir(pi_folder):
            html_lines.append(f"<p>No logs found for <b>{pi}</b> in {pi_folder}</p>")
            continue

        # rpi_health_snapshot
        health_csv = os.path.join(pi_folder, "rpi_health_snapshot", f"{log_date}_rpi_health.csv")
        health_section = parse_health_csv(health_csv, pi, log_date)
        html_lines.append(health_section)

        # backup_recordings
        backup_log = os.path.join(pi_folder, "backup_recordings", f"{log_date}_backup_recordings.log")
        backup_section = parse_backup_log(backup_log, pi, log_date)
        html_lines.extend(backup_section)

        # mount_watchdog only for analytics pi
        if pi == "analyticspi":
            watchdog_log = os.path.join(pi_folder, "mount_watchdog", f"{log_date}_mount_watchdog.log")
            wd_section = parse_mount_watchdog(watchdog_log, log_date)
            html_lines.append(wd_section)

    html_lines.append("</body></html>")

    out_file = os.path.join(DAILY_SUM_DIR, f"{log_date}_summary.html")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(html_lines))

    print(f"Summary generated: {out_file}")


def parse_health_csv(csv_path, pi_name, log_date):
    if not os.path.isfile(csv_path):
        return f"<p>No rpi_health_snapshot found for <b>{pi_name}</b> on {log_date}.</p>"

    rows = []
    with open(csv_path, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rows.append(row)

    if not rows:
        return f"<p>Empty rpi_health_snapshot CSV for <b>{pi_name}</b> on {log_date}.</p>"

    columns = reader.fieldnames
    col_data = {col: [] for col in columns}

    for row in rows:
        for col in columns:
            col_data[col].append(row[col])

    lines = []
    lines.append(f"<h4>Health Snapshot for {pi_name} (all columns)</h4>")
    lines.append("<table border='1' cellpadding='4' cellspacing='0'>")
    lines.append("<tr><th>Column</th><th>Min</th><th>Max</th><th>Average / Stats</th></tr>")

    for col in columns:
        col_list = col_data[col]
        numeric_values = []
        bool_values = []
        for val in col_list:
            if val.lower() in ["true", "false"]:
                bool_values.append(val.lower() == "true")
            else:
                try:
                    fval = float(val)
                    numeric_values.append(fval)
                except ValueError:
                    pass

        min_str = "N/A"
        max_str = "N/A"
        avg_str = "N/A"

        if col.lower().startswith("timestamp"):
            first_ts = col_list[0]
            last_ts = col_list[-1]
            min_str = f"first: {first_ts}"
            max_str = f"last: {last_ts}"
            avg_str = "&nbsp;"
        elif bool_values and len(bool_values) == len(col_list):
            true_count = sum(bool_values)
            false_count = len(bool_values) - true_count
            min_str = f"True: {true_count}"
            max_str = f"False: {false_count}"
            avg_str = "&nbsp;"
        elif numeric_values and len(numeric_values) == len(col_list):
            n_min = min(numeric_values)
            n_max = max(numeric_values)
            n_avg = statistics.mean(numeric_values)
            min_str = f"{n_min:.2f}"
            max_str = f"{n_max:.2f}"
            avg_str = f"{n_avg:.2f}"
        else:
            min_str = col_list[0] if col_list else "N/A"
            max_str = col_list[-1] if col_list else "N/A"
            avg_str = f"{len(col_list)} rows"

        lines.append(f"<tr><td>{col}</td><td>{min_str}</td><td>{max_str}</td><td>{avg_str}</td></tr>")

    lines.append("</table>")
    return "\n".join(lines)


def parse_backup_log(log_path, pi_name, log_date):
    if not os.path.isfile(log_path):
        return [f"<p>No backup_recordings log found for <b>{pi_name}</b> on {log_date}.</p>"]

    errors = []
    synced_files = []
    verified_files = []
    capturing_rsync = False

    wav_pattern = re.compile(r"(zoom_f8_pro_\d{8}_\d{6}_\d{4}\.wav)")

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            ls = line.strip("\n")

            # Parse errors
            if "[WARNING]" in ls or "[ERROR]" in ls:
                errors.append(ls)

            # If we see "rsync stdout:", start capturing lines for newly synced .wav
            if "rsync stdout:" in ls:
                capturing_rsync = True
                continue

            # If capturing, look for wave filenames, or stop on blank lines or next "[INFO]"
            if capturing_rsync:
                if not ls or "[INFO]" in ls:
                    capturing_rsync = False
                else:
                    wmatch = wav_pattern.search(ls)
                    if wmatch:
                        fname = wmatch.group(1)
                        synced_files.append(fname)

            # For analytics pi, we also want to detect verification lines
            if pi_name == "analyticspi":
                # e.g. "[INFO] File zoom_f8_pro_20250416_124800_0016.wav verified successfully (sha256)."
                if "verified successfully (sha256)" in ls.lower():
                    # parse out the file name with a simple regex
                    match = re.search(r"file\s+(.+?)\s+verified successfully \(sha256\)", ls, re.IGNORECASE)
                    if match:
                        verified_files.append(match.group(1))

    lines = []
    # Errors
    if errors:
        lines.append("<h4>Backup Errors/Warnings</h4><ul>")
        for e in errors:
            lines.append(f"<li>{e}</li>")
        lines.append("</ul>")
    else:
        lines.append("<p>No backup errors or warnings found.</p>")

    # Synced
    if synced_files:
        lines.append(f"<h4>Successfully Synced Files ({len(synced_files)} total)</h4><ol>")
        for sf in synced_files:
            lines.append(f"<li>{sf}</li>")
        lines.append("</ol>")
    else:
        lines.append("<p>No .wav files synced today.</p>")

    # Verified (sha256) - only relevant if pi_name == 'analyticspi'
    if pi_name == "analyticspi" and verified_files:
        lines.append(f"<h4>Verified Files (sha256) ({len(verified_files)} total)</h4><ul>")
        for vf in verified_files:
            lines.append(f"<li>{vf}</li>")
        lines.append("</ul>")

    return lines


def parse_mount_watchdog(log_path, log_date):
    if not os.path.isfile(log_path):
        return f"<p>No mount_watchdog log found for analytics-pi on {log_date}.</p>"

    fail_count = 0
    success_count = 0
    fail_details = []

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            ls = line.strip("\n")
            if "❌" in ls:
                fail_count += 1
                fail_details.append(ls)
            elif "✅" in ls:
                success_count += 1

    lines = []
    lines.append("<h4>Mount Watchdog</h4>")
    lines.append(f"<p>Mount OK count: {success_count}<br>Mount Fail count: {fail_count}</p>")
    if fail_count > 0:
        lines.append("<ul>")
        for d in fail_details:
            lines.append(f"<li>{d}</li>")
        lines.append("</ul>")

    return "\n".join(lines)


if __name__ == "__main__":
    main()

