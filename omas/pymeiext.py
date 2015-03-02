import six

from pymei import MeiElement

# Extend MeiElement

def getChildrenNodes(self):
    """Return all children nodes, including text nodes"""
    nodes = []
    head = self.getValue()
    if head: 
        nodes.append(head)
    nodes += self.getChildren()
    nodes.append(self.getTail())
    return nodes

def getDecendantsTextNodes(self):
    """Return a flattened list of descendant text nodes"""
    
    def _extractTextNode(el):
        nodes = el.getChildrenNodes()
        for node in nodes:
            if isinstance(node, six.string_types):
                text_nodes.append(node)
            else:
                _extractTextNode(node)

    text_nodes = []    
    _extractTextNode(self)
    return text_nodes

def moveTo(self, parent):
    """Move this element to new parent, as last child"""
    self.getParent().removeChild(self)
    parent.addChild(self)

    return self

def getStaffDefs(self):
    """Return list of current staff definitions for the element's staff"""

    # N.B. some elements may belong to more than one staff e.g. @staff="1 2"

    staffDefs = []

    def _look(el, val):
        """Implements a recursive lookback"""
        sd = el.lookback("staffDef")
        if sd:
            if sd.hasAttribute("n"):
                if sd.getAttribute("n").getValue() == val:
                    return sd
                else:
                    _look(sd, val)
            else:
                _look(sd, val)
        else:
            return None

    # Get n if element is a staff
    if self.getName() == "staff":
        if self.hasAttribute("n"):
            value = staff.getAttribute("n").getValue()
            sd = _look(self, value)
            if sd:
                staffDefs.append(sd) 
    # Then look for attribute
    elif self.hasAttribute("staff"):
        values = el.getAttribute("staff").getValue().split()
        for v in values:
            sd = _look(self, v)
            if sd:
                staffDefs.append(sd)
    # Then staff ancestor element
    elif self.getAncestor("staff"):
        staff = self.getAncestor("staff")
        if staff.hasAttribute("n"):
            value = staff.getAttribute("n").getValue()
            sd = _look(self, value)
            if sd:
                staffDefs.append(sd) 
    # If the element does not belong to a staff, return all closest staff defs
    else:
        self.getClosestStaffDefs()

    return staffDefs

def getClosestStaffDefs(self):
    """Return all the closest staff definitions from the element"""

    stack = {}

    # Emulate xpath preceding axis
    doc = self.getDocument()
    allEls = doc.getFlattenedTree()
    preceding = allEls[:self.getPositionInDocument()]

    for el in reversed(preceding): # Boost doens't allow extended slicing :'(
        if el.getName() == "staffDef":
            if el.hasAttribute("n"):
                val = el.getAttribute("n").getValue()
                if val not in stack:
                    stack[val] = el

    # Return flattened stack object
    return [stack[sd] for sd in stack]

MeiElement.getChildrenNodes = getChildrenNodes
MeiElement.getDecendantsTextNodes = getDecendantsTextNodes
MeiElement.moveTo = moveTo
MeiElement.getStaffDefs = getStaffDefs
MeiElement.getClosestStaffDefs = getClosestStaffDefs