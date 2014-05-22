"""
Functions for easier use of cElementTree.

  Program:    cElementTree Utilities
  Date:       Oct. 16, 2007
  Author:     Jari Bjoerne

  Description: Convenience functions for easier use of cElementTree.
"""
__version__ = "$Revision: 1.20 $"

import sys, os
import codecs

try:
    import cElementTree as ElementTree
except ImportError:
    import xml.etree.cElementTree as ElementTree

from gzip import GzipFile

def removeAll(element):
    for child in list(element):
        removeAll(child)
    for child in list(element):
        element.remove(child)

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

def iterparse2(file, events=("start", "end")):
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
    # get an iterable
    context = ElementTree.iterparse(file, events=events)
    
    # turn it into an iterator
    context = iter(context)
    
    # get the root element
    event, root = context.next()
    yield (event, root)
    
    for event, elem in context:
        yield (event, elem)
        if event == "end":
            root.clear()

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
            #fStream = codecs.getreader("utf-8")(GzipFile(obj,"rt"))
        elif obj.endswith(".xml") or obj.endswith(".svg") or obj.endswith(".nxml") or obj.endswith(".csml"):
            fStream=open(obj,"rt")
            #fStream=codecs.open(obj, "rt", "utf-8")
        else:
            raise ValueError("%s: File format not recognized (expected .xml or .xml.gz)"%obj)
        return ElementTree.parse(fStream)
    elif isinstance(obj,ElementTree.ElementTree) or ElementTree.iselement(obj):
        return obj
    else:
        #not a string, not a tree, not an element, should be a stream
        #let's parse it
        return ElementTree.parse(obj)
    
def escapeText(text):
    import xml.sax.saxutils
    return xml.sax.saxutils.escape(text).replace("'", "&apos;").replace("\"", "&quot;")

class ETWriter():
    def __init__(self, out):
        if isinstance(out,str):
            if not os.path.exists(os.path.dirname(out)):
                os.makedirs(os.path.dirname(out))
            if out.endswith(".gz"):
                self.out = GzipFile(out,"wt") #codecs.getwriter("utf-8")(GzipFile(out,"wt"))
            else:
                self.out = codecs.open(out,"wt") #codecs.open(out, "wt", "utf-8")
        else:
            self.out = out
        print >> self.out, '<?xml version="1.0" encoding="UTF-8"?>'
        self.indentLevel = 0
        self.beginString = None
        self.tags = []
        self.lastElement = None
    
    def close(self):
        while len(self.tags) > 0:
            self.end()
        self.out.close()
        self.out = None
    
    # open element
    def begin(self, element):
        self._flush()
        self.tags.append(element.tag)
        self.beginString = self.indentLevel * "  " + "<" + element.tag
        for key in sorted(element.attrib.keys()):
            self.beginString += " " + key + "=\"" + unicode(escapeText(element.get(key)), "utf-8") + "\""
        self.beginString += ">" + "\n"
        self.indentLevel += 1
        self.lastElement = element
    
    def _flush(self):
        if self.beginString != None:
            self.out.write(self.beginString)
            #self.out.write("\n" + self.indentLevel * "  ")
        self.beginString = None
    
    # close element
    def end(self, element):
        self.indentLevel -= 1
        if element == self.lastElement:
            self.beginString = None
            self.write(element)
        else:
            self.out.write(self.indentLevel * "  " + "</" + element.tag + ">")
            if self.indentLevel > 0:
                self.out.write("\n")
        self.lastElement = None
        if len(self.tags) > 0:
            return self.tags.pop()
        else:
            return None
    
    def write(self, element):
        self._flush()
        indent(element, self.indentLevel)
        if element.tail != None:
            element.tail = element.tail[:-self.indentLevel * 2]
        self.out.write(self.indentLevel * "  " + ElementTree.tostring(element, "utf-8"))
        self.lastElement = None

def ETIteratorFromObj(obj, events=None, parser=None):
    """obj can be
    1) a string that ends with .xml -> the file is parsed and the resulting ElementTree returned
    2) a string that ends with .xml.gz -> the file is unzipped, parsed, and the resulting ElementTree is returned
    3) an open input stream -> the input is parsed and the resulting ElementTree is returned
    4) an ElementTree or an Element -> obj is returned as-is, nothing is done"""
    if isinstance(obj,str) or isinstance(obj,unicode):
        if obj.endswith(".gz"):
            fStream=GzipFile(obj,"rt")
            #fStream = codecs.getreader("utf-8")(GzipFile(obj,"rt"))
        else:
            fStream=open(obj,"rt")
            #fStream=codecs.open(obj, "rt", "utf-8")
        for rv in iterparse2(fStream, events):
            yield rv
    elif isinstance(obj,ElementTree.ElementTree) or ElementTree.iselement(obj):
        if ElementTree.iselement(obj):
            root = obj
        else:
            root = obj.getroot()
        #if events == None:
        #    events = ["END"]
        for element in root.getiterator():
            yield ("memory", element)
    else:
        #not a string, not a tree, not an element, should be a stream
        #let's parse it
        for rv in ElementTree.iterparse(obj, events):
            yield rv

def write(rootElement, filename):
    if isinstance(rootElement,ElementTree.ElementTree):
        rootElement = rootElement.getroot()
    indent(rootElement)
    # Create intermediate paths if needed
    if os.path.dirname(filename) != "" and not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    # Open the output file
    if filename.endswith(".gz"):
        out=GzipFile(filename,"wt") #out=codecs.getwriter("utf-8")(GzipFile(filename,"wt"))
    else:
        out=codecs.open(filename,"wt") #out=codecs.open(filename,"wt","utf-8")
    print >> out, '<?xml version="1.0" encoding="UTF-8"?>'
    ElementTree.ElementTree(rootElement).write(out,"utf-8")
    out.close()
    # Fix newlines inside attributes
    encodeNewlines(filename)

def encodeNewlines(filename):
    import tempfile, shutil
    # fix newlines
    tempdir = tempfile.mkdtemp()
    tempfilepath = os.path.join(tempdir, os.path.basename(filename))
    if filename.endswith(".gz"):
        #inFile=GzipFile(filename,"rt")
        inFile = codecs.getreader("utf-8")(GzipFile(filename, "rb"))
        out = codecs.getwriter("utf-8")(GzipFile(tempfilepath, "wb"))
    else:
        #inFile=open(filename,"rt")
        inFile=codecs.open(filename, "rt", "utf-8")
        out = codecs.open(tempfilepath, "wt", "utf-8")
    
    for content in inFile:
        #content = inFile.read()
        #inFile.close()    
        content = content.replace(">\n", "TEMP_PROTECT_N") # newlines between elements
        content = content.replace(">\r", "TEMP_PROTECT_R") # newlines between elements
        content = content.replace("\n", "&#10;") # newlines in attributes
        content = content.replace("\r", "&#10;") # newlines in attributes
        content = content.replace("TEMP_PROTECT_N", ">\n") # newlines between elements
        content = content.replace("TEMP_PROTECT_R", ">\r") # newlines between elements
        out.write(content)
    inFile.close()
    out.close()
    shutil.copy2(tempfilepath, filename)
    shutil.rmtree(tempdir)
    
#    if filename.endswith(".gz"):
#        #out=GzipFile(filename,"wt")
#        out = codecs.getwriter("utf-8")(GzipFile(filename,"wt"))
#    else:
#        #out=open(filename,"wt")
#        out=codecs.open(filename, "wt", "utf-8")
#    out.write(content)
#    out.close()

#def writeUTF8(rootElement,out):
#    indent(rootElement)
#    if isinstance(out,str):
#        if out.endswith(".gz"):
#            f=GzipFile(out,"wt")
#        else:
#            f=open(out,"wt")
#        print >> f, '<?xml version="1.0" encoding="UTF-8"?>'
#        ElementTree.ElementTree(rootElement).write(f,"utf-8")
#        f.close()
#        encodeNewlines(out)
#    else:
#        print >> out, '<?xml version="1.0" encoding="UTF-8"?>'
#        ElementTree.ElementTree(rootElement).write(out,"utf-8")


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

def toStr(element, recursive=True, removePreTag=True):
    tag = element.tag
    if removePreTag:
        tag = tag.split("}")[-1]
    s = "<" + tag
    for key in sorted(element.attrib.keys()):
        s += " " + key + "=\"" + element.get(key) + "\""
    # get content
    text = element.text
    children = element.getchildren()
    if text != None or len(children) > 0: # if content, close opening
        s += ">"
    # write content
    if text != None:
        s += text
    for child in children:
        s += toStr(child)
    if text != None or len(children) > 0:
        s += "</" + tag + ">"
    else:
        s += "/>"
    
    if element.tail != None:
        s += element.tail
        
    return s

def getElementByAttrib(parent, tag, attDict):
    for element in parent.getiterator():
        if element.tag == tag:
            found = True
            for k, v in attDict.iteritems():
                if element.get(k) != v:
                    found = False
            if found:
                return element
    return None

def setDefaultElement(parent, name):
    element = parent.find(name)
    if element == None:
        element = ElementTree.Element(name)
        parent.append(element)
    return element

if __name__=="__main__":
    r=ElementTree.parse("delme.xml").getroot()
    write(r,"delme1.xml.gz")
    r2=ETFromObj("delme1.xml.gz").getroot()
    write(r2,"delme2.xml.gz")
