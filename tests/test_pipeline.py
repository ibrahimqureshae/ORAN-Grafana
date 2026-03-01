import json

import pytest

from oran_viz import pipeline


def test_run_exits_when_grafana_unreachable(monkeypatch):
    called = {"get_client": 0}

    monkeypatch.setattr(pipeline, "is_reachable", lambda: False)
    monkeypatch.setattr(
        pipeline,
        "get_client",
        lambda: called.__setitem__("get_client", called["get_client"] + 1),
    )

    pipeline.run()

    assert called["get_client"] == 0


def test_run_exits_when_datasource_missing(monkeypatch):
    called = {"get_client": 0}

    monkeypatch.setattr(pipeline, "is_reachable", lambda: True)
    monkeypatch.setattr(pipeline, "get_datasource_uid", lambda _: None)
    monkeypatch.setattr(
        pipeline,
        "get_client",
        lambda: called.__setitem__("get_client", called["get_client"] + 1),
    )

    pipeline.run()

    assert called["get_client"] == 0


def test_run_pushes_initial_dashboard_and_saves_schema(monkeypatch, tmp_path):
    schema = {"model_training": {"fields": ["loss"], "tags": ["model_name"]}}
    calls = {"build": 0, "push": 0}

    monkeypatch.setattr(pipeline, "is_reachable", lambda: True)
    monkeypatch.setattr(pipeline, "get_datasource_uid", lambda _: "ds-123")
    monkeypatch.setattr(pipeline, "get_client", lambda: object())
    monkeypatch.setattr(pipeline, "discover_schema", lambda _: schema)
    monkeypatch.setattr(pipeline, "build_dashboard", lambda s, d: calls.__setitem__("build", calls["build"] + 1) or {"panels": [], "schema": s, "ds": d})
    monkeypatch.setattr(pipeline, "push_dashboard", lambda _: calls.__setitem__("push", calls["push"] + 1) or {"status": "success", "url": "/d/test"})
    monkeypatch.setattr(pipeline.config, "GRAFANA_URL", "http://grafana.local")

    cache_file = tmp_path / "last_schema.json"
    monkeypatch.setattr(pipeline.config, "SCHEMA_CACHE", cache_file)

    def stop_after_first_sleep(_seconds):
        raise KeyboardInterrupt("stop loop")

    monkeypatch.setattr(pipeline.time, "sleep", stop_after_first_sleep)

    with pytest.raises(KeyboardInterrupt):
        pipeline.run()

    assert calls["build"] == 1
    assert calls["push"] == 1
    assert cache_file.exists()
    assert json.loads(cache_file.read_text()) == schema
