"""
Base class for ExampleWriters working with interaction XML.
"""
    
import sys, os, types
import itertools
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
import Core.ExampleUtils as ExampleUtils
import Core.SentenceGraph as SentenceGraph
from Core.IdSet import IdSet
from Utils.ProgressCounter import ProgressCounter
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
import Utils.InteractionXML.ResolveEPITriggerTypes as ResolveEPITriggerTypes
from collections import defaultdict

class SentenceExampleWriter:
    """
    Base class for ExampleWriters working with interaction XML.
    """

    def __init__(self):
        SentenceExampleWriter.counts = defaultdict(int)
    
    def write(self, examples, predictions, corpus, outputFile, classSet=None, parse=None, tokenization=None, goldCorpus=None, insertWeights=False, exampleStyle=None, structureAnalyzer=None):
        return self.writeXML(examples, predictions, corpus, outputFile, classSet, parse, tokenization, goldCorpus, exampleStyle=exampleStyle, structureAnalyzer=structureAnalyzer)
    
    def loadCorpus(self, corpus, parse, tokenization):
        if type(corpus) == types.StringType or isinstance(corpus,ET.ElementTree): # corpus is in file
            return SentenceGraph.loadCorpus(corpus, parse, tokenization)
        else:
            return corpus
        
    def loadExamples(self, examples, predictions):
        if type(predictions) == types.StringType:
            print >> sys.stderr, "Reading predictions from", predictions
            predictions = ExampleUtils.loadPredictions(predictions)
        if type(examples) == types.StringType:
            print >> sys.stderr, "Reading examples from", examples
            examples = ExampleUtils.readExamples(examples, False)
        return examples, predictions
    
    def writeXML(self, examples, predictions, corpus, outputFile, classSet=None, parse=None, tokenization=None, goldCorpus=None, exampleStyle=None, structureAnalyzer=None):
        #print >> sys.stderr, "Writing output to Interaction XML"
        corpus = self.loadCorpus(corpus, parse, tokenization)
        if goldCorpus != None:
            goldCorpus = self.loadCorpus(corpus, parse, tokenization)
        examples, predictions = self.loadExamples(examples, predictions)
        
        if type(classSet) == types.StringType: # class names are in file
            classSet = IdSet(filename=classSet)
        classIds = None
        if classSet != None:
            classIds = classSet.getIds()
            
        #counter = ProgressCounter(len(corpus.sentences), "Write Examples")
                
        exampleQueue = [] # One sentence's examples
        predictionsByExample = {}
        currentMajorId = None
        prevMajorIds = set()
        processedSentenceIds = set()
        xType = None
        
        count = 0
        for example in examples:
            count += 1
        #assert count > 0
        if count > 0:
            progress = ProgressCounter(count, "Write Examples")
        else:
            predCount = 0
            for prediction in predictions:
                predCount += 1
            assert predCount == 0
        
        for example, prediction in itertools.izip_longest(examples, predictions):
            assert example != None
            assert prediction != None
            majorId, minorId = example[0].rsplit(".x", 1)
            #if currentMajorId == "GENIA.d114.s9": print "Start"
            if majorId != currentMajorId: # new sentence
                if currentMajorId != None:
                    #if currentMajorId == "GENIA.d114.s9": print "JAA"
                    processedSentenceIds.add(currentMajorId)
                    sentenceObject = corpus.sentencesById[currentMajorId]
                    goldSentence = None
                    if goldCorpus != None:
                        goldSentence = goldCorpus.sentencesById[currentMajorId]
                    self.writeXMLSentence(exampleQueue, predictionsByExample, sentenceObject, classSet, classIds, goldSentence=goldSentence, exampleStyle=exampleStyle, structureAnalyzer=structureAnalyzer) # process queue
                    progress.update(len(exampleQueue), "Writing examples ("+exampleQueue[-1][0]+"): ")
                exampleQueue = []
                predictionsByExample = {}
                prevMajorIds.add(currentMajorId)
                assert majorId not in prevMajorIds, majorId
                currentMajorId = majorId 
            exampleQueue.append(example) # queue example
            predictionsByExample[example[0]] = prediction
            assert example[3]["xtype"] == self.xType, str(example[3]["xtype"]) + "/" + str(self.xType)
        
        # Process what is still in queue
        if currentMajorId != None:
            processedSentenceIds.add(currentMajorId)
            sentenceObject = corpus.sentencesById[currentMajorId]
            goldSentence = None
            if goldCorpus != None:
                goldSentence = goldCorpus.sentencesById[currentMajorId]
            self.writeXMLSentence(exampleQueue, predictionsByExample, sentenceObject, classSet, classIds, goldSentence=goldSentence, exampleStyle=exampleStyle, structureAnalyzer=structureAnalyzer) # process queue
            progress.update(len(exampleQueue), "Writing examples ("+exampleQueue[-1][0]+"): ")
            exampleQueue = []
            predictionsByExample = {}
        
        # Process sentences with no examples (e.g. to clear interactions)
        for sentenceId in sorted(corpus.sentencesById.keys()):
            if sentenceId not in processedSentenceIds:
                sentenceObject = corpus.sentencesById[sentenceId]
                goldSentence = None
                if goldCorpus != None:
                    goldSentence = goldCorpus.sentencesById[currentMajorId]
                self.writeXMLSentence([], {}, sentenceObject, classSet, classIds, goldSentence=goldSentence, exampleStyle=exampleStyle, structureAnalyzer=structureAnalyzer)
        
        # Print statistics
        if len(self.counts) > 0:
            print >> sys.stderr, self.counts
            self.counts = defaultdict(int)
    
        # Write corpus
        if outputFile != None:
            print >> sys.stderr, "Writing corpus to", outputFile
            ETUtils.write(corpus.rootElement, outputFile)
        return corpus.tree

    def writeXMLSentence(self, examples, predictionsByExample, sentenceObject, classSet, classIds, goldSentence=None, exampleStyle=None, structureAnalyzer=None):
        raise NotImplementedError
    
    def assertSameSentence(self, examples, sentenceId=None):
        currentSetMajorId = None
        for example in examples:
            majorId, minorId = example[0].rsplit(".x", 1)
            if currentSetMajorId == None: 
                currentSetMajorId = majorId
            else: 
                assert currentSetMajorId == majorId, str(currentSetMajorId) + "/" + str(majorId)
        if sentenceId != None and len(examples) > 0:
            assert sentenceId == currentSetMajorId, sentenceId + "/" + currentSetMajorId
    
    def removeChildren(self, element, childTags, childAttributes=None):
        removed = []
        for tag in childTags:
            childElements = element.findall(tag)
            if childElements != None:
                for childElement in childElements:
                    if childAttributes == None:
                        removed.append(childElement)
                        element.remove(childElement)
                    else:
                        removeElement = True
                        for k, v in childAttributes.iteritems():
                            if childElement.get(k) != v:
                                removeElement = False
                                break
                        if removeElement:
                            removed.append(childElement)
                            element.remove(childElement)
        return removed
    
    def removeNonNameEntities(self, sentenceElement):
        """
        Removes non-name entities and returns number of entities
        before removal.
        """
        entityElements = sentenceElement.findall("entity")
        removed = []
        if entityElements != None:
            entityCount = len(entityElements) # get the count _before_ removing entities
            for entityElement in entityElements:
                if entityElement.get("given") in (None, "False"): # interaction word
                    removed.append(entityElement)
                    sentenceElement.remove(entityElement)
        return removed

    def isNegative(self, prediction, classSet=None):
        if classSet == None: # binary classification
            if prediction[0] > 0:
                return False
            else:
                return True
        else:
            return classSet.getName(prediction[0]) == "neg"
    
    def getElementTypes(self, prediction, classSet=None, classIds=None, unmergeEPINegText=None):
        if classSet == None: # binary classification
            if prediction[0] > 0:
                return [str(True)]
            else:
                return [str(False)]
        else:
            eTypes = classSet.getName(prediction[0]).split("---") # split merged types
            if unmergeEPINegText != None: # an element text was provided
                for i in range(len(eTypes)):
                    eTypes[i] = ResolveEPITriggerTypes.determineNewType(eTypes[i], unmergeEPINegText)
        return eTypes

    def setElementType(self, element, prediction, classSet=None, classIds=None, unmergeEPINeg=False):
        eText = element.get("text")
        if classSet == None: # binary classification
            if prediction[0] > 0:
                element.attrib["type"] = str(True)
            else:
                element.attrib["type"] = str(False)
        else:
            if unmergeEPINeg:
                element.set("type", ResolveEPITriggerTypes.determineNewType(classSet.getName(prediction[0]), eText))
            else:
                element.attrib["type"] = classSet.getName(prediction[0])
            classWeights = prediction[1:]
            predictionString = ""
            for i in range(len(classWeights)):
                if predictionString != "":
                    predictionString += ","
                className = classSet.getName(classIds[i])
                if unmergeEPINeg:
                    className = InteractionXML.ResolveEPITriggerTypes.determineNewType(className, eText)
                predictionString += className + ":" + str(classWeights[i])
            element.attrib["predictions"] = predictionString
    
    def getPredictionStrengthString(self, prediction, classSet, classIds, skipClasses=None):
        classWeights = prediction[1:]
        predictionString = ""
        for i in range(len(classWeights)):
            className = classSet.getName(classIds[i])
            if skipClasses != None and className in skipClasses:
                continue
            if predictionString != "":
                predictionString += ","
            predictionString += classSet.getName(classIds[i]) + ":" + str(classWeights[i])
        return predictionString
