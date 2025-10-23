#!/usr/bin/env python3
import argparse
import logging
import sys
import types
from pathlib import Path

from vantage6.common.utest import find_tests, run_tests

# Suppress all logging output
logging.getLogger().setLevel(logging.CRITICAL)
for logger_name in logging.root.manager.loggerDict:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

# The uwsgi Python package is a C extension that is only available when running
# inside a uwsgi process.
# Required here because the blobstream resource imports uwsgi, and it is built
# in the Dockerfile and not in the requirements.txt.
sys.modules["uwsgi"] = types.SimpleNamespace()


def run():
    parser = argparse.ArgumentParser(description="Run vantage6 test suites")
    parser.add_argument("--common", action="store_true", help="Run common tests")
    parser.add_argument("--cli", action="store_true", help="Run CLI tests")
    parser.add_argument(
        "--algorithm-store", action="store_true", help="Run algorithm store tests"
    )
    parser.add_argument(
        "--algorithm-tools", action="store_true", help="Run algorithm tools tests"
    )
    parser.add_argument("--server", action="store_true", help="Run server tests")
    parser.add_argument("--node", action="store_true", help="Run node tests")
    parser.add_argument("--all", action="store_true", help="Run all test suites")

    args = parser.parse_args()

    # If no specific tests are selected, run all by default
    if not any(
        [
            args.common,
            args.cli,
            args.algorithm_store,
            args.algorithm_tools,
            args.server,
            args.node,
            args.all,
        ]
    ):
        args.all = True

    success = True

    # run common tests
    if args.common or args.all:
        common_test_path = Path(__file__).parent / "vantage6-common" / "tests"
        common_test_suites = find_tests(str(common_test_path))
        success_common = run_tests(common_test_suites)
        success = success and success_common

    # run CLI tests
    # if args.cli or args.all:
    #     cli_test_suites = find_tests(str(Path(__file__).parent / "vantage6"))
    #     success_cli = run_tests(cli_test_suites)
    #     success = success and success_cli

    # run algorithm store tests
    if args.algorithm_store or args.all:
        algorithm_store_test_suites = find_tests(
            str(Path(__file__).parent / "vantage6-algorithm-store")
        )
        success = success and run_tests(algorithm_store_test_suites)

    # run algorithm tools tests
    if args.algorithm_tools or args.all:
        algorithm_tools_test_suites = find_tests(
            str(Path(__file__).parent / "vantage6-algorithm-tools")
        )
        success = success and run_tests(algorithm_tools_test_suites)

    # run algorithm tools tests
    if args.algorithm_tools or args.all:
        algorithm_tools_test_suites = find_tests(
            str(Path(__file__).parent / "vantage6-algorithm-tools")
        )
        success_algorithm_tools = run_tests(algorithm_tools_test_suites)
        success = success and success_algorithm_tools

    # run server tests
    if args.server or args.all:
        server_test_suites = find_tests(str(Path(__file__).parent / "vantage6-server"))
        success_server = run_tests(server_test_suites)
        success = success and success_server

    # run node tests
    if args.node or args.all:
        node_test_suites = find_tests(str(Path(__file__).parent / "vantage6-node"))
        success_node = run_tests(node_test_suites)
        success = success and success_node

    sys.exit(not success)


if __name__ == "__main__":
    run()
