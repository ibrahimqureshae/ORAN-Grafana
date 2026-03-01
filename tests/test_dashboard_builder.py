from oran_viz import dashboard_builder as builder


def test_get_unit_mapping():
    assert builder._get_unit("cpu_percent") == "percent"
    assert builder._get_unit("accuracy") == "percentunit"
    assert builder._get_unit("latency_ms") == "ms"
    assert builder._get_unit("memory_mb") == "decmbytes"
    assert builder._get_unit("some_unknown_metric") == "short"


def test_field_config_bounds():
    percent_cfg = builder._field_config("cpu_percent")
    assert percent_cfg["defaults"]["min"] == 0
    assert percent_cfg["defaults"]["max"] == 100

    unit_cfg = builder._field_config("accuracy")
    assert unit_cfg["defaults"]["min"] == 0
    assert unit_cfg["defaults"]["max"] == 1

    plain_cfg = builder._field_config("events")
    assert "min" not in plain_cfg["defaults"]
    assert "max" not in plain_cfg["defaults"]


def test_build_dashboard_generates_expected_panels_and_queries():
    schema = {
        "model_training": {
            "fields": ["loss", "accuracy", "learning_rate"],
            "tags": ["model_name"],
        }
    }

    dashboard = builder.build_dashboard(schema, "ds-uid-1")
    panels = dashboard["panels"]

    assert dashboard["uid"] == "oran-aiml-auto"
    assert len(panels) == (3 + 3 + 1)

    stat = panels[0]
    assert stat["type"] == "stat"
    assert stat["datasource"]["uid"] == "ds-uid-1"
    assert stat["targets"][0]["query"] == 'SELECT last("loss") FROM "model_training"'

    timeseries = next(panel for panel in panels if panel["type"] == "timeseries")
    assert "WHERE $timeFilter" in timeseries["targets"][0]["query"]
    assert "GROUP BY time($__interval)" in timeseries["targets"][0]["query"]

    table = panels[-1]
    assert table["type"] == "table"
    assert table["targets"][0]["resultFormat"] == "table"
    assert "LIMIT 100" in table["targets"][0]["query"]


def test_build_dashboard_skips_measurement_without_fields():
    schema = {
        "empty_measurement": {"fields": [], "tags": ["node"]},
        "resource_usage": {"fields": ["cpu_percent"], "tags": ["node_id"]},
    }

    dashboard = builder.build_dashboard(schema, "ds-uid-2")
    assert len(dashboard["panels"]) == (1 + 1 + 1)
