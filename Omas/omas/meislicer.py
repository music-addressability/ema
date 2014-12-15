#!/usr/bin/env python

class MeiSlicer(object):
    """A class to slice an MEI document provided a range of 
    measures, staves, and beats."""
    def __init__(self, doc, measures, staves, beats, completeness):
        self.meiDoc = doc
        self.requested_measures = measures
        self.requested_staves = staves
        self.requested_beats = beats
        self.completeness = completeness

    @property
    def musicEl(self):
        # There is always only one music element in an MEI doc
        return self.meiDoc.getElementsByName("music")[0]

    @property
    def measures(self):
        mm = self.musicEl.getDescendantsByName("measure")
        selected = []
        # measure ranges will always return 1 item
        m_idxs = self._parseRanges(self.requested_measures)

        for m_idx in m_idxs:
            selected.append(mm[m_idx-1])

        return selected

    @property
    def staves(self):
        selected = {
          "on"     : [],
          "around" : []
        }
        s_nos = self._parseRanges(self.requested_staves)
        for m in self.measures:
            # If staff elements have @layer, use it to select the correct staff,
            # otherwise default to element position order.
            selected["on"].append(m.getDescendantsByName("staff"))
            for el in m.getChildren():
                if el.hasAttribute("staff"):
                    if int(el.getAttribute("staff").getValue()) in s_nos:
                        selected["around"].append(el)

        return selected

    # @property
    # def beats(self):
    #     selected = []
    #     srange = self._parseRanges(self.requested_staves)
    #     for m in self.measures:
    #         # If staff elements have @layer, use it to select the correct staff,
    #         # otherwise default to element position order.
    #         selected.append(m.getDescendantsByName("staff"))

    #     return selected

    def _parseRanges(self, ran):
        groups = ran.split(",")
        ranges = []

        for g in groups:
            values = g.split("-")
            length = len(values)

            if length == 1:
                ranges.append(int(values[0]))
            elif length == 2:
                ranges += range(int(values[0]), int(values[1])+1)
            else:
                return "invalid range - return 500"

        return ranges