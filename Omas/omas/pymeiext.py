from __future__ import print_function
import six

from pymei import MeiElement

# Extend MeiElement with methods to deal with mixed content

def getChildrenNodes(self):
    """Return all children nodes, including text nodes"""
    nodes = []
    head = self.getValue()
    if head: nodes.append(head)
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

MeiElement.getChildrenNodes = getChildrenNodes
MeiElement.getDecendantsTextNodes = getDecendantsTextNodes