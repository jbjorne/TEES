import sys,os
sys.path.append("..")
import shutil
import subprocess
import killableprocess
import Core.ExampleUtils as Example
import combine
import copy
import types
#from Core.Evaluation import Evaluation
from Core.Classifier import Classifier
import Core.Split as Split
from Evaluators.MultiClassEvaluator import MultiClassEvaluator
from Utils.Timer import Timer

binDir = "/usr/share/biotext/ComplexPPI/SVMMultiClass"

defaultOptimizationParameters = {"c":[0.0001,0.001,0.01,0.1,1,10,100]}

def train(examples, parameters, model, workDir=None):
    print >> sys.stderr, "Training SVM-MultiClass on", examples
    timer = Timer()
    classifier = SVMMultiClassClassifier(workDir=workDir)
    classifier.train(examples, parameters, model)
    print >> sys.stderr, timer.toString()
        
def test(examples, parameters, model, classifications, workDir=None):
    print >> sys.stderr, "Classifying", examples, "with SVM-MultiClass model", model
    timer = Timer()
    classifier = SVMMultiClassClassifier(workDir=workDir)
    classifier.classify(examples, model, parameters, classifications)
    print >> sys.stderr, timer.toString()

class SVMMultiClassClassifier(Classifier):
    def __init__(self, workDir=None, negRatio=None):
        #global tempDir
        self.negRatio = None
        self._makeTempDir(workDir)        
    
    def __del__(self):
        self.debugFile.close()
        if self._workDir == None and os.path.exists(self.tempDir):
            print >> sys.stderr, "Removing temporary SVM-multi-class work directory", self.tempDir
            shutil.rmtree(self.tempDir)
    
    def train(self, examples, classifierArgs, outputFile=None, style=None, timeout=None):
#        if parameters.has_key("predefined"):
#            return 0
        if type(examples) == types.ListType:
            trainPath = self.tempDir+"/train.dat"
            examples = self.filterTrainingSet(examples)
            if self.negRatio != None:
                examples = self.downSampleNegatives(examples, self.negRatio)
            Example.writeExamples(examples, trainPath)
        else:
            trainPath = examples
        if style != None and "no_duplicates" in style:
            if type(examples) == types.ListType:
                examples = Example.removeDuplicates(examples)
            else:
                print >> sys.stderr, "Warning, duplicates not removed from example file", examples
        if timeout == None:
            timeout = -1
        args = [binDir+"/svm_multiclass_learn"]
        self.__addParametersToSubprocessCall(args, classifierArgs)
        if outputFile == None:
            args += [trainPath, self.tempDir+"/model"]
        else:
            args += [trainPath, outputFile]
        return killableprocess.call(args, stdout = self.debugFile, timeout = timeout)
        
    def classify(self, examples, modelPath, parameters=None, output=None):
        if type(examples) == types.ListType:
            examples, predictions = self.filterClassificationSet(examples, False)
            testPath = self.tempDir+"/test.dat"
            Example.writeExamples(examples, testPath)
        else:
            testPath = examples
            examples = Example.readExamples(examples,False)
        args = [binDir+"/svm_multiclass_classify"]
        if modelPath == None:
            modelPath = self.tempDir+"/model"
        if parameters != None:
            parameters = copy.copy(parameters)
            if parameters.has_key("c"):
                del parameters["c"]
            if parameters.has_key("predefined"):
                parameters = copy.copy(parameters)
                modelPath = os.path.join(parameters["predefined"][0],"classifier/model")
                del parameters["predefined"]
            self.__addParametersToSubprocessCall(args, parameters)
        if output == None:
            output = self.tempDir+"/predictions"
        args += [testPath, modelPath, output]
        subprocess.call(args, stdout = self.debugFile)
        #os.remove(self.tempDir+"/model")
        predictionsFile = open(output, "rt")
        lines = predictionsFile.readlines()
        predictionsFile.close()
        predictions = []
        for i in range(len(lines)):
            predictions.append( (examples[i],int(lines[i].split()[0]),"multiclass",lines[i].split()[1:]) )
        return predictions
    
    def __addParametersToSubprocessCall(self, args, parameters):
        for k,v in parameters.iteritems():
            args.append("-"+k)
            args.append(str(v))

    def downSampleNegatives(self, examples, ratio):
        positives = []
        negatives = []
        for example in examples:
            if example[1] == 1:
                negatives.append(example)
            else:
                positives.append(example)
        
        targetNumNegatives = ratio * len(positives)
        if targetNumNegatives > len(negatives):
            targetNumNegatives = len(negatives)
        sample = Split.getSample(len(negatives), targetNumNegatives / float(len(negatives)) )
        examples = positives
        for i in range(len(sample)):
            if sample[i] == 0:
                examples.append(negatives[i])
        return examples

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    from optparse import OptionParser
    import os
    from Utils.Parameters import *
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-e", "--examples", default=None, dest="examples", help="Example File", metavar="FILE")
    optparser.add_option("-t", "--train", default=None, dest="train", action="store_true", help="train (default = classify)")
    optparser.add_option("-w", "--work", default=None, dest="work", help="Working directory for intermediate and debug files")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output directory or file")
    optparser.add_option("-c", "--classifier", default="SVMMultiClassClassifier", dest="classifier", help="Classifier Class")
    optparser.add_option("-p", "--parameters", default=None, dest="parameters", help="Parameters for the classifier")
    (options, args) = optparser.parse_args()

    # import classifier
    print >> sys.stderr, "Importing classifier module"
    exec "from Classifiers." + options.classifier + " import " + options.classifier + " as Classifier"

    # Create classifier object
    if options.work != None:
        classifier = Classifier(workDir = options.output)
    else:
        classifier = Classifier()
    
    if options.train:
        parameters = getArgs(Classifier.train, options.parameters)
        print >> sys.stderr, "Training on", options.examples, "Parameters:", parameters
        startTime = time.time()
        predictions = classifier.train(options.examples, options.output, **parameters)
        print >> sys.stderr, "(Time spent:", time.time() - startTime, "s)"
    else: # Classify
        parameters = getArgs(Classifier.classify, options.parameters)
        print >> sys.stderr, "Classifying", options.examples, "Parameters:", parameters
        startTime = time.time()
        predictions = classifier.classify(options.examples, options.output, **parameters)
        print >> sys.stderr, "(Time spent:", time.time() - startTime, "s)"

