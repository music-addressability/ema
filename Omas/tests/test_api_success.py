import unittest
from api import app
import json

TEST_MEI_URL = "http%3A%2F%2Fmusic-encoding.org%2FsampleCollection%2Fencodings%2FFigured_Bass.xml"


class ApiTest(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app = app.test_client()

    def test_info_route(self):
        url = TEST_MEI_URL + "/info.json"
        resp = self.app.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')

    def test_slicing_route(self):
        url = TEST_MEI_URL + "/1/1-2/@all"
        resp = self.app.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_slicing_completeness_route(self):
        url = TEST_MEI_URL + "/1/1-2/@all/cut"
        resp = self.app.get(url)
        self.assertEqual(resp.status_code, 200)

    def tearDown(self):
        pass
