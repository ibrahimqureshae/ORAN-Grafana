import requests

from oran_viz import grafana_client as client


class _Response:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def test_is_reachable_true(monkeypatch):
    monkeypatch.setattr(client.config, "GRAFANA_URL", "http://grafana.local")

    def fake_get(url, timeout):
        assert url == "http://grafana.local/api/health"
        assert timeout == 5
        return _Response(200)

    monkeypatch.setattr(client.requests, "get", fake_get)
    assert client.is_reachable() is True


def test_is_reachable_connection_error(monkeypatch):
    def fake_get(url, timeout):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(client.requests, "get", fake_get)
    assert client.is_reachable() is False


def test_get_datasource_uid(monkeypatch):
    monkeypatch.setattr(client.config, "GRAFANA_URL", "http://grafana.local")

    def fake_get(url, headers):
        assert url.endswith("/api/datasources/name/InfluxDB-ORAN")
        assert "Authorization" in headers
        return _Response(200, {"uid": "uid-123"})

    monkeypatch.setattr(client.requests, "get", fake_get)
    assert client.get_datasource_uid("InfluxDB-ORAN") == "uid-123"


def test_push_dashboard_payload(monkeypatch):
    monkeypatch.setattr(client.config, "GRAFANA_URL", "http://grafana.local")
    captured = {}

    def fake_post(url, headers, json):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _Response(200, {"status": "success", "url": "/d/test"})

    monkeypatch.setattr(client.requests, "post", fake_post)

    dashboard = {"uid": "x", "title": "t", "panels": []}
    result = client.push_dashboard(dashboard)

    assert result["status"] == "success"
    assert captured["url"].endswith("/api/dashboards/db")
    assert captured["json"]["dashboard"] == dashboard
    assert captured["json"]["overwrite"] is True


def test_post_annotation_payload(monkeypatch):
    monkeypatch.setattr(client.config, "GRAFANA_URL", "http://grafana.local")
    monkeypatch.setattr(client.time, "time", lambda: 1700000000.0)
    captured = {}

    def fake_post(url, headers, json):
        captured["url"] = url
        captured["json"] = json
        return _Response(200, {"id": 42})

    monkeypatch.setattr(client.requests, "post", fake_post)

    result = client.post_annotation("Schema updated")

    assert result == {"id": 42}
    assert captured["url"].endswith("/api/annotations")
    assert captured["json"]["dashboardUID"] == "oran-aiml-auto"
    assert captured["json"]["time"] == 1700000000000
    assert captured["json"]["text"] == "Schema updated"
