"""
Telegram message formatting for the alarm pipeline.
"""

from html import escape

from processor import LONG_OUTAGE_MINUTES, SEVERITY_ORDER, format_minutes

OLDEST_ALARMS_PER_REGION = 3
TOP_REGIONS_IN_OVERVIEW = 3


def format_overview(result):
    """One nationwide summary message."""
    active = result["active"]
    lines = [
        "<b>Network Alarm Overview</b>",
        result["generated_at"].strftime("%d %b %Y, %H:%M"),
        "",
        f"Active alarms: <b>{len(active):,}</b>",
    ]

    for severity in SEVERITY_ORDER:
        count = int((active["Severity"] == severity).sum())
        lines.append(f"{severity}: {count:,}")

    lines += [
        f"Long outages ({LONG_OUTAGE_MINUTES // 60}h+): {len(result['long_outages']):,}",
        f"Affected sites: {active['SiteID'].nunique():,}",
        "",
        "<b>Most critical regions</b>",
    ]

    top_regions = result["regions"].head(TOP_REGIONS_IN_OVERVIEW)
    for rank, row in enumerate(top_regions.itertuples(), start=1):
        lines.append(f"{rank}. {escape(row.Region)} - {row.Critical} critical")

    return "\n".join(lines)


def format_region_message(region_row, result):
    """One message for a single region's operations team."""
    region = region_row["Region"]
    active = result["active"]

    critical = active[(active["Region"] == region) & (active["Severity"] == "Critical")]
    oldest = critical.sort_values("DurationMin", ascending=False).head(
        OLDEST_ALARMS_PER_REGION
    )

    lines = [
        f"<b>{escape(region)} - Active Alarms</b>",
        result["generated_at"].strftime("%d %b %Y, %H:%M"),
        "",
        f"Critical: <b>{region_row['Critical']}</b> | "
        f"Major: {region_row['Major']} | Minor: {region_row['Minor']}",
        f"Total active: {region_row['Total']}",
        f"Long outages ({LONG_OUTAGE_MINUTES // 60}h+): {region_row['LongOutages']}",
        "",
    ]

    if len(oldest):
        lines.append("<b>Longest critical alarms</b>")
        for rank, alarm in enumerate(oldest.itertuples(), start=1):
            lines.append(
                f"{rank}. {alarm.SiteID} | {escape(alarm.AlarmName)} | "
                f"{format_minutes(alarm.DurationMin)}"
            )
    else:
        lines.append("No active critical alarms.")

    return "\n".join(lines)