#!/usr/bin/env python3
from __future__ import unicode_literals, print_function

import sys
import os

import logging
import unittest
from datetime import datetime

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


class TestResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity, log):
        super(TestResult, self).__init__(stream, descriptions, verbosity)
        self.log = log

    def startTest(self, test):
        unittest.result.TestResult.startTest(self, test)

        if self.showAll:
            # self.stream.write("%-85s " % self.getDescription(test))
            self.stream.write("%-85s " % str(test))
            self.stream.flush()

    def addError(self, test, err):
        unittest.result.TestResult.addError(self, test, err)
        error = f"{RED}[ERROR]{RESET}"

        if self.showAll:
            self.stream.writeln(error)
        elif self.dots:
            self.stream.write(f"{RED}E{RESET}")
            self.stream.flush()

        self.log.error("%-85s %s" % (test, error))
        self.log.exception(err[1])

    def addFailure(self, test, err):
        unittest.result.TestResult.addFailure(self, test, err)
        fail = f"{RED}[FAIL]{RESET}"

        if self.showAll:
            self.stream.writeln(fail)
        elif self.dots:
            self.stream.write(f"{RED}F{RESET}")
            self.stream.flush()

        self.log.error("%-85s %s" % (test, fail))
        # self.log.error(self.separator1)
        # self.log.error("%s: %s" % ('FAIL', self.getDescription(test)))
        # self.log.error(self.separator2)

        err_str = self._exc_info_to_string(err, test)
        for line in err_str.splitlines():
            self.log.error(line)

        self.log.error("")

    def addSkip(self, test, reason):
        unittest.result.TestResult.addSkip(self, test, reason)
        skipped = f"{YELLOW}[SKIPPED]{RESET} (%s)" % reason

        if self.showAll:
            self.stream.writeln(skipped)
        elif self.dots:
            self.stream.write(f"{YELLOW}s{RESET}")
            self.stream.flush()

        self.log.info("%-85s %s" % (test, skipped))

    def addSuccess(self, test):
        unittest.result.TestResult.addSuccess(self, test)
        ok = f"{GREEN}[OK]{RESET}"

        if self.showAll:
            self.stream.writeln(ok)
        elif self.dots:
            self.stream.write(f"{GREEN}.{RESET}")
            self.stream.flush()

        self.log.info("%-75s %s" % (test, ok))


class TestRunner(unittest.TextTestRunner):
    resultclass = TestResult

    def __init__(
        self,
        log,
        stream=sys.stderr,
        descriptions=True,
        verbosity=1,
        failfast=False,
        buffer=False,
        resultclass=None,
    ):
        super(TestRunner, self).__init__(
            stream, descriptions, verbosity, failfast, buffer, resultclass
        )
        self.log = log

    def _makeResult(self):
        return self.resultclass(
            self.stream, self.descriptions, self.verbosity, self.log
        )


def find_test_packages(suite, retval=set()):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            find_test_packages(item, retval)
        else:
            retval.add(item.__module__)

    return retval


def find_tests(path=None):
    # Find test cases
    if path is None:
        path = os.path.abspath(os.path.dirname(__file__))

    loader = unittest.TestLoader()
    suites = loader.discover(path)

    packages = find_test_packages(suites)

    log = logging.getLogger("utest")

    log.info("Found the following packages with tests:")
    for p in packages:
        log.info("  * %s" % p)

    return suites


def run_tests(suites) -> bool:
    log = logging.getLogger("utest")
    print("-" * 90)
    print("Started: " + datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
    print("-" * 90)

    # Setting verbosity=1 will display dots instead.
    result = TestRunner(log, verbosity=2).run(suites)
    log.info(result)
    return result.wasSuccessful()


# ------------------------------------------------------------------------------
# run
# ------------------------------------------------------------------------------
def run():
    suites = find_tests()
    run_tests(suites)


# ------------------------------------------------------------------------------
# __main__
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    run()
