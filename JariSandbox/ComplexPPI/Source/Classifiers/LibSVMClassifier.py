import sys,os
import shutil
sys.path.append("..")
sys.path.append("/usr/share/biotext/ComplexPPI/LibSVM/libsvm-2.86/python")
import svm
from Core.Classifier import Classifier
import Core.ExampleUtils as ExampleUtils

class LibSVMClassifier(Classifier):
    def __init__(self, workDir=None):
        #global tempDir
        self.negRatio = None
        self._makeTempDir(workDir)
        self.model = None
        self.isBinary = None
        self.classes = None     
    
    def __del__(self):
        self.debugFile.close()
        if self._workDir == None and os.path.exists(self.tempDir):
            print >> sys.stderr, "Removing temporary LibSVM output directory", self.tempDir
            shutil.rmtree(self.tempDir)
  
    def isBinaryProblem(self, examples):
        self.classes = {}
        if self.classSet != None:
            classNames = self.classSet.getNames()
            for name in classNames:
                self.classes[name] = 0
        for example in examples:
            if not self.classes.has_key(example[1]):
                self.classes[example[1]] = 0
            self.classes[example[1]] += 1
        assert(len(self.classes)>1)
        if len(self.classes) == 2:
            assert(1 in self.classes.keys())
            assert(-1 in self.classes.keys())
            return True
        else:
            assert(-1 not in self.classes.keys())
            return False
    
    def train(self, examples, parameters=None):
        self.isBinary = self.isBinaryProblem(examples)
        examples = self.filterTrainingSet(examples)
        ExampleUtils.writeExamples(examples, self.tempDir+"/train.dat")
        #prepare parameters:
        if parameters.has_key("c"):
            assert(not parameters.has_key("C"))
            parameters["C"] = parameters["c"]
            del parameters["c"]
        totalExamples = float(sum(self.classes.values()))
        weight_label = self.classes.keys()
        weight_label.sort()
        weight = []
        for k in weight_label:
            weight.append(1.0-self.classes[k]/totalExamples)
        libSVMparam = svm.svm_parameter(nr_weight = len(self.classes), weight_label=weight_label, weight=weight, **parameters)
        labels = []
        samples = []
        for example in examples:
            labels.append(example[1])
            samples.append(example[2])
        problem = svm.svm_problem(labels, samples)
        self.model = svm.svm_model(problem, libSVMparam)
    
    def classify(self, examples, parameters=None):
        examples, predictions = self.filterClassificationSet(examples, self.isBinary)
        ExampleUtils.writeExamples(examples, self.tempDir+"/test.dat")
        for i in range(len(examples)):
            if self.isBinary:
                predictedClass = self.model.predict(examples[i][2])
                predictions.append( (examples[i],predictedClass,"binary") )
            else:
                predictedClass = self.model.predict(examples[i][2])
                predictions.append( (examples[i],predictedClass,"multiclass") )
        return predictions
            
            