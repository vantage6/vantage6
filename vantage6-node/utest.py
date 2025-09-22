#!/usr/bin/env python3
from pathlib import Path

from vantage6.common.utest import find_tests, run_tests


def run():
    suites = find_tests(str(Path(__file__).parent))
    run_tests(suites)


if __name__ == "__main__":
    run()
