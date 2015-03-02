import pytest

import os
from pymei import XmlImport
from omas.meiinfo import MusDocInfo

def test_DC_file():
	meiDoc = XmlImport.documentFromFile(os.path.join("..", "data", "DC0101.mei"))
	meiDocInfo = MusDocInfo(meiDoc)
	assert len(meiDocInfo.measures) == 37
	assert meiDocInfo.measure_labels == ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10',
		'11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24',
		'25', '26', '27', '28', '29', '30', '31', '32', '33', '34', '35', '36', '37']
	assert meiDocInfo.staves == {'0': ['Superius', 'Contratenor', 'Tenor', 'Bassus']}
	assert meiDocInfo.beats == {"0": 4}
@pytest.mark.full
def test_MEI_samples():
	path = os.path.join("..", "data", "MEISamples")
	for mei in os.listdir(path):
		meiDoc = XmlImport.documentFromFile(os.path.join(path, mei))
		meiDocInfo = MusDocInfo(meiDoc)
