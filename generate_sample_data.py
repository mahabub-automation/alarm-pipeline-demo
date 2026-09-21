"""
Generate a realistic but fully synthetic telecom tower alarm dataset.

No real site IDs, operators or company data are used. Region names are
generic geographic areas; site IDs and alarm IDs are randomly generated.
"""

import os
import random
from datetime import datetime, timedelta

import pandas as pd

RANDOM_SEED = 42
TOTAL_ALARMS = 10000
SITES_PER_REGION = 120
LOOKBACK_HOURS = 24
OUTPUT_FILE = os.path.join("data", "sample_alarms.csv")

# Region name -> short code used to build fake site IDs
REGIONS = {
    "Dhaka North": "DHN",
    "Dhaka South": "DHS",
    "Dhaka East": "DHE",
    "Dhaka West": "DHW",
    "Gazipur": "GAZ",
    "Narayanganj": "NGJ",
    "Mymensingh": "MYM",
    "Chattogram North": "CTN",
    "Chattogram South": "CTS",
    "Cumilla": "CUM",
    "Noakhali": "NOA",
    "Sylhet": "SYL",
    "Rajshahi": "RAJ",
    "Rangpur": "RAN",
    "Khulna": "KHU",
    "Barishal": "BAR",
}

# (alarm name, severity, relative frequency, (min minutes, max minutes))
ALARM_TYPES = [
    ("Mains Failure",         "Critical", 30, (20, 600)),
    ("DG On Load",            "Major",    20, (30, 480)),
    ("Battery Low Voltage",   "Critical", 12, (10, 240)),
    ("High Temperature",      "Major",    10, (15, 300)),
    ("Rectifier Module Fail", "Major",     8, (60, 1440)),
    ("Door Open",             "Minor",    10, (5, 60)),
    ("Transmission Link Down","Critical",  6, (5, 180)),
    ("Fuel Level Low",        "Minor",     4, (120, 2880)),
]


def build_sites():
    """Create a list of (site_id, region) pairs."""
    sites = []
    for region, code in REGIONS.items():
        for number in range(1, SITES_PER_REGION + 1):
            sites.append((f"{code}{number:04d}", region))
    return sites


def generate_alarms(now):
    """Generate synthetic alarm records relative to the given time."""
    sites = build_sites()
    weights = [alarm[2] for alarm in ALARM_TYPES]
    rows = []

    for index in range(1, TOTAL_ALARMS + 1):
        site_id, region = random.choice(sites)
        name, severity, _, (min_minutes, max_minutes) = random.choices(
            ALARM_TYPES, weights=weights
        )[0]

        occur_time = now - timedelta(minutes=random.randint(0, LOOKBACK_HOURS * 60))
        duration = random.randint(min_minutes, max_minutes)
        clear_time = occur_time + timedelta(minutes=duration)

        # If the alarm would clear in the future, it is still active now
        if clear_time > now:
            clear_time = None

        rows.append({
            "AlarmID": f"ALM{index:06d}",
            "SiteID": site_id,
            "Region": region,
            "AlarmName": name,
            "Severity": severity,
            "OccurTime": occur_time.strftime("%Y-%m-%d %H:%M:%S"),
            "ClearTime": clear_time.strftime("%Y-%m-%d %H:%M:%S") if clear_time else "",
        })

    dataframe = pd.DataFrame(rows)
    return dataframe.sort_values("OccurTime", ascending=False).reset_index(drop=True)


def main():
    random.seed(RANDOM_SEED)
    os.makedirs("data", exist_ok=True)

    now = datetime.now().replace(microsecond=0)
    alarms = generate_alarms(now)
    alarms.to_csv(OUTPUT_FILE, index=False)

    active = alarms[alarms["ClearTime"] == ""]

    print("=" * 50)
    print("Synthetic alarm dataset generated")
    print("=" * 50)
    print(f"File           : {OUTPUT_FILE}")
    print(f"Total alarms   : {len(alarms):,}")
    print(f"Active alarms  : {len(active):,}")
    print(f"Cleared alarms : {len(alarms) - len(active):,}")
    print(f"Regions        : {alarms['Region'].nunique()}")
    print(f"Sites          : {alarms['SiteID'].nunique():,}")
    print("\nActive alarms by severity:")
    print(active["Severity"].value_counts().to_string())


if __name__ == "__main__":
    main()