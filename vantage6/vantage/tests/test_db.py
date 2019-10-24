# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import unittest
import doctest
import logging



def load_tests(loader, tests, ignore):
    # tests.addTests(doctest.DocTestSuite(fhir.node))
    return tests

class TestOrganization(unittest.TestCase):
    
    def setUp(self):
        pass

    def test_test(self):
        self.assertEquals(1, 1)
