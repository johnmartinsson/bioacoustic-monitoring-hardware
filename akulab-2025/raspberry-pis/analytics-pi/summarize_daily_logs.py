#!/usr/bin/env python3
"""
summarize_daily_logs.py

Generates one HTML summary for the given date (default = today), scanning:
  /home/analyticspi/logs/pooled/<pi_name>/
    backup_recordings/<DATE>_backup_recordings.log
    rpi_health_snapshot/<DATE>_rpi_health.csv
    mount_watchdog/<DATE>_mount_watchdog.log   (analytics-pi only)

Three pi_name sections:
  1) Clock Pi
  2) Analytics Pi
  3) Recording Pi

The health CSV table now includes all columns from rpi_health_snapshot,
with min/max/avg for numeric columns, count of True vs. False for boolean columns, etc.
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
    # 1) Determine date argument
    if len(sys.argv) > 1:
        log_date = sys.argv[1]
    else:
        # Default to today's date (YYYY-MM-DD)
        log_date = datetime.now().strftime("%Y-%m-%d")

    LOG_BASE = "/home/analyticspi/logs/pooled"
    DAILY_SUM_DIR = os.path.join("/home/analyticspi/logs", "daily_summaries")
    os.makedirs(DAILY_SUM_DIR, exist_ok=True)

    # We'll gather HTML in a list of lines
    html_lines = []
    html_lines.append("<html><head><meta charset='utf-8'><title>Daily Summary</title></head><body>")
    html_lines.append(f"<h1>Daily Summary for {log_date}</h1>")

    # Process each Pi
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

    # Write out the HTML
    out_file = os.path.join(DAILY_SUM_DIR, f"{log_date}_summary.html")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(html_lines))

    print(f"Summary generated: {out_file}")


def parse_health_csv(csv_path, pi_name, log_date):
    """
    Parse rpi_health_snapshot CSV, building a table that includes
    all columns (timestamp, cpu usage, mem usage, disk usage, mount checks, etc.)
    We'll show min/avg/max for numeric columns, and a small summary for boolean columns.
    Also show first/last for timestamp columns.
    """
    if not os.path.isfile(csv_path):
        return f"<p>No rpi_health_snapshot found for <b>{pi_name}</b> on {log_date}.</p>"

    # We'll read the entire CSV into a list of dicts
    rows = []
    with open(csv_path, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rows.append(row)

    if not rows:
        return f"<p>Empty rpi_health_snapshot CSV for <b>{pi_name}</b> on {log_date}.</p>"

    # Collect columns
    columns = reader.fieldnames  # the column headers
    # We'll gather each column’s data in a list
    col_data = {col: [] for col in columns}

    for row in rows:
        for col in columns:
            col_data[col].append(row[col])

    # Build HTML
    lines = []
    lines.append(f"<h4>Health Snapshot for {pi_name} (all columns)</h4>")

    # Summaries for each column
    # We'll do a small table with one row per column
    lines.append("<table border='1' cellpadding='4' cellspacing='0'>")
    lines.append("<tr><th>Column</th><th>Min</th><th>Max</th><th>Average / Stats</th></tr>")

    for col in columns:
        col_list = col_data[col]
        # Decide if numeric, boolean, or timestamp, etc.
        # We'll attempt to parse them as floats; if many fail, maybe they are strings or booleans
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

        # Build summary
        # If the column name has "timestamp" or the values look like "YYYY-MM-DD HH:MM:SS",
        # we might show first/last. But let's keep it simpler: if it's the 'timestamp' column, do first/last
        # For numeric, we do min/avg/max
        # For boolean, count how many True vs. False
        # For everything else, we skip detailed stats and do "N/A"

        min_str = "N/A"
        max_str = "N/A"
        avg_str = "N/A"

        # If this column is 'timestamp', show first and last
        if col.lower().startswith("timestamp"):
            # e.g. col_data['timestamp'][0] and col_data['timestamp'][-1]
            first_ts = col_list[0]
            last_ts = col_list[-1]
            min_str = f"first: {first_ts}"
            max_str = f"last: {last_ts}"
            avg_str = "&nbsp;"
        elif bool_values and len(bool_values) == len(col_list):
            # entire column is boolean
            true_count = sum(bool_values)
            false_count = len(bool_values) - true_count
            min_str = f"True: {true_count}"
            max_str = f"False: {false_count}"
            avg_str = "&nbsp;"
        elif numeric_values and len(numeric_values) == len(col_list):
            # entire column is numeric
            n_min = min(numeric_values)
            n_max = max(numeric_values)
            n_avg = statistics.mean(numeric_values)
            min_str = f"{n_min:.2f}"
            max_str = f"{n_max:.2f}"
            avg_str = f"{n_avg:.2f}"
        else:
            # Mixed or string data => no stats
            # We'll just show the first/few examples
            min_str = col_list[0] if col_list else "N/A"
            max_str = col_list[-1] if col_list else "N/A"
            avg_str = f"{len(col_list)} rows"

        lines.append(f"<tr><td>{col}</td><td>{min_str}</td><td>{max_str}</td><td>{avg_str}</td></tr>")

    lines.append("</table>")
    return "\n".join(lines)


def parse_backup_log(log_path, pi_name, log_date):
    """Gather errors/warnings, list of synced .wav files (sorted by time)."""
    if not os.path.isfile(log_path):
        return [f"<p>No backup_recordings log found for <b>{pi_name}</b> on {log_date}.</p>"]

    errors = []
    synced_files = []
    # We'll gather lines that appear after "rsync completed" in the "rsync stdout:" block.
    wav_pattern = re.compile(r"(zoom_f8_pro_\d{8}_\d{6}_\d{4}\.wav)")

    def parse_filename_time(fname):
        match = re.search(r"zoom_f8_pro_(\d{8}_\d{6})_\d{4}\.wav", fname)
        if match:
            dt_str = match.group(1)  # "20250416_101800"
            try:
                return datetime.strptime(dt_str, "%Y%m%d_%H%M%S")
            except ValueError:
                pass
        return None

    capturing_rsync = False

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            ls = line.strip("\n")
            if "[WARNING]" in ls or "[ERROR]" in ls:
                errors.append(ls)

            if "rsync stdout:" in ls:
                capturing_rsync = True
                continue

            if capturing_rsync:
                if not ls or "[INFO]" in ls:
                    capturing_rsync = False
                else:
                    wmatch = wav_pattern.search(ls)
                    if wmatch:
                        fname = wmatch.group(1)
                        synced_files.append(fname)

    # Sort
    parse_results = []
    for sf in synced_files:
        dt = parse_filename_time(sf)
        if dt:
            parse_results.append((dt, sf))
        else:
            parse_results.append((datetime.min, sf))

    parse_results.sort(key=lambda x: x[0])
    sorted_synced_fnames = [x[1] for x in parse_results]

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
    if sorted_synced_fnames:
        lines.append(f"<h4>Successfully Synced Files ({len(sorted_synced_fnames)} total)</h4><ol>")
        for sf in sorted_synced_fnames:
            lines.append(f"<li>{sf}</li>")
        lines.append("</ol>")
    else:
        lines.append("<p>No .wav files synced today.</p>")

    return lines


def parse_mount_watchdog(log_path, log_date):
    """Analytics Pi only: parse mount_watchdog for success/fail lines."""
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

