from SentenceElements import *
import types
import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
import Utils.ElementTreeUtils as ETUtils
from Utils.InteractionXML.IDUtils import checkUnique

def loadCorpus(filename, parse=None, tokenization=None, removeIntersentenceInteractions=True, removeNameInfo=False):
    try:
        import xml.etree.cElementTree as ET
    except ImportError:
        import cElementTree as ET
    import sys, gzip
    
    if type(filename) == types.StringType:
        print >> sys.stderr, "Loading corpus file", filename
    corpusTree = ETUtils.ETFromObj(filename)
    corpusRoot = corpusTree.getroot()
    return CorpusElements(corpusRoot, parse, tokenization, removeIntersentenceInteractions, corpusTree, removeNameInfo)

class CorpusElements:
    def __init__(self, rootElement, parse, tokenization=None, removeIntersentenceInteractions=True, tree=None, removeNameInfo=False):
        self.tree = tree
        self.rootElement = rootElement
        if rootElement.tag != "corpus":
            raise Exception("Corpus root element is not 'corpus', but '" + str(rootElement.tag) + "'")
        self.documents = rootElement.findall("document")
        self.documentsById = {}
        self.sentencesById = {}
        self.sentencesByOrigId = {}
        self.sentences = []
        self.documentSentences = []
        counts = {"sentences":0, "missing-tok":0, "missing-parse":0}
        docIds = {}
        for documentElement in self.documents:
            checkUnique(documentElement, docIds)
            self.documentsById[documentElement.attrib["id"]] = documentElement
            sentenceElements = documentElement.findall("sentence")
            self.documentSentences.append([])
            for sentenceElement in sentenceElements:
                checkUnique(sentenceElement, docIds)
                counts["sentences"] += 1
                sentenceObj = SentenceElements(sentenceElement, parse, tokenization, removeIntersentenceInteractions)
                self.sentencesById[sentenceElement.attrib["id"]] = sentenceObj
                if sentenceElement.attrib.has_key("origId"):
                    self.sentencesByOrigId[sentenceElement.attrib["origId"]] = sentenceObj
                self.sentences.append(sentenceObj)
                self.documentSentences[-1].append(sentenceObj)
                if parse != None and sentenceObj.tokenizationElement == None:
                    counts["missing-tok"] += 1
                if parse != None and sentenceObj.parseElement == None:
                    counts["missing-parse"] += 1
        if counts["missing-tok"] + counts["missing-parse"] > 0:
            print >> sys.stderr, "Warning, parse missing from", counts["missing-parse"], "and tokenization from", counts["missing-tok"], "sentences out of a total of", counts["sentences"]
            print >> sys.stderr, "Requested parse", parse, "and tokenization", tokenization
