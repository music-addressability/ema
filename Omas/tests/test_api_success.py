import unittest
from api import app
import json

CHOPIN_MEI_URL = "https%3A%2F%2Fraw.githubusercontent.com%2Fmusic-encoding%2Fmusic-encoding%2Fmaster%2Fsamples%2FMEI2013%2FMusic%2FComplete%20examples%2FChopin_Etude_op.10_no.9.mei"


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

    def test_single_staff_selector(self):
        url = CHOPIN_MEI_URL
        # grab all measures and all beats from staff 1
        selector = url + "/1/all/@all"
        resp = self.app.get(selector)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')
        # ??? profit?

    def test_double_staff_selector(self):
        url = CHOPIN_MEI_URL
        # select the first measure of both staves
        selector = url + "/1,2/1/all"
        resp = self.app.get(selector)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')
        # stuff

    def test_measure_instances_selector(self):
        url = CHOPIN_MEI_URL
        # staff 1, measures 1 & 3
        selector = url + "/1/1+3/all"
        resp = self.app.get(selector)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')

    def test_measure_range_selector(self):
        url = CHOPIN_MEI_URL
        # staff 1, measures 1-3
        selector = url + "/1/1-3/all"
        resp = self.app.get(selector)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')

    def test_multi_staff_measure_instances(self):
        url = CHOPIN_MEI_URL
        selector = url + "/1,2/1+3+5,2+4+6/all"
        resp = self.app.get(selector)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')

    def test_multi_staff_measure_ranges(self):
        url = CHOPIN_MEI_URL
        selector = url + "/1,2/1-3,2-4/all"
        resp = self.app.get(selector)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')

    def test_multi_staff_measure_ranges_and_instances(self):
        url = CHOPIN_MEI_URL
        selector = url + "/1,2/1-3+5-8,2-4+6-8/all"
        resp = self.app.get(selector)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')

    def test_staff_measure_single_beat(self):
        url = CHOPIN_MEI_URL
        selector = url + "/1/1/@1"
        resp = self.app.get(selector)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')

    def test_staff_measure_beat_range(self):
        url = CHOPIN_MEI_URL
        selector = url + "/1/1/@1-3"
        resp = self.app.get(selector)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')

    def test_staff_measure_beat_multiple_instances(self):
        url = CHOPIN_MEI_URL
        selector = url + "/1/1/@1@3"
        resp = self.app.get(selector)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')

    def test_multi_staff_beat(self):
        url = CHOPIN_MEI_URL
        # staff 1, m1-3, all beats; staff 2, m4-6, beats 1 & 3
        selector = url + "/1,2/1-3,4-6/@all,@1@3"
        resp = self.app.get(selector)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')

    def test_multi_staff_measure_instance_beats(self):
        url = CHOPIN_MEI_URL
        # staff 1, m1 & m3, all beats; staff 2, m4, beat 1 & m6 beat 3
        selector = url + "/1,2/1+3,4+6/@all+@all,@1+@3"
        resp = self.app.get(selector)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')

    def test_staff_measure_start_alias(self):
        url = CHOPIN_MEI_URL
        # from the beginning of the piece to measure 3
        selector = url + "/1,2/start-3,start-3/all"
        resp = self.app.get(selector)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')

    def test_staff_measure_end_alias(self):
        url = CHOPIN_MEI_URL
        # from measure 65 to the end of the piece
        selector = url + "/1,2/65-end,65-end/all"
        resp = self.app.get(selector)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')

    def test_staff_measure_one_alias(self):
        url = CHOPIN_MEI_URL
        # all staves, measure one, all beats
        selector = url + "/all/1/all"
        resp = self.app.get(selector)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')

    def test_staff_measure_one_start_alias(self):
        url = CHOPIN_MEI_URL
        # all staves, measure one, all beats
        selector = url + "/all/start/all"
        resp = self.app.get(selector)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')

    def test_staff_measure_one_beat_start_alias(self):
        url = CHOPIN_MEI_URL
        # all staves, measure one, beats 1-3
        selector = url + "/all/1/@start-3"
        resp = self.app.get(selector)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')

    def test_staff_measure_one_beat_end_alias(self):
        url = CHOPIN_MEI_URL
        # all staves, measure one, beats 1-3
        selector = url + "/all/1/@1-end"
        resp = self.app.get(selector)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'application/json')



    def test_specific_info(self):
        url = "http%3A%2F%2Fmusic-encoding.org%2FsampleCollection%2Fencodings%2Fattribute_syl.xml/1-1/1,3/1-1"
        resp = self.app.get(url)
        self.assertEqual(resp.status_code, 200)

    def tearDown(self):
        pass
