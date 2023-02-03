"""
Docker Wrapper

This module contains the `docker_wrapper` function for providing vantage6
algorithms with uniform input and output handling.
"""

import os
import io
from abc import ABC, abstractmethod
from types import ModuleType
import pandas
import json

from vantage6.tools.dispatch_rpc import dispatch_rpc
from vantage6.tools.util import info
from vantage6.tools import deserialization, serialization
from vantage6.tools.exceptions import DeserializationException
from SPARQLWrapper import SPARQLWrapper, CSV

_SPARQL_RETURN_FORMAT = CSV


def docker_wrapper(module: str, load_data=True):
    wrapper = DockerWrapper()
    wrapper.wrap_algorithm(module, load_data)


def sparql_wrapper(module: str):
    wrapper = SparqlDockerWrapper()
    wrapper.wrap_algorithm(module)


def parquet_wrapper(module: str):
    wrapper = ParquetWrapper()
    wrapper.wrap_algorithm(module)


def multidb_wrapper(module: str):
    wrapper = MultiDBWrapper()
    wrapper.wrap_algorithm(module)


class WrapperBase(ABC):

    def wrap_algorithm(self, module: ModuleType,
                       load_data: bool = True) -> None:
        """
        Wrap an algorithm module to provide input and output handling for the
        vantage6 infrastructure.

        Data is received in the form of files, whose location should be
        specified in the following environment variables:
        - `INPUT_FILE`: input arguments for the algorithm
        - `OUTPUT_FILE`: location where the results of the algorithm should be
            stored
        - `TOKEN_FILE`: access token for the vantage6 server REST api
        - `DATABASE_URI`: either a database endpoint or path to a csv file.

        The wrapper expects the input file to be a json file. Any other file
        format will result in an error.

        Parameters
        ----------
        module: module
            module that contains the vantage6 algorithms
        load_data: bool
            attempt to load the data or not, default True
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

        # TODO in v4+, we should work with multiple databases instead of this
        # default one
        database_uri = os.environ["DATABASE_URI"]
        info(f"Using '{database_uri}' as database")

        if load_data:
            data = self.load_data(database_uri, input_data)
        else:
            data = None

        # make the actual call to the method/function
        info("Dispatching ...")
        output = dispatch_rpc(data, input_data, module, token)

        # write output from the method to mounted output file. Which will be
        # transferred back to the server by the node-instance.
        output_file = os.environ["OUTPUT_FILE"]
        info(f"Writing output to {output_file}")

        write_output(output, output_file)

    @staticmethod
    @abstractmethod
    def load_data(database_uri, input_data):
        pass


class DockerWrapper(WrapperBase):
    @staticmethod
    def load_data(database_uri, input_data):
        return pandas.read_csv(database_uri)


CsvWrapper = DockerWrapper


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


class ParquetWrapper(WrapperBase):
    @staticmethod
    def load_data(database_uri, input_data):
        return pandas.read_parquet(database_uri)


class MultiDBWrapper(WrapperBase):
    @staticmethod
    def load_data(database_uri, input_data):
        db_labels = json.loads(os.environ.get("DB_LABELS"))
        databases = {}
        for db_label in db_labels:
            db_env_var = f'{db_label.upper()}_DATABASE_URI'
            databases[db_label] = os.environ.get(db_env_var)
        return databases


def write_output(output: any, output_file: str) -> None:
    """
    Write output to output_file using JSON serialization.

    Parameters
    ----------
    output : any
        Output of the algorithm
    output_file : str
        Path to the output file
    """
    with open(output_file, 'wb') as fp:
        serialized = serialization.serialize(output)
        fp.write(serialized)


def load_input(input_file: str) -> dict:
    """
    Load the input from the input file.

    Parameters
    ----------
    input_file : str
        File containing the input

    Returns
    -------
    input_data : dict
        Input data for the algorithm
    """
    with open(input_file, "rb") as fp:
        try:
            input_data = deserialization.deserialize(fp)
        except DeserializationException:
            raise DeserializationException('Could not deserialize input')
    return input_data
