from meiinfo import MusDocInfo
from emaexpression import EmaExpression
from omas.exceptions import BadApiRequest
from omas.exceptions import UnsupportedEncoding

import re
from pymei import MeiElement, MeiAttribute
from pymeiext import getClosestStaffDefs, moveTo


def slice(doc, req_m, req_s, req_b, completeness):
    """ Return a modified MEI doc containing the selected notation
        provided a EMA expression of measures, staves, and beats."""
    
    # Store useful MEI data
    docInfo = MusDocInfo(doc).get()
    musicEl = doc.getElementsByName("music")[0]
    measures = musicEl.getDescendantsByName("measure")

    # Parse EMA expression
    ema_exp = EmaExpression(docInfo,
                            req_m,
                            req_s,
                            req_b,
                            completeness)
    ema_measures = ema_exp.get()

    # parse general beats information
    beatsInfo = docInfo["beats"]
    timeChanges = beatsInfo.keys()
    timeChanges.sort(key=int)

    # Let's start with measures
    for ema_m in ema_measures:
        
        # Get requested measure
        measure = measures[ema_m.idx-1]
        events = measure.getChildren()

        # determine current measure beat info          
        meter = None
        for change in timeChanges:
            if int(change)+1 <= ema_m.idx:
                meter = beatsInfo[change]

        # Get list of staff numbers in current measure
        sds = [int(sd.getAttribute("n").getValue())
               for sd in measure.getClosestStaffDefs()]

        # Set aside selected staff numbers
        s_nos = []

        # Proceed to locate requested staves
        for ema_s in ema_m.staves:
            s_no = ema_s.number
            s_nos.append(s_no)
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
                if _getSelectedStaffNosFor(el, ema_m.idx, s_no):
                    around.append(el)

            # Populate this with selected events
            around_events = []

            # Now locate the requested beat ranges within the staff
            for ema_beat_range in ema_s.beat_ranges:

                # shorten them names
                tstamp_first = ema_beat_range.tstamp_first
                tstamp_final = ema_beat_range.tstamp_final

                # check that the requested beats actually fit in the meter
                if tstamp_first > int(meter["count"]) or \
                   tstamp_final > int(meter["count"]):
                    raise BadApiRequest(
                        "Request beat is out of measure bounds")

                # Set a list of elements marked for removal
                # Elements are not removed or cut immediately to make sure that 
                # beat calcualtions are accurate.
                marked_as_selected = []
                marked_for_cutting = []

                # Find all descendants with att.duration.musical (@dur)
                for layer in staff.getDescendantsByName("layer"):
                    cur_beat = 0.0
                    for el in layer.getDescendants():
                        if el.hasAttribute("dur"):
                            dur = _calculateDur(el, meter)
                            # exclude descendants at and in between tstamps
                            if cur_beat + dur >= tstamp_first:
                                if cur_beat < tstamp_final:
                                    marked_as_selected.append(el)

                                    # Cut the duration of the last element if
                                    # completeness = cut
                                    if cur_beat + dur > tstamp_final and \
                                       "cut" in ema_exp.completenessOptions: 
                                        marked_for_cutting.append(el)
                            # continue
                            cur_beat += dur

                # select elements affect staff that occuring within beat range
                for event in around:
                    if event.hasAttribute("tstamp"):
                        ts = float(event.getAttribute("tstamp").getValue())
                        if tstamp_first <= ts <= tstamp_final:
                            if event not in around_events:
                                around_events.append(event)
                    elif event.hasAttribute("startid"):
                        startid = (
                            event.getAttribute("startid")
                            .getValue()
                            .replace("#", "")
                        )
                        target = doc.getElementById(startid)
                        # Make sure the target event is in the same measure
                        event_m = event.getAncestor("measure").getId()
                        target_m = target.getAncestor("measure").getId()
                        if not event_m == target_m:
                            msg = """Unsupported Encoding: attribute startid on
                            element {0} does not point to an element in the
                            same measure.""".format(event.getName())
                            raise UnsupportedEncoding(
                                re.sub(r'\s+', ' ', msg.strip()))
                        else:
                            if target in marked_as_selected:
                                if event not in around_events:
                                    around_events.append(event)

            print around_events
                

    # mm = self.measures
    # m_first = mm[0]
    # m_final = mm[-1]

    # # Go through the children of selected measures.
    # # Keep those matching elements in measure["on"] and measure["around"].

    # selected = self.beats

    # for i, m in enumerate(mm):
    #     # Casting MeiElementList to Python list to avoid modifying
    #     # the sequence while looping through and removing elements.
    #     for el in list(m.getChildren()):
    #         on = selected[i]["on"]
    #         around = selected[i]["around"]
    #         if el not in on and el not in around:
    #             m.removeChild(el)

    # # Then recursively remove all unwanted siblings of selected measures.

    # # List of elements to keep, to be adjusted according to parameters
    # keep = ["meiHead"]

    # def _removeBefore(curEl):
    #     parent = curEl.getParent()
    #     if parent:
    #         # Casting to list to avoid modfying the sequence
    #         for el in list(curEl.getPeers()):
    #             if el == curEl:
    #                 break
    #             else:
    #                 if not el.getName() in keep:
    #                     parent.removeChild(el)
    #         return _removeBefore(parent)
    #     return curEl

    # def _removeAfter(curEl):
    #     parent = curEl.getParent()
    #     if parent:
    #         removing = False
    #         # Casting to list to avoid modfying the sequence
    #         for el in list(curEl.getPeers()):
    #             if removing:
    #                 if not el.getName() in keep:
    #                     parent.removeChild(el)
    #             elif el == curEl:
    #                 removing = True
    #         return _removeAfter(parent)
    #     return curEl

    # def _findLowestCommonAncestor(el1, el2):
    #     while not el1 == el2:
    #         el1 = el1.getParent()
    #         el2 = el2.getParent()
    #     return el1

    # # Compute closest score definition to start measure
    # allEls = self.meiDoc.getFlattenedTree()
    # preceding = allEls[:m_first.getPositionInDocument()]

    # scoreDef = None

    # for el in reversed(preceding):
    #     if el.getName() == "scoreDef":
    #         scoreDef = el

    # # Remove definitions of unselected staves everywhere
    # s_nos = self.exp.staffRange
    # root = self.meiDoc.getRootElement()
    # for sd in list(root.getDescendantsByName("staffDef")):
    #     if sd.hasAttribute("n"):
    #         if not int(sd.getAttribute("n").getValue()) in s_nos:
    #             sd.getParent().removeChild(sd)
    #             # Remove parent staffGrp if this is the last staffDef
    #             sg = sd.getAncestor("staffGrp")
    #             if sg:
    #                 if len(sg.getDescendantsByName("staffDef")) <= 1:
    #                     sg.getParent().removeChild(sg)
    #                 else:
    #                     sd.getParent().removeChild(sd)

    # # Recursively remove elements before and after selected measures
    # _removeBefore(m_first)
    # _removeAfter(m_final)

    # # Then re-attach computed score definition
    # sec_first = m_first.getAncestor("section")
    # sec_first.getParent().addChildBefore(sec_first, scoreDef)

    # if "raw" in self.exp.completenessOptions:
    #     lca = _findLowestCommonAncestor(mm[0], mm[-1])
    #     self.meiDoc.setRootElement(lca)

    #     # re-attach computed score definition if required by
    #     # completeness = signature
    #     if "signature" in self.exp.completenessOptions:
    #         m_first.getParent().addChildBefore(m_first, scoreDef)

    # return self.meiDoc


def _calculateDur(element, meter):
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


def _cutDuration(element, meter):
    """ Cut the duration of given element to the final beat """
    element.getAttribute("dur").setValue(str(meter["unit"]))
    # Remove dots if any
    element.removeAttribute("dots")
    element.removeChildrenByName("dot")


def _getSelectedStaffNosFor(el, m_idx, s_no):
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
