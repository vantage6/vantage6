#!/usr/bin/env python3
from pathlib import Path
from vantage6.common.utest import run_tests, find_tests
import sys


def run():
    # run CLI tests
    cli_test_suites = find_tests(str(Path(__file__).parent / "vantage6"))
    success_cli = run_tests(cli_test_suites)

    # run server tests
    server_test_suites = find_tests(str(Path(__file__).parent / "vantage6-server"))
    success_server = run_tests(server_test_suites)

    sys.exit(not (success_server and success_cli))


if __name__ == "__main__":
    run()
