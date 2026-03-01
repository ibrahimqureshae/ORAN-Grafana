# ─────────────────────────────────────────────────────────────────────
# config.py
# Reads all configuration from the .env file in the project root.
# Never hardcode tokens — always use environment variables.
# ─────────────────────────────────────────────────────────────────────

import pathlib
import os
from dotenv import load_dotenv

load_dotenv()

# ── InfluxDB 3 ────────────────────────────────────────────────────────
INFLUX_HOST  = os.getenv("INFLUX_HOST",  "http://localhost:8181")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_DB    = os.getenv("INFLUX_DB",    "oran_aiml")

# ── Grafana ───────────────────────────────────────────────────────────
GRAFANA_URL     = os.getenv("GRAFANA_URL",     "http://localhost:3000")
GRAFANA_TOKEN   = os.getenv("GRAFANA_TOKEN",   "")
GRAFANA_DS_NAME = os.getenv("GRAFANA_DS_NAME", "InfluxDB-ORAN")

# ── Pipeline ──────────────────────────────────────────────────────────
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 30))

# ── Paths ─────────────────────────────────────────────────────────────
ROOT_DIR     = pathlib.Path(__file__).parent.parent.parent  # G:/oran_viz
DATA_DIR     = ROOT_DIR / "data"
SCHEMA_CACHE = DATA_DIR / "last_schema.json"
LOG_FILE     = DATA_DIR / "pipeline.log"

# Ensure data/ folder always exists when config is imported
DATA_DIR.mkdir(exist_ok=True)
