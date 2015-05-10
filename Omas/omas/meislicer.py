from meiinfo import MusDocInfo
from emaexpression import EmaExpression
from omas.exceptions import BadApiRequest
from omas.exceptions import UnsupportedEncoding
from meielementset import MeiElementSet

import re
from pymei import MeiElement, MeiAttribute
from pymeiext import getClosestStaffDefs, moveTo


class MeiSlicer(object):
    """Class for slicing an MEI doc given a split EMA expresion. """
    def __init__(self, doc, req_m, req_s, req_b, completeness=None):
        self.doc = doc
        self.flat_doc = doc.getFlattenedTree()
        self.docInfo = MusDocInfo(doc).get()
        self.musicEl = doc.getElementsByName("music")[0]
        self.measures = self.musicEl.getDescendantsByName("measure")
        self.ema_exp = EmaExpression(self.docInfo,
                                     req_m,
                                     req_s,
                                     req_b,
                                     completeness)

        self.ema_measures = self.ema_exp.get()
        self.compiled_exp = self.ema_exp.getCompiled()

    def slice(self):
        """ Return a modified MEI doc containing the selected notation
            provided a EMA expression of measures, staves, and beats."""

        # parse general beats information
        self.beatsInfo = self.docInfo["beats"]
        self.timeChanges = self.beatsInfo.keys()
        self.timeChanges.sort(key=int)

        # Process measure ranges and store boundary measures
        boundary_mm = []
        for em in self.ema_measures:
            boundary_mm.append(em.measures[0].idx)
            boundary_mm.append(em.measures[-1].idx)
            self.processContigRange(em)

        # Recursively remove remaining data in between
        # measure ranges before returning modified doc

        # First remove measures in between
        # TODO: remove score/staffDefs in between and other elements...
        to_remove = []
        middle_boundaries = boundary_mm[1:-1]
        for bm in middle_boundaries[::2]:
            i = middle_boundaries.index(bm)
            try:
                start_m = self.measures[bm-1]
                start_m_pos = start_m.getPositionInDocument()
                end_m = self.measures[middle_boundaries[i+1]-1]
                end_m_pos = end_m.getPositionInDocument()
                for el in self.flat_doc[start_m_pos+1:end_m_pos]:
                    if el.hasAncestor("measure"):
                        if el.getAncestor("measure").getId() != start_m.getId():
                            to_remove.append(el)
                    else:
                        to_remove.append(el)
            except IndexError:
                pass

        m_first = self.measures[boundary_mm[0]-1]
        m_final = self.measures[boundary_mm[-1]-1]

        # List of elements to keep
        keep = ["meiHead"]

        def _removeBefore(curEl):
            parent = curEl.getParent()
            if parent:
                # Casting to list to avoid modfying the sequence
                for el in list(curEl.getPeers()):
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
                # Casting to list to avoid modfying the sequence
                for el in list(curEl.getPeers()):
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

        # TODO! Remove definitions of unselected staves WITHIN RANGE

        # Compute closest score definition to start measure
        preceding = self.flat_doc[:m_first.getPositionInDocument()]

        first_scoreDef = None

        for el in reversed(preceding):
            if el.getName() == "scoreDef":
                first_scoreDef = el
                break

        # Recursively remove elements before and after selected measures
        _removeBefore(m_first)
        _removeAfter(m_final)

        # Compute closest score definition to start measure of each range
        b_scoreDef = first_scoreDef
        for bm in boundary_mm[::2]:  # list comprehension get only start mm
            b_measure = self.measures[bm-1]
            preceding = self.flat_doc[:b_measure.getPositionInDocument()]

            for el in reversed(preceding):
                if el.getName() == "scoreDef":
                    try:
                        s_id = b_scoreDef.getId()
                        if s_id == el.getId():
                            # Re-attach computed score definition
                            sec = b_measure.getAncestor("section")
                            copy = MeiElement(b_scoreDef)
                            sec.getParent().addChildBefore(sec, copy)
                        else:
                            # new scoreDef
                            b_scoreDef = el
                    except AttributeError:
                        b_scoreDef = el
                    break

        for el in to_remove:
            el.getParent().removeChild(el)

        if "raw" in self.ema_exp.completenessOptions:
            lca = _findLowestCommonAncestor(m_first, m_final)
            self.doc.setRootElement(lca)

            # re-attach computed score definition if required by
            # completeness = signature
            if "signature" in self.ema_exp.completenessOptions:
                m_first.getParent().addChildBefore(m_first, first_scoreDef)

        return self.doc

    def processContigRange(self, ema_range):
        """ Process a contigous range of measures give an MEI doc and an
            EmaExpression.EmaMeasureRange object """

        # get all the spanners for total extension of meaure selection
        # (including gap measures, if present)
        # NB: Doing this for every range may be inefficient for larger files
        spanners = self.getMultiMeasureSpanners(ema_range.measures[0].idx-1,
                                                ema_range.measures[-1].idx-1)

        # Let's start with measures
        for i, ema_m in enumerate(ema_range.measures):

            is_first_m = i == 0
            is_last_m = i == len(ema_range.measures)-1

            # Get requested measure
            measure = self.measures[ema_m.idx-1]
            events = measure.getChildren()

            # determine current measure beat info
            meter = None
            for change in self.timeChanges:
                if int(change)+1 <= ema_m.idx:
                    meter = self.beatsInfo[change]

            # Get list of staff numbers in current measure
            sds = [int(sd.getAttribute("n").getValue())
                   for sd in measure.getClosestStaffDefs()]

            # Set aside selected staff numbers
            s_nos = []

            # Proceed to locate requested staves
            for ema_s in ema_m.staves:
                if ema_s.number not in sds:
                    # CAREFUL: there may be issues with "silent" staves
                    # that may be defined by missing from current measure.
                    # TODO: Write test, fix.
                    raise BadApiRequest("Requested staff is not defined")
                s_nos.append(ema_s.number)

            for s_i, staff in enumerate(measure.getChildrenByName("staff")):
                s_no = s_i
                if staff.hasAttribute("n"):
                    s_no = int(staff.getAttribute("n").getValue())

                if s_no in s_nos:
                    ema_s = ema_m.staves[s_nos.index(s_no)]

                    # Get other elements affecting the staff, e.g. slurs
                    around = []

                    for el in events:
                        if self._isInStaff(el, s_no):
                            around.append(el)

                    # Create sets of elements marked for selection, removal and
                    # cutting. Elements are not removed or cut immediately to make
                    # sure that beat calcualtions are accurate.
                    marked_as_selected = MeiElementSet()
                    marked_as_space = MeiElementSet()
                    marked_for_removal = MeiElementSet()
                    marked_for_cutting = MeiElementSet()

                    # Now locate the requested beat ranges within the staff
                    for b_i, ema_beat_range in enumerate(ema_s.beat_ranges):

                        is_first_b = i == 0
                        is_last_b = i == len(ema_s.beat_ranges)-1

                        def _remove(el):
                            """ Determine whether a removed element needs to
                            be converted to a space or removed altogether"""
                            if is_last_b and is_last_m:
                                marked_for_removal.add(el)
                            else:
                                marked_as_space.add(el)

                        # shorten them names
                        tstamp_first = ema_beat_range.tstamp_first
                        tstamp_final = ema_beat_range.tstamp_final
                        co = self.ema_exp.completenessOptions

                        # check that the requested beats actually fit in the meter
                        if tstamp_first > int(meter["count"]) or \
                           tstamp_final > int(meter["count"]):
                            raise BadApiRequest(
                                "Request beat is out of measure bounds")

                        # Find all descendants with att.duration.musical (@dur)
                        for layer in staff.getDescendantsByName("layer"):
                            cur_beat = 0.0
                            is_first_match = True

                            for el in layer.getDescendants():

                                if el.hasAttribute("dur"):
                                    dur = self._calculateDur(el, meter)
                                    # exclude descendants at and in between tstamps
                                    if cur_beat + dur >= tstamp_first:
                                        if cur_beat < tstamp_final:
                                            marked_as_selected.add(el)
                                            if is_first_match and "cut" in co:
                                                marked_for_cutting.add(el)
                                                is_first_match = False

                                            # discard from removal set if it had
                                            # been placed there from other beat
                                            # range print marked_as_space
                                            marked_as_space.discard(el)

                                            # Cut the duration of the last element
                                            # if completeness = cut
                                            needs_cut = cur_beat+dur > tstamp_final
                                            if needs_cut and "cut" in co:
                                                marked_for_cutting.add(el)
                                                is_first_match = False
                                        elif not marked_as_selected.get(el):
                                            _remove(el)
                                    elif not marked_as_selected.get(el):
                                        marked_as_space.add(el)

                                    # continue
                                    cur_beat += dur

                        # select elements affecting the staff occurring
                        # within beat range
                        for event in around:
                            if not marked_as_selected.get(event):
                                if event.hasAttribute("tstamp"):
                                    ts = float(event.getAttribute("tstamp").getValue())
                                    ts2_att = None
                                    if event.hasAttribute("tstamp2"):
                                        ts2_att = event.getAttribute("tstamp2")
                                    if ts > tstamp_final or (not ts2_att and ts < tstamp_first):
                                        marked_for_removal.add(event)
                                    elif ts2_att:
                                        ts2 = ts2_att.getValue()
                                        if "+" not in ts2:
                                            if ts2 < tstamp_first:
                                                marked_for_removal.add(event)
                                            elif ts2 == tstamp_final:
                                                marked_as_selected.add(event)
                                                marked_for_removal.discard(event)
                                            if ts < tstamp_first and ts2 >= tstamp_final:
                                                marked_as_selected.add(event)
                                                marked_for_removal.discard(event)
                                            else:
                                                marked_for_removal.add(event)
                                        else:
                                            marked_as_selected.add(event)
                                    else:
                                        marked_as_selected.add(event)

                                elif event.hasAttribute("startid"):
                                    startid = (
                                        event.getAttribute("startid")
                                        .getValue()
                                        .replace("#", "")
                                    )
                                    target = self.doc.getElementById(startid)
                                    # Make sure the target event is in the same measure
                                    event_m = event.getAncestor("measure").getId()
                                    target_m = target.getAncestor("measure").getId()
                                    if not event_m == target_m:
                                        msg = """Unsupported Encoding: attribute
                                        startid on element {0} does not point to an
                                        element in the same measure.""".format(
                                            event.getName())
                                        raise UnsupportedEncoding(
                                            re.sub(r'\s+', ' ', msg.strip()))
                                    else:
                                        if marked_as_selected.get(target):
                                            marked_as_selected.add(event)
                                            marked_for_removal.discard(event)
                                        elif not event.hasAttribute("endid"):
                                            marked_for_removal.add(event)
                                        else:
                                            # Skip if event starts after latest
                                            # selected element with duration
                                            pos = target.getPositionInDocument()
                                            is_ahead = False
                                            for i in reversed(marked_as_selected.getElements()):
                                                if i.hasAttribute("dur"):
                                                    if pos > i.getPositionInDocument():
                                                        marked_for_removal.add(event)
                                                        is_ahead = True
                                                    break

                                            if not is_ahead:
                                                # last chance to keep it:
                                                # must start before and end after
                                                # latest selected element with duration

                                                endid = (
                                                    event.getAttribute("endid")
                                                    .getValue()
                                                    .replace("#", "")
                                                )
                                                target2 = self.doc.getElementById(endid)
                                                if marked_as_selected.get(target2):
                                                    marked_as_selected.add(event)
                                                    marked_for_removal.discard(event)
                                                else:
                                                    pos2 = target2.getPositionInDocument()
                                                    for i in reversed(marked_as_selected.getElements()):
                                                        if i.hasAttribute("dur"):
                                                            if pos2 > i.getPositionInDocument():
                                                                marked_as_selected.add(event)
                                                                marked_for_removal.discard(event)
                                                            else:
                                                                marked_for_removal.add(event)
                                                            break

                    # Remove elements marked for removal
                    for el in marked_for_removal:
                        el.getParent().removeChild(el)

                    # Replace elements marked as spaces with actual spaces,
                    # unless completion = nospace, then remove the elements.
                    for el in marked_as_space:
                        parent = el.getParent()
                        if "nospace" not in self.ema_exp.completenessOptions:
                            space = MeiElement("space")
                            space.setId(el.id)
                            space.addAttribute(el.getAttribute("dur"))
                            if el.getAttribute("dots"):
                                space.addAttribute(el.getAttribute("dots"))
                            elif el.getChildrenByName("dot"):
                                dots = str(len(el.getChildrenByName("dot")))
                                space.addAttribute(MeiAttribute("dots", dots))
                            parent.addChildBefore(el, space)
                        el.getParent().removeChild(el)

                else:
                    # Remove this staff and its attached events
                    staff.getParent().removeChild(staff)

                    for el in events:
                        if self._isInStaff(el, s_no):
                            el.getParent().removeChild(el)

            # At the first measure, also add relevant multi-measure spanners
            # for each selected staff
            if is_first_m:
                for evs in spanners.values():
                    for event_id in evs:
                        ev = self.doc.getElementById(event_id)
                        # Spanners starting outside of beat ranges
                        # may be already gone
                        if ev:
                            # Determine staff of event for id changes
                            for ema_s in ema_m.staves:
                                staff_no = self._isInStaff(ev, ema_s.number)

                            if staff_no and staff_no in s_nos:
                                # If the event is attached to more than one staff, just
                                # consider it attached to the its first one
                                staff_no = staff_no[0]

                                staff = None
                                for staff_candidate in measure.getDescendantsByName("staff"):
                                    if staff_candidate.hasAttribute("n"):
                                        n = int(staff_candidate.getAttribute("n").getValue())
                                        if n == staff_no:
                                            staff = staff_candidate

                                # Truncate event to start at the beginning of the beat range
                                if ev.hasAttribute("startid"):
                                    # Set startid to the first event still on staff,
                                    # at the first available layer
                                    try:
                                        layer = (
                                            staff.getChildrenByName("layer")
                                        )
                                        first_id = layer[0].getChildren()[0].getId()
                                        ev.getAttribute("startid").setValue("#"+first_id)
                                    except IndexError:
                                        msg = """
                                            Unsupported encoding. Omas attempted to adjust the
                                            starting point of a selected multi-measure element
                                            that starts before the selection, but the staff or
                                            layer could not be located.
                                            """
                                        msg = re.sub(r'\s+', ' ', msg.strip())
                                        raise UnsupportedEncoding(msg)

                                if ev.hasAttribute("tstamp"):
                                    # Set tstamp to first in beat selection
                                    tstamp_first = 0
                                    for e_s in ema_m.staves:
                                        if e_s.number == staff_no:
                                            tstamp_first = e_s.beat_ranges[0].tstamp_first
                                    ev.getAttribute("tstamp").setValue(str(tstamp_first))

                                # Truncate to end of range if completeness = cut
                                # (actual beat cutting will happen when beat ranges are procesed)
                                if "cut" in self.ema_exp.completenessOptions:
                                    if ev.hasAttribute("tstamp2"):
                                        att = ev.getAttribute("tstamp2")
                                        t2 = att.getValue()
                                        p = re.compile(r"([1-9]+)(?=m\+)")
                                        multimeasure = p.match(t2)
                                        if multimeasure:
                                            new_val = len(mm) - 1
                                            att.setValue(p.sub(str(new_val), t2))

                                # Otherwise adjust tspan2 value to correct distance.
                                # E.g. given 4 measures with a spanner originating
                                # in 1 and ending in 4 and a selection of measures 2 and 3,
                                # change @tspan2 from 3m+X to 2m+X
                                else:
                                    if ev.hasAttribute("tstamp2"):
                                        att = ev.getAttribute("tstamp2")
                                        t2 = att.getValue()
                                        p = re.compile(r"([1-9]+)(?=m\+)")
                                        multimeasure = p.match(t2)
                                        if multimeasure:
                                            dis = evs[event_id]["distance"]
                                            new_val = int(multimeasure.group(1)) - dis
                                            att.setValue(p.sub(str(new_val), t2))

                                # move element to first measure and add it to selected
                                # events "around" the staff.
                                ev.moveTo(measure)

        return self.doc

    def getMultiMeasureSpanners(self, start, end=-1):
        """Return a dictionary of spanning elements encompassing,
           landing or starting within selected measures"""
        mm = self.musicEl.getDescendantsByName("measure")
        try:
            start_m = mm[start]
        except IndexError:
            raise BadApiRequest("Requested measure does not exist.")
        table = {}

        # Template of table dictionary (for reference):
        # {
        #     "_targetMeasureID_" : {
        #         "_eventID_" : {
        #             "origin" : "_originMeasureID_",
        #             "distance" : 0,
        #             "startid" : "_startID_",
        #             "endid" : "_endID_",
        #             "tstamp" : "_beat_",
        #             "tstamp2" : "_Xm+beat_"
        #         }
        #     }
        # }

        def _calculateDistance(origin):
            """ Calcualte distance of origin measure from
                first measure in selection """
            # Cast MeiElementList to python list
            list_mm = list(mm)
            return list_mm.index(start_m) - list_mm.index(origin)

        # Exclude end measure index from request,
        # unless last measure is requested (creates table for whole file).
        if end == -1:
            end = len(mm) + 1

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

                    target_el = self.doc.getElementById(endid)

                    if target_el:
                        if target_el.hasAncestor("measure"):
                            # This could be a comparison of objects,
                            # but comparing ids feels safer.
                            destination = target_el.getAncestor("measure")
                            if destination.getId() != prev_m.getId():
                                # Create table entry
                                dest_id = destination.getId()
                                distance = _calculateDistance(prev_m)
                                el_id = el.getId()

                                if dest_id not in table:
                                    table[dest_id] = {}
                                table[dest_id][el_id] = {
                                    "origin": m_id,
                                    "distance": distance,
                                    "endid": endid
                                }
                                if el.hasAttribute("startid"):
                                    startid = (
                                        el
                                        .getAttribute("startid")
                                        .getValue()
                                        .replace("#", "")
                                    )
                                    table[dest_id][el_id]["startid"] = startid
                elif el.hasAttribute("tstamp2"):
                    t2 = el.getAttribute("tstamp2").getValue()
                    multiMesSpan = re.match(r"([1-9]+)m\+", t2)
                    if multiMesSpan:
                        destination = mm[i + int(multiMesSpan.group(1))]
                        # Create table entry
                        dest_id = destination.getId()
                        distance = _calculateDistance(prev_m)
                        el_id = el.getId()

                        if dest_id not in table:
                            table[dest_id] = {}
                        table[dest_id][el_id] = {
                            "origin": m_id,
                            "distance": distance,
                            "tstamp2": t2
                        }
                        if el.hasAttribute("tstamp"):
                            table[dest_id][el_id]["tstamp"] = (
                                el
                                .getAttribute("tstamp")
                                .getValue()
                            )

        return table

    def _calculateDur(self, element, meter):
        """ Determine the duration of an element given a meter """
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


    def _cutDuration(self, element, meter):
        """ Cut the duration of given element to the final beat """
        element.getAttribute("dur").setValue(str(meter["unit"]))
        # Remove dots if any
        element.removeAttribute("dots")
        element.removeChildrenByName("dot")

    def _isInStaff(self, el, s_no):
        """ Get all staff numbers of element if element is in given staff"""
        values = self._getSelectedStaffNosFor(el)

        if s_no in values:
                return values
        else:
            values = []
        return values

    def _getSelectedStaffNosFor(self, el):
        """ Get staff numbers of element if the staves in given measure
            are selected"""
        # TODO: CAREFUL - EDITORIAL MARKUP MAY OBFUSCATE THIS
        values = []

        if el.hasAttribute("staff"):
            # Split value of @staff, as it may contain multiple values.
            values = el.getAttribute("staff").getValue().split()
            values = [int(x) for x in values]

        return values
