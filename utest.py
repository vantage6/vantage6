#!/usr/bin/env python3
import doctest
import sys
from pathlib import Path

from vantage6.algorithm.tools.preprocessing import (
    aggregation,
    column,
    datetime,
    encoding,
    filter,
)
from vantage6.common.utest import find_tests, run_tests


def run():
    # run CLI tests
    cli_test_suites = find_tests(str(Path(__file__).parent / "vantage6"))
    success_cli = run_tests(cli_test_suites)

    # run server tests
    server_test_suites = find_tests(
        str(Path(__file__).parent / "vantage6-server")
    )
    success_server = run_tests(server_test_suites)

    # run algorithm tests
    algorithm_test_suites = find_tests(
        str(Path(__file__).parent / "vantage6-algorithm-tools")
    )

    # add preprocessing doctests
    for module in [aggregation, column, datetime, encoding, filter]:
        algorithm_test_suites.addTests(doctest.DocTestSuite(module))

    success_algo = run_tests(algorithm_test_suites)

    success = success_server and success_cli and success_algo

    sys.exit(not success)


if __name__ == "__main__":
    run()
