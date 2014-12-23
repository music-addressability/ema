from meiinfo import MusDocInfo
import re

from pymei import XmlExport, MeiElement #for testing

class MeiSlicer(object):
    """A class to slice an MEI document provided a range of 
    measures, staves, and beats."""
    def __init__(self, doc, measures, staves, beats, completeness):
        self.meiDoc = doc
        self.docInfo = MusDocInfo(doc).get()
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
        selected = []
        s_nos = self._parseRanges(self.requested_staves)
        
        for i, m in enumerate(self.measures):
            data = {
              "on"     : [],
              "around" : []
            }

            ## Getting events ON staff ##

            # If staff elements have @n, use it to select the correct staff,
            # otherwise default to element position order.
            for staff in m.getDescendantsByName("staff"):
                if staff.hasAttribute("n"):
                    if int(staff.getAttribute("n").getValue()) in s_nos:
                        data["on"].append(staff)
            if not data["on"]:
                staves = m.getDescendantsByName("staff")
                for n in s_nos:
                    if len(staves) >= n:
                        data["on"].append(staves[n])
            # fail if all staves could not be retrieved
            if len(data["on"]) != len(s_nos):
                return "Could not retrieve requested staves - aborting 400"

            ## Getting events AROUND a staff ##

            for el in m.getChildren():
                #TODO: CAREFUL - EDITORIAL MARKUP MAY OBFUSCATE THIS
                if el.hasAttribute("staff"):
                    if int(el.getAttribute("staff").getValue()) in s_nos:
                        data["around"].append(el)

            selected.append(data)

            ## At the first measure, locate events landing on or including this staff 
            # from out of range measures (eg a long slur)
            m_idx = self._parseRanges(self.requested_measures)[0] - 1
            spanners = {}
            if i == 0 and m_idx > 0:
                spanners = self.getMultiMeasureSpanners(m_idx)
            
            # Use table to determine elements to include in each affected measure
            m_id = m.getId()
            if m_id in spanners:
                for event_id in spanners[m_id]:
                    event = self.meiDoc.getElementById(event_id)

                    # Truncate event to start at the beginning of the range
                    if event.hasAttribute("startid"):
                        # Set startid to the first event on staff
                        first_id = selected[0]["on"][0].getId()
                        event.getAttribute("startid").setValue("#"+first_id)
                    if event.hasAttribute("tstamp"):
                        # Set tstamp to 0
                        event.getAttribute("tstamp").setValue("0")                    

                    # and attach to "around" data of first measure
                    selected[0]["around"].append(event)

                    # TODO truncate to end at end of range

        return selected

    @property
    def beats(self):
        tstamps = self.requested_beats.split("-")

        # According to the API, the beat selection must be a range,
        # even when only one beat is selected.
        if len(tstamps) != 2:
            return "invalid beat range - return 400"

        tstamp_first = int(tstamps[0])
        tstamp_final = int(tstamps[1])

        beatsInfo = self.docInfo["beats"]

        meter_first = 0
        meter_final = 0

        if len(beatsInfo) > 1:
            #TODO
            return "many beats"
        else:
            meter_first = beatsInfo["0"]
            meter_final = beatsInfo["0"]

        # check that the requested beat actually fits in the meter
        if tstamp_first > int(meter_first["count"]) or tstamp_final > int(meter_final["count"]):
            return "request beat is out of measure bounds - return 400"

        # FIRST MEASURE
        data_first = self.staves[0]

        # TODO: beware of @duration.default - though not very common

        # Start by counting durations of on-staff elements
        for staff in data_first["on"]:
            # Find all descendants with att.duration.musical (@dur)
            cur_beat = 0.0
            for el in staff.getDescendants():
                if el.hasAttribute("dur"):
                    # TODO DEAL WITH DOTS
                    cur_beat += float(int(meter_first["unit"]) / float(el.getAttribute("dur").getValue()))
                    # exclude those before tstamp
                    if cur_beat <= tstamp_first: 
                        el.getParent().removeChild(el)


        # LAST MEASURE
        data_first = self.staves[-1]

        # Start by counting durations of on-staff elements
        for staff in data_first["on"]:
            # Find all descendants with att.duration.musical (@dur)
            cur_beat = 0.0
            for el in staff.getDescendants():
                if el.hasAttribute("dur"):
                    # TODO DEAL WITH DOTS
                    cur_beat += float(int(meter_final["unit"]) / float(el.getAttribute("dur").getValue()))
                    # exclude those after tstamp
                    if cur_beat > tstamp_final: 
                        el.getParent().removeChild(el)

        return self.staves

    def getMultiMeasureSpanners(self, end=-1):

        mm = self.musicEl.getDescendantsByName("measure")
        table = {}

        # {
        #     "_targetMeasureID_" : {
        #         "_eventID_" : {
        #             "origin" : "_originMeasureID_", 
        #             "startid" : "_startID_",
        #             "endid" : "_endID_",
        #             "tstamp" : "_beat_",
        #             "tstamp2" : "_Xm+beat_"
        #         }
        #     }
        # }

        # Exclude end measure index from request, 
        # unless last measure is requested (creates table for whole file).
        if end == -1: end = len(mm) + 1 
        
        # Look back through measures and build a table of events
        # spanning multiple measures via tstamp/tstamp2 or startid/endid pairs.
        for i, prev_m in enumerate(mm[:end]):
            m_id = prev_m.getId()

            for el in prev_m.getDescendants():

                # Determine destination based on startid/endid pairs.
                # If not found, look for tstamp/tstamp2 pairs before moving on.

                if el.hasAttribute("endid"):
                    endid = el.getAttribute("endid").getValue()
                    endid = endid.replace("#", "")

                    target_el = self.meiDoc.getElementById(endid)

                    if target_el.hasAncestor("measure"):
                        # This could be a comparison of objects, but comparing ids feels safer.
                        destination = target_el.getAncestor("measure")
                        if destination.getId() != prev_m.getId():
                            # Create table entry
                            dest_id = destination.getId()
                            el_id = el.getId()
                            
                            if dest_id not in table: table[dest_id] = {}
                            table[dest_id][el_id] = {
                                "origin" : m_id,
                                "endid": endid
                            }
                            if el.hasAttribute("startid"):
                                startid = el.getAttribute("startid").getValue().replace("#", "")
                                table[dest_id][el_id]["startid"] = startid
                elif el.hasAttribute("tstamp2"):
                    t2 = el.getAttribute("tstamp2").getValue() 
                    multiMesSpan = re.match(r"([1-9])+m\+", t2)
                    if multiMesSpan:
                        destination = mm[ i + int(multiMesSpan.group(1)) ]
                        # Create table entry
                        dest_id = destination.getId()
                        el_id = el.getId()
                        
                        if dest_id not in table: table[dest_id] = {}
                        table[dest_id][el_id] = {
                            "origin" : m_id,
                            "tstamp2": t2
                        }
                        if el.hasAttribute("tstamp"):
                            table[dest_id][el_id]["tstamp"] = el.getAttribute("tstamp").getValue()

        return table

    def select(self):
        
        # Temporarily build example tree
        root = MeiElement("section")

        for m in self.beats:
            # Temporarily re-build measures
            temp_container = MeiElement("measure")
            for staff in m["on"]:
                temp_container.addChild(staff)
            for el in m["around"]:
                temp_container.addChild(el)
            root.addChild(temp_container)

        return XmlExport.meiElementToText(root)


    #TODO add support for keywords "start" and "end"
    def _parseRanges(self, rang):
        groups = rang.split(",")
        ranges = []

        for g in groups:
            values = g.split("-")
            length = len(values)

            if length == 1:
                ranges.append(int(values[0]))
            elif length == 2:
                ranges += range(int(values[0]), int(values[1])+1)
            else:
                return "invalid range - return 400"

        return ranges