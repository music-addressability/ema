from omas.exceptions import BadApiRequest
import itertools

class EmaExpression(object):
    """ A class to parse an EMA expression given EMA information about a
        music document. """
    def __init__(self, docInfo, measures, staves, beats, completeness=None):
        self.docInfo = docInfo
        self.requested_measures = measures
        self.requested_staves = staves
        self.requested_beats = beats
        self.completeness = completeness

        # Re-organize a complex expression into a set of simpler ones.
        # For most EMA expressions this will result into just one expr.

        # Compile measure ranges

        end = str(self.docInfo["measures"])

        all_mm = "1-{0}".format(end)

        m_request = (
            self.requested_measures
            .replace("start", "1")
            .replace("end", end)
            .replace("all", all_mm)
            )

        mm_ranges = m_request.split(",")

        # Determine consecutive ranges and merge them.
        # e.g. 1-2,3 -> 1-3
        # 2,3 -> 2-3
        # 1-2,3-4 -> 1-4
        ranges = []
        for p in mm_ranges:
            if '-' in p:
                begin, end = map(int, p.split('-', 2))
            else:
                begin = end = int(p)
            ranges.append([begin, end])

        new_ranges = []

        for r in ranges:
            full = range(r[0], r[1]+1)
            if len(new_ranges) == 0:
                new_ranges.append(full)
            else:
                last_r = new_ranges[-1]
                if last_r[-1] + 1 == r[0]:
                    expanded = range(last_r[-1]+1,r[1]+1)
                    new_ranges[-1] = last_r + expanded
                else:
                    new_ranges.append(full)

        mm_ranges = new_ranges
        staves_by_m = self.requested_staves.split(",")
        beats_by_m = self.requested_beats.split(",")

        # In staves and beats, only one measure range is applied to
        # all measures
        # So flatten measure lists to expand staves and beats when needed
        merged = list(itertools.chain(*mm_ranges))

        if len(staves_by_m) == 1:
            for x in merged[:-1]:
                staves_by_m.append(staves_by_m[0])
        if len(beats_by_m) == 1:
            for x in merged[:-1]:
                beats_by_m.append(beats_by_m[0])

        # At this point, the ranges must match the number of measures
        if len(staves_by_m) != len(merged) or \
           len(beats_by_m) != len(merged):
            e = "Requested staff/beat ranges do not match measure ranges."
            raise BadApiRequest(e)

        selections = []
        for m_range in mm_ranges:
            start = merged.index(m_range[0])
            end = start + len(m_range)
            selection = EmaSingleRangeExpression(docInfo,
                                                 m_range,
                                                 staves_by_m[start:end],
                                                 beats_by_m[start:end])
            selections.append(selection)

        self.selections = selections

    def getCompiled(self):
        """ Return a list of compiled simplified EMA expresions """
        return [sel.getCompiled() for sel in self.selections]

    def get(self):
        """ Return a list of EMA mesure range objects.
            They contain other objects modelling staves and beats
        """
        ema_ranges = []
        for sel in self.selections:
            ema_range = EmaMeasureRange()
            ema_measures = []
            for m_i, m in enumerate(sel.measureRange):
                ema_m = EmaMeasure(idx=int(m))
                ema_staves = []
                for s_i, s in enumerate(sel.staffRanges[m_i]):
                    ema_s = EmaStaff(number=int(s), measure=ema_m)
                    ema_beat_ranges = []
                    for br in sel.beatRanges[m_i][s_i]:
                        ema_beat_ranges.append(
                            EmaBeatRange(range_str=br,
                                         measure=ema_m,
                                         staff=ema_s)
                        )
                    ema_s.setBeatRanges(ema_beat_ranges)
                    ema_staves.append(ema_s)
                ema_m.setStaves(ema_staves)
                ema_measures.append(ema_m)
            ema_range.setMeasures(ema_measures)
            ema_ranges.append(ema_range)

        return ema_ranges


class EmaSingleRangeExpression(object):
    """ A class to parse a single-range EMA expression.
        A single-range EMA expression may only select contiguous measures """
    def __init__(self, docInfo, measures, staves, beats):
        self.docInfo = docInfo
        self.requested_measures = measures
        self.requested_staves = staves
        self.requested_beats = beats

    @property
    def measureRange(self):
        """Return list of indexes of requested measures"""  
        self.compiled_measures = self.requested_measures
        return self.requested_measures

    @property
    def staffRanges(self):
        """Return list of indexes of requested staves, organized by measure"""

        # Locate number of staves defined at beggining of selection
        m = self.measureRange[0]-1
        info = self.docInfo["staves"]
        closestDef = str(min(info, key=lambda x: abs(int(x)-int(m))))

        end = str(len(info[closestDef]))

        all_s = "1-{0}".format(end)

        staves_by_m = []

        for measure in self.requested_staves:

            request = (
                measure
                .replace("start", "1")
                .replace("end", end)
                .replace("all", all_s)
                )

            staves = []
            for r in request.split("+"):
                staves = staves + self._parseNumericRanges(r)
            staves_by_m.append(staves)

        self.compiled_staves = ",".join(self.requested_staves)

        return staves_by_m

    @property
    def beatRanges(self):
        """Return list of request beats (timestamps) organized by
           staff and measure """

        # buils compiled expression
        compiled_staves = []

        beats_by_measure = []
        for m_i, m in enumerate(self.measureRange):
            beats_by_staff = []

            # only replace wildcards here once you know the measure context
            info = self.docInfo["beats"]
            closestDef = str(min(info, key=lambda x: abs(int(x)-int(m))))

            end = str(info[closestDef]["count"])

            all_b = "1-{0}".format(end)

            ranges = (
                self.requested_beats[m_i]
                .replace("start", "1")
                .replace("end", end)
                .replace("all", all_b)
                )

            # Only one staff range may need to be applied to all staves
            s_ranges = ranges.split("+")

            if len(s_ranges) == 1:
                for x in self.staffRanges[m_i][:-1]:
                    s_ranges.append(s_ranges[0])

            compiled_staves.append("+".join(s_ranges))

            for ra in s_ranges:
                beats = []
                for r in ra.split("@")[1:]:
                    # beat ranges are kept intact as it is easier to parse
                    # consequent beats based on the underlying music
                    # representation system.
                    beats.append(r)
                beats_by_staff.append(beats)

            # At this point, the ranges must match the number of staves
            if len(beats_by_staff) != len(self.staffRanges[m_i]):
                e = "Requested beat range does not match requested staff range"
                raise BadApiRequest(e)
            beats_by_measure.append(beats_by_staff)

        # store compiled expression
        self.compiled_beats = ",".join(compiled_staves)

        return beats_by_measure

    @property
    def completenessOptions(self):
        """Return list of completeness options"""

        opts = []

        if self.completeness:
            opts = self.completeness.split(",")

        return opts

    def _parseNumericRanges(self, rang):
        """Generic method for parsing ranges as specified in the EMA API"""

        ranges = []
        values = rang.split("-")
        length = len(values)

        values = [int(v) for v in values]

        if length == 1:
            ranges.append(values[0])
        elif length == 2:
            ranges += range(values[0], values[1]+1)
        else:
            raise BadApiRequest("Invalid range format")

        if not ranges:
            raise BadApiRequest("Invalid range format")

        return ranges

    def getCompiled(self):
        # Kick off selection
        self.beatRanges

        return "{0}/{1}/{2}".format(self.compiled_measures,
                                    self.compiled_staves,
                                    self.compiled_beats)


class EmaMeasureRange(object):
    """Object representing a range of EMA measures"""
    def __init__(self, measures=None):
        self.measures = measures

    def setMeasures(self, measures):
        self.measures = measures


class EmaMeasure(object):
    """Object representing an EMA measure"""
    def __init__(self, idx, staves=None):
        self.idx = idx
        self.staves = staves

    def setStaves(self, staves):
        self.staves = staves


class EmaStaff(object):
    """Object representing an EMA staff"""
    def __init__(self, number, measure,  br=None):
        self.number = number
        self.beat_ranges = br
        self.measure = measure

    def setBeatRanges(self, br):
        self.beat_ranges = br


class EmaBeatRange(object):
    """Object representing an EMA beat range"""
    def __init__(self, range_str, measure, staff):
        self.range_str = range_str
        self.measure = measure
        self.staff = staff

        tstamps = self.range_str.split("-")

        self.tstamp_first = float(tstamps[0])

        if len(tstamps) == 1:
            self.tstamp_final = float(tstamps[0])
        else:
            self.tstamp_final = float(tstamps[1])
