import unittest
from omas import meiinfo
from omas import meislicer
import requests
from urllib import unquote

TEST_MEI_URL = "http%3A%2F%2Fmusic-encoding.org%2FsampleCollection%2Fencodings%2FFigured_Bass.xml"

class MeiSlicerTest(unittest.TestCase):
    def setUp(self):
        r = requests.get(unquote(TEST_MEI_URL), timeout=15)
        self.meidoc = meiinfo.read_MEI(r.content).getMeiDocument()

    def test_single_staff_selector(self):
        url = TEST_MEI_URL
        # grab all measures and all beats from staff 1
        mei_slicer = meislicer.MeiSlicer(
            self.meidoc,
            'all',
            '1',
            '@all',
            None
        )
        mei_slice = mei_slicer.slice()

        returned_m1 = mei_slice.getElementsByName("measure")[0]

        els = returned_m1.getDescendants()

        self.assertEqual(returned_m1.getId(), 'm1')
        self.assertEqual(els[0].getName(), 'staff')
        self.assertTrue(els[0].hasAttribute('n'))
        self.assertEqual(els[0].getAttribute('n').getValue(), "1")
        self.assertEqual(els[1].getName(), 'layer')
        self.assertEqual(els[2].getName(), 'mRest')
        self.assertEqual(els[3].getName(), 'dir')
        self.assertTrue(els[3].hasAttribute('staff'))
        self.assertEqual(els[3].getAttribute('staff').getValue(), "1")
        self.assertTrue(els[3].hasAttribute('tstamp'))
        self.assertEqual(els[3].getAttribute('tstamp').getValue(), "0.5")
