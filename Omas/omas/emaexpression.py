from omas.exceptions import BadApiRequest


class EmaExpression(object):
    """ A class to parse an EMA expression given EMA information about a
        music document. """
    def __init__(self, docInfo, measures, staves, beats, completeness=None):
        self.docInfo = docInfo
        self.requested_measures = measures
        self.requested_staves = staves
        self.requested_beats = beats
        self.completeness = completeness

    @property
    def measureRange(self):
        """Return list of indexes of requested measures"""
        # BNF of data:
        # measure ::= integer
        # measureRange ::= {measure | startOrEnd | all / "+"} |
        #                  {measure | start, "-", measure | end / "+"}

        end = str(self.docInfo["measures"])

        all_mm = "1-{0}".format(end)

        request = (
            self.requested_measures
            .replace("start", "1")
            .replace("end", end)
            .replace("all", all_mm)
            )

        # store compiled expression
        self.compiled_measures = request

        measures = []
        for rang in request.split(","):
            measures = measures + self._parseNumericRanges(rang)

        return measures

    @property
    def staffRange(self):
        """Return list of indexes of requested staves organized by measure"""
        # BNF of data:
        # staff ::= integer
        # staffRange ::= {staff | startOrEnd | all / ","} |
        #                {staff | start, "-", staff | end / ","}
        # stavesToMeasure ::= {staffRange / ","}

        # Locate number of staves defined at beggining of selection
        m = self.measureRange[0]-1
        info = self.docInfo["staves"]
        closestDef = str(min(info, key=lambda x: abs(int(x)-int(m))))

        end = str(len(info[closestDef]))

        all_s = "1-{0}".format(end)

        request = (
            self.requested_staves
            .replace("start", "1")
            .replace("end", end)
            .replace("all", all_s)
            )

        # Only one measure range may need to be applied to all measures
        mm_ranges = request.split(",")

        if len(mm_ranges) == 1:
            for x in self.measureRange[:-1]:
                mm_ranges.append(mm_ranges[0])

        # At this point, the ranges must match the number of measures
        # (stavesToMeasure)
        if len(mm_ranges) != len(self.measureRange):
            e = "Requested staff range does not match requested measure range"
            raise BadApiRequest(e)

        # store compiled expression
        self.compiled_staves = ",".join(mm_ranges)

        staves_by_measure = []
        for ranges in mm_ranges:
            staves = []
            for r in ranges.split("+"):
                staves = staves + self._parseNumericRanges(r)
            staves_by_measure.append(staves)

        return staves_by_measure

    @property
    def beatRange(self):
        """Return list of request beats (timestamps) organized by
           staff and measure """
        # BNF of data:
        # beat ::= float
        # beatRange ::= {"@", beat | startOrEnd | all / "+"} |
        #               {"@", beat | start, "-", beat | end / "+"}
        # beatsToMeasure ::= {beatRange / ","}

        # If there is only one measure range, it may need to be applied
        # to all measures
        mm_ranges = self.requested_beats.split(",")

        if len(mm_ranges) == 1:
            for x in self.measureRange[:-1]:
                mm_ranges.append(mm_ranges[0])

        # At this point, the ranges must match the number of measures
        # (beatsToMeasure)
        if len(mm_ranges) != len(self.measureRange):
            e = "Requested beat range does not match requested measure range"
            raise BadApiRequest(e)

        # buils compiled expression
        compiled_staves = []

        beats_by_measure = []
        for i, ranges in enumerate(mm_ranges):
            beats_by_staff = []

            # only replace wildcards here once you know the measure context
            m = self.measureRange[i]
            info = self.docInfo["beats"]
            closestDef = str(min(info, key=lambda x: abs(int(x)-int(m))))

            end = str(info[closestDef]["count"])

            all_b = "1-{0}".format(end)

            ranges = (
                ranges
                .replace("start", "1")
                .replace("end", end)
                .replace("all", all_b)
                )

            # Only one staff range may need to be applied to all staves
            s_ranges = ranges.split("+")

            if len(s_ranges) == 1:
                for x in self.staffRange[i][:-1]:
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
            if len(beats_by_staff) != len(self.staffRange[i]):
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
        self.getIndexes()

        return "{0}/{1}/{2}".format(self.compiled_measures,
                                    self.compiled_staves,
                                    self.compiled_beats)

    def get(self):
        ema_measures = []
        for m_i, m in enumerate(self.measureRange):
            ema_m = EmaMeasure(idx=int(m))
            ema_staves = []
            for s_i, s in enumerate(self.staffRange[m_i]):
                ema_s = EmaStaff(number=int(s), measure=ema_m)
                ema_beat_ranges = []
                for br in self.beatRange[m_i][s_i]:
                    ema_beat_ranges.append(
                        EmaBeatRange(range_str=br, measure=ema_m, staff=ema_s)
                    )
                ema_s.setBeatRanges(ema_beat_ranges)
                ema_staves.append(ema_s)
            ema_m.setStaves(ema_staves)
            ema_measures.append(ema_m)

        return ema_measures


class EmaMeasure(object,):
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
    """Object representing an EMA staff"""
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
