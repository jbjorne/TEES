import sys
from SentenceExampleWriter import SentenceExampleWriter
import Utils.ElementTreeUtils as ETUtils
from Core.IdSet import IdSet
import types
import itertools
    
class ModifierExampleWriter(SentenceExampleWriter):
    def __init__(self):
        self.xType = "task3"
        
    def writeXML(self, examples, predictions, corpus, outputFile, classSet=None, parse=None, tokenization=None, goldCorpus=None, exampleStyle=None, structureAnalyzer=None):
        """
        Writes task 3 examples to interaction XML. Assumes task 3 classification
        is done with SVMMulticlass Classifier, used for two classes.
        """
        print >> sys.stderr, "Adding task 3 to Interaction XML"
        examples, predictions = self.loadExamples(examples, predictions)
        
        if type(classSet) == types.StringType: # class names are in file
            classSet = IdSet(filename=classSet)
        classIds = None
        if classSet != None:
            classIds = classSet.getIds()

        corpusTree = ETUtils.ETFromObj(corpus)
        corpusRoot = corpusTree.getroot()
        
        # Determine subtask
        task3Type = None
        for example in examples:
            assert example[3].has_key("t3type")
            task3Type = example[3]["t3type"]
            break        
        if task3Type == None:
            if outputFile != None:
                print >> sys.stderr, "Writing corpus to", outputFile
                ETUtils.write(corpusRoot, outputFile)
            return corpusTree
        assert task3Type in ["multiclass", "speculation", "negation"]
        
        # Remove the task 3 subtask information if it already exists
        for entity in corpusRoot.getiterator("entity"):
            if task3Type == "multiclass":
                entity.set("speculation", "False")
                entity.set("negation", "False")
            elif task3Type == "speculation":
                entity.set("speculation", "False")
            else: # task3Type == "negation"
                entity.set("negation", "False")
        
        specMap = {}
        negMap = {}
        for example, prediction in itertools.izip(examples, predictions):
            assert example[3]["xtype"] == "task3"
            if example[3]["t3type"] == "multiclass":
                predictedClassName = classSet.getName(prediction[0])
                if predictedClassName != "neg":
                    predictedModifiers = predictedClassName.split("---")
                    if "negation" in predictedModifiers:
                        assert not negMap.has_key(example[3]["entity"])
                        negMap[example[3]["entity"]] = (True, prediction)
                    if "speculation" in predictedModifiers:
                        assert not specMap.has_key(example[3]["entity"])
                        specMap[example[3]["entity"]] = (True, prediction)
            else:
                if example[3]["t3type"] == "speculation":
                    map = specMap
                else:
                    map = negMap
                if prediction[0] != 1:
                    assert not map.has_key(example[3]["entity"])
                    map[example[3]["entity"]] = (True, prediction)
                else:
                    assert not map.has_key(example[3]["entity"])
                    map[example[3]["entity"]] = (False, prediction)
        
        for entity in corpusRoot.getiterator("entity"):
            eId = entity.get("id")
            if task3Type == "multiclass":
                if specMap.has_key(eId):
                    entity.set("speculation", str(specMap[eId][0]))
                    entity.set("modConf", self.getPredictionStrengthString(specMap[eId][1], classSet, classIds))
                if negMap.has_key(eId):
                    entity.set("negation", str(negMap[eId][0]))
                    entity.set("modConf", self.getPredictionStrengthString(negMap[eId][1], classSet, classIds))
            else:
                if task3Type == "speculation":
                    if specMap.has_key(eId):
                        entity.set("speculation", str(specMap[eId][0]))
                        entity.set("specConf", self.getPredictionStrengthString(specMap[eId][1], classSet, classIds, [""]))
                elif task3Type == "negation":
                    if negMap.has_key(eId):
                        entity.set("negation", str(negMap[eId][0]))
                        entity.set("negConf", self.getPredictionStrengthString(negMap[eId][1], classSet, classIds, ["","speculation"]))
        
        # Write corpus
        if outputFile != None:
            print >> sys.stderr, "Writing corpus to", outputFile
            ETUtils.write(corpusRoot, outputFile)
        return corpusTree