import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd

from vantage6.common.globals import ContainerEnvNames
from vantage6.algorithm.tools import wrapper

MODULE_NAME = "algorithm_module"
DATA = "column1,column2\n1,2"
TOKEN = "This is a fake token"
INPUT_PARAMETERS = {"method": "hello_world"}
SEPARATOR = "."
SAMPLE_DB = pd.DataFrame([[1, 2]], columns=["column1", "column2"])

MOCK_SPARQL_ENDPOINT = "sparql://some_triplestore"


# def test_json_input_without_format_raises_deserializationexception(tmp_path):
#     """
#     It should only be possible to provide json input if it is preceded by the
#     string "json." in unicode. Otherwise a `DeserializationException` should
#     be thrown.
#     """
#     input_file = tmp_path / 'input.json'

#     with input_file.open('wb') as f:
#         f.write(json.dumps(INPUT_PARAMETERS).encode())

#     with raises(DeserializationException):
#         run_docker_wrapper_with_echo_db(input_file, tmp_path)


# def test_json_input_with_format_succeeds(tmp_path):
#     input_file = tmp_path / 'input.txt'

#     with input_file.open('wb') as f:
#         f.write(json.dumps(INPUT_PARAMETERS).encode())

#     output_file = run_docker_wrapper_with_echo_db(input_file, tmp_path)
#     assert file_echoes_db(output_file)


# def test_wrapper_serializes_json_output(tmp_path):
#     input_parameters = {'method': 'hello_world', 'output_format': JSON_FORMAT}
#     input_file = create_pickle_input(tmp_path, input_parameters)

#     output_file = run_docker_wrapper_with_echo_db(input_file, tmp_path)

#     with output_file.open('rb') as f:
#         # Check whether the data is preceded by json format string
#         assert f.read(len(JSON_FORMAT) + 1).decode() == f'{JSON_FORMAT}.'

#         # Since the echo_db algorithm was triggered, output will be table that
#         # can be read by pandas.
#         result = pd.read_json(f.read())
#         pd.testing.assert_frame_equal(SAMPLE_DB, result)


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
    db_file = tmp_path / "db_file.csv"
    token_file = tmp_path / "token.txt"
    output_file = tmp_path / "output_file.pkl"
    db_file.write_text(DATA)
    token_file.write_text(TOKEN)
    with patch("vantage6.algorithm.tools.docker_wrapper.os") as mock_os:
        mock_os.environ = {
            ContainerEnvNames.INPUT_FILE.value: input_file,
            ContainerEnvNames.TOKEN_FILE.value: token_file,
            ContainerEnvNames.DATABASE_URI.value: db_file,
            ContainerEnvNames.OUTPUT_FILE.value: output_file,
        }

        wrapper.docker_wrapper(MODULE_NAME)
    return output_file


@patch("vantage6.algorithm.tools.wrap._run_algorithm_method")
@patch("vantage6.algorithm.tools.docker_wrapper.os")
@patch("vantage6.algorithm.tools.docker_wrapper.SPARQLWrapper")
def test_sparql_docker_wrapper_passes_dataframe(
    SPARQLWrapper: MagicMock,
    os: MagicMock,
    _run_algorithm_method: MagicMock,
    tmp_path: Path,
):
    input_file = tmp_path / "input_file.pkl"
    token_file = tmp_path / "token.txt"
    output_file = tmp_path / "output.pkl"

    environ = {
        ContainerEnvNames.INPUT_FILE.value: str(input_file),
        ContainerEnvNames.TOKEN_FILE.value: str(token_file),
        ContainerEnvNames.DATABASE_URI.value: MOCK_SPARQL_ENDPOINT,
        ContainerEnvNames.OUTPUT_FILE.value: str(output_file),
    }

    os.environ = environ

    input_args = {"query": "select *"}

    with input_file.open("wb") as f:
        json.dumps(input_args, f)

    with token_file.open("w") as f:
        f.write(TOKEN)

    _run_algorithm_method.return_value = pd.DataFrame()
    SPARQLWrapper.return_value.query.return_value.convert.return_value = DATA.encode()

    wrapper.sparql_wrapper(MODULE_NAME)

    _run_algorithm_method.assert_called_once()

    target_df = pd.DataFrame([[1, 2]], columns=["column1", "column2"])
    pd.testing.assert_frame_equal(target_df, _run_algorithm_method.call_args[0][0])
