import sys,os
sys.path.append("..")
import shutil
import subprocess
import Core.ExampleUtils as Example
import combine
#from Core.Evaluation import Evaluation
from Core.Classifier import Classifier
import copy
import time
import killableprocess
import types

class JoachimsSVMBase(Classifier):
    def __init__(self, workDir=None):
        #global tempDir
        Classifier.__init__(self)
        self.trainBin = None
        self.classifyBin = None
        self.type = None # "binary or multiclass
        self.defaultEvaluator = None # e.g. "BinaryEvaluator"
        
        self._makeTempDir(workDir)        
    
    def __del__(self):
        self.debugFile.close()
        if self._workDir == None and os.path.exists(self.tempDir):
            print >> sys.stderr, "Removing temporary SVM work directory", self.tempDir
            shutil.rmtree(self.tempDir)
    
    def train(self, examples, parameters=None, outputDir=None):
        timeout = -1
        if type(examples) == types.StringType:
            trainFilePath = examples
        elif type(examples) == types.ListType:
            examples = self.filterTrainingSet(examples)
            parameters = copy.copy(parameters)
            if parameters.has_key("style"):
                if "no_duplicates" in parameters["style"]:
                    examples = Example.removeDuplicates(examples)
                del parameters["style"]
            Example.writeExamples(examples, self.tempDir+"/train.dat")
            trainFilePath = self.tempDir+"/train.dat"

        if parameters.has_key("timeout"):
            timeout = parameters["timeout"]
            del parameters["timeout"]        
        args = [self.trainBin]
        if parameters != None:
            self.__addParametersToSubprocessCall(args, parameters)
        args += [trainFilePath, self.tempDir+"/model"]
        return killableprocess.call(args, stdout = self.debugFile, timeout = timeout)
        
    def classify(self, examples, parameters=None):
        if type(examples) == types.StringType:
            testFilePath = examples
            predictions = []
            realClasses = []
            exampleFile = open(examples,"rt")
            for line in exampleFile.readlines():
                realClasses.append(int(line.split(" ",1)[0].strip()))
            exampleFile.close()
        elif type(examples) == types.ListType:
            examples, predictions = self.filterClassificationSet(examples, True)
            Example.writeExamples(examples, self.tempDir+"/test.dat")
            testFilePath = self.tempDir+"/test.dat"
        args = [self.classifyBin]
        if parameters != None:
            self.__addParametersToSubprocessCall(args, parameters)
        args += [testFilePath, self.tempDir+"/model", self.tempDir+"/predictions"]
        #print args
        subprocess.call(args, stdout = self.debugFile)
        os.remove(self.tempDir+"/model")
        predictionsFile = open(self.tempDir+"/predictions", "rt")
        lines = predictionsFile.readlines()
        predictionsFile.close()
        #predictions = []
        for i in range(len(lines)):
            if type(examples) == types.ListType:
                predictions.append( (examples[i],float(lines[i]),self.type,lines[i]) )
            else:
                predictions.append( ([None,realClasses[i]],float(lines[i]),self.type) )
        return predictions
    
    def __addParametersToSubprocessCall(self, args, parameters):
        for k,v in parameters.iteritems():
            args.append("-"+k)
            args.append(str(v))