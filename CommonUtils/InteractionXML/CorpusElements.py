from SentenceElements import *

class CorpusElements:
    def __init__(self, rootElement, parse, tokenization=None):
        self.rootElement = rootElement
        self.documents = rootElement.findall("document")
        self.documentsById = {}
        self.sentencesById = {}
        for documentElement in self.documents:
            self.documentsById[documentElement.attrib["id"]] = documentElement
            sentenceElements = documentElement.findall("sentence")
            for sentenceElement in sentenceElements:
                sentenceObj = SentenceElements(sentenceElement, parse, tokenization)
                self.sentencesById[sentenceElement.attrib["id"]] = sentenceObj
