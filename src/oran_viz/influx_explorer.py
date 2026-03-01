# ─────────────────────────────────────────────────────────────────────
# influx_explorer.py
# Dynamically discovers what measurements and fields exist in InfluxDB.
# Uses SQL information_schema — no field names are ever hardcoded.
# ─────────────────────────────────────────────────────────────────────

from influxdb_client_3 import InfluxDBClient3
from oran_viz import config

# In InfluxDB 3, tag columns are stored as dictionary-encoded strings.
# These data_type values identify a column as a tag (label), not a field.
TAG_DATA_TYPES = {"Dictionary(Int32, Utf8)", "Utf8"}
SKIP_COLUMNS   = {"time"}


def get_client() -> InfluxDBClient3:
    return InfluxDBClient3(
        host=config.INFLUX_HOST,
        token=config.INFLUX_TOKEN,
        database=config.INFLUX_DB
    )


def discover_schema(client: InfluxDBClient3) -> dict:
    """
    Queries InfluxDB 3 information_schema to discover all measurements
    and their fields and tags.

    Returns:
    {
        "model_training": {
            "fields": ["loss", "accuracy", "val_loss", "learning_rate"],
            "tags":   ["model_name", "experiment_id"]
        },
        ...
    }
    """
    schema = {}

    # ── Step 1: get all user measurements ────────────────────────────
    tables_result = client.query("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'iox'
    """)

    if tables_result is None:
        return schema

    tables_df    = tables_result.to_pandas()
    measurements = tables_df["table_name"].unique().tolist()

    # ── Step 2: get columns for each measurement ──────────────────────
    for measurement in measurements:
        cols_result = client.query(f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'iox'
            AND   table_name   = '{measurement}'
        """)

        if cols_result is None:
            continue

        cols_df = cols_result.to_pandas()
        fields, tags = [], []

        for _, row in cols_df.iterrows():
            name  = row["column_name"]
            dtype = row["data_type"]

            if name in SKIP_COLUMNS:
                continue
            elif dtype in TAG_DATA_TYPES:
                tags.append(name)
            else:
                fields.append(name)

        schema[measurement] = {"fields": fields, "tags": tags}

    return schema


def schema_changed(old: dict, new: dict) -> bool:
    """Returns True if anything in the schema was added or changed."""
    return old != new
