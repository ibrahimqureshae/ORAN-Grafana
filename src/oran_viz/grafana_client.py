# ─────────────────────────────────────────────────────────────────────
# grafana_client.py
# Handles all HTTP communication with the Grafana REST API.
# ─────────────────────────────────────────────────────────────────────

import time
import requests
from oran_viz import config

HEADERS = {
    "Authorization": f"Bearer {config.GRAFANA_TOKEN}",
    "Content-Type":  "application/json"
}


def is_reachable() -> bool:
    """Checks if Grafana is running before the pipeline starts."""
    try:
        r = requests.get(f"{config.GRAFANA_URL}/api/health", timeout=5)
        return r.status_code == 200
    except requests.ConnectionError:
        return False


def get_datasource_uid(name: str) -> str | None:
    """
    Fetches the internal UID of a Grafana datasource by its display name.
    Every dashboard panel must reference this UID to know which database
    to query.
    """
    r = requests.get(
        f"{config.GRAFANA_URL}/api/datasources/name/{name}",
        headers=HEADERS
    )
    if r.status_code == 200:
        return r.json().get("uid")
    print(f"⚠️  Datasource '{name}' not found — status {r.status_code}")
    return None


def push_dashboard(dashboard_json: dict) -> dict:
    """
    Creates or fully replaces a dashboard via the Grafana REST API.
    'overwrite: true' replaces the existing dashboard with the same UID
    instead of creating a duplicate.
    """
    payload = {
        "dashboard": dashboard_json,
        "overwrite": True,
        "folderId":  0,
        "message":   "Auto-updated by oran-viz pipeline"
    }
    r = requests.post(
        f"{config.GRAFANA_URL}/api/dashboards/db",
        headers=HEADERS,
        json=payload
    )
    return r.json()


def post_annotation(text: str) -> dict:
    """
    Stamps a vertical marker line on the dashboard at the current time.
    Used to mark the exact moment a schema change was detected.
    """
    payload = {
        "dashboardUID": "oran-aiml-auto",
        "time":         int(time.time() * 1000),
        "isRegion":     False,
        "tags":         ["schema-change", "auto"],
        "text":         text
    }
    r = requests.post(
        f"{config.GRAFANA_URL}/api/annotations",
        headers=HEADERS,
        json=payload
    )
    return r.json()
