#!/usr/bin/env python3
"""Analyze parsed summary JSON files and flag potentially odd days."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class Finding:
    date: str
    pi: str
    severity: str
    check: str
    details: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parsed-dir", required=True, help="Directory with *_summary.json files")
    parser.add_argument("--out-dir", default="./analysis", help="Output directory")

    parser.add_argument("--temp-threshold-c", type=float, default=65.0)
    parser.add_argument("--chrony-offset-threshold-s", type=float, default=0.01)
    parser.add_argument("--chrony-rms-threshold-s", type=float, default=0.02)
    parser.add_argument("--max-mount-fails", type=int, default=0)
    parser.add_argument("--min-synced-files", type=int, default=1)
    parser.add_argument("--require-zoom-ok", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--segment-tolerance-s", type=int, default=1,
                        help="Allowed deviation (seconds) from expected segment length before flagging a gap")
    return parser.parse_args()


def to_float(value: str | None) -> float | None:
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_true_false_count(value: str | None, label: str) -> int | None:
    if value is None:
        return None
    m = re.search(rf"{label}:\s*(\d+)", value)
    return int(m.group(1)) if m else None


def expected_clock_source(pi: str) -> str | None:
    if pi == "clockpi":
        return "PPS"
    if pi in {"analyticspi", "recordingpi"}:
        return "clockpi"
    return None


def add_health_findings(date_s: str, pi: str, health: dict[str, Any], args: argparse.Namespace, findings: list[Finding]) -> None:
    temp_max = to_float(health.get("temperature_c", {}).get("max"))
    if temp_max is not None and temp_max > args.temp_threshold_c:
        findings.append(Finding(date_s, pi, "warning", "temperature", f"max temperature {temp_max:.2f}C > {args.temp_threshold_c:.2f}C"))

    throttled_max = to_float(health.get("throttled_flags", {}).get("max"))
    if throttled_max is not None and throttled_max > 0:
        findings.append(Finding(date_s, pi, "warning", "throttling", f"throttled_flags max is {throttled_max}"))

    ro_min = health.get("root_readonly", {}).get("min")
    true_count = parse_true_false_count(ro_min, "True")
    if true_count is not None and true_count > 0:
        findings.append(Finding(date_s, pi, "critical", "root_readonly", f"root_readonly true count = {true_count}"))

    if args.require_zoom_ok and pi == "recordingpi":
        zoom_min = health.get("zoom_hw2_ok", {}).get("min")
        false_count = parse_true_false_count(zoom_min, "False")
        if false_count is not None and false_count > 0:
            findings.append(Finding(date_s, pi, "critical", "zoom_hw2_ok", f"zoom_hw2_ok false count = {false_count}"))


def add_chrony_findings(date_s: str, pi: str, section: dict[str, Any], args: argparse.Namespace, findings: list[Finding]) -> None:
    chrony = section.get("chrony", {})
    last_off = chrony.get("chrony_last_offset_s", {})
    rms_off = chrony.get("chrony_rms_offset_s", {})

    min_last = to_float(last_off.get("min"))
    max_last = to_float(last_off.get("max"))
    if min_last is not None and abs(min_last) > args.chrony_offset_threshold_s:
        findings.append(Finding(date_s, pi, "warning", "chrony_last_offset_s", f"min {min_last:.6f}s exceeds threshold"))
    if max_last is not None and abs(max_last) > args.chrony_offset_threshold_s:
        findings.append(Finding(date_s, pi, "warning", "chrony_last_offset_s", f"max {max_last:.6f}s exceeds threshold"))

    max_rms = to_float(rms_off.get("max"))
    if max_rms is not None and max_rms > args.chrony_rms_threshold_s:
        findings.append(Finding(date_s, pi, "warning", "chrony_rms_offset_s", f"max {max_rms:.6f}s exceeds threshold"))

    src_usage = section.get("clock_source_usage") or ""
    expected = expected_clock_source(pi)
    if expected and expected not in src_usage:
        findings.append(Finding(date_s, pi, "warning", "clock_source_usage", f"expected source '{expected}' not found in '{src_usage}'"))


def add_mount_and_sync_findings(date_s: str, pi: str, section: dict[str, Any], args: argparse.Namespace, findings: list[Finding]) -> None:
    mount = section.get("mount_watchdog", {})
    fail_count = mount.get("fail_count")
    if isinstance(fail_count, int) and fail_count > args.max_mount_fails:
        findings.append(Finding(date_s, pi, "warning", "mount_watchdog", f"mount fail count {fail_count} > {args.max_mount_fails}"))

    if pi == "analyticspi":
        synced = section.get("synced_files", [])
        if isinstance(synced, list) and len(synced) < args.min_synced_files:
            findings.append(Finding(date_s, pi, "warning", "synced_files", f"only {len(synced)} synced files (< {args.min_synced_files})"))


# ── Recording-continuity helpers ─────────────────────────────────────────────

_OLD_PAT = re.compile(r"^auklab_zoom_f8_pro_(\d{8})_(\d{6})_\d+\.wav$")
_NEW_PAT = re.compile(r"^auklab_(\d{8})T(\d{6})\.wav$")
_OLD_SEGMENT_S = 3600
_NEW_SEGMENT_S = 600


def _parse_audio_filename(name: str) -> tuple[datetime | None, str | None]:
    """Return (datetime, 'old'|'new') or (None, None) if unrecognised."""
    m = _OLD_PAT.match(name)
    if m:
        return datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S"), "old"
    m = _NEW_PAT.match(name)
    if m:
        return datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S"), "new"
    return None, None


def add_continuity_findings(
    parsed_docs: list[dict[str, Any]],
    args: argparse.Namespace,
    findings: list[Finding],
) -> None:
    """Collect all synced audio filenames, sort by timestamp, flag gaps."""
    # De-duplicate: same file may appear in multiple days' synced lists.
    seen: dict[str, tuple[datetime, str]] = {}
    for doc in parsed_docs:
        synced = doc.get("sections", {}).get("analyticspi", {}).get("synced_files", [])
        for name in synced:
            if name not in seen:
                dt, fmt = _parse_audio_filename(name)
                if dt is not None:
                    seen[name] = (dt, fmt)

    if not seen:
        return

    sorted_files = sorted(seen.items(), key=lambda x: x[1][0])

    prev_name, (prev_dt, prev_fmt) = sorted_files[0]
    for name, (dt, fmt) in sorted_files[1:]:
        gap_s = (dt - prev_dt).total_seconds()

        date_s = dt.strftime("%Y-%m-%d")
        if prev_fmt != fmt:
            details = f"filename format changed (gap {gap_s:.0f}s): last old='{prev_name}', first new='{name}'"
            if date_s == "2025-05-20" and prev_fmt == "old" and fmt == "new":
                details += " [known caveat: summary synced-file list may omit early 2025-05-20 old-format files; true downtime likely much shorter]"
            findings.append(Finding(date_s, "recordingpi", "warning", "recording_restart", details))
        else:
            expected_s = _OLD_SEGMENT_S if fmt == "old" else _NEW_SEGMENT_S
            if gap_s > expected_s + args.segment_tolerance_s:
                findings.append(Finding(
                    date_s, "recordingpi", "warning", "recording_continuity",
                    f"gap {gap_s:.0f}s between '{prev_name}' and '{name}' (expected ~{expected_s}s)",
                ))
            elif gap_s < 0:
                findings.append(Finding(
                    date_s, "recordingpi", "warning", "recording_continuity",
                    f"negative gap {gap_s:.0f}s between '{prev_name}' and '{name}'",
                ))

        prev_name, prev_dt, prev_fmt = name, dt, fmt


# ─────────────────────────────────────────────────────────────────────────────


def build_daily_overview(parsed_docs: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for doc in parsed_docs:
        day = doc.get("date")
        sections = doc.get("sections", {})
        for pi, section in sections.items():
            health = section.get("health", {})
            mount = section.get("mount_watchdog", {})
            rows.append(
                {
                    "date": day,
                    "pi": pi,
                    "temp_max_c": to_float(health.get("temperature_c", {}).get("max")),
                    "cpu_max_pct": to_float(health.get("cpu_percent", {}).get("max")),
                    "disk_pct_max": to_float(health.get("disk_percent", {}).get("max")),
                    "throttled_flags_max": to_float(health.get("throttled_flags", {}).get("max")),
                    "chrony_src": section.get("clock_source_usage"),
                    "synced_files_count": len(section.get("synced_files", [])) if isinstance(section.get("synced_files", []), list) else None,
                    "mount_fail_count": mount.get("fail_count"),
                }
            )
    return pd.DataFrame(rows)


def get_known_caveats(parsed_docs: list[dict[str, Any]]) -> list[str]:
    dates = sorted({doc.get("date") for doc in parsed_docs if doc.get("date")})
    if not dates:
        return []

    caveats: list[str] = []
    if "2025-05-20" in dates:
        caveats.append(
            "2025-05-20 recording restart changed filename format (hourly -> 10-minute). "
            "Daily summary synced-file lists may omit some old-format files from early that day; "
            "continuity gaps at this boundary can be overstated relative to true recorder downtime."
        )
    return caveats


def main() -> int:
    args = parse_args()
    parsed_dir = Path(args.parsed_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(parsed_dir.glob("*_summary.json"))
    if not files:
        raise SystemExit(f"No parsed summary files found in {parsed_dir}")

    parsed_docs: list[dict[str, Any]] = []
    findings: list[Finding] = []

    for fp in files:
        doc = json.loads(fp.read_text(encoding="utf-8"))
        parsed_docs.append(doc)
        date_s = doc.get("date", fp.stem.replace("_summary", ""))

        sections = doc.get("sections", {})
        for pi, section in sections.items():
            health = section.get("health", {})
            add_health_findings(date_s, pi, health, args, findings)
            add_chrony_findings(date_s, pi, section, args, findings)
            add_mount_and_sync_findings(date_s, pi, section, args, findings)

    add_continuity_findings(parsed_docs, args, findings)

    findings_df = pd.DataFrame([f.__dict__ for f in findings])
    overview_df = build_daily_overview(parsed_docs)

    overview_df.to_csv(out_dir / "daily_overview.csv", index=False)
    if not findings_df.empty:
        findings_df.sort_values(["date", "severity", "pi", "check"]).to_csv(out_dir / "findings.csv", index=False)
    else:
        pd.DataFrame(columns=["date", "pi", "severity", "check", "details"]).to_csv(out_dir / "findings.csv", index=False)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "num_days": len(parsed_docs),
        "num_findings": len(findings),
        "num_critical": int(sum(1 for f in findings if f.severity == "critical")),
        "num_warning": int(sum(1 for f in findings if f.severity == "warning")),
        "thresholds": {
            "temp_threshold_c": args.temp_threshold_c,
            "chrony_offset_threshold_s": args.chrony_offset_threshold_s,
            "chrony_rms_threshold_s": args.chrony_rms_threshold_s,
            "max_mount_fails": args.max_mount_fails,
            "min_synced_files": args.min_synced_files,
            "require_zoom_ok": args.require_zoom_ok,
            "segment_tolerance_s": args.segment_tolerance_s,
        },
    }
    (out_dir / "analysis_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    known_caveats = get_known_caveats(parsed_docs)

    md_lines = [
        "# Season Summary Analysis",
        "",
        f"- Days analyzed: {summary['num_days']}",
        f"- Findings: {summary['num_findings']} (critical: {summary['num_critical']}, warning: {summary['num_warning']})",
        "",
        "## Thresholds",
        f"- temp_threshold_c: {args.temp_threshold_c}",
        f"- chrony_offset_threshold_s: {args.chrony_offset_threshold_s}",
        f"- chrony_rms_threshold_s: {args.chrony_rms_threshold_s}",
        f"- max_mount_fails: {args.max_mount_fails}",
        f"- min_synced_files: {args.min_synced_files}",
        f"- require_zoom_ok: {args.require_zoom_ok}",
        f"- segment_tolerance_s: {args.segment_tolerance_s}",
        "",
    ]

    if known_caveats:
        md_lines.append("## Known Data Caveats")
        for note in known_caveats:
            md_lines.append(f"- {note}")
        md_lines.append("")

    if findings:
        md_lines.append("## Findings")
        for f in sorted(findings, key=lambda x: (x.date, x.severity, x.pi, x.check)):
            md_lines.append(f"- {f.date} | {f.severity.upper()} | {f.pi} | {f.check} | {f.details}")
    else:
        md_lines.append("## Findings")
        md_lines.append("- No anomalies detected with current thresholds.")

    (out_dir / "analysis_report.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"[INFO] Analysis complete. Days={summary['num_days']} Findings={summary['num_findings']}")
    print(f"[INFO] Outputs written to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
