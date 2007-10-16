"""
  Program:    cElemenrTree Utilities
  Date:       Oct. 16, 2007
  Author:     Jari Bjoerne

  Description: Convenience functions for easier use of cElementTree.
                
  Status: UNDER CONSTRUCTION, doesn't work yet!
"""

import cElementTree as ElementTree

def iterparse(file, elementName, callback, limit = -1):
    """ Parse iteratively xml-files
    
    This function offers a simple way to use the cElementTree
    iterparse-function the way it is often used.
    
    Keyword arguments:
    file -- (file) file or file-like object to parse 
    elementName -- (string) matching elements are passed to the callback
    callback -- (function) called when parser has parsed an element
                of name elementName
    limit -- (int) stop after reading "limit" elements. If -1, read
             until end of file. This is mostly useful when debugging
             programs that parse large files.
    """
    context = ElementTree.iterparse(file, events=("start", "end"))
    root = None

    for event, elem in context:
        if limit == 0:
            return

        if event == "start" and root is None:
            root = elem     # the first element is root
        if event == "end" and elem.tag == elementName: #elem.tag == "record":
            #... process record elements ...
            callback(elem)
            root.clear()
            if limit != -1:
                limit -= 1

def indent(elem, level=0):
    """ indent-function as defined in cElementTree-documentation
    
    This function will become part of cElementTree in some future
    release. Until then, it can be used from here. This function
    indents the xml-tree, so that it is more readable when written
    out. 
    
    Keyword arguments:
    elem -- (Element) root of the tree to indent 
    level -- (int) starting level of indentation
    """
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            indent(e, level+1)
        if not e.tail or not e.tail.strip():
            e.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i
