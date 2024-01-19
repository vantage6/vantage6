from pathlib import Path
from vantage6.common.client import deserialization

SIMPLE_TARGET_DATA = {"key": "value"}


def test_deserialize_json(tmp_path: Path):
    data = '{"key": "value"}'
    json_path = tmp_path / "jsonfile.json"
    json_path.write_text(data)

    with json_path.open("r") as f:
        result = deserialization.deserialize(f)

        assert SIMPLE_TARGET_DATA == result
