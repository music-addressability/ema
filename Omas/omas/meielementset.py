import collections


class MeiElementSet(object):
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