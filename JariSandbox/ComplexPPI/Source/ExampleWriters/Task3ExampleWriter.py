import sys
from SentenceExampleWriter import SentenceExampleWriter
import cElementTreeUtils as ETUtils
import types
import itertools
    
class Task3ExampleWriter(SentenceExampleWriter):
    def __init__(self):
        self.xType = "task3"
        
    def writeXML(self, examples, predictions, corpus, outputFile, classSet=None, parse=None, tokenization=None):
        print >> sys.stderr, "Adding task 3 to Interaction XML"
        examples, predictions = self.loadExamples(examples, predictions)
        
        if type(classSet) == types.StringType: # class names are in file
            classSet = IdSet(filename=classSet)
        classIds = None
        if classSet != None:
            classIds = classSet.getIds()
        
        # Determine subtask
        task3Type = None
        for example in examples:
            assert example[3].has_key("t3type")
            task3Type = example[3]["t3type"]
            break
        assert task3Type == "speculation" or task3Type == "negation"
        
        corpusTree = ETUtils.ETFromObj(corpus)
        corpusRoot = corpusTree.getroot()
        
        # Remove the task 3 subtask information if it already exists
        for entity in corpusRoot.getiterator("entity"):
            if task3Type == "speculation":
                entity.set("speculation", "False")
            else: # task3Type == "negation"
                entity.set("negation", "False")
        
        specMap = {}
        negMap = {}
        for example, prediction in itertools.izip(examples, predictions):
            assert example[3]["xtype"] == "task3"
            if example[3]["t3type"] == "speculation":
                map = specMap
            else:
                map = negMap
            if prediction[0] != 1:
                assert not map.has_key(example[3]["entity"])
                map[example[3]["entity"]] = True
        
        for entity in corpusRoot.getiterator("entity"):
            if task3Type == "speculation":
                if specMap.has_key(entity.get("id")):
                    entity.set("speculation", "True")
                else:
                    entity.set("speculation", "False")
            elif task3Type == "negation":
                if negMap.has_key(entity.get("id")):
                    entity.set("negation", "True")
                else:
                    entity.set("negation", "False")
        
        # Write corpus
        if outputFile != None:
            print >> sys.stderr, "Writing corpus to", outputFile
            ETUtils.write(corpusRoot, outputFile)
        return corpusTree