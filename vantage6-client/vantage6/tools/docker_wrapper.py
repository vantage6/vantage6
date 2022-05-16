"""
Docker Wrapper

This module contains the `docker_wrapper` function for providing vantage6
algorithms with uniform input and output handling.
"""

import os
import pickle
import io
from abc import ABC, abstractmethod
import pandas

from vantage6.tools.dispatch_rpc import dispact_rpc
from vantage6.tools.util import info
from vantage6.tools import deserialization, serialization
from vantage6.tools.data_format import DataFormat
from vantage6.tools.exceptions import DeserializationException
from SPARQLWrapper import SPARQLWrapper, CSV
from typing import BinaryIO

_DATA_FORMAT_SEPARATOR = '.'
_MAX_FORMAT_STRING_LENGTH = 10

_SPARQL_RETURN_FORMAT = CSV


def docker_wrapper(module: str):
    wrapper = DockerWrapper()
    wrapper.wrap_algorithm(module)


def sparql_wrapper(module: str):
    wrapper = SparqlDockerWrapper()
    wrapper.wrap_algorithm(module)


class WrapperBase(ABC):

    def wrap_algorithm(self, module):
        """
            Wrap an algorithm module to provide input and output handling for the
            vantage6 infrastructure.

            Data is received in the form of files, whose location should be specified
            in the following environment variables:
            - `INPUT_FILE`: input arguments for the algorithm
            - `OUTPUT_FILE`: location where the results of the algorithm should be
              stored
            - `TOKEN_FILE`: access token for the vantage6 server REST api
            - `DATABASE_URI`: either a database endpoint or path to a csv file.

            The wrapper is able to parse a number of input file formats. The available
            formats can be found in `vantage6.tools.data_format.DataFormat`. When the
            input is not pickle (legacy), the format should be specified in the first
            bytes of the input file, followed by a '.'.

            It is also possible to specify the desired output format. This is done by
            including the parameter 'output_format' in the input parameters. Again, the
            list of possible output formats can be found in
            `vantage6.tools.data_format.DataFormat`.

            It is still possible that output serialization will fail even if the
            specified format is listed in the DataFormat enum. Algorithms can in
            principle return any python object, but not every serialization format will
            support arbitrary python objects. When dealing with unsupported algorithm
            output, the user should use 'pickle' as output format, which is the
            default.

            The other serialization formats support the following algorithm output:
            - built-in primitives (int, float, str, etc.)
            - built-in collections (list, dict, tuple, etc.)
            - pandas DataFrames

            :param module: module that contains the vantage6 algorithms
            :return:
            """
        info(f"wrapper for {module}")

        # read input from the mounted inputfile.
        input_file = os.environ["INPUT_FILE"]
        info(f"Reading input file {input_file}")

        input_data = load_input(input_file)

        # all containers receive a token, however this is usually only
        # used by the master method. But can be used by regular containers also
        # for example to find out the node_id.
        token_file = os.environ["TOKEN_FILE"]
        info(f"Reading token file '{token_file}'")
        with open(token_file) as fp:
            token = fp.read().strip()

        database_uri = os.environ["DATABASE_URI"]
        info(f"Using '{database_uri}' as database")
        # with open(data_file, "r") as fp:
        data = self.load_data(database_uri, input_data)

        # make the actual call to the method/function
        info("Dispatching ...")
        output = dispact_rpc(data, input_data, module, token)

        # write output from the method to mounted output file. Which will be
        # transfered back to the server by the node-instance.
        output_file = os.environ["OUTPUT_FILE"]
        info(f"Writing output to {output_file}")

        output_format = input_data.get('output_format', None)
        write_output(output_format, output, output_file)

    @staticmethod
    @abstractmethod
    def load_data(database_uri, input_data):
        pass


class DockerWrapper(WrapperBase):
    @staticmethod
    def load_data(database_uri, input_data):
        return pandas.read_csv(database_uri)


class SparqlDockerWrapper(WrapperBase):
    @staticmethod
    def load_data(database_uri, input_data):
        query = input_data['query']
        return SparqlDockerWrapper._query_triplestore(database_uri, query)

    @staticmethod
    def _query_triplestore(endpoint: str, query: str):
        sparql = SPARQLWrapper(endpoint, returnFormat=_SPARQL_RETURN_FORMAT)
        sparql.setQuery(query)

        result = sparql.query().convert().decode()

        return pandas.read_csv(io.StringIO(result))


def write_output(output_format, output, output_file):
    """
    Write output to output_file using the format from output_format.

    If output_format == None, write output as pickle without indicating format (legacy method)

    :param output_format:
    :param output:
    :param output_file:
    :return:
    """
    with open(output_file, 'wb') as fp:
        if output_format:
            # Indicate output format
            fp.write(output_format.encode() + b'.')

            # Write actual data
            output_format = DataFormat(output_format.lower())
            serialized = serialization.serialize(output, output_format)
            fp.write(serialized)
        else:
            # No output format specified, use legacy method
            fp.write(pickle.dumps(output))


def load_input(input_file):
    """
    Try to read the specified data format and deserialize the rest of the
    stream accordingly. If this fails, assume the data format is pickle.

    :param input_file:
    :return:
    """
    with open(input_file, "rb") as fp:
        try:
            input_data = _read_formatted(fp)
        except DeserializationException:
            info('No data format specified. '
                 'Assuming input data is pickle format')
            fp.seek(0)
            try:
                input_data = pickle.load(fp)
            except pickle.UnpicklingError:
                raise DeserializationException('Could not deserialize input')
    return input_data


def _read_formatted(file: BinaryIO):
    data_format = str.join('', list(_read_data_format(file)))
    data_format = DataFormat(data_format.lower())
    return deserialization.deserialize(file, data_format)


def _read_data_format(file: BinaryIO):
    """
    Try to read the prescribed data format. The data format should be specified
    as follows: DATA_FORMAT.ACTUAL_BYTES. This function will attempt to read
    the string before the period. It will fail if the file is not in the right
    format.

    :param file: Input file received from vantage infrastructure.
    :return:
    """
    success = False

    for i in range(_MAX_FORMAT_STRING_LENGTH):
        try:
            char = file.read(1).decode()
        except UnicodeDecodeError:
            # We aren't reading a unicode string
            raise DeserializationException('No data format specified')

        if char == _DATA_FORMAT_SEPARATOR:
            success = True
            break
        else:
            yield char

    if not success:
        # The file didn't have a format prepended
        raise DeserializationException('No data format specified')
