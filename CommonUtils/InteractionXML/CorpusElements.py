from SentenceElements import *

def loadCorpus(filename, parse=None, tokenization=None, removeIntersentenceInteractions=True):
    try:
        import xml.etree.cElementTree as ET
    except ImportError:
        import cElementTree as ET
    import sys, gzip
    
    print >> sys.stderr, "Loading corpus file", filename
    if filename.rsplit(".",1)[-1] == "gz":
        import gzip
        corpusTree = ET.parse(gzip.open(filename))
    else:
        corpusTree = ET.parse(filename)
    corpusRoot = corpusTree.getroot()
    return CorpusElements(corpusRoot, parse, tokenization, removeIntersentenceInteractions)

class CorpusElements:
    def __init__(self, rootElement, parse, tokenization=None, removeIntersentenceInteractions=True):
        self.rootElement = rootElement
        self.documents = rootElement.findall("document")
        self.documentsById = {}
        self.sentencesById = {}
        self.sentencesByOrigId = {}
        self.sentences = []
        for documentElement in self.documents:
            self.documentsById[documentElement.attrib["id"]] = documentElement
            sentenceElements = documentElement.findall("sentence")
            for sentenceElement in sentenceElements:
                sentenceObj = SentenceElements(sentenceElement, parse, tokenization, removeIntersentenceInteractions)
                self.sentencesById[sentenceElement.attrib["id"]] = sentenceObj
                if sentenceElement.attrib.has_key("origId"):
                    self.sentencesByOrigId[sentenceElement.attrib["origId"]] = sentenceObj
                self.sentences.append(sentenceObj)
