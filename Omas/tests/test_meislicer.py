import unittest
from omas import meiinfo
from omas import meislicer


class MeiSlicerTest(unittest.TestCase):
    # def setUp(self):
    #     print('MeiSlicer Test Running')
    #     f = open('tests/testfiles/attribute_syl.xml')
    #     content = f.read()
    #     f.close()
    #     self.meidoc = meiinfo.read_MEI(content)

    # def test_slicer(self):
    #     slicer = meislicer.MeiSlicer(self.meidoc, '1-1', '1,3', '1-1', None)
    #     slicer.select()
    #     print(slicer)

    def tearDown(self):
        pass
