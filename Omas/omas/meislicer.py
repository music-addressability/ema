#!/usr/bin/env python

class MeiSlicer(object):
    """A class to slice an MEI document provided a range of 
    measures, staves, and beats."""
    def __init__(self, doc, measures, staves, beats, completeness):
        self.meiDoc = doc
        self.measures = measures
        self.staves = staves
        self.beats = beats
        self.completeness = completeness

    def parseRanges(self, ran):
        groups = ran.split(",")
        ranges = []
        for g in groups:
            ranges.append(g.split("-"))

        return ranges

    def getMeasures(self):
        # There is always only one music element in an MEI doc
        musicEl = self.meiDoc.getElementsByName("music")[0]
        measures = musicEl.getDescendantsByName("measure")
        # measure ranges will always return 1 item
        mrange = self.parseRanges(self.measures)[0]

        if len(mrange) == 1:
            print measures[int(mrange[0])-1]
            return "1 measure selected"
        else:
            selected_mm = []
            for m_idx in range(int(mrange[0])-1, int(mrange[1])):
                selected_mm.append(measures[m_idx])
            print selected_mm
            return "%i measures selected" % len(selected_mm)

        return mrange