from ProcessUtils import *

class Parser:
    def __init__(self):
        pass
    
    def addAnalysis(self, sentence, name, group):
        if sentence.find("sentenceanalyses") != None: # old format
            sentenceAnalyses = setDefaultElement(sentence, "sentenceanalyses")
            groupElement = setDefaultElement(sentenceAnalyses, group)
            return setDefaultElement(groupElement, name)
        else:
            analyses = setDefaultElement(sentence, "analyses")
            return setDefaultElement(analyses, name)
    
    def getAnalysis(self, sentence, name, attrib, group):
        if sentence.find("sentenceanalyses") != None: # old format
            sentenceAnalyses = setDefaultElement(sentence, "sentenceanalyses")
            groupElement = setDefaultElement(sentenceAnalyses, group)
            return getElementByAttrib(groupElement, name, attrib)
        else:
            analyses = setDefaultElement(sentence, "analyses")
            return getElementByAttrib(analyses, name, attrib)