from meiinfo import MusDocInfo
from omas.exceptions import BadApiRequest

import re
from pymei import MeiElement, MeiAttribute
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
    def measureRange(self):
        """Return list of indexes of requested measure"""

        end = str(self.docInfo["measures"])

        rang = self.requested_measures.replace("start", "1").replace("end", end)

        return self._parseNumericRanges(rang)

    @property
    def staffRange(self):
        """Return list of indexes of requested staves"""

        # Locate number of staved defined at beggining of selection
        m = self.measureRange[0]-1        
        info = self.docInfo["staves"]
        closestDef = str(min(info, key=lambda x:abs(int(x)-int(m))))
        
        end = str(len(info[closestDef]))

        rang = self.requested_staves.replace("start", "1").replace("end", end)

        return self._parseNumericRanges(rang)

    @property
    def beatRange(self):
        """Return two-item list of start and end beat (timestamps)"""

        m = self.measureRange[-1]
        info = self.docInfo["beats"]
        closestDef = str(min(info, key=lambda x:abs(int(x)-int(m))))

        end = str(info[closestDef]["count"])

        rang = self.requested_beats.replace("start", "1").replace("end", end)

        return rang.split("-")

    @property
    def completenessOptions(self):
        """Return list of completeness options"""

        opts = []
        
        if self.completeness:
            opts = self.completeness.split(",")

        return opts

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
        m_idxs = self.measureRange

        for m_idx in m_idxs:
            selected.append(mm[m_idx-1])

        return selected

    @property
    def staves(self):
        """Return selected staves"""
        selected = []
        s_nos = self.staffRange
        
        # Make sure that required staves are not out of bounds.
        mm = self.measures
        sds = [int(sd.getAttribute("n").getValue()) for sd in mm[0].getClosestStaffDefs()]

        for s_no in s_nos:
            if s_no not in sds:
                raise BadApiRequest("Requested staves are not defined")

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
            m_idx = self.measureRange[0] - 1
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
        tstamps = self.beatRange
        m_idxs = self.measureRange

        # According to the API, the beat selection must be a range,
        # even when only one beat is selected.
        if len(tstamps) != 2:
            raise BadApiRequest("Invalid beat range")

        tstamp_first = int(tstamps[0])
        tstamp_final = int(tstamps[1])

        beatsInfo = self.docInfo["beats"]

        meter_first = None
        meter_final = None

        # get the closest beat info to the index of each measure
        timeChanges = beatsInfo.keys()
        timeChanges.sort(key=int)
        for change in timeChanges:
            if int(change)+1 <= m_idxs[0]:
                meter_first = beatsInfo[change]
            if int(change)+1 <= m_idxs[-1]:
                meter_final = beatsInfo[change]

        # check that the requested beat actually fits in the meter
        if tstamp_first > int(meter_first["count"]) or tstamp_final > int(meter_final["count"]):
            raise BadApiRequest("Request beat is out of measure bounds")

        def _calculateDur(element, meter):
        # TODO: beware of @duration.default - though not very common
            duration = int(element.getAttribute("dur").getValue())
            relative_dur = float(int(meter["unit"]) / float(duration))

            dots = 0
            if element.getAttribute("dots"):
                dots = int(element.getAttribute("dots").getValue())
            elif element.getChildrenByName("dot"):
                dots = len(element.getChildrenByName("dot"))

            dot_dur = duration
            for d in range(1, int(dots)+1):
                dot_dur = dot_dur * 2
                relative_dur += float(int(meter["unit"]) / float(dot_dur))

            return relative_dur

        # Set a dictionary of elements marked for removal, organized by measure
        # Elements are not removed immediately to make sure that beat
        # calcualtions are accurate.
        marked_for_removal = {"first" : [], "last" : []}

        staves = self.staves

        # FIRST MEASURE

        # Start by counting durations of on-staff elements
        for staff in staves[0]["on"]:
            # Find all descendants with att.duration.musical (@dur)
            cur_beat = 0.0
            if staff: #staves can also be "silent"
                for el in staff.getDescendants():
                    if el.hasAttribute("dur"):
                        cur_beat += _calculateDur(el, meter_first)
                        # exclude descendants before tstamp, 
                        # unless they end after or on tstamp
                        if cur_beat < tstamp_first: 
                            marked_for_removal["first"].append(el)

        # LAST MEASURE

        # Start by counting durations of on-staff elements
        for staff in staves[-1]["on"]:
            # Find all descendants with att.duration.musical (@dur)
            cur_beat = 0.0
            if staff: #staves can also be "silent"
                for el in staff.getDescendants():
                    if el.hasAttribute("dur"):
                        cur_beat += _calculateDur(el, meter_final)
                        # exclude decendants after tstamp
                        if cur_beat > tstamp_final: 
                            marked_for_removal["last"].append(el)

        # Remove elements marked for deletion
        for el in marked_for_removal["first"]:
            parent = el.getParent()
            # Add space element to replace the one marked for deletion
            # unless completeness is set to nospace
            if "nospace" not in self.completenessOptions:
                space = MeiElement("space")
                space.addAttribute(el.getAttribute("dur"))
                if el.getAttribute("dots"):
                    space.addAttribute(el.getAttribute("dots"))
                elif el.getChildrenByName("dot"):
                    dots = str(len(el.getChildrenByName("dot")))
                    space.addAttribute( MeiAttribute("dots", dots) )
                parent.addChildBefore(el, space)
            el.getParent().removeChild(el)

        for el in marked_for_removal["last"]:
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
        m_first = mm[0]
        m_final = mm[-1]

        # Go through the children of selected measures. 
        # Keep those matching elements in m["on"] and m["around"].

        selected = self.beats

        for i, m in enumerate(mm):
            for el in m.getChildren():
                if el not in selected[i]["on"] and el not in selected[i]["around"]:
                    m.removeChild(el)

        # Then recursively remove all unwanted siblings of selected measures.        

        # List of elements to keep, to be adjusted according to parameters
        keep = ["meiHead"]

        def _removeBefore(curEl):
            parent = curEl.getParent()
            if parent:
                for el in curEl.getPeers():
                    if el == curEl:
                        break
                    else:
                        if not el.getName() in keep:
                            parent.removeChild(el)
                return _removeBefore(parent)
            return curEl

        def _removeAfter(curEl):
            parent = curEl.getParent()
            if parent:
                removing = False
                for el in curEl.getPeers():
                    if removing:
                        if not el.getName() in keep:
                            parent.removeChild(el)
                    elif el == curEl: 
                        removing = True
                return _removeAfter(parent)
            return curEl

        def _findLowestCommonAncestor(el1, el2):
            while not el1 == el2:
                el1 = el1.getParent()
                el2 = el2.getParent()
            return el1

        # Compute closest score definition to start measure        
        allEls = self.meiDoc.getFlattenedTree()
        preceding = allEls[:m_first.getPositionInDocument()]

        scoreDef = None

        for el in reversed(preceding):
            if el.getName() == "scoreDef":
                scoreDef = el

        # Remove definitions of unselected staves
        s_nos = self.staffRange

        for sd in scoreDef.getDescendantsByName("staffDef"):            
            if sd.hasAttribute("n"):
                if not int(sd.getAttribute("n").getValue()) in s_nos:
                    # Remove parent staffGrp if this is the last staffDef
                    sg = sd.getAncestor("staffGrp")
                    if len(sg.getDescendantsByName("staffDef")) == 1:
                        sg.getParent().removeChild(sg)
                    else:
                        sd.getParent().removeChild(sd)
        
        # Recursively remove elements before and after selected measures
        _removeBefore(m_first)
        _removeAfter(m_final)

        # Then re-attach computed score definition
        sec_first = m_first.getAncestor("section")
        sec_first.getParent().addChildBefore(sec_first, scoreDef)


        if "raw" in self.completenessOptions:
            lca = _findLowestCommonAncestor(mm[0], mm[-1])
            self.meiDoc.setRootElement(lca)

            # re-attach computed score definition if required by
            # completeness = signature
            if "signature" in self.completenessOptions:
                m_first.getParent().addChildBefore(m_first, scoreDef)

        return self.meiDoc


    def _parseNumericRanges(self, rang):
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
                raise BadApiRequest("Invalid range format")

            if not ranges:
                raise BadApiRequest("Invalid range format")

        return ranges