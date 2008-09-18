import sys, os
import combine
from Evaluation import Evaluation
import ExampleUtils
import tempfile

defaultOptimizationParameters = {"c":[0.0001,0.001,0.01,0.1,1,10,100]}

class Classifier:
    def _makeTempDir(self, workDir=None):
        self._workDir = workDir
        if workDir == None:
            self.tempDir = tempfile.mkdtemp() #(dir=tempDir)
        else:
            self.tempDir = workDir
        self.debugFile = open(self.tempDir + "/debug.txt", "wt")

    def train(self, examples, parameters=None):        
        raise NotImplementedError
    
    def classify(self, examples, parameters=None):
        raise NotImplementedError
    
    def filterTrainingSet(self, examples):
        trainingSet = []
        for example in examples:
            if not example[2].has_key(self.featureSet.getId("always_negative")):
                trainingSet.append(example)
        return trainingSet
    
    def filterClassificationSet(self, examples, isBinary):
        classificationSet = []
        predictions = []
        for example in examples:
            if not example[2].has_key(self.featureSet.getId("always_negative")):
                classificationSet.append(example)
            else:
                if not example[2].has_key(self.featureSet.getId("out_of_scope")):
                    if isBinary:
                        predictions.append( (example,0.0,"binary") )
                    else:
                        predictions.append( (example,1,"multiclass") )
        return classificationSet, predictions
    
    def optimize(self, trainExamples, classifyExamples, parameters=defaultOptimizationParameters, evaluationClass=Evaluation, evaluationArgs={}):
        print >> sys.stderr, "Optimizing parameters"              
        parameterNames = parameters.keys()
        parameterNames.sort()
        parameterValues = []
        for parameterName in parameterNames:
            parameterValues.append([])
            for value in parameters[parameterName]:
                parameterValues[-1].append( (parameterName,value) )
        combinationLists = combine.combine(*parameterValues)
        combinations = []
        for combinationList in combinationLists:
            combinations.append({})
            for value in combinationList:
                combinations[-1][value[0]] = value[1]
        
        bestResult = None
        count = 1
        if hasattr(self, "tempDir"):
            mainTempDir = self.tempDir
            mainDebugFile = self.debugFile
        for combination in combinations:
            # Make copies of examples in case they are modified
            trainExamplesCopy = ExampleUtils.copyExamples(trainExamples)
            classifyExamplesCopy = ExampleUtils.copyExamples(classifyExamples)
            if hasattr(self, "tempDir"):
                self.tempDir = mainTempDir+"/optimization"+str(count)
                if not os.path.exists(self.tempDir):
                    os.mkdir(self.tempDir)
                self.debugFile = open(self.tempDir + "/debug.txt", "wt")
            print >> sys.stderr, " Parameters "+str(count)+"/"+str(len(combinations))+":", str(combination)
            self.train(trainExamplesCopy, combination)
            predictions = self.classify(classifyExamplesCopy)        
            evaluation = evaluationClass(predictions, **evaluationArgs)
            print >> sys.stderr, evaluation.toStringConcise("  ")
            if bestResult == None or evaluation.fScore > bestResult[1].fScore:
                bestResult = (predictions, evaluation, combination)
            count += 1
            if hasattr(self, "tempDir"):
                self.debugFile.close()
        if hasattr(self, "tempDir"):
            self.tempDir = mainTempDir
            self.debugFile = mainDebugFile
        return bestResult