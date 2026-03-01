# O-RAN Grafana Visualization Pipeline

[![CI](https://github.com/ibrahimqureshae/ORAN-Grafana/actions/workflows/ci.yml/badge.svg)](https://github.com/ibrahimqureshae/ORAN-Grafana/actions/workflows/ci.yml)

**Auto-generates and continuously updates Grafana dashboards from InfluxDB 3 O-RAN AI/ML data.**

This project is completely open source and available under the MIT License.

No hardcoded field names. Schema is discovered at runtime using `information_schema` queries. Dashboard regenerates whenever measurements, fields, or tags change.

---

## Architecture

```
┌─────────────┐    
│  InfluxDB 3 │    
│ information_│ ◄──┐ (measure/field discovery)
│  _schema    │    │
└─────────────┘    │
                   │
              ┌────┴─────────────────────┐
              │                          │
              │  oran-viz-run            │  oran-viz-populate
              │  (main pipeline)         │  (test data seeder)
              │                          │
              │ • Discover schema        │  • Batch backfill
              │ • Build dashboard JSON   │    30 min history
              │ • Poll every 30s         │
              │ • Post annotations       │  • Stream live 2s
              │   on schema change       │    intervals
              │                          │
              └────┬─────────────────────┘
                   │ (push dashboard)
                   │ (get datasource UID)
                   ▼
              ┌─────────────┐
              │   Grafana   │
              │  Dashboard  │
              └─────────────┘
```

### Modules

| Module | Purpose |
|--------|---------|
| `config.py` | Loads all env vars (InfluxDB host/token, Grafana URL/token, poll interval) |
| `influx_explorer.py` | Queries `information_schema` to discover measurements, fields, and tags |
| `dashboard_builder.py` | Generates Grafana dashboard JSON with stat panels (latest value), timeseries (trends), and table panels (raw rows) |
| `grafana_client.py` | HTTP wrapper for Grafana REST API (health, datasource UID, dashboard push, annotations) |
| `pipeline.py` | Main orchestrator — starts health checks, discovers schema, builds/pushes dashboard, then polls for schema changes every 30s |
| `dummy_data.py` | Generates realistic O-RAN telemetry (model training, inference, resource usage, RIC policy stats) |

---

## Setup

### Requirements
- Python ≥ 3.10
- InfluxDB 3 (running at `http://localhost:8181` by default)
- Grafana (running at `http://localhost:3000` by default)
- An InfluxDB datasource configured in Grafana

### Install Dependencies

```bash
# Activate virtual environment (if using one)
source oral_env/bin/activate  # Linux/macOS
# or
.\oral_env\Scripts\Activate.ps1  # Windows PowerShell

# Install package in editable mode
pip install -e .
```

### Environment Variables

Create a `.env` file in the project root:

```env
# InfluxDB 3
INFLUX_HOST=http://localhost:8181
INFLUX_TOKEN=your-influxdb-token
INFLUX_DB=oran_aiml

# Grafana
GRAFANA_URL=http://localhost:3000
GRAFANA_TOKEN=your-grafana-api-token
GRAFANA_DS_NAME=InfluxDB-ORAN

# Pipeline polling interval (seconds)
POLL_INTERVAL=30
```

**To obtain tokens:**

1. **InfluxDB Token**: GUI → Data → API Tokens → Generate API Token
2. **Grafana Token**: GUI → Administration → API Keys → New API Key (give Admin role)
3. **InfluxDB Datasource in Grafana**: GUI → Connections → Data Sources → InfluxDB → configure with your host, token, and database name
   - The name you choose in Grafana must match `GRAFANA_DS_NAME` in `.env`

---

## Usage

### 1. Seed Test Data

Writes 30 minutes of historical O-RAN AI/ML metrics + streams live data every 2 seconds.

```bash
oran-viz-populate
```

**Output:**
```
📦 Collecting 30 minutes of historical data...
   → 3240 records ready — sending in one batch write...
✅ Historical data written!

🔴 Writing live data every 2 seconds — Ctrl+C to stop

[14:32:15] 9 records | cpu≈65% loss≈0.234 lat≈13.2ms
[14:32:17] 9 records | cpu≈67% loss≈0.210 lat≈12.1ms
[14:32:19] 9 records | cpu≈68% loss≈0.198 lat≈13.5ms
```

**Leave running** in a separate terminal while you use the pipeline.

### 2. Start the Pipeline

Discovers schema, builds dashboard, pushes to Grafana, then polls every 30s for schema changes.

```bash
oran-viz-run
```

**Output:**
```
════════════════════════════════════════════════════════
  O-RAN Grafana Visualization Pipeline
════════════════════════════════════════════════════════
Grafana OK       datasource UID: fbz6LDZnz
InfluxDB OK      http://localhost:8181
Running initial schema discovery...
Schema discovery took 0.38s — 4 measurement(s) found
  • model_training        fields=4  tags=2
  • inference_metrics     fields=3  tags=2
  • resource_usage        fields=3  tags=1
  • ric_policy_stats      fields=3  tags=1
Dashboard push took 0.24s
Total initial latency: 0.62s
Dashboard live → http://localhost:3000/d/oran-aiml-auto/o-ran-aiml-auto-dashboard
Polling every 30s for schema changes...

Schema discovery took 0.36s
No change — 4 measurements stable (discovery: 0.36s)

Schema discovery took 0.37s
No change — 4 measurements stable (discovery: 0.37s)
```

**Dashboard is now live**. Open your browser to the printed Grafana URL.

---

## Expected Dashboard

The auto-generated dashboard includes:

### Layout (per measurement)
1. **Stat Panels** (4 per row, 6 units wide each)
   - Shows **latest value** of each field
   - Auto-colored by value vs. min/max bounds
   - Examples: `Latest › loss`, `Latest › accuracy`, `Latest › latency_ms`

2. **Timeseries Panels** (2 per row, 12 units wide each)
   - Line chart of mean values over time
   - Auto-binned to Grafana's interval (e.g., 10s, 1m)
   - Examples: `model_training › loss`, `inference_metrics › latency_ms`

3. **Table Panel** (full width)
   - Most recent 100 rows of the measurement
   - All fields + tags visible

### Unit Auto-Detection
Field names containing keywords auto-apply Grafana units:
- `percent` → 0–100% scale
- `_ms` / `latency` → milliseconds
- `_mb` / `memory` → megabytes (decimal)
- `accuracy`, `score`, `rate` → 0.0–1.0 scale (percentunit)

Example: `cpu_percent` will display as "65%" with 0–100 bounds.

---

## Schema Change Detection

When new measurements or fields appear in InfluxDB:

1. **Pipeline detects** via `information_schema` query
2. **Schema cached** to `data/last_schema.json` for comparison
3. **Dashboard rebuilt** immediately with new panels
4. **Pushed to Grafana** with `overwrite: true`
5. **Annotation posted** on dashboard with timestamp and change description

Example log:
```
Schema discovery took 0.42s
Schema change — New: {'new_measurement'}
Dashboard push took 0.31s
Total update latency 0.73s
Dashboard regenerated → http://localhost:3000/d/oran-aiml-auto/o-ran-aiml-auto-dashboard
```

---

## Development & Logging

Logs are written to **both** stdout and `data/pipeline.log`.

```bash
# Watch logs in real-time
tail -f data/pipeline.log  # Linux/macOS
Get-Content data/pipeline.log -Wait  # Windows PowerShell
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Grafana not reachable` | Ensure Grafana is running (`docker run grafana/grafana` or `net start grafana`) |
| `Datasource 'X' not found` | Configure the datasource in Grafana GUI and verify `GRAFANA_DS_NAME` in `.env` matches exactly |
| `No data found — run: oran-viz-populate` | Start `oran-viz-populate` in another terminal to seed test data |
| `Dashboard doesn't appear` | Check `GRAFANA_TOKEN` is valid (Admin role required) and Grafana logs for 401/403 errors |
| `INFLUX_TOKEN empty` | Run `cat .env` to verify token is set; if missing, set it and restart `oran-viz-run` |

---

## License

MIT — see [LICENSE](LICENSE) for details.
