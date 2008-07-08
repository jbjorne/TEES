import sys,os
import shutil
import subprocess
import tempfile
import Example
import combine
from Evaluation import Evaluation

binDir = "../../../Download/svm_light_linux"
tempDir = "Data/SVMLightTempFiles"

defaultOptimizationParameters = {"c":[0.00001,0.0001,0.001,0.01,0.1,0,1,10,100,1000,10000]}

class SVMLightClassifier:
    def __init__(self, workDir=None):
        global tempDir
        
        self.__workDir = workDir
        if workDir == None:
            self.tempDir = tempfile.mkdtemp(dir=tempDir)
        else:
            self.tempDir = workDir
    
    def __del__(self):
        if self.__workDir == None and os.path.exists(self.tempDir):
            print >> sys.stderr, "Removing temporary SVM-light work directory", self.tempDir
            shutil.rmtree(self.tempDir)
    
    def train(self, examples, parameters=None):        
        Example.writeExamples(examples, self.tempDir+"/train.dat")
        args = [binDir+"/svm_learn",self.tempDir+"/train.dat", self.tempDir+"/model"] 
        if parameters != None:
            self.__addParametersToSubprocessCall(args, parameters)
        subprocess.call(args)
        
    def classify(self, examples, parameters=None):
        Example.writeExamples(examples, self.tempDir+"/test.dat")
        args = [binDir+"/svm_classify",self.tempDir+"/test.dat", self.tempDir+"/model", self.tempDir+"/predictions"]
        if parameters != None:
            self.__addParametersToSubprocessCall(args, parameters)
        subprocess.call(args)
        
        predictionsFile = open(self.tempDir+"/predictions", "rt")
        lines = predictionsFile.readlines()
        predictionsFile.close()
        predictions = []
        for i in range(len(lines)):
            predictions.append( (examples[i],float(lines[i])) )
        return predictions
    
    def optimize(self, trainExamples, classifyExamples, parameters=defaultOptimizationParameters):
        print >> sys.stderr, "Optimizing parameters"        
        parameterNames = parameters.keys()
        parameterNames.sort()
        parameterValues = []
        for parameterName in parameterNames:
            parameterValues.append([])
            for value in parameters[parameterName]:
                parameterValues[-1].append( (parameterName,value) )
        combinationLists = combine.combine(parameterValues)
        combinations = []
        for combinationList in combinationLists:
            combinations.append({})
            for value in combinationList:
                combinations[-1][value[0]] = value[1]
        bestResult = (-1,0)
        count = 1
        for combination in combinations:
            print >> sys.stderr, "Parameters "+str(1)+"/"+str(len(combinations))+":", str(combination)
            self.train(trainExamples)
            predictions = self.classify(classifyExamples)        
            evaluation = Evaluation(predictions)
            print >> sys.stderr, " " + evaluation.toStringConcise()
            if evaluation.fScore > bestResult[0]:
                bestResult = (predictions, evaluation, combination)
            count += 1
        return bestResult
    
    def __addParametersToSubprocessCall(self, args, parameters):
        for k,v in parameters.iteritems():
            args.append("-"+key+" "+str(v))