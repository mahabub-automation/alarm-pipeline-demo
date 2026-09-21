"""
Alarm processing module.

Loads raw alarm records, validates and cleans them, and produces the
summaries that feed the Excel report and the Telegram notifications.
"""

import os
from datetime import datetime

import pandas as pd

INPUT_FILE = os.path.join("data", "sample_alarms.csv")
LONG_OUTAGE_MINUTES = 240
TOP_SITES_COUNT = 10

REQUIRED_COLUMNS = [
    "AlarmID", "SiteID", "Region", "AlarmName",
    "Severity", "OccurTime", "ClearTime",
]
SEVERITY_ORDER = ["Critical", "Major", "Minor"]


def load_alarms(path=INPUT_FILE):
    """Read the alarm CSV and parse the time columns."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Input file not found: {path}. Run generate_sample_data.py first."
        )

    alarms = pd.read_csv(path, dtype={"ClearTime": str})

    missing = [column for column in REQUIRED_COLUMNS if column not in alarms.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    alarms["OccurTime"] = pd.to_datetime(alarms["OccurTime"], errors="coerce")
    alarms["ClearTime"] = pd.to_datetime(alarms["ClearTime"], errors="coerce")
    return alarms


def validate_alarms(alarms):
    """Count data-quality problems without changing the data."""
    return {
        "duplicate_alarm_ids": int(alarms["AlarmID"].duplicated().sum()),
        "missing_occur_time": int(alarms["OccurTime"].isna().sum()),
        "clear_before_occur": int((alarms["ClearTime"] < alarms["OccurTime"]).sum()),
        "unknown_severity": int((~alarms["Severity"].isin(SEVERITY_ORDER)).sum()),
    }


def clean_alarms(alarms):
    """Remove rows that would distort the analysis."""
    cleaned = alarms.drop_duplicates(subset="AlarmID")
    cleaned = cleaned.dropna(subset=["OccurTime"])
    cleaned = cleaned[~(cleaned["ClearTime"] < cleaned["OccurTime"])]
    cleaned = cleaned[cleaned["Severity"].isin(SEVERITY_ORDER)]
    return cleaned.copy()


def add_duration(alarms, now):
    """Add alarm duration in minutes and an active flag."""
    alarms = alarms.copy()
    end_time = alarms["ClearTime"].fillna(now)
    minutes = (end_time - alarms["OccurTime"]).dt.total_seconds() / 60
    alarms["DurationMin"] = minutes.round().astype(int)
    alarms["IsActive"] = alarms["ClearTime"].isna()
    return alarms


def region_summary(alarms, active, long_outages):
    """Active alarms per region, split by severity, with long-outage count."""
    all_regions = sorted(alarms["Region"].unique())

    counts = pd.crosstab(active["Region"], active["Severity"])
    counts = counts.reindex(index=all_regions, columns=SEVERITY_ORDER, fill_value=0)
    counts.columns.name = None
    counts["Total"] = counts[SEVERITY_ORDER].sum(axis=1)
    counts["LongOutages"] = (
        long_outages["Region"].value_counts().reindex(all_regions, fill_value=0)
    )

    counts = counts.sort_values(["Critical", "Total"], ascending=False)
    counts.index.name = "Region"
    return counts.reset_index()


def top_problem_sites(active, count=TOP_SITES_COUNT):
    """Sites with the most active alarms right now."""
    sites = (
        active.groupby(["SiteID", "Region"])
        .agg(
            ActiveAlarms=("AlarmID", "count"),
            CriticalAlarms=("Severity", lambda values: int((values == "Critical").sum())),
            LongestMin=("DurationMin", "max"),
        )
        .sort_values(["ActiveAlarms", "CriticalAlarms", "LongestMin"], ascending=False)
        .head(count)
    )
    return sites.reset_index()


def format_minutes(minutes):
    """Turn 325 into '5h 25m'."""
    hours, remainder = divmod(int(minutes), 60)
    return f"{hours}h {remainder:02d}m" if hours else f"{remainder}m"


def process(path=INPUT_FILE, now=None):
    """Run the full processing step and return every result the pipeline needs."""
    now = now or datetime.now().replace(microsecond=0)

    raw = load_alarms(path)
    issues = validate_alarms(raw)
    alarms = add_duration(clean_alarms(raw), now)

    active = alarms[alarms["IsActive"]]
    long_outages = active[active["DurationMin"] >= LONG_OUTAGE_MINUTES].sort_values(
        "DurationMin", ascending=False
    )

    return {
        "generated_at": now,
        "raw_count": len(raw),
        "clean_count": len(alarms),
        "issues": issues,
        "alarms": alarms,
        "active": active,
        "long_outages": long_outages,
        "regions": region_summary(alarms, active, long_outages),
        "top_sites": top_problem_sites(active),
    }


def main():
    result = process()

    print("=" * 60)
    print("Alarm processing summary")
    print("=" * 60)
    print(f"Generated at   : {result['generated_at']}")
    print(f"Raw records    : {result['raw_count']:,}")
    print(f"Clean records  : {result['clean_count']:,}")
    print(f"Active alarms  : {len(result['active']):,}")
    print(f"Long outages   : {len(result['long_outages']):,} (>= {LONG_OUTAGE_MINUTES} min)")

    print("\nData quality checks:")
    for check, value in result["issues"].items():
        status = "OK" if value == 0 else "FOUND"
        print(f"  {check:<22}: {value:>5}  {status}")

    print("\nActive alarms by region:")
    print(result["regions"].to_string(index=False))

    print(f"\nTop {TOP_SITES_COUNT} problem sites:")
    top_sites = result["top_sites"].copy()
    top_sites["Longest"] = top_sites["LongestMin"].apply(format_minutes)
    print(top_sites.drop(columns="LongestMin").to_string(index=False))

    print("\nLongest running outages:")
    longest = result["long_outages"].head(5)[
        ["SiteID", "Region", "AlarmName", "Severity", "DurationMin"]
    ].copy()
    longest["Duration"] = longest["DurationMin"].apply(format_minutes)
    print(longest.drop(columns="DurationMin").to_string(index=False))


if __name__ == "__main__":
    main()