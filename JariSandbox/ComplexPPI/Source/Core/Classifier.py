import sys, os
import combine
#from Evaluation import Evaluation
#import Evaluators.Evaluation as EvaluationBase
import ExampleUtils
import tempfile
sys.path.append("..")
import Utils.TableUtils as TableUtils
import time

defaultOptimizationParameters = {"c":[0.0001,0.001,0.01,0.1,1,10,100]}

class Classifier:
    def __init__(self):
        self.classSet = None
        self.featureSet = None
        #self.notOptimizedParameters = []
    
    def _makeTempDir(self, workDir=None):
        self._workDir = workDir
        if workDir == None:
            self.tempDir = tempfile.mkdtemp() #(dir=tempDir)
        else:
            self.tempDir = workDir
        if not os.path.exists(self.tempDir):
            os.makedirs(self.tempDir)
        if not os.path.exists(self._workDir):
            os.makedirs(self._workDir)
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
    
    def _dictIsIdentical(self, c1, c2):
        k = list(set(c1.keys() + c2.keys()))
        for k in keys:
            if (not c1.has_key(k)) or (not c2.has_key(k)):
                return False
            if c1[k] != c2[k]:
                return False
        return True
    
    def optimize(self, trainSets, classifySets, parameters=defaultOptimizationParameters, evaluationClass=None, evaluationArgs={}, combinationsThatTimedOut=None):
        print >> sys.stderr, "Optimizing parameters"              
        parameterNames = parameters.keys()
        parameterNames.sort()
#        for p in self.notOptimizedParameters:
#            if p in parameterNames:
#                parameterNames.remove(p)
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
        if combinationsThatTimedOut == None:
            combinationsThatTimedOut = []
#        # re-add non-optimized parameters to combinations
#        for p in self.notOptimizedParameters:
#            if parameters.has_key(p):
#                for combination in combinations:
#                    combination[p] = parameters[p]
        
        bestResult = None
        combinationCount = 1
        if hasattr(self, "tempDir"):
            mainTempDir = self.tempDir
            mainDebugFile = self.debugFile
        for combination in combinations:
            print >> sys.stderr, " Parameters "+str(combinationCount)+"/"+str(len(combinations))+":", str(combination),
            skip = False
            for discarded in combinationsThatTimedOut:
                if self._dictIsIdentical(combination, discarded):
                    print >> sys.stderr
                    print >> sys.stderr, "  Discarded before, skipping"
                    skip = True
                    break
            if skip:
                continue
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
                    self.tempDir = mainTempDir+"/parameters"+str(combinationCount)+"/optimization"+str(fold)
                    if not os.path.exists(self.tempDir):
                        os.makedirs(self.tempDir)
                    self.debugFile = open(self.tempDir + "/debug.txt", "wt")
                
                trainStartTime = time.time()
                trainRV = self.train(trainExamplesCopy, combination)
                trainTime = time.time() - trainStartTime
                print >> sys.stderr, " Time spent:", trainTime, "s"
                if trainRV == 0:
                    predictions = self.classify(classifyExamplesCopy)        
                    evaluation = evaluationClass(predictions, **evaluationArgs)
                    if len(classifySets) == 1:
                        print >> sys.stderr, evaluation.toStringConcise("  ")
                    else:
                        print >> sys.stderr, evaluation.toStringConcise(indent="  ", title="Fold "+str(fold))
                    foldResults.append(evaluation)
                    if hasattr(self, "tempDir"):
                        evaluation.saveCSV( self.tempDir+"/results.csv" )
                else:
                    combinationsThatTimedOut.append(combination)
                    print >> sys.stderr, "  Timed out"
                fold += 1
            averageResult = evaluationClass.average(foldResults)
            poolResult = evaluationClass.pool(foldResults)
            if hasattr(self, "tempDir"):
                TableUtils.writeCSV(combination, mainTempDir + "/parameters"+str(combinationCount)+".csv")
                averageResult.saveCSV( mainTempDir+"/parameters"+str(combinationCount)+"/resultsAverage.csv" )
                poolResult.saveCSV( mainTempDir+"/parameters"+str(combinationCount)+"/resultsPooled.csv" )
            if len(classifySets) > 1:
                print >> sys.stderr, averageResult.toStringConcise("  Avg: ")
                print >> sys.stderr, poolResult.toStringConcise("  Pool: ")
            if bestResult == None or poolResult.compare(bestResult[1]) > 0: #: averageResult.fScore > bestResult[1].fScore:
                #bestResult = (predictions, averageResult, combination)
                bestResult = (None, poolResult, combination)
                # Make sure memory is released, especially important since some of the previous steps
                # copy examples
                bestResult[1].classifications = None
                bestResult[1].predictions = None
            combinationCount += 1
            if hasattr(self, "tempDir"):
                self.debugFile.close()
        if hasattr(self, "tempDir"):
            self.tempDir = mainTempDir
            self.debugFile = mainDebugFile
        return bestResult