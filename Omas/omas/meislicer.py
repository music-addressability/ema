from meiinfo import MusDocInfo
from flask.ext.restful import abort
import re

from pymei import XmlExport, MeiElement #for testing
from pymeiext import getClosestStaffDefs


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
        """Return the music element"""
        # There is always only one music element in an MEI doc
        return self.meiDoc.getElementsByName("music")[0]

    @property
    def measures(self):
        """Return selected measures"""
        mm = self.musicEl.getDescendantsByName("measure")
        selected = []
        # measure ranges will always return 1 item
        m_idxs = self._parseRanges(self.requested_measures)

        for m_idx in m_idxs:
            selected.append(mm[m_idx-1])

        return selected

    @property
    def staves(self):
        """Return selected staves"""
        selected = []
        s_nos = self._parseRanges(self.requested_staves)
        
        # Make sure that required staves are not out of bounds.
        mm = self.measures
        sds = [int(sd.getAttribute("n").getValue()) for sd in mm[0].getClosestStaffDefs()]

        for s_no in s_nos:
            if s_no not in sds:
                abort(400, error="400", message="Requested staves are not defined")

        for i, m in enumerate(mm):
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

            ## Getting events AROUND a staff ##

            for el in m.getChildren():
                #TODO: CAREFUL - EDITORIAL MARKUP MAY OBFUSCATE THIS
                if el.hasAttribute("staff"):
                    # Split value of @staff, as it may contain multiple values.
                    values = el.getAttribute("staff").getValue().split()
                    values = [ int(x) for x in values ]

                    # Then check that any of the values are in s_nos.
                    if len(set(values).intersection(s_nos)) > 0:
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

                    # TODO truncate to end at end of range (depending on completeness reqs)

        return selected

    @property
    def beats(self):
        """Return selected staves including only selected beats"""
        tstamps = self.requested_beats.split("-")
        m_idxs = self._parseRanges(self.requested_measures)

        # According to the API, the beat selection must be a range,
        # even when only one beat is selected.
        if len(tstamps) != 2:
            abort(400, error="400", message="Invalid beat range")

        tstamp_first = int(tstamps[0])
        tstamp_final = int(tstamps[1])

        beatsInfo = self.docInfo["beats"]

        meter_first = None
        meter_final = None

        # get the closest beat info to the index of each measure
        timeChanges = beatsInfo.keys()
        timeChanges.sort(key=int)
        for change in timeChanges:
            if int(change) <= m_idxs[0]:
                meter_first = beatsInfo[change]
            if int(change) <= m_idxs[-1]:
                meter_final = beatsInfo[change]

        # check that the requested beat actually fits in the meter
        if tstamp_first > int(meter_first["count"]) or tstamp_final > int(meter_final["count"]):
            abort(400, error="400", message="Request beat is out of measure bounds")

        # FIRST MEASURE
        staves = self.staves
        data_first = staves[0]

        # TODO: beware of @duration.default - though not very common

        def _calculateDur(element):
            duration = element.getAttribute("dur").getValue()
            dots = 0
            if element.getAttribute("dots"):
                dots = int(element.getAttribute("dots").getValue())
            elif element.getChildrenByName("dot"):
                dots = len(element.getChildrenByName("dot"))

            dotsvalue = duration
            for d in range(1, int(dots)+1):
                dotsvalue = dotsvalue * 2
                duration += dotsvalue

            return duration

        # Start by counting durations of on-staff elements
        for staff in data_first["on"]:
            # Find all descendants with att.duration.musical (@dur)
            cur_beat = 0.0
            if staff: #staves can also be "silent"
                for el in staff.getDescendants():
                    if el.hasAttribute("dur"):                    
                        dur = _calculateDur(el)
                        cur_beat += float(int(meter_first["unit"]) / float(dur))
                        # exclude descendants before tstamp
                        if cur_beat <= tstamp_first: 
                            el.getParent().removeChild(el)


        # LAST MEASURE
        data_first = staves[-1]

        # Start by counting durations of on-staff elements
        for staff in data_first["on"]:
            # Find all descendants with att.duration.musical (@dur)
            cur_beat = 0.0
            if staff: #staves can also be "silent"
                for el in staff.getDescendants():
                    if el.hasAttribute("dur"):
                        dur = _calculateDur(el)
                        cur_beat += float(int(meter_final["unit"]) / float(dur))
                        # exclude decendants after tstamp
                        if cur_beat > tstamp_final: 
                            el.getParent().removeChild(el)

        return self.staves

    def getMultiMeasureSpanners(self, end=-1):
        """Return a dictionary of spanning elements landing or starting within selected measures"""
        mm = self.musicEl.getDescendantsByName("measure")
        table = {}

        # Template of table dictionary (for reference):
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
        """ Return a modified MEI doc containing the selected notation"""

        mm = self.measures

        # Go through the children of selected measures. 
        # Keep those matching elements in m["on"] and m["around"].

        selected = self.beats

        for i, m in enumerate(mm):
            for el in m.getChildren():
                if el not in selected[i]["on"] and el not in selected[i]["around"]:
                    m.removeChild(el)

        # Then recursively remove all unwanted siblings of selected measures.
        # TODO: Take completeness parameter into account.

        def _removeBefore(curEl):
            parent = curEl.getParent()
            if parent:
                for el in curEl.getPeers():
                    if el == curEl:
                        break
                    else:
                        parent.removeChild(el)
                return _removeBefore(parent)
            return curEl

        def _removeAfter(curEl):
            parent = curEl.getParent()
            if parent:
                removing = False
                for el in curEl.getPeers():
                    if removing:
                        parent.removeChild(el)
                    elif el == curEl: 
                        removing = True
                return _removeAfter(parent)
            return curEl

        # Apply
        _removeBefore(mm[0])
        _removeAfter(mm[-1])

        return self.meiDoc


    #TODO add support for keywords "start" and "end"
    def _parseRanges(self, rang):
        """Generic method for parsing ranges as specified in the EMA API"""

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
                abort(400, error="400", message="Invalid range format")

        return ranges