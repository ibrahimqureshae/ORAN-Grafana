# ─────────────────────────────────────────────────────────────────────
# dashboard_builder.py
# Builds the full Grafana dashboard JSON from the discovered schema.
# Uses InfluxQL — no field names are ever hardcoded.
# ─────────────────────────────────────────────────────────────────────

# Maps keywords in field names to Grafana unit codes.
# Grafana uses these codes to format the displayed value correctly.
UNIT_MAP = {
    "percent":     "percent",       # e.g. cpu_percent        (0–100)
    "utilization": "percent",       # e.g. gpu_utilization    (0–100)
    "accuracy":    "percentunit",   # e.g. accuracy           (0.0–1.0)
    "score":       "percentunit",   # e.g. confidence_score   (0.0–1.0)
    "rate":        "percentunit",   # e.g. enforcement_rate   (0.0–1.0)
    "_ms":         "ms",            # e.g. latency_ms
    "latency":     "ms",            # e.g. latency
    "_mb":         "decmbytes",     # e.g. memory_mb
    "memory":      "decmbytes",     # e.g. memory
}


def _get_unit(field: str) -> str:
    """Inspects a field name and returns the correct Grafana unit code."""
    f = field.lower()
    for keyword, unit in UNIT_MAP.items():
        if keyword in f:
            return unit
    return "short"


def _field_config(field: str) -> dict:
    """Builds the Grafana fieldConfig for a panel based on field name."""
    unit    = _get_unit(field)
    cfg     = {"defaults": {"unit": unit, "decimals": 2}, "overrides": []}

    if unit == "percent":
        cfg["defaults"]["min"] = 0
        cfg["defaults"]["max"] = 100
    elif unit == "percentunit":
        cfg["defaults"]["min"] = 0
        cfg["defaults"]["max"] = 1

    return cfg


def _stat_panel(measurement, field, ds_uid, panel_id, x, y) -> dict:
    """Big number card showing the most recent value of a field."""
    return {
        "id":          panel_id,
        "title":       f"Latest › {field}",
        "type":        "stat",
        "gridPos":     {"x": x, "y": y, "w": 6, "h": 4},
        "datasource":  {"type": "influxdb", "uid": ds_uid},
        "fieldConfig": _field_config(field),
        "options": {
            "reduceOptions": {"calcs": ["lastNotNull"]},
            "colorMode":     "background",
            "textMode":      "auto",
            "orientation":   "auto"
        },
        "targets": [{
            "refId":        "A",
            "rawQuery":     True,
            "query":        f'SELECT last("{field}") FROM "{measurement}"',
            "resultFormat": "time_series"
        }]
    }


def _timeseries_panel(measurement, field, ds_uid, panel_id, x, y) -> dict:
    """Line chart of a numeric field's trend over time."""
    return {
        "id":          panel_id,
        "title":       f"{measurement} › {field}",
        "type":        "timeseries",
        "gridPos":     {"x": x, "y": y, "w": 12, "h": 8},
        "datasource":  {"type": "influxdb", "uid": ds_uid},
        "fieldConfig": _field_config(field),
        "targets": [{
            "refId":        "A",
            "rawQuery":     True,
            "query": (
                f'SELECT mean("{field}") FROM "{measurement}"'
                f' WHERE $timeFilter'
                f' GROUP BY time($__interval) fill(null)'
            ),
            "resultFormat": "time_series"
        }]
    }


def _table_panel(measurement, ds_uid, panel_id, x, y) -> dict:
    """Table showing the 100 most recent rows of a measurement."""
    return {
        "id":         panel_id,
        "title":      f"{measurement} › recent rows",
        "type":       "table",
        "gridPos":    {"x": x, "y": y, "w": 24, "h": 8},
        "datasource": {"type": "influxdb", "uid": ds_uid},
        "targets": [{
            "refId":        "A",
            "rawQuery":     True,
            "query": (
                f'SELECT * FROM "{measurement}"'
                f' WHERE $timeFilter'
                f' LIMIT 100'
            ),
            "resultFormat": "table"
        }]
    }


def build_dashboard(schema: dict, ds_uid: str) -> dict:
    """
    Iterates the discovered schema and generates a complete Grafana
    dashboard JSON with stat, timeseries, and table panels per measurement.
    """
    panels   = []
    panel_id = 1
    y        = 0

    for measurement, info in schema.items():
        fields = info.get("fields", [])
        if not fields:
            continue

        # ── Stat row (4 per row × 6 units wide) ──────────────────────
        x = 0
        for field in fields:
            panels.append(_stat_panel(measurement, field, ds_uid, panel_id, x, y))
            panel_id += 1
            x        += 6
            if x >= 24:
                x  = 0
                y += 4
        y += 4

        # ── Timeseries row (2 per row × 12 units wide) ────────────────
        x = 0
        for field in fields:
            panels.append(_timeseries_panel(measurement, field, ds_uid, panel_id, x, y))
            panel_id += 1
            x        += 12
            if x >= 24:
                x  = 0
                y += 8
        y += 8

        # ── Table row (full 24 units wide) ────────────────────────────
        panels.append(_table_panel(measurement, ds_uid, panel_id, 0, y))
        panel_id += 1
        y        += 12

    return {
        "uid":           "oran-aiml-auto",
        "title":         "O-RAN AI/ML — Auto Dashboard",
        "tags":          ["oran", "aiml", "auto-generated"],
        "schemaVersion": 36,
        "refresh":       "5s",
        "time":          {"from": "now-30m", "to": "now"},
        "panels":        panels
    }
