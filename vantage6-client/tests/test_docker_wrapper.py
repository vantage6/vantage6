import json
import pickle
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
from pytest import raises

from vantage6.tools import docker_wrapper
from vantage6.tools.exceptions import DeserializationException

MODULE_NAME = 'algorithm_module'
DATA = 'column1,column2\n1,2'
TOKEN = 'This is a fake token'
INPUT_PARAMETERS = {'method': 'hello_world'}
JSON_FORMAT = 'json'
SEPARATOR = '.'
SAMPLE_DB = pd.DataFrame([[1, 2]], columns=['column1', 'column2'])
PICKLE_FORMAT = 'pickle'

MOCK_SPARQL_ENDPOINT = 'sparql://some_triplestore'


def test_old_pickle_input_wrapper(tmp_path):
    """
    Testing if wrapper still parses legacy input.
    """
    input_file = tmp_path / 'input.pkl'

    with input_file.open('wb') as f:
        pickle.dump(INPUT_PARAMETERS, f)

    output_file = run_docker_wrapper_with_echo_db(input_file, tmp_path)
    assert file_echoes_db(output_file)


def test_json_input_without_format_raises_deserializationexception(tmp_path):
    """
    It should only be possible to provide json input if it is preceded by the
    string "json." in unicode. Otherwise a `DeserializationException` should
    be thrown.
    """
    input_file = tmp_path / 'input.json'

    with input_file.open('wb') as f:
        f.write(json.dumps(INPUT_PARAMETERS).encode())

    with raises(DeserializationException):
        run_docker_wrapper_with_echo_db(input_file, tmp_path)


def test_json_input_with_format_succeeds(tmp_path):
    input_file = tmp_path / 'input.txt'

    with input_file.open('wb') as f:
        f.write(f'JSON{SEPARATOR}'.encode())
        f.write(json.dumps(INPUT_PARAMETERS).encode())

    output_file = run_docker_wrapper_with_echo_db(input_file, tmp_path)
    assert file_echoes_db(output_file)


def test_pickle_input_with_format_succeeds(tmp_path):
    input_file = create_pickle_input(tmp_path)
    output_file = run_docker_wrapper_with_echo_db(input_file, tmp_path)
    assert file_echoes_db(output_file)


def test_wrapper_serializes_pickle_output(tmp_path):
    input_parameters = {
        'method': 'hello_world',
        'output_format': PICKLE_FORMAT
    }
    input_file = create_pickle_input(tmp_path, input_parameters)

    output_file = run_docker_wrapper_with_echo_db(input_file, tmp_path)

    with output_file.open('rb') as f:
        # Check whether the output starts with `pickle.` to indicate the pickle
        # data format
        assert f.read(len(PICKLE_FORMAT) + 1).decode() == f'{PICKLE_FORMAT}.'

        result = pickle.loads(f.read())
        pd.testing.assert_frame_equal(SAMPLE_DB, result)


def test_wrapper_serializes_json_output(tmp_path):
    input_parameters = {'method': 'hello_world', 'output_format': JSON_FORMAT}
    input_file = create_pickle_input(tmp_path, input_parameters)

    output_file = run_docker_wrapper_with_echo_db(input_file, tmp_path)

    with output_file.open('rb') as f:
        # Check whether the data is preceded by json format string
        assert f.read(len(JSON_FORMAT) + 1).decode() == f'{JSON_FORMAT}.'

        # Since the echo_db algorithm was triggered, output will be table that
        # can be read by pandas.
        result = pd.read_json(f.read())
        pd.testing.assert_frame_equal(SAMPLE_DB, result)


def create_pickle_input(tmp_path, input_parameters=None):
    if input_parameters is None:
        input_parameters = INPUT_PARAMETERS

    input_file = tmp_path / 'input.pkl'
    with input_file.open('wb') as f:
        f.write(f'PICKLE{SEPARATOR}'.encode())
        f.write(pickle.dumps(input_parameters))
    return input_file


def file_echoes_db(output_file):
    with output_file.open('rb') as f:
        result = pickle.load(f)
        target = SAMPLE_DB

        return target.equals(result)


def run_docker_wrapper_with_echo_db(input_file, tmp_path):
    """
    Run the `echo_db` testing algorithm through the wrapper code. The wrapper
    communicates through files whose locations are stored in the `INPUT_FILE`,
    `TOKEN_FILE` and `DATABASE_URI` environment variables. The output of the
    algorithm is stored in the location specified in environment variable
    `OUTPUT_FILE`.

    :param input_file: input arguments to the wrapper and algorithm
    :param tmp_path: temporary path to store additional files.
    :return:
    """
    db_file = tmp_path / 'db_file.csv'
    token_file = tmp_path / 'token.txt'
    output_file = tmp_path / 'output_file.pkl'
    db_file.write_text(DATA)
    token_file.write_text(TOKEN)
    with patch('vantage6.tools.docker_wrapper.os') as mock_os:
        mock_os.environ = {
            'INPUT_FILE': input_file,
            'TOKEN_FILE': token_file,
            'OUTPUT_FILE': output_file,
            'DATABASE_URI': db_file
        }

        docker_wrapper.docker_wrapper(MODULE_NAME)
    return output_file


@patch('vantage6.tools.docker_wrapper.dispatch_rpc')
@patch('vantage6.tools.docker_wrapper.os')
@patch('vantage6.tools.docker_wrapper.SPARQLWrapper')
def test_sparql_docker_wrapper_passes_dataframe(
    SPARQLWrapper: MagicMock, os: MagicMock, dispatch_rpc: MagicMock,
    tmp_path: Path
):
    input_file = tmp_path / 'input_file.pkl'
    token_file = tmp_path / 'token.txt'
    output_file = tmp_path / 'output.pkl'

    environ = {'INPUT_FILE': str(input_file),
               'TOKEN_FILE': str(token_file),
               'DATABASE_URI': MOCK_SPARQL_ENDPOINT,
               'OUTPUT_FILE': str(output_file)}

    os.environ = environ

    input_args = {'query': 'select *'}

    with input_file.open('wb') as f:
        pickle.dump(input_args, f)

    with token_file.open('w') as f:
        f.write(TOKEN)

    dispatch_rpc.return_value = pd.DataFrame()
    SPARQLWrapper.return_value.query.return_value.convert.return_value = \
        DATA.encode()

    docker_wrapper.sparql_wrapper(MODULE_NAME)

    dispatch_rpc.assert_called_once()

    target_df = pd.DataFrame([[1, 2]], columns=['column1', 'column2'])
    pd.testing.assert_frame_equal(target_df, dispatch_rpc.call_args[0][0])
