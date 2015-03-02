import unittest
from tests import test_api
from tests import test_meislicer


def suite():
    test_suite = unittest.TestSuite()
    test_suite.addTest(test_api.make_test())
    test_suite.addTest(test_meislicer.make_test())
    return test_suite


runner = unittest.TextTestRunner()
runner.run(suite())
