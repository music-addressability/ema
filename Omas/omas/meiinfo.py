import re
import json
import api

class MusDocInfo(object):
    """An object storing information from an MEI file needed for the EMA API."""
    def __init__(self, doc):
        self.meiDoc = doc

    @property
    def music(self):
        """Get music element."""
        musicEl = self.meiDoc.getElementsByName("music")
        # Exception
        if len(musicEl) != 1:
            raise api.BadApiRequest("MEI document must have one and only one music element")
        else: return musicEl[0]

    @property
    def measures(self):
        return self.music.getDescendantsByName("measure")

    @property
    def measure_labels(self):
        """Return a list of the labels (@n) of all measures."""
        labels = []
        for m in self.measures:
            n = m.getAttribute("n")
            if n:
                labels.append(n.getValue())
            else:
                labels.append("")
        return labels

    @property
    def staves(self):
        staves, beats = self._getStavesBeats()
        self.beats = beats
        return staves

    # The following property is defined with property()
    # so that it can be set by staves()
    def beats():
        def fget(self):
            # Run staves property, which will populate beats
            self.staves
            return self._beats
        def fset(self, value):
            self._beats = value
        def fdel(self):
            del self._beats
        return locals()
    beats = property(**beats())

    def _getStavesBeats(self):
        """
        Return two dictionaries.
        The first containing all changes in staves and the measure
        at which the change happens.
        The second containing all changes in beats and the measure at which the change
        happens.
        """
        def _getMeasurePos(idx):
            return next((i for i, x in enumerate(self.measures) if x.id == idx), None)

        def _seekMeasure(elm, pos):
            """ Return the closest following measure element """

            # If the given element is not a measure, look up
            # descendants before recursing

            if elm.name == "measure":
                return _getMeasurePos(elm.getId())
            else:
                descendant_measures = elm.getDescendantsByName("measure")
                if len(descendant_measures) > 0:
                    return _getMeasurePos(descendant_measures[0].getId())
                else:
                    return _seekMeasure(peers[pos + 1], pos+1)

            return None

        staves = {}
        beats = {}

        scoreDefs = self.music.getDescendantsByName("scoreDef")
        for sd in scoreDefs:

            # Get current scoreDef's peers
            peers = sd.getPeers()

            # get its position in the list of peers based on its id
            # (either from @xml:id or added by pymei)
            # use it to retrieve next following-sibling[1] element
            sd_pos = next((i for i, x in enumerate(peers) if x.id == sd.getId()), None)
            following_el = peers[sd_pos + 1]

            m_pos = _seekMeasure(following_el, sd_pos+1)

            # If at this point a measure hasn't been located, there is
            # something unusual with the data
            if m_pos == None:
                raise api.BadApiRequest("Could not locate measure after new score definition (scoreDef)")

            # Process for beat data if the scoreDef defines meter
            count_att = sd.getAttribute("meter.count")
            unit_att = sd.getAttribute("meter.unit")
            if count_att and unit_att:
                beats[str(m_pos)] = {"count" : int(count_att.getValue())}
                beats[str(m_pos)]["unit"] = int(unit_att.getValue())
            else:
                count_elm = sd.getDescendantsByName("meterSig")
                if count_elm:
                    if len(count_elm) > 1:
                        sys.exit("Mixed meter is not supported, exiting.")
                    count = count_elm[0].getAttribute("count")
                    unit = count_elm[0].getAttribute("unit")
                    if count and unit:
                        beats[str(m_pos)] = {"count" : int(count.getValue())}
                        beats[str(m_pos)]["unit"] = int(unit.getValue())
                    else:
                        sys.exit("Could not locate meter and compute beats.")

            # Process for staff data if this scoreDef defines staves
            if len(sd.getChildrenByName("staffGrp")) > 0:

                # Get labels of staffDef and add them to the dictionary
                staffDefs = sd.getDescendantsByName("staffDef")
                labels = []
                for staffDef in staffDefs:
                    # Try to get label in this order: @label, /label, @label, @label.abbr
                    label = ""
                    label_data = staffDef.getAttribute("label")

                    if label_data:
                        label = label_data.getValue()
                    else:
                        label_data = staffDef.getChildrenByName("label")
                        if label_data:
                            label_nodes = []
                            for l in label_data:
                                label_nodes += l.getDecendantsTextNodes()
                            # filter out blank text nodes
                            label_nodes = [n for n in label_nodes if n.strip()]
                            # normalize space and concatenate
                            label = " ".join(re.sub(r"\s+", " ", l.strip()) for l in label_nodes)
                        else:
                            label_data = staffDef.getAttribute("label.abbr")
                            if label_data: label = label_data.getValue()

                    labels.append(label)

                staves[str(m_pos)] = labels

        return staves, beats

    def get(self):
        """Return info as Python object"""
        return {"measures" : len(self.measures),
                "measure_labels" : self.measure_labels,
                "staves" : self.staves,
                "beats" : self.beats,
                "completeness" : ["raw", "signature", "nospace", "cut"]}

    def toJsonString(self):
        """Return info as JSON string"""
        return json.dumps(self.get())