import pandas as pd

from oran_viz import influx_explorer as explorer


class _FakeQueryResult:
    def __init__(self, frame):
        self._frame = frame

    def to_pandas(self):
        return self._frame


class _FakeClient:
    def __init__(self, responses):
        self._responses = responses

    def query(self, sql):
        for marker, value in self._responses.items():
            if marker in sql:
                return value
        return None


def test_discover_schema_returns_fields_and_tags():
    tables_df = pd.DataFrame({"table_name": ["model_training", "resource_usage", "model_training"]})

    model_cols = pd.DataFrame(
        {
            "column_name": ["time", "model_name", "accuracy", "loss"],
            "data_type": [
                "Timestamp(Nanosecond, None)",
                "Utf8",
                "Float64",
                "Float64",
            ],
        }
    )

    resource_cols = pd.DataFrame(
        {
            "column_name": ["time", "node_id", "cpu_percent"],
            "data_type": [
                "Timestamp(Nanosecond, None)",
                "Dictionary(Int32, Utf8)",
                "Float64",
            ],
        }
    )

    client = _FakeClient(
        {
            "FROM information_schema.tables": _FakeQueryResult(tables_df),
            "table_name   = 'model_training'": _FakeQueryResult(model_cols),
            "table_name   = 'resource_usage'": _FakeQueryResult(resource_cols),
        }
    )

    schema = explorer.discover_schema(client)

    assert schema == {
        "model_training": {"fields": ["accuracy", "loss"], "tags": ["model_name"]},
        "resource_usage": {"fields": ["cpu_percent"], "tags": ["node_id"]},
    }


def test_discover_schema_handles_missing_tables_result():
    client = _FakeClient({"FROM information_schema.tables": None})
    assert explorer.discover_schema(client) == {}


def test_schema_changed_simple_comparison():
    old = {"m": {"fields": ["a"], "tags": []}}
    new = {"m": {"fields": ["a", "b"], "tags": []}}

    assert explorer.schema_changed(old, new) is True
    assert explorer.schema_changed(old, old) is False
