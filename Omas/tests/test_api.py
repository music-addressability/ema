import unittest
from api import app
import json


class ApiTest(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app = app.test_client()

    def test_app(self):
        # test that the root of the app gets a 404 (for now)
        resp = self.app.get('/')
        self.assertEqual(resp.status_code, 404)

    def test_basic_info(self):
        url = "http%3A%2F%2Fmusic-encoding.org%2FsampleCollection%2Fencodings%2Fattribute_syl.xml/info.json"
        resp = self.app.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')

        data = json.loads(resp.data)
        self.assertEqual(data["completeness"], ["raw", "signature", "nospace", "cut"])

    def test_specific_info(self):
        url = "http%3A%2F%2Fmusic-encoding.org%2FsampleCollection%2Fencodings%2Fattribute_syl.xml/1-1/1,3/1-1"
        resp = self.app.get(url)
        self.assertEqual(resp.status_code, 200)

    def tearDown(self):
        pass
