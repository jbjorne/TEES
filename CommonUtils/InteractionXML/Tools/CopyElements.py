"""
Copy elements from one InteractionXML structure to another.

  Program:    CopyElements
  Date:       Sep. 25, 2008
  Author:     Jari Bjorne
  
  Status: Usable, but could use more testing

  Description: Copy elements from one InteractionXML structure to another.
  
  Copies subelements betweem matching elements in an XML structure. Can be used to f.e. merge
  parses from different files into one. The program works by defining parent elements, that
  are matched betweem 'source' and 'target'. These could be f.e. 'sentence'-elements that are
  matched by their 'id' and 'text' attributes. Once the corresponding elements in source and
  target have been defined, the 'element' and 'identifier' options are used to select the
  subelement from source and copy it to the corresponding position in target.
  
  Example: The following options will take two corpus files that have the same sentences which
  can be uniquely matched with the values of their 'id' and 'text' attributes. Between these
  sentence pairs, a subelement of type 'sentenceanalyses/parses/parse' will be copied from the
  source sentence to the target sentence. The subelement will be uniquely identified as a parse-
  element that has an attribute 'parse' with the value 'Charniak-Lease'. Finally, the merged
  xml will be saved to 'outputFileName.xml'.
  
  -s (--source) sourceFileName.xml 
  -t (--target) targetFileName.xml 
  -o (--output) outputFileName.xml 
  -p (--parent) "document/sentence" 
  -m (--match) "id,text" 
  -e (--element) "sentenceanalyses/parses/parse" 
  -i (--identifiers) "{'parser':'Charniak-Lease'}"
"""
__version__ = "$Revision: 1.4 $"

import sys, os
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils

def getMatchConditions(matchString):
    """Split the match options string"""
    if matchString == None:
        return []
    elif matchString.find(",") != -1:
        return matchString.split(",")
    else:
        return [matchString]

def matchElements(e1, e2, match):
    """
    Test whether two elements have the same attributes. Used to check equality of elements
    beyond the primary key (the first match option)
    """
    isMatch = True
    for matchCondition in match:
        if(e1.attrib[matchCondition] != e2.attrib[matchCondition]):
            isMatch = False
            break
    return isMatch

def matchElement(e, conditions):
    """
    e = ElementTree element
    conditions = attrib-name:value dictionary
    
    Tests wheter the element has certain attributes and that those attributes have
    the correct values
    """
    isMatch = True
    for k,v in conditions.iteritems():
        if(not e.attrib.has_key(k) or e.attrib[k] != v):
            isMatch = False
            break
    return isMatch

def matchPairs(sourceParents, targetParents, match):
    """
    Links parent elements (the elements whose subelements will be copied)
    betweem source and target trees. Returs a list of (source element, target element)-pairs.
    """
    sourceKeys = sourceParents.keys()
    sourceKeys.sort()
    pairs = []
    for sourceKey in sourceKeys:
        if targetParents.has_key(sourceKey):
            assert(matchElements(sourceParents[sourceKey], targetParents[sourceKey], match))
            pairs.append( (sourceParents[sourceKey], targetParents[sourceKey]) )
    print >> sys.stderr, "Formed", str(len(pairs)), "pairs"
    return pairs

def getParentElements(root, pattern, match):
    """
    Returns a dictionary of parent elements indexed by the values
    of the first attribute in the match-list.
    """
    primaryKey = match[0]
    elementsByKey = {}
    elements = root.findall(pattern)
    for element in elements:
        assert(not elementsByKey.has_key(element.attrib[primaryKey]))
        elementsByKey[element.attrib[primaryKey]] = element
    print >> sys.stderr, "Found", str(len(elementsByKey)), "elements"
    return elementsByKey

def copyElements(pairs, elementPath, identifiers):
    """
    Copies subelements that match the conditions in 'identifiers'
    from the source-parents to the target-parents.
    """
    copied = 0
    # Loop through all matched parent-pairs
    for pair in pairs:
        sourceParent = pair[0]
        targetParent = pair[1]
        # Locate the source element
        sourceElements = sourceParent.findall(elementPath) # source element is under the source parent
        sourceElement = None
        for element in sourceElements:
            if matchElement(element, identifiers):
                assert(sourceElement==None) # The source element must be identified uniquely
                sourceElement = element
        assert(sourceElement != None) # The source element must be found for each source parent
        #if sourceElement == None:
        #    return
        
        # Locate the target element       
        # The subelement is added to the same level in the target XML that it existed in the source XML
        if elementPath.find("/") != -1:
            targetPath = elementPath.rsplit("/",1)[0]
            targetElements = targetParent.findall(targetPath) # Find the immediate parent for the copied element
            assert(len(targetElements) == 1) # The place to add the element must be identified uniquely
            targetElement = targetElements[0]
        else:
            targetElement = targetParent
        targetElement.append(sourceElement)
        copied += 1
    print >> sys.stderr, "Copied", str(copied), "elements"

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\nCopy elements from one interaction XML file to another.")
    optparser.add_option("-s", "--source", default=None, dest="source", help="File from which is read the XML-structure from which elements are copied", metavar="FILE")
    optparser.add_option("-t", "--target", default=None, dest="target", help="File from which is read the XML-structure to which elements are added", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="The file to which the new XML structure is saved. If None, will be the same as target.", metavar="FILE")
    optparser.add_option("-p", "--parent", default=None, dest="parent", help="The path to elements between which subelements are copied")
    optparser.add_option("-m", "--match", default=None, dest="match", help="A comma-separated list of attributes by which 'parent'-elements are matched between source and target")
    optparser.add_option("-e", "--element", default=None, dest="element", help="The path of the subelements to copy from source to target. Relative to parent.")
    optparser.add_option("-i", "--identifiers", default=None, dest="identifiers", help="A python-dictionary of attributes and values that will be used to select copied elements.")
    (options, args) = optparser.parse_args()
    
    assert(options.source != None)
    assert(options.target != None)
    if options.output == None:
        options.output = options.target
    if options.identifiers != None:
        options.identifiers = eval(options.identifiers)
    else:
        options.identifiers = {}
    
    print >> sys.stderr, "Loading source file", options.source
    sourceTree = ET.parse(options.source)
    sourceRoot = sourceTree.getroot()
    print >> sys.stderr, "Loading target file", options.target
    targetTree = ET.parse(options.target)
    targetRoot = targetTree.getroot()
    
    match = getMatchConditions(options.match)
    print >> sys.stderr, "Extracting source parents"
    sourceParents = getParentElements(sourceRoot, options.parent, match)
    print >> sys.stderr, "Extracting target parents"
    targetParents = getParentElements(targetRoot, options.parent, match)
    
    print >> sys.stderr, "Copying elements"
    pairs = matchPairs(sourceParents, targetParents, match)
    copyElements(pairs, options.element, options.identifiers)
    
    print >> sys.stderr, "Saving output file to", options.output
    ETUtils.write(targetRoot, options.output)