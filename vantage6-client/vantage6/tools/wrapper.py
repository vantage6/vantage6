"""
Wrapper

This module contains algorithm wrappers. These wrappers are used to provide
different data adapters to the algorithms. This way we ony need to write the
algorithm once and can use it with different data adapters.

Currently the following wrappers are available:
    - ``DockerWrapper`` (= ``CSVWrapper``)
    - ``SparqlDockerWrapper``
    - ``ParquetWrapper``
    - ``SQLWrapper``
    - ``OMOPWrapper``
    - ``ExcelWrapper``

When writing the Docker file for the algorithm, you can call the
`auto_wrapper` which will automatically select the correct wrapper based on
the database type. The database type is set by the vantage6 node based on its
configuration file.

For legacy reasons, the ``docker_wrapper``, ``sparql_docker_wrapper`` and
``parquet_wrapper`` are still available. These wrappers are deprecated and
will be removed in the future.

The ``multi_wrapper`` is used when multiple databases are connected to a single
algorithm. This wrapper is separated from the other wrappers because it is not
compatible with the ``smart_wrapper``.
"""
import os
import pickle
import io
import pandas
import json

from typing import BinaryIO, Any, Generator
from abc import ABC, abstractmethod
from SPARQLWrapper import SPARQLWrapper, CSV

from vantage6.tools import deserialization, serialization
from vantage6.tools.dispatch_rpc import dispatch_rpc
from vantage6.tools.util import info, error
from vantage6.tools.data_format import DataFormat
from vantage6.tools.exceptions import DeserializationException

_DATA_FORMAT_SEPARATOR = '.'
_MAX_FORMAT_STRING_LENGTH = 10

_SPARQL_RETURN_FORMAT = CSV


def auto_wrapper(module: str, load_data: bool = True,
                 use_new_client: bool = False) -> None:
    """
    Wrap an algorithm module to provide input and output handling for the
    vantage6 infrastructure. This function will automatically select the
    correct wrapper based on the database type.

    Parameters
    ----------
    module : str
        Python module name of the algorithm to wrap.
    load_data : bool, optional
        Wether to load the data or not, by default True
    use_new_client : bool, optional
        Wether to use the new client or not, by default False
    """

    # Get the database label from the environment variable, this variable is
    # set by the client/user/researcher.
    try:
        label = os.environ["USER_REQUESTED_DATABASE_LABEL"]
    except KeyError:
        error("No database label found, are you using an outdated node?")
        return

    # Get the database type from the environment variable, this variable is
    # set by the vantage6 node based on its configuration file.
    database_type = os.environ.get(f"{label.upper()}_DATABASE_TYPE", "csv")\
        .lower()

    # Create the correct wrapper based on the database type, note that the
    # multi database wrapper is not available.
    if database_type == "csv":
        wrapper = CSVWrapper()
    if database_type == "excel":
        wrapper = ExcelWrapper()
    elif database_type == "sparql":
        wrapper = SparqlDockerWrapper()
    elif database_type == "parquet":
        wrapper = ParquetWrapper()
    elif database_type == "sql":
        wrapper = SQLWrapper()
    elif database_type == "omop":
        wrapper = OMOPWrapper()
    else:
        error(f"Unknown database type: {database_type}")
        return

    # Execute the algorithm with the correct data wrapper
    wrapper.wrap_algorithm(module, load_data, use_new_client)


def docker_wrapper(module: str, load_data: bool = True,
                   use_new_client: bool = False) -> None:
    """
    Specific wrapper for CSV only data sources. Use the ``auto_wrapper``
    to automatically select the correct wrapper based on the database type.

    Parameters
    ----------
    module : str
        Module name of the algorithm package.
    load_data : bool, optional
        Whether to load the data into a pandas DataFrame or not, by default
        True
    use_new_client : bool, optional
        Whether to use the new or old client, by default False
    """
    wrapper = DockerWrapper()
    wrapper.wrap_algorithm(module, load_data, use_new_client)


def sparql_wrapper(module: str, use_new_client: bool = False) -> None:
    """
    Specific wrapper for SPARQL only data sources. Use the ``auto_wrapper``
    to automatically select the correct wrapper based on the database type.

    Parameters
    ----------
    module : str
        Module name of the algorithm package.
    use_new_client : bool, optional
        Whether to use the new or old client, by default False
    """
    wrapper = SparqlDockerWrapper()
    wrapper.wrap_algorithm(module, use_new_client)


def parquet_wrapper(module: str, use_new_client: bool = False) -> None:
    """
    Specific wrapper for Parquet only data sources. Use the ``auto_wrapper``
    to automatically select the correct wrapper based on the database type.

    Parameters
    ----------
    module : str
        Module name of the algorithm package.
    use_new_client : bool, optional
        Whether to use the new or old client, by default False
    """
    wrapper = ParquetWrapper()
    wrapper.wrap_algorithm(module, use_new_client)


def multidb_wrapper(module: str, use_new_client: bool = False) -> None:
    """
    Specific wrapper for multiple data sources.

    Parameters
    ----------
    module : str
        Module name of the algorithm package.
    use_new_client : bool, optional
        Whether to use the new or old client, by default False
    """
    wrapper = MultiDBWrapper()
    wrapper.wrap_algorithm(module, use_new_client)


class WrapperBase(ABC):

    def wrap_algorithm(self, module: str, load_data: bool = True,
                       use_new_client: bool = False) -> None:
        """
        Wrap an algorithm module to provide input and output handling for the
        vantage6 infrastructure.

        Data is received in the form of files, whose location should be
        specified in the following environment variables:
        - ``INPUT_FILE``: input arguments for the algorithm
        - ``OUTPUT_FILE``: location where the results of the algorithm should
          be stored
        - ``TOKEN_FILE``: access token for the vantage6 server REST api
        - ``DATABASE_URI``: either a database endpoint or path to a csv file.

        The wrapper is able to parse a number of input file formats. The
        available formats can be found in
        `vantage6.tools.data_format.DataFormat`. When the input is not pickle
        (legacy), the format should be specified in the first bytes of the
        input file, followed by a '.'.

        It is also possible to specify the desired output format. This is done
        by including the parameter 'output_format' in the input parameters.
        Again, the list of possible output formats can be found in
        `vantage6.tools.data_format.DataFormat`.

        It is still possible that output serialization will fail even if the
        specified format is listed in the DataFormat enum. Algorithms can in
        principle return any python object, but not every serialization format
        will support arbitrary python objects. When dealing with unsupported
        algorithm output, the user should use 'pickle' as output format, which
        is the default.

        The other serialization formats support the following algorithm output:
        - built-in primitives (int, float, str, etc.)
        - built-in collections (list, dict, tuple, etc.)
        - pandas DataFrames

        Parameters
        ----------
        module : str
            Python module name of the algorithm to wrap.
        load_data : bool, optional
            Whether to load the data into a pandas DataFrame or not, by default
            True
        """
        info(f"wrapper for {module}")

        # read input from the mounted input file.
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
        label = os.environ["USER_REQUESTED_DATABASE_LABEL"]
        database_uri = os.environ[f"{label.upper()}_DATABASE_URI"]
        info(f"Using '{database_uri}' as database")

        if load_data:
            data = self.load_data(database_uri, input_data)
        else:
            data = None

        # make the actual call to the method/function
        info("Dispatching ...")
        output = dispatch_rpc(data, input_data, module, token, use_new_client)

        # write output from the method to mounted output file. Which will be
        # transferred back to the server by the node-instance.
        output_file = os.environ["OUTPUT_FILE"]
        info(f"Writing output to {output_file}")

        output_format = input_data.get('output_format', None)
        write_output(output_format, output, output_file)

    @staticmethod
    @abstractmethod
    def load_data(database_uri: str, input_data: dict):
        """
        Load the local privacy-sensitive data from the database.

        Parameters
        ----------
        database_uri : str
            URI of the database to read
        input_data : dict
            User defined input, which may contain a query for the database
        """
        pass


class CSVWrapper(WrapperBase):
    @staticmethod
    def load_data(database_uri: str, input_data: dict) -> pandas.DataFrame:
        """
        Load the local privacy-sensitive data from the database.

        Parameters
        ----------
        database_uri : str
            URI of the csv file, supplied by te node
        input_data : dict
            Unused, as csv files do not require a query

        Returns
        -------
        pandas.DataFrame
            The data from the csv file
        """
        return pandas.read_csv(database_uri)


# for backwards compatibility
CsvWrapper = CSVWrapper
DockerWrapper = CSVWrapper


class ExcelWrapper(WrapperBase):
    @staticmethod
    def load_data(database_uri: str, input_data: dict) -> pandas.DataFrame:
        """
        Load the local privacy-sensitive data from the database.

        Parameters
        ----------
        database_uri : str
            URI of the excel file, supplied by te node
        input_data : dict
            May contain a 'sheet_name', which is passed to pandas.read_excel

        Returns
        -------
        pandas.DataFrame
            The data from the excel file
        """
        # The default sheet_name is 0, which is the first sheet
        sheet_name = input_data.get('sheet_name', 0)
        if sheet_name:
            info(f"Reading sheet '{sheet_name}' from excel file")
        return pandas.read_excel(database_uri, sheet_name=sheet_name)


class SparqlDockerWrapper(WrapperBase):
    @staticmethod
    def load_data(database_uri: str, input_data: dict) -> pandas.DataFrame:
        """
        Load the local privacy-sensitive data from the database.

        Parameters
        ----------
        database_uri : str
            URI of the triplestore, supplied by te node
        input_data : dict
            Can contain a 'query', to retrieve the data from the triplestore

        Returns
        -------
        pandas.DataFrame
            The data from the triplestore
        """
        if 'query' not in input_data:
            error("No query in the input specified. Exiting ...")
        query = input_data['query']
        return SparqlDockerWrapper._query_triplestore(database_uri, query)

    @staticmethod
    def _query_triplestore(endpoint: str, query: str) -> pandas.DataFrame:
        sparql = SPARQLWrapper(endpoint, returnFormat=_SPARQL_RETURN_FORMAT)
        sparql.setQuery(query)

        result = sparql.query().convert().decode()

        return pandas.read_csv(io.StringIO(result))


class ParquetWrapper(WrapperBase):
    @staticmethod
    def load_data(database_uri: str, input_data: dict) -> pandas.DataFrame:
        """
        Load the local privacy-sensitive data from the database.

        Parameters
        ----------
        database_uri : str
            URI of the parquet file, supplied by te node
        input_data : dict
            Unused, as no additional settings are required

        Returns
        -------
        pandas.DataFrame
            The data from the parquet file
        """
        return pandas.read_parquet(database_uri)


class SQLWrapper(WrapperBase):
    @staticmethod
    def load_data(database_uri: str, input_data: dict) -> pandas.DataFrame:
        """
        Load the local privacy-sensitive data from the database.

        Parameters
        ----------
        database_uri : str
            URI of the sql database, supplied by te node
        input_data : dict
            Contain a 'query', to retrieve the data from the database

        Returns
        -------
        pandas.DataFrame
            The data from the database
        """
        if 'query' not in input_data:
            error("No query in the input specified. Exiting ...")
        return pandas.read_sql(database_uri, input_data['query'])


class OMOPWrapper(WrapperBase):
    @staticmethod
    def load_data(database_uri: str, input_data: dict) -> pandas.DataFrame:
        """
        Load the local privacy-sensitive data from the database.

        Parameters
        ----------
        database_uri : str
            URI of the OMOP database, supplied by te node
        input_data : dict
            Contain a JSON cohort definition from the ATLAS tool, to retrieve
            the data from the database

        Returns
        -------
        pandas.DataFrame
            The data from the database
        """
        # TODO: parse the OMOP json and convert to SQL
        return pandas.read_sql(database_uri, input_data['query'])


class MultiDBWrapper(WrapperBase):
    @staticmethod
    def load_data(database_uri: str, input_data: dict) -> dict:
        """
        Supply the all URI's to the algorithm. Note that this does not load
        the data from the database, but only the URI's. So the algorithm
        needs to load the data itself.

        Parameters
        ----------
        database_uri : str
            Unused, as all databases URI are passed on to the algorithm.
        input_data : dict
            Unused

        Returns
        -------
        dict
            A dictionary with the database label as key and the URI as value
        """
        db_labels = json.loads(os.environ.get("DB_LABELS"))
        databases = {}
        for db_label in db_labels:
            db_env_var = f'{db_label.upper()}_DATABASE_URI'
            databases[db_label] = os.environ.get(db_env_var)
        return databases


def write_output(output_format: str, output: Any, output_file: str) -> None:
    """
    Write output to output_file using the format from output_format.

    If output_format == None, write output as pickle without indicating format
    (legacy method)

    Parameters
    ----------
    output_format : str
        Data type of the output e.g. 'pickle', 'json', 'csv', 'parquet'
    output : Any
        Output of the algorithm, could by any type
    output_file : str
        Path to the output file
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


def load_input(input_file: str) -> Any:
    """
    Try to read the specified data format and deserialize the rest of the
    stream accordingly. If this fails, assume the data format is pickle.

    Parameters
    ----------
    input_file : str
        Path to the input file

    Returns
    -------
    Any
        Deserialized input data

    Raises
    ------
    DeserializationException
        Failed to deserialize input data
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


def _read_formatted(file: BinaryIO) -> Any:
    data_format = str.join('', list(_read_data_format(file)))
    data_format = DataFormat(data_format.lower())
    return deserialization.deserialize(file, data_format)


def _read_data_format(file: BinaryIO) -> Generator:
    """
    Try to read the prescribed data format. The data format should be specified
    as follows: DATA_FORMAT.ACTUAL_BYTES. This function will attempt to read
    the string before the period. It will fail if the file is not in the right
    format.

    Parameters
    ----------
    file : BinaryIO
        Input file received from the user.

    Yields
    ------
    Generator
        The data format as a string

    Raises
    ------
    DeserializationException
        The file did not have a data format prepended or a non-unicode string
        was encountered
    """
    success = False

    for _ in range(_MAX_FORMAT_STRING_LENGTH):
        try:
            char = file.read(1).decode()
        except UnicodeDecodeError:
            # We aren't reading a unicode string
            raise DeserializationException('Non unicode string encountered')

        if char == _DATA_FORMAT_SEPARATOR:
            success = True
            break
        else:
            yield char

    if not success:
        # The file didn't have a format prepended
        raise DeserializationException('No data format specified')
