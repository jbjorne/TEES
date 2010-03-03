"""
Functions for easier use of cElementTree.

  Program:    cElementTree Utilities
  Date:       Oct. 16, 2007
  Author:     Jari Bjoerne

  Description: Convenience functions for easier use of cElementTree.
"""
__version__ = "$Revision: 1.12 $"

import sys

try:
    import cElementTree as ElementTree
except ImportError:
    import xml.etree.cElementTree as ElementTree

from gzip import GzipFile

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

def ETFromObj(obj):
    """obj can be
    1) a string that ends with .xml -> the file is parsed and the resulting ElementTree returned
    2) a string that ends with .xml.gz -> the file is unzipped, parsed, and the resulting ElementTree is returned
    3) an open input stream -> the input is parsed and the resulting ElementTree is returned
    4) an ElementTree or an Element -> obj is returned as-is, nothing is done"""
    if isinstance(obj,str) or isinstance(obj,unicode):
        if obj.endswith(".xml.gz"):
            fStream=GzipFile(obj,"rt")
        elif obj.endswith(".xml"):
            fStream=open(obj,"rt")
        else:
            raise ValueError("%s: File format not recognized (expected .xml or .xml.gz)"%obj)
        return ElementTree.parse(fStream)
    elif isinstance(obj,ElementTree.ElementTree) or ElementTree.iselement(obj):
        return obj
    else:
        #not a string, not a tree, not an element, should be a stream
        #let's parse it
        return ElementTree.parse(obj)

def write(rootElement, filename):
    if isinstance(rootElement,ElementTree.ElementTree):
        rootElement = rootElement.getroot()
    indent(rootElement)
    if filename.endswith(".gz"):
        out=GzipFile(filename,"wt")
    else:
        out=open(filename,"wt")
    print >> out, '<?xml version="1.0" encoding="UTF-8"?>'
    ElementTree.ElementTree(rootElement).write(out,"utf-8")
    out.close()

def writeUTF8(rootElement,out):
    indent(rootElement)
    if isinstance(out,str):
        if out.endswith(".gz"):
            f=GzipFile(out,"wt")
        else:
            f=open(out,"wt")
        print >> f, '<?xml version="1.0" encoding="UTF-8"?>'
        ElementTree.ElementTree(rootElement).write(f,"utf-8")
        f.close()
    else:
        print >> out, '<?xml version="1.0" encoding="UTF-8"?>'
        ElementTree.ElementTree(rootElement).write(out,"utf-8")


def makePath(element,tagList):
    #taglist is a list of tag names
    #a list of corresponding elements is returned
    #if these did not exist, they are created!
    #
    result=[]
    currElem=element
    for tag in tagList:
        for subElem in currElem:
            if subElem.tag==tag:
                break
        else:
            subElem=ElementTree.SubElement(currElem,tag)
        result.append(subElem)
        currElem=subElem
    return result

def toStr(element):
    s = "<" + element.tag
    for key in sorted(element.attrib.keys()):
        s += " " + key + "=\"" + element.get(key) + "\""
    text = element.text
    if text == None or len(text) == 0:
        s += " />"
    else:
        s += ">" + text + " <" + element.tag + "/>"
    return s
    

if __name__=="__main__":
    r=ElementTree.parse("delme.xml").getroot()
    write(r,"delme1.xml.gz")
    r2=ETFromObj("delme1.xml.gz").getroot()
    write(r2,"delme2.xml.gz")
