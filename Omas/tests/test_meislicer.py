import unittest
from omas import meiinfo
from omas import meislicer
import requests
from urllib import unquote


class MeiSlicerTest(unittest.TestCase):
    def setUp(self):
        url = "http://music-encoding.org/sampleCollection/encodings/attribute_syl.xml"
        r = requests.get(unquote(url), timeout=15)
        self.meidoc = meiinfo.read_MEI(r.content).getMeiDocument()

    def test_slicer(self):
        mei_slicer = meislicer.MeiSlicer(
            self.meidoc,
            '1',
            'all',
            '@all',
            None
        )
        mei_slice = mei_slicer.slice()

    def tearDown(self):
        pass
