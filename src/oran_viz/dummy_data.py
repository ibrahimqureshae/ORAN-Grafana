# ─────────────────────────────────────────────────────────────────────
# dummy_data.py
# Writes realistic O-RAN AI/ML data into InfluxDB.
# CLI entry point: oran-viz-populate
# ─────────────────────────────────────────────────────────────────────

import time
import random
import math
from datetime import datetime, timezone, timedelta
from influxdb_client_3 import InfluxDBClient3
from oran_viz import config


def _get_client() -> InfluxDBClient3:
    return InfluxDBClient3(
        host=config.INFLUX_HOST,
        token=config.INFLUX_TOKEN,
        database=config.INFLUX_DB
    )


def _make_line(measurement, tags, fields, timestamp) -> str:
    """
    Builds an InfluxDB line protocol string without writing it.
    Collecting lines into a list then writing in one batch is far
    faster than writing one point per HTTP call.
    """
    tag_str   = ",".join(f"{k}={v}"  for k, v in tags.items())
    field_str = ",".join(f"{k}={v}"  for k, v in fields.items())
    ts_ns     = int(timestamp.timestamp() * 1_000_000_000)
    return f"{measurement},{tag_str} {field_str} {ts_ns}"


def _make_model_training(ts, epoch) -> list:
    records = []
    for model in ["resnet50", "transformer_v1", "lstm_baseline"]:
        loss     = max(0.05, math.exp(-0.03 * epoch) + random.uniform(-0.02, 0.02))
        val_loss = max(0.08, loss + random.uniform(0.01, 0.05))
        accuracy = min(0.99, 1 - loss + random.uniform(-0.01, 0.01))
        lr       = 0.001 * (0.95 ** (epoch // 10))
        records.append(_make_line(
            "model_training",
            {"model_name": model, "experiment_id": "exp_001"},
            {
                "loss":          round(loss, 4),
                "val_loss":      round(val_loss, 4),
                "accuracy":      round(accuracy, 4),
                "learning_rate": round(lr, 6)
            },
            ts
        ))
    return records


def _make_inference_metrics(ts) -> list:
    records = []
    for endpoint in ["endpoint_A", "endpoint_B"]:
        spike = 50 if random.random() < 0.05 else 0
        records.append(_make_line(
            "inference_metrics",
            {"endpoint": endpoint, "model_version": "v2.1"},
            {
                "latency_ms":       round(max(1.0, random.gauss(12, 2) + spike), 2),
                "throughput":       round(max(0.0, random.gauss(200, 15)), 1),
                "confidence_score": round(random.uniform(0.75, 0.99), 3)
            },
            ts
        ))
    return records


def _make_resource_usage(ts) -> list:
    records = []
    for node in ["node_1", "node_2"]:
        records.append(_make_line(
            "resource_usage",
            {"node_id": node},
            {
                "cpu_percent":     round(random.uniform(40, 95), 1),
                "memory_mb":       round(random.uniform(4000, 16000), 1),
                "gpu_utilization": round(random.uniform(60, 100), 1)
            },
            ts
        ))
    return records


def _make_ric_policy_stats(ts) -> list:
    return [_make_line(
        "ric_policy_stats",
        {"ric_instance": "nonrtric_1"},
        {
            "active_policies":   float(random.randint(3, 10)),
            "policy_violations": float(random.randint(0, 3)),
            "enforcement_rate":  round(random.uniform(0.85, 1.0), 3)
        },
        ts
    )]


def main():
    client = _get_client()

    # ── Phase 1: Batch backfill last 30 minutes ───────────────────────
    print("📦 Collecting 30 minutes of historical data...")
    now     = datetime.now(timezone.utc)
    current = now - timedelta(minutes=30)
    epoch   = 0
    batch   = []

    while current <= now:
        batch += _make_model_training(current, epoch)
        batch += _make_inference_metrics(current)
        batch += _make_resource_usage(current)
        batch += _make_ric_policy_stats(current)
        current += timedelta(seconds=30)
        epoch   += 1

    print(f"   → {len(batch)} records ready — sending in one batch write...")
    client.write(record=batch, database=config.INFLUX_DB)
    print("✅ Historical data written!\n")

    # ── Phase 2: Live data every 2 seconds ────────────────────────────
    print("🔴 Writing live data every 2 seconds — Ctrl+C to stop\n")

    cpu_drift  = 60.0
    loss_drift = 0.8
    lat_drift  = 12.0

    while True:
        now    = datetime.now(timezone.utc)
        epoch += 1

        cpu_drift  = max(20,   min(95,   cpu_drift  + random.uniform(-3, 3)))
        loss_drift = max(0.05, min(0.95, loss_drift + random.uniform(-0.03, 0.03)))
        lat_drift  = max(2,    min(80,   lat_drift  + random.uniform(-2, 2)))

        live = []

        for model in ["resnet50", "transformer_v1", "lstm_baseline"]:
            loss     = max(0.05, loss_drift + random.uniform(-0.05, 0.05))
            val_loss = max(0.08, loss + random.uniform(0.01, 0.05))
            accuracy = min(0.99, 1 - loss + random.uniform(-0.01, 0.01))
            lr       = 0.001 * (0.95 ** (epoch // 10))
            live.append(_make_line(
                "model_training",
                {"model_name": model, "experiment_id": "exp_001"},
                {
                    "loss":          round(loss, 4),
                    "val_loss":      round(val_loss, 4),
                    "accuracy":      round(accuracy, 4),
                    "learning_rate": round(lr, 6)
                },
                now
            ))

        for endpoint in ["endpoint_A", "endpoint_B"]:
            spike = 40 if random.random() < 0.08 else 0
            live.append(_make_line(
                "inference_metrics",
                {"endpoint": endpoint, "model_version": "v2.1"},
                {
                    "latency_ms":       round(max(1.0, lat_drift + random.uniform(-3, 3) + spike), 2),
                    "throughput":       round(max(0.0, random.gauss(200, 20)), 1),
                    "confidence_score": round(random.uniform(0.70, 0.99), 3)
                },
                now
            ))

        for node in ["node_1", "node_2"]:
            live.append(_make_line(
                "resource_usage",
                {"node_id": node},
                {
                    "cpu_percent":     round(max(5, min(100, cpu_drift + random.uniform(-5, 5))), 1),
                    "memory_mb":       round(random.uniform(4000, 16000), 1),
                    "gpu_utilization": round(max(10, min(100, cpu_drift * 1.1 + random.uniform(-4, 4))), 1)
                },
                now
            ))

        live.append(_make_line(
            "ric_policy_stats",
            {"ric_instance": "nonrtric_1"},
            {
                "active_policies":   float(random.randint(3, 10)),
                "policy_violations": float(random.randint(0, 3)),
                "enforcement_rate":  round(random.uniform(0.80, 1.0), 3)
            },
            now
        ))

        client.write(record=live, database=config.INFLUX_DB)
        print(f"[{now.strftime('%H:%M:%S')}] {len(live)} records "
              f"| cpu≈{cpu_drift:.0f}% loss≈{loss_drift:.3f} lat≈{lat_drift:.1f}ms")
        time.sleep(2)


if __name__ == "__main__":
    main()
