"""
Tests for the alarm processor.

Run from the project folder with:  python -m pytest -v
"""

import random
from datetime import datetime

import pandas as pd
import pytest

import generate_sample_data as generator
from processor import (
    add_duration,
    clean_alarms,
    format_minutes,
    load_alarms,
    process,
    validate_alarms,
)

NOW = datetime(2026, 9, 21, 12, 0, 0)

COLUMNS = [
    "AlarmID", "SiteID", "Region", "AlarmName",
    "Severity", "OccurTime", "ClearTime",
]


def write_alarms(tmp_path, rows):
    """Save rows as a CSV the processor can load, and return its path."""
    path = tmp_path / "alarms.csv"
    pd.DataFrame(rows, columns=COLUMNS).to_csv(path, index=False)
    return str(path)


@pytest.fixture
def small_dataset(tmp_path):
    """Eight hand-picked rows: four valid alarms and one of each problem."""
    rows = [
        # Valid: active critical, running 5 hours -> long outage
        ["A1", "DHN0001", "Dhaka North", "Mains Failure", "Critical", "2026-09-21 07:00:00", ""],
        # Valid: active minor, running 10 hours -> long outage
        ["A2", "DHN0002", "Dhaka North", "Door Open", "Minor", "2026-09-21 02:00:00", ""],
        # Valid: cleared after 30 minutes
        ["A3", "SYL0001", "Sylhet", "DG On Load", "Major", "2026-09-21 09:00:00", "2026-09-21 09:30:00"],
        # Valid: active major, running 1 hour -> not a long outage
        ["A4", "SYL0002", "Sylhet", "High Temperature", "Major", "2026-09-21 11:00:00", ""],
        # Problem: duplicate of A1
        ["A1", "DHN0001", "Dhaka North", "Mains Failure", "Critical", "2026-09-21 07:00:00", ""],
        # Problem: missing occur time
        ["A5", "RAJ0001", "Rajshahi", "Mains Failure", "Critical", "", ""],
        # Problem: clear time before occur time
        ["A6", "RAJ0002", "Rajshahi", "Door Open", "Minor", "2026-09-21 10:00:00", "2026-09-21 09:00:00"],
        # Problem: unknown severity
        ["A7", "RAJ0003", "Rajshahi", "Door Open", "Warning", "2026-09-21 10:00:00", ""],
    ]
    return write_alarms(tmp_path, rows)


def test_validation_finds_each_issue_once(small_dataset):
    issues = validate_alarms(load_alarms(small_dataset))

    assert issues == {
        "duplicate_alarm_ids": 1,
        "missing_occur_time": 1,
        "clear_before_occur": 1,
        "unknown_severity": 1,
    }


def test_cleaning_keeps_only_valid_rows(small_dataset):
    cleaned = clean_alarms(load_alarms(small_dataset))

    assert sorted(cleaned["AlarmID"]) == ["A1", "A2", "A3", "A4"]


def test_duration_and_active_flag(small_dataset):
    alarms = add_duration(clean_alarms(load_alarms(small_dataset)), NOW)
    alarms = alarms.set_index("AlarmID")

    assert alarms.loc["A1", "DurationMin"] == 300
    assert alarms.loc["A3", "DurationMin"] == 30
    assert bool(alarms.loc["A1", "IsActive"]) is True
    assert bool(alarms.loc["A3", "IsActive"]) is False


def test_long_outages_list_critical_before_longer_minor(small_dataset):
    result = process(small_dataset, now=NOW)

    # A1 is critical (5h) and must come before A2, which is minor but longer (10h)
    assert list(result["long_outages"]["AlarmID"]) == ["A1", "A2"]


def test_region_summary_adds_up_to_active_alarms(small_dataset):
    result = process(small_dataset, now=NOW)
    regions = result["regions"].set_index("Region")

    assert regions["Total"].sum() == len(result["active"])
    assert regions.loc["Dhaka North", "Critical"] == 1
    assert regions.loc["Dhaka North", "LongOutages"] == 2
    assert regions.loc["Sylhet", "Total"] == 1


@pytest.mark.parametrize(
    "minutes, expected",
    [(0, "0m"), (45, "45m"), (60, "1h 00m"), (325, "5h 25m")],
)
def test_format_minutes(minutes, expected):
    assert format_minutes(minutes) == expected


def test_full_generated_dataset(tmp_path):
    """The injected problems in the synthetic dataset are all caught."""
    random.seed(generator.RANDOM_SEED)
    dataset = generator.inject_data_quality_issues(generator.generate_alarms(NOW))
    path = tmp_path / "sample.csv"
    dataset.to_csv(path, index=False)

    result = process(str(path), now=NOW)

    assert result["raw_count"] == 10015
    assert result["clean_count"] == 9977
    assert result["issues"] == {
        "duplicate_alarm_ids": 15,
        "missing_occur_time": 10,
        "clear_before_occur": 8,
        "unknown_severity": 5,
    }
    assert result["regions"]["Total"].sum() == len(result["active"])