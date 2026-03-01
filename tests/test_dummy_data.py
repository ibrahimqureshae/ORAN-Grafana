from datetime import datetime, timezone

from oran_viz import dummy_data


def test_make_line_formats_influx_line_protocol():
    ts = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)

    line = dummy_data._make_line(
        "resource_usage",
        {"node_id": "node_1"},
        {"cpu_percent": 75.2, "memory_mb": 8192.0},
        ts,
    )

    assert line.startswith("resource_usage,node_id=node_1 ")
    assert "cpu_percent=75.2" in line
    assert "memory_mb=8192.0" in line
    assert line.endswith(" 1772366400000000000")


def test_make_ric_policy_stats_contains_expected_measurement_and_tag():
    ts = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)

    records = dummy_data._make_ric_policy_stats(ts)

    assert len(records) == 1
    assert records[0].startswith("ric_policy_stats,ric_instance=nonrtric_1 ")
