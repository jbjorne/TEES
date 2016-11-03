try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
    
###############################################################################
# XML Utilities
###############################################################################

def getElementIndex(parent, element):
    index = 0
    for e in parent:
        if e == element:
            return index
        index += 1
    return -1

def getPrevElementIndex(parent, eTag):
    index = 0
    elemIndex = -1
    for element in parent:
        if element.tag == eTag:
            elemIndex = index
        index += 1
    return elemIndex

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
        element = ET.Element(name)
        parent.append(element)
    return element

###############################################################################
# Sentence Analyses
###############################################################################

def addAnalysis(sentence, name, group, attrib=None):
    if sentence.find("sentenceanalyses") != None: # old format
        sentenceAnalyses = setDefaultElement(sentence, "sentenceanalyses")
        groupElement = setDefaultElement(sentenceAnalyses, group)
        element = setDefaultElement(groupElement, name)
    else:
        analyses = setDefaultElement(sentence, "analyses")
        element = setDefaultElement(analyses, name)
    if attrib != None:
        for key in attrib:
            element.set(key, attrib[key])
    return element
    
def getAnalysis(sentence, name, attrib, group, addIfNotExist=False, mustNotExist=False):
    if sentence.find("sentenceanalyses") != None: # old format
        sentenceAnalyses = setDefaultElement(sentence, "sentenceanalyses")
        groupElement = setDefaultElement(sentenceAnalyses, group)
        element = getElementByAttrib(groupElement, name, attrib)
    else:
        analyses = setDefaultElement(sentence, "analyses")
        element = getElementByAttrib(analyses, name, attrib)
    if element != None and mustNotExist:
        raise Exception("Existing " + name + " in sentence", sentence.get("id"))
    if element == None and addIfNotExist:
        element = addAnalysis(sentence, name, group=group, attrib=attrib)
    return element

# def getParseElements(sentence, parserName, addIfNotExist=True, mustNotExist=False):
#     parse = getAnalysis(sentence, parserName, None, "parses")
#     tokenization = getAnalysis(sentence, parserName, None, "tokenizations")
#     if mustNotExist and (parse != None or tokenization != None):
#         raise Exception("Existing parse in sentence", sentence.get("id"))
#     if addIfNotExist:
#         if parse == None:
#             parse = addAnalysis(sentence, parserName, group="parses")
#         if tokenization == None:
#             tokenization = addAnalysis(sentence, parserName, group="tokenizations")
#     return parse, tokenization

def getParseElement(sentence, parserName, addIfNotExist=False, mustNotExist=False):
    return getAnalysis(sentence, "parse", {"parser":parserName}, "parses", addIfNotExist, mustNotExist)

def getTokenizationElement(sentence, tokenizerName, addIfNotExist=False, mustNotExist=False):
    return getAnalysis(sentence, "tokenization", {"tokenizer":tokenizerName}, "tokenizations", addIfNotExist, mustNotExist)