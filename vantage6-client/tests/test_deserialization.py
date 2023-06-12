import pickle
from pathlib import Path
from vantage6.tools import deserialization
from vantage6.tools.data_format import DataFormat

SIMPLE_TARGET_DATA = {'key': 'value'}


def test_deserialize_json(tmp_path: Path):
    data = '{"key": "value"}'
    json_path = tmp_path / 'jsonfile.json'
    json_path.write_text(data)

    with json_path.open('r') as f:
        result = deserialization.deserialize(f, DataFormat.JSON)

        assert SIMPLE_TARGET_DATA == result


def test_deserialize_pickle(tmp_path: Path):
    data = {'key': 'value'}

    pickle_path = tmp_path / 'picklefile.pkl'

    with pickle_path.open('wb') as f:
        pickle.dump(data, f)

    with pickle_path.open('rb') as f:
        result = deserialization.deserialize(f, DataFormat.PICKLE)
        assert SIMPLE_TARGET_DATA == result
