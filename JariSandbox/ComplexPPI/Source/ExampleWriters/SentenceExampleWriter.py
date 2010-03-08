import sys, os, types
import itertools
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
import ExampleUtils
import Core.SentenceGraph as SentenceGraph
from Core.IdSet import IdSet
from Utils.ProgressCounter import ProgressCounter
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils

class SentenceExampleWriter:
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
    
    def writeXML(self, examples, predictions, corpus, outputFile, classSet=None, parse=None, tokenization=None):
        #print >> sys.stderr, "Writing output to Interaction XML"
        corpus = self.loadCorpus(corpus, parse, tokenization)
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
        for example, prediction in itertools.izip(examples, predictions):
            majorId, minorId = example[0].rsplit(".x", 1)
            if majorId != currentMajorId: # new sentence
                if currentMajorId != None:
                    processedSentenceIds.add(currentMajorId)
                    sentenceObject = corpus.sentencesById[currentMajorId]
                    self.writeXMLSentence(exampleQueue, predictionsByExample, sentenceObject, classSet, classIds) # process queue
                exampleQueue = []
                predictionsByExample = {}
                prevMajorIds.add(currentMajorId)
                assert majorId not in prevMajorIds
                currentMajorId = majorId 
            exampleQueue.append(example) # queue example
            predictionsByExample[example[0]] = prediction
            assert example[3]["xtype"] == self.xType, str(example[3]["xtype"]) + "/" + str(self.xType)
        
        # Process what is still in queue
        if currentMajorId != None:
            processedSentenceIds.add(currentMajorId)
            sentenceObject = corpus.sentencesById[currentMajorId]
            self.writeXMLSentence(exampleQueue, predictionsByExample, sentenceObject, classSet, classIds) # process queue
            exampleQueue = []
            predictionsByExample = {}
        
        # Process sentences with no examples (e.g. to clear interactions)
        for sentenceId in sorted(corpus.sentencesById.keys()):
            if sentenceId not in processedSentenceIds:
                sentenceObject = corpus.sentencesById[sentenceId]
                self.writeXMLSentence([], {}, sentenceObject, classSet, classIds)
    
        # Write corpus
        if outputFile != None:
            print >> sys.stderr, "Writing corpus to", outputFile
            ETUtils.write(corpus.rootElement, outputFile)
        return corpus.tree

    def writeXMLSentence(self, examples, predictionsByExample, sentenceObject, classSet, classIds):
        raise NotImplementedError
    
    def assertSameSentence(self, examples):
        currentSetMajorId = None
        for example in examples:
            majorId, minorId = example[0].rsplit(".x", 1)
            if currentSetMajorId == None: 
                currentSetMajorId = majorId
            else: 
                assert currentSetMajorId == majorId, str(currentSetMajorId) + "/" + str(majorId)
    
    def removeChildren(self, element, childTags, childAttributes=None):
        for tag in childTags:
            childElements = element.findall(tag)
            if childElements != None:
                for childElement in childElements:
                    if childAttributes == None:
                        element.remove(childElement)
                    else:
                        removeElement = True
                        for k, v in childAttributes.iteritems():
                            if childElement.get(k) != v:
                                removeElement = False
                                break
                        if removeElement:
                            element.remove(childElement)
    
    def removeNonNameEntities(self, sentenceElement):
        """
        Removes non-name entities and returns number of entities
        before removal.
        """
        entityElements = sentenceElement.findall("entity")
        if entityElements != None:
            entityCount = len(entityElements) # get the count _before_ removing entities
            for entityElement in entityElements:
                if entityElement.get("isName") == "False": # interaction word
                    sentenceElement.remove(entityElement)

    def isNegative(self, prediction, classSet=None):
        if classSet == None: # binary classification
            if prediction[0] > 0:
                return False
            else:
                return True
        else:
            return classSet.getName(prediction[0]) == "neg"

    def setElementType(self, element, prediction, classSet=None, classIds=None):
        if classSet == None: # binary classification
            if prediction[0] > 0:
                element.attrib["type"] = str(True)
            else:
                element.attrib["type"] = str(False)
        else:
            element.attrib["type"] = classSet.getName(prediction[0])
            classWeights = prediction[1:]
            predictionString = ""
            for i in range(len(classWeights)):
                if predictionString != "":
                    predictionString += ","
                predictionString += classSet.getName(classIds[i]) + ":" + str(classWeights[i])
            element.attrib["predictions"] = predictionString