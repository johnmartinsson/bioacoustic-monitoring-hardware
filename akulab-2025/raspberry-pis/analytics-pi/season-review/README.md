# Season Summary Crawl + Review

This folder contains tools to download, parse, and analyze daily summary pages.

## Files

- `crawl_and_parse_summaries.py`
  - Downloads `YYYY-MM-DD_summary.html` pages in a date range.
  - Saves raw HTML and parsed JSON.
- `analyze_summaries.py`
  - Reads parsed JSON files and flags anomalies.
  - Writes `daily_overview.csv`, `findings.csv`, `analysis_summary.json`, `analysis_report.md`.

## Install Dependencies

```bash
python3 -m pip install beautifulsoup4 pandas
```

## 1) Crawl and Parse

```bash
python3 crawl_and_parse_summaries.py \
  --start-date 2025-04-01 \
  --end-date 2025-09-30 \
  --base-url https://johnmartinsson.github.io/akulab2025/daily_summaries \
  --out-dir ./season_2025
```

Outputs:

- `season_2025/raw_html/*.html`
- `season_2025/parsed_json/*.json`
- `season_2025/crawl_report.json`

## 2) Analyze for Odd Events

```bash
python3 analyze_summaries.py \
  --parsed-dir ./season_2025/parsed_json \
  --out-dir ./season_2025/analysis \
  --temp-threshold-c 65 \
  --chrony-offset-threshold-s 0.01 \
  --chrony-rms-threshold-s 0.02 \
  --max-mount-fails 0 \
  --min-synced-files 1
```

Outputs:

- `season_2025/analysis/daily_overview.csv`
- `season_2025/analysis/findings.csv`
- `season_2025/analysis/analysis_summary.json`
- `season_2025/analysis/analysis_report.md`

## Notes

- Missing pages are recorded in `crawl_report.json` as HTTP errors.
- Thresholds are intentionally configurable; tune them to your seasonal norms.
- If a day has very low activity, `min-synced-files` may need to be reduced.
