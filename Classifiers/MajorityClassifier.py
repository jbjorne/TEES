import sys,os
sys.path.append("..")
import shutil
import subprocess
import Core.ExampleUtils as Example
import combine
from Core.Evaluation import Evaluation
from Core.Classifier import Classifier
from Evaluators.MultiClassEvaluator import MultiClassEvaluator


class MajorityClassifier(Classifier):
    def __init__(self, workDir=None):
        self.majorityClass = None
        self._makeTempDir(workDir)
    
    def __del__(self):
        self.debugFile.close()
        if self._workDir == None and os.path.exists(self.tempDir):
            print >> sys.stderr, "Removing temporary classifier work directory", self.tempDir
            shutil.rmtree(self.tempDir)    
    
    def train(self, examples, parameters=None):
        examples = self.filterTrainingSet(examples)
        classDict = {}
        for example in examples:
            if not classDict.has_key(example[1]):
                classDict[example[1]] = 0
            classDict[example[1]] += 1
        bestCount = -1
        for k,v in classDict.iteritems():
            if k != 1: # neg
                if classDict[k] > bestCount:
                    bestCount = classDict[k]
                    self.majorityClass = k
        return 0
        
    def classify(self, examples, parameters=None):        
        examples, predictions = self.filterClassificationSet(examples, False)
        for example in examples:
            predictions.append( (example, self.majorityClass) )
        return predictions