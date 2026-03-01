# ─────────────────────────────────────────────────────────────────────
# pipeline.py
# Main orchestrator — discovers schema, pushes dashboards, polls loop.
# CLI entry point: oran-viz-run
# ─────────────────────────────────────────────────────────────────────

import time
import json
import logging
from oran_viz import config
from oran_viz.influx_explorer   import get_client, discover_schema, schema_changed
from oran_viz.grafana_client    import is_reachable, get_datasource_uid, push_dashboard, post_annotation
from oran_viz.dashboard_builder import build_dashboard

# ── Logging setup ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.LOG_FILE)
    ]
)
log = logging.getLogger(__name__)


def _load_cached_schema() -> dict:
    if config.SCHEMA_CACHE.exists():
        with open(config.SCHEMA_CACHE) as f:
            return json.load(f)
    return {}


def _save_schema(schema: dict):
    with open(config.SCHEMA_CACHE, "w") as f:
        json.dump(schema, f, indent=2)


def run():
    log.info("═" * 52)
    log.info("  O-RAN Grafana Visualization Pipeline")
    log.info("═" * 52)

    # ── Health checks ─────────────────────────────────────────────────
    if not is_reachable():
        log.error(f"Grafana not reachable at {config.GRAFANA_URL}")
        log.error("Run: net start grafana")
        return

    ds_uid = get_datasource_uid(config.GRAFANA_DS_NAME)
    if not ds_uid:
        log.error(f"Datasource '{config.GRAFANA_DS_NAME}' not found in Grafana")
        log.error("Add it: Grafana → Connections → Data Sources → InfluxDB")
        return

    influx = get_client()
    log.info(f"Grafana OK       datasource UID: {ds_uid}")
    log.info(f"InfluxDB OK      {config.INFLUX_HOST}")

    # ── Initial discovery + dashboard push ────────────────────────────
    last_schema = _load_cached_schema()

    log.info("Running initial schema discovery...")
    start          = time.time()
    current_schema = discover_schema(influx)
    elapsed        = time.time() - start
    log.info(f"Schema discovery took {elapsed:.2f}s — "
             f"{len(current_schema)} measurement(s) found")

    if not current_schema:
        log.warning("No data found — run: oran-viz-populate")
    else:
        for m, info in current_schema.items():
            log.info(f"  • {m}  fields={info['fields']}  tags={info['tags']}")

        push_start = time.time()
        result     = push_dashboard(build_dashboard(current_schema, ds_uid))
        push_time  = time.time() - push_start
        log.info(f"Dashboard push took {push_time:.2f}s")
        log.info(f"Total initial latency: {elapsed + push_time:.2f}s")

        if result.get("status") == "success":
            log.info(f"Dashboard live → {config.GRAFANA_URL}{result.get('url')}")
        else:
            log.warning(f"Push response: {result}")

        _save_schema(current_schema)
        last_schema = current_schema

    # ── Polling loop ──────────────────────────────────────────────────
    log.info(f"Polling every {config.POLL_INTERVAL}s for schema changes...\n")

    while True:
        time.sleep(config.POLL_INTERVAL)
        try:
            # ── Measure schema discovery latency ──────────────────────
            start          = time.time()
            current_schema = discover_schema(influx)
            elapsed        = time.time() - start
            log.info(f"Schema discovery took {elapsed:.2f}s")

            if schema_changed(last_schema, current_schema):
                new_m = set(current_schema.keys()) - set(last_schema.keys())
                msg   = f"New: {new_m}" if new_m else "New fields or tags detected"
                log.info(f"Schema change — {msg}")
                post_annotation(f"Schema updated: {msg}")

                # ── Measure dashboard push latency ────────────────────
                push_start = time.time()
                result     = push_dashboard(build_dashboard(current_schema, ds_uid))
                push_time  = time.time() - push_start
                log.info(f"Dashboard push took  {push_time:.2f}s")
                log.info(f"Total update latency {elapsed + push_time:.2f}s")

                if result.get("status") == "success":
                    log.info(f"Dashboard regenerated → {config.GRAFANA_URL}{result.get('url')}")
                else:
                    log.warning(f"Push failed: {result}")

                _save_schema(current_schema)
                last_schema = current_schema

            else:
                log.info(f"No change — {len(current_schema)} measurements stable "
                         f"(discovery: {elapsed:.2f}s)")

        except Exception as e:
            log.error(f"Poll error: {e}")


if __name__ == "__main__":
    run()
