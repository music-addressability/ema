from meiinfo import MusDocInfo
from emaexpression import EmaExpression
from omas.exceptions import BadApiRequest
from omas.exceptions import UnsupportedEncoding

import re
from pymei import MeiElement, MeiAttribute
from pymeiext import getClosestStaffDefs, moveTo
import collections


class MeiSlicer(object):
    """Class for slicing an MEI doc given a split EMA expresion. """
    def __init__(self, doc, req_m, req_s, req_b, completeness=None):
        self.doc = doc
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

        for em in self.ema_measures:
            self.processContigRange(em)

        return self.doc

    def processContigRange(self, ema_range):
        """ Process a contigous range of measures give an MEI doc and an
            EmaExpression.EmaMeasureRange object """

        # get all the spanners for total extension of meaure selection
        # (including gap measures, if present)
        # NB: Doing this for every range may be inefficient for larger files
        spanners = self.getMultiMeasureSpanners(ema_range.measures[0].idx-1,
                                                ema_range.measures[-1].idx-1)

        # Let's start with measuress)
        for ema_m, last_m in iter_islast(ema_range.measures):

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
            s_nos = set()

            # Proceed to locate requested staves
            for ema_s in ema_m.staves:
                s_no = ema_s.number
                s_nos.add(s_no)
                # Make sure that the required staff is not out of bounds.
                if s_no not in sds:
                    # CAREFUL: there may be issues with "silent" staves
                    # that may be defined by missing from current measure.
                    # TODO: Write test, fix.
                    raise BadApiRequest("Requested staff is not defined")

                #  If staff elements have @n, use it to select the correct staff,
                # otherwise default to element position order (risky).
                staff = None
                for staff_candidate in measure.getDescendantsByName("staff"):
                    if staff_candidate.hasAttribute("n"):
                        n = int(staff_candidate.getAttribute("n").getValue())
                        if n == s_no:
                            staff = staff_candidate
                if not staff:
                    mei_staves = measure.getDescendantsByName("staff")
                    if len(mei_staves) >= s_no:
                        staff = mei_staves[s_no]

                # Get other elements affecting the staff, e.g. slurs
                around = []

                for el in events:
                    if self._getSelectedStaffNosFor(el, ema_m.idx, s_no):
                        around.append(el)

                # Populate this with selected events
                around_events = []
                # Create sets of elements marked for selection, removal and
                # cutting. Elements are not removed or cut immediately to make
                # sure that beat calcualtions are accurate.
                marked_as_selected = ElementSet()
                marked_as_space = ElementSet()
                marked_for_removal = ElementSet()
                marked_for_cutting = ElementSet()

                # Now locate the requested beat ranges within the staff
                for ema_beat_range, last_b in iter_islast(ema_s.beat_ranges):

                    def _remove(el):
                        """ Determine whether a removed element needs to
                        be converted to a space or removed altogether"""
                        if last_b and last_m:
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
                                        # print marked_as_space

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
                                            print "r", i
                                            if i.hasAttribute("dur"):
                                                print i
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

                # INCLUDE SPANNERS

                # Locate events landing on or including this staff
                # from out of range measures (eg a long slur),
                # and append to first measure in selection

                # Include spanners from table
                # for events in spanners.values():
                #     for event_id in events:
                #         event = self.doc.getElementById(event_id)

                #         # Determine staff of event for id changes
                #         staff = 0
                #         staff_nos = self._getSelectedStaffNosFor(event)
                #         if staff_nos:
                #             staff = self.exp.staffRange.index(staff_nos[0])

                #         # Truncate event to start at the beginning of the beat range
                #         if event.hasAttribute("startid"):
                #             # Set startid to the first event still on staff,
                #             # at the first available layer
                #             try:
                #                 layer = (
                #                     staves_by_measure[0]["on"][staff]
                #                     .getChildrenByName("layer")
                #                 )
                #                 first_id = layer[0].getChildren()[0].getId()
                #                 event.getAttribute("startid").setValue("#"+first_id)
                #             except IndexError:
                #                 msg = """
                #                     Unsupported encoding. Omas attempted to adjust the
                #                     starting point of a selected multi-measure element
                #                     that starts before the selection, but the staff or
                #                     layer could not be located.
                #                     """
                #                 msg = re.sub(r'\s+', ' ', msg.strip())
                #                 raise UnsupportedEncoding(msg)

                #         if event.hasAttribute("tstamp"):
                #             # Set tstamp to first in beat selection
                #             event.getAttribute("tstamp").setValue(str(tstamp_first))

                #         # Truncate to end of range if completeness = cut
                #         if "cut" in self.exp.completenessOptions:
                #             if event.hasAttribute("tstamp2"):
                #                 att = event.getAttribute("tstamp2")
                #                 t2 = att.getValue()
                #                 p = re.compile(r"([1-9]+)(?=m\+)")
                #                 multimeasure = p.match(t2)
                #                 if multimeasure:
                #                     new_val = len(mm) - 1
                #                     att.setValue(p.sub(str(new_val), t2))
                #             if event.hasAttribute("endid"):
                #                 if events[event_id]["distance"] > 0:
                #                     # Set end to the last event on staff
                #                     try:
                #                         layer = (
                #                             staves_by_measure[-1]["on"][staff]
                #                             .getChildrenByName("layer")
                #                         )
                #                         last_id = layer[0].getChildren()[-1].getId()
                #                         event.getAttribute("endid").setValue("#"+last_id)
                #                     except IndexError:
                #                         msg = """
                #                             Unsupported encoding. Omas attempted to
                #                             adjust the ending point of a selected
                #                             multi-measure element that ends after the
                #                             selection, but the staff or layer could not
                #                             be located.
                #                             """
                #                         msg = re.sub(r'\s+', ' ', msg.strip())
                #                         raise UnsupportedEncoding(msg)

                #         # Otherwise adjust tspan2 value to correct distance.
                #         # E.g. given 4 measures with a spanner originating
                #         # in 1 and ending in 4 and a selection of measures 2 and 3,
                #         # change @tspan2 from 3m+X to 2m+X
                #         else:
                #             if event.hasAttribute("tstamp2"):
                #                 att = event.getAttribute("tstamp2")
                #                 t2 = att.getValue()
                #                 p = re.compile(r"([1-9]+)(?=m\+)")
                #                 multimeasure = p.match(t2)
                #                 if multimeasure:
                #                     dis = events[event_id]["distance"]
                #                     new_val = int(multimeasure.group(1)) - dis
                #                     att.setValue(p.sub(str(new_val), t2))

                #         # move element to first measure and add it to selected
                #         # events "around" the staff.
                #         event.moveTo(mm[0])
                #         staves_by_measure[0]["around"].append(event)

        return self.doc


    def getMultiMeasureSpanners(self, start, end=-1):
        """Return a dictionary of spanning elements ecompassing,
           or landing or starting within selected measures"""
        mm = self.musicEl.getDescendantsByName("measure")
        start_m = mm[start]
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


    def _getSelectedStaffNosFor(self, el, m_idx, s_no):
        """ Get staff numbers of element if the staves in given measure
            are selected"""
        # TODO: CAREFUL - EDITORIAL MARKUP MAY OBFUSCATE THIS
        values = []

        if el.hasAttribute("staff"):
            # Split value of @staff, as it may contain multiple values.
            values = el.getAttribute("staff").getValue().split()
            values = [int(x) for x in values]

            if s_no in values:
                return values
            else:
                values = []
        return values


def iter_islast(iterable):
    """ Generates pairs where the first element is an item from the iterable
    source and the second element is a boolean flag indicating if it is the
    last item in the sequence.
    """

    it = iter(iterable)
    prev = it.next()
    for item in it:
        yield prev, False
        prev = item
    yield prev, True


class ElementSet(object):
    """ Helper class to manage sets of MeiElement objects """
    def __init__(self):
        self._set = collections.OrderedDict()

    def __iter__(self):
        return iter(self._set.values())

    def __str__(self):
        return str(self._set.values())

    def add(self, el):
        self._set[el.id] = el

    def discard(self, el):
        self._set.pop(el.id, None)

    def get(self, el):
        return self._set.get(el.id, None)

    def getElements(self):
        return self._set.values()
