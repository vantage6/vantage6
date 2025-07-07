#!/usr/bin/env python3
from pathlib import Path
from vantage6.common.utest import run_tests, find_tests
import sys


def run():

    # run common tests
    common_test_suites = find_tests(str(Path(__file__).parent / "vantage6-common"))
    success_common = run_tests(common_test_suites)

    # run CLI tests
    cli_test_suites = find_tests(str(Path(__file__).parent / "vantage6"))
    success_cli = run_tests(cli_test_suites)

    # run algorithm store tests
    algorithm_store_test_suites = find_tests(
        str(Path(__file__).parent / "vantage6-algorithm-store")
    )
    success_algorithm_store = run_tests(algorithm_store_test_suites)

    # run server tests
    server_test_suites = find_tests(str(Path(__file__).parent / "vantage6-server"))
    success_server = run_tests(server_test_suites)

    # run node tests
    node_test_suites = find_tests(str(Path(__file__).parent / "vantage6-node"))
    success_node = run_tests(node_test_suites)

    sys.exit(
        not (
            success_server
            and success_cli
            and success_node
            and success_common
            and success_algorithm_store
        )
    )


if __name__ == "__main__":
    run()
