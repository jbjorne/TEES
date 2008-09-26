import sys, os
import combine
#from Evaluation import Evaluation
#import Evaluators.Evaluation as EvaluationBase
import ExampleUtils
import tempfile

defaultOptimizationParameters = {"c":[0.0001,0.001,0.01,0.1,1,10,100]}

class Classifier:
    def __init__(self):
        self.classSet = None
        self.featureSet = None
    
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
    
    def optimize(self, trainSets, classifySets, parameters=defaultOptimizationParameters, evaluationClass=None, evaluationArgs={}):
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
            print >> sys.stderr, " Parameters "+str(count)+"/"+str(len(combinations))+":", str(combination)
            # Make copies of examples in case they are modified
            fold = 1
            foldResults = []
            for classifyExamples in classifySets:
                trainExamples = []
                for trainSet in trainSets:
                    if trainSet != classifyExamples:
                        trainExamples.extend(trainSet)
                trainExamplesCopy = ExampleUtils.copyExamples(trainExamples)
                classifyExamplesCopy = ExampleUtils.copyExamples(classifyExamples)
                if hasattr(self, "tempDir"):
                    self.tempDir = mainTempDir+"/optimization"+str(count)
                    if not os.path.exists(self.tempDir):
                        os.mkdir(self.tempDir)
                    self.debugFile = open(self.tempDir + "/debug.txt", "wt")
                self.train(trainExamplesCopy, combination)
                predictions = self.classify(classifyExamplesCopy)        
                evaluation = evaluationClass(predictions, **evaluationArgs)
                if len(classifySets) == 1:
                    print >> sys.stderr, evaluation.toStringConcise("  ")
                else:
                    print >> sys.stderr, evaluation.toStringConcise(indent="  ", title="Fold "+str(fold))
                foldResults.append(evaluation)
                if hasattr(self, "tempDir"):
                    evaluation.saveCSV( self.tempDir+"/optimizationResultsF"+str(count)+".csv" )
                fold += 1
            averageResult = evaluationClass.average(foldResults)
            if hasattr(self, "tempDir"):
                averageResult.saveCSV( self.tempDir+"/optimizationResultsAvg"+str(count)+".csv" )
            if len(classifySets) > 1:
                print >> sys.stderr, averageResult.toStringConcise("  Avg: ")
            if bestResult == None or averageResult.compare(bestResult[1]) > 0: #: averageResult.fScore > bestResult[1].fScore:
                #bestResult = (predictions, averageResult, combination)
                bestResult = (None, averageResult, combination)
            count += 1
            if hasattr(self, "tempDir"):
                self.debugFile.close()
        if hasattr(self, "tempDir"):
            self.tempDir = mainTempDir
            self.debugFile = mainDebugFile
        return bestResult