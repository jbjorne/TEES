import sys,os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import shutil
import subprocess
#import killableprocess
import Core.ExampleUtils as Example
import combine
import copy
import types
#from Core.Evaluation import Evaluation
from Core.Classifier import Classifier
import Core.Split as Split
from Evaluators.MultiClassEvaluator import MultiClassEvaluator
from Utils.Timer import Timer
from Utils.Parameters import *

class SVMMultiClassClassifier(Classifier):
    binDir = "/usr/share/biotext/ComplexPPI/SVMMultiClass"
    indent = ""
    
    louhiBinDir = "/v/users/jakrbj/svm-multiclass"
    
#    def __init__(self, workDir=None, negRatio=None):
#        sys.exit("Just use the class methods")
#        #global tempDir
#        #self.negRatio = None
#        self._makeTempDir(workDir)        
#    
#    def __del__(self):
#        self.debugFile.close()
#        if self._workDir == None and os.path.exists(self.tempDir):
#            print >> sys.stderr, "Removing temporary SVM-multi-class work directory", self.tempDir
#            shutil.rmtree(self.tempDir)
    
    @classmethod
    def train(cls, examples, parameters, outputFile=None, timeout=None):
        timer = Timer()
        if type(parameters) == types.StringType:
            parameters = splitParameters(parameters)
            for k, v in parameters.iteritems():
                assert(len(v)) == 1
                parameters[k] = v[0]
        if type(examples) == types.ListType:
            print >> sys.stderr, "Training SVM-MultiClass on", len(examples), "examples"
            trainPath = self.tempDir+"/train.dat"
            examples = self.filterTrainingSet(examples)
            #if self.negRatio != None:
            #    examples = self.downSampleNegatives(examples, self.negRatio)
            Example.writeExamples(examples, trainPath)
        else:
            print >> sys.stderr, "Training SVM-MultiClass on file", examples
            trainPath = examples
#        if style != None and "no_duplicates" in style:
#            if type(examples) == types.ListType:
#                examples = Example.removeDuplicates(examples)
#            else:
#                print >> sys.stderr, "Warning, duplicates not removed from example file", examples
        args = [cls.binDir+"/svm_multiclass_learn"]
        cls.__addParametersToSubprocessCall(args, parameters)
        if outputFile == None:
            args += [trainPath, "model"]
            logFile = open("svmmulticlass.log","at")
        else:
            args += [trainPath, outputFile]
            logFile = open(outputFile+".log","wt")
        if timeout == None:
            timeout = -1
        rv = subprocess.call(args, stdout = logFile)
        logFile.close()
        print >> sys.stderr, timer.toString()
        return rv
    
    @classmethod
    def test(cls, examples, modelPath, output=None, parameters=None, timeout=None):
        timer = Timer()
        if type(examples) == types.ListType:
            print >> sys.stderr, "Classifying", len(examples), "with SVM-MultiClass model", modelPath
            examples, predictions = self.filterClassificationSet(examples, False)
            testPath = self.tempDir+"/test.dat"
            Example.writeExamples(examples, testPath)
        else:
            print >> sys.stderr, "Classifying file", examples, "with SVM-MultiClass model", modelPath
            testPath = examples
            examples = Example.readExamples(examples,False)
        args = [cls.binDir+"/svm_multiclass_classify"]
        if modelPath == None:
            modelPath = "model"
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
            output = "predictions"
            logFile = open("svmmulticlass.log","at")
        else:
            logFile = open(output+".log","wt")
        args += [testPath, modelPath, output]
        if timeout == None:
            timeout = -1
        #print args
        subprocess.call(args, stdout = logFile, stderr = logFile)
        predictionsFile = open(output, "rt")
        lines = predictionsFile.readlines()
        predictionsFile.close()
        predictions = []
        for i in range(len(lines)):
            predictions.append( [int(lines[i].split()[0])] + lines[i].split()[1:] )
            #predictions.append( (examples[i],int(lines[i].split()[0]),"multiclass",lines[i].split()[1:]) )
        print >> sys.stderr, timer.toString()
        return predictions
    
    @classmethod
    def __addParametersToSubprocessCall(cls, args, parameters):
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
    
    @classmethod
    def initTrainAndTestOnLouhi(cls, trainExamples, testExamples, trainParameters, cscConnection, localWorkDir=None):
        if cscConnection.account.find("murska") != -1:
            isMurska = True
        else:
            isMurska = False
        assert( type(trainExamples)==types.StringType )
        assert( type(testExamples)==types.StringType )
        trainExampleFileName = os.path.split(trainExamples)[-1]
        testExampleFileName = os.path.split(testExamples)[-1]
        assert(trainExampleFileName != testExampleFileName)
        cscConnection.upload(trainExamples, trainExampleFileName, False)
        cscConnection.upload(testExamples, testExampleFileName, False)
        
        idStr = ""
        paramStr = ""
        for key in sorted(trainParameters.keys()):
            idStr += "-" + str(key) + "_" + str(trainParameters[key])
            paramStr += " -" + str(key) + " " + str(trainParameters[key])
        scriptName = "script"+idStr+".sh"
        if cscConnection.exists(scriptName):
            print >> sys.stderr, "Script already on Louhi, process not queued for", scriptName
            return idStr
        
        # Build script
        scriptFilePath = scriptName
        if localWorkDir != None:
            scriptFilePath = os.path.join(localWorkDir, scriptName)
        scriptFile = open(scriptFilePath, "wt")
        scriptFile.write("#!/bin/bash\ncd " + cscConnection.workDir + "\n")
        if not isMurska: # louhi
            scriptFile.write("aprun -n 1 ")
        scriptFile.write(cls.louhiBinDir + "/svm_multiclass_learn" + paramStr + " " + cscConnection.workDir + "/" + trainExampleFileName + " " + cscConnection.workDir + "/model" + idStr + "\n")
        if not isMurska: # louhi
            scriptFile.write("aprun -n 1 ")
        scriptFile.write(cls.louhiBinDir + "/svm_multiclass_classify " + cscConnection.workDir + "/" + testExampleFileName + " " + cscConnection.workDir + "/model" + idStr + " " + cscConnection.workDir + "/predictions" + idStr + "\n")
        scriptFile.close()
        
        cscConnection.upload(scriptFilePath, scriptName)
        cscConnection.run("chmod a+x " + cscConnection.workDir + "/" + scriptName)
        cscScriptPath = cscConnection.workDir + "/" + scriptName
        if isMurska:
            cscConnection.run("bsub -o " + cscScriptPath + "-stdout -e " + cscScriptPath + "-stderr -W 10:0 -M 4194304 < " + cscScriptPath)
        else:
            cscConnection.run("qsub -o " + cscConnection.workDir + "/" + scriptName + "-stdout -e " + cscConnection.workDir + "/" + scriptName + "-stderr " + cscConnection.workDir + "/" + scriptName)
        return idStr
    
    @classmethod
    def getLouhiStatus(cls, idStr, cscConnection):
        return cscConnection.exists("predictions"+idStr)

    @classmethod
    def downloadModel(cls, idStr, cscConnection, localWorkDir=None):
        if not cls.getLouhiStatus(idStr, cscConnection):
            return None
        modelFileName = "model"+idStr
        if localWorkDir != None:
            modelFileName = os.path.join(localWorkDir, modelFileName)
        cscConnection.download("model"+idStr, modelFileName)
        return "model"+idStr
    
    @classmethod
    def getLouhiPredictions(cls, idStr, examples, cscConnection, localWorkDir=None):
        assert(type(examples)==types.ListType)
        if not cls.getLouhiStatus(idStr, cscConnection):
            return None
        predFileName = "predictions"+idStr
        if localWorkDir != None:
            predFileName = os.path.join(localWorkDir, predFileName)
        cscConnection.download("predictions"+idStr, predFileName)
        predictionsFile = open(predFileName, "rt")
        lines = predictionsFile.readlines()
        predictionsFile.close()
        predictions = []
        for i in range(len(lines)):
            predictions.append( [int(lines[i].split()[0])] + lines[i].split()[1:] )
            #predictions.append( (examples[i],int(lines[i].split()[0]),"multiclass",lines[i].split()[1:]) )
        return predictions
    
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

