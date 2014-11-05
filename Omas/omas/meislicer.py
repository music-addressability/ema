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

    def slice(self):
        return "sliced"