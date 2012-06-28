__version__ = "$Revision: 1.51 $"

import sys,os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import shutil, tempfile
import subprocess
import Core.ExampleUtils as ExampleUtils
import Core.OptimizeParameters
import combine
import copy
import tempfile
import subprocess
import atexit
import gzip
"""
A wrapper for the Joachims SVM Multiclass classifier.
"""
    
import types, copy
from Core.Classifier import Classifier
import Core.Split as Split
from Utils.Timer import Timer
import Utils.Parameters as Parameters
from Utils.ProgressCounter import ProgressCounter
import Utils.Settings as Settings
import Utils.Download as Download
import Tools.Tool
import SVMMultiClassModelUtils
import Utils.Connection.Unix
from Utils.Connection.Unix import UnixConnection
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator

def install(destDir=None, downloadDir=None, redownload=False, compile=True, updateLocalSettings=False):
    print >> sys.stderr, "Installing SVM-Multiclass"
    if compile:
        url = Settings.URL["SVM_MULTICLASS_SOURCE"]
    else:
        url = Settings.URL["SVM_MULTICLASS_LINUX"]
    if downloadDir == None:
        downloadDir = os.path.join(Settings.DATAPATH, "tools/download/")
    if destDir == None:
        destDir = Settings.DATAPATH
    destDir += "/tools/SVMMultiClass"
    
    Download.downloadAndExtract(url, destDir, downloadDir, redownload=redownload)
    if compile:
        print >> sys.stderr, "Compiling SVM-Multiclass"
        Tools.Tool.testPrograms("SVM-Multiclass", ["make"])
        subprocess.call("cd " + destDir + "; make", shell=True)
    
    Tools.Tool.finalizeInstall(["svm_multiclass_learn", "svm_multiclass_classify"], 
        {"svm_multiclass_learn":"echo | ./svm_multiclass_learn -? > /dev/null", 
         "svm_multiclass_classify":"echo | ./svm_multiclass_classify -? > /dev/null"},
        destDir, {"SVM_MULTICLASS_DIR":destDir}, updateLocalSettings)

def tempUnzip(filename):
    tempdir = tempfile.mkdtemp() # a place for the file
    dst = os.path.join(tempdir, os.path.basename(filename))
    shutil.copy(filename, dst)
    #print "gunzip -fv " + dst
    #subprocess.call("gunzip -fv " + dst, shell=True)
    subprocess.call("gunzip -f " + dst, shell=True)
    if dst.endswith(".gz"):
        dst = dst[:-3]
    atexit.register(shutil.rmtree, tempdir) # mark for deletion
    return os.path.join(tempdir, dst)

class SVMMultiClassClassifier(Classifier):
    """
    A wrapper for the Joachims SVM Multiclass classifier.
    """
    
    def __init__(self, connection=None):
        self.defaultEvaluator = AveragingMultiClassEvaluator
        if connection == None:
            self.connection = UnixConnection() # A local connection
        else:
            self.connection = connection
        self.parameterGrid = None
        self.state = None
        self._job = None
        self._prevJobStatus = None
        
        self.parameters = None
        self.model = None
        self.predictions = None
        #self.parameterFormat = "-%k %v"
        #self.trainDir = "SVM_MULTICLASS_DIR"
        #self.trainCommand = "svm_multiclass_learn %a %m"
        #self.classifyDir = "SVM_MULTICLASS_DIR"
        #self.classifyCommand = "svm_multiclass_classify %m %e %p"
    
    def getJob(self):
        return self._job
    
    def getStatus(self):
        if self._job != None:
            self._prevJobStatus = self.connection.getJobStatus(self._job)
        if self._prevJobStatus in ["FINISHED", "FAILED"]:
            self.state = None
            self._job = None
        if self._prevJobStatus == None:
            return "FINISHED"
        else:
            return self._prevJobStatus
    
    def setState(self, stateName):
        assert self.getStatus() in ["FINISHED", "FAILED"]
        self.state = stateName
        self._job = None
        self._prevJobStatus = None
        if stateName == "TRAIN" or stateName == "OPTIMIZE":
            self.model = None
            self.parameters = None
        # for all states
        self.predictions = None
        #self.optimizeJobs = []
    
    def getExampleFile(self, examples, upload=True, replaceRemote=True, dummy=False):
        # If examples are in a list, they will be written to a file for SVM-multiclass
        if examples == None:
            return None
        if dummy:
            return "DUMMY"
        elif type(examples) == types.ListType:
            assert False
            #ExampleUtils.writeExamples(examples, trainPath + "/")
        else:
            examplesPath = os.path.normpath(os.path.abspath(examples))
       
        localPath = examplesPath
        if upload:
            examplesPath = self.connection.upload(examplesPath, uncompress=True, replace=replaceRemote)
        if examplesPath == localPath and examplesPath.endswith(".gz"): # no upload happened
            examplesPath = tempUnzip(examplesPath)
        return examplesPath
    
    def train(self, examples, outDir, parameters, classifyExamples=None, finishBeforeReturn=False, replaceRemoteExamples=True, dummy=False):
        outDir = os.path.abspath(outDir)
        
        examples = self.getExampleFile(examples, replaceRemote=replaceRemoteExamples, dummy=dummy)
        classifyExamples = self.getExampleFile(classifyExamples, replaceRemote=replaceRemoteExamples, dummy=dummy)
        parameters = Parameters.get(parameters, valueListKey="c")
        svmMulticlassDir = self.connection.getSetting("SVM_MULTICLASS_DIR")
        
        # Return a new classifier instance for following the training process and using the model
        classifier = copy.copy(self)
        classifier.setState("TRAIN")
        classifier.parameters = parameters
        # Train
        if not os.path.exists(outDir):
            os.makedirs(outDir)
        trainCommand = svmMulticlassDir + "/svm_multiclass_learn "
        paramKeys = sorted(parameters.keys())
        idStr = ""
        for key in paramKeys:
            trainCommand += "-" + str(key) + " "
            idStr += "-" + str(key)
            if parameters[key] != None:
                trainCommand += str(parameters[key]) + " "
                idStr += "_" + str(parameters[key])
        classifier.parameterIdStr = idStr
        classifier.model = self.connection.getRemotePath(outDir + "/model" + idStr, True)
        modelPath = self.connection.getRemotePath(outDir + "/model" + idStr, False)
        trainCommand += examples + " " + modelPath
        self.connection.addCommand(trainCommand)
        # Classify with the trained model (optional)
        if classifyExamples != None:
            classifier.predictions = self.connection.getRemotePath(outDir + "/predictions" + idStr, True)
            predictionsPath = self.connection.getRemotePath(outDir + "/predictions" + idStr, False)
            classifyCommand = svmMulticlassDir + "/svm_multiclass_classify " + classifyExamples + " " + modelPath + " " + predictionsPath
            self.connection.addCommand(classifyCommand)
        # Run the process
        jobName = "svm_multiclass_learn" + idStr
        logPath = outDir + "/" + jobName
        if dummy: # return a classifier that connects to an existing job
            self.connection.clearCommands()
            classifier._job = self.connection.getJob(jobDir=outDir, jobName=jobName)
        else: # submit the job
            classifier._job = self.connection.submit(jobDir=outDir, jobName=jobName, stdout=logPath+".stdout")
            if finishBeforeReturn:
                self.connection.waitForJob(classifier._job)
        return classifier
    
    def downloadModel(self, outPath=None, breakConnection=True):
        assert self.getStatus() == "FINISHED" and self.model != None
        self.model = self.connection.download(self.model, outPath)
        if breakConnection:
            self.connection = UnixConnection() # A local connection
        return self.model
    
    def downloadPredictions(self, outPath=None):
        assert self.getStatus() == "FINISHED" and self.predictions != None
        self.predictions = self.connection.download(self.predictions, outPath)
        return self.predictions
    
    def classify(self, examples, output, model=None, finishBeforeReturn=False, replaceRemoteFiles=True):
        output = os.path.abspath(output)
        # Return a new classifier instance for following the training process and using the model
        classifier = copy.copy(self)
        classifier.setState("CLASSIFY")
        # Classify
        if model == None:
            classifier.model = model = self.model
        model = os.path.abspath(model)
        model = self.connection.upload(model, uncompress=True, replace=replaceRemoteFiles)
        classifier.predictions = self.connection.getRemotePath(output, True)
        predictionsPath = self.connection.getRemotePath(output, False)
        examples = self.getExampleFile(examples, replaceRemote=replaceRemoteFiles)
        classifyCommand = self.connection.getSetting("SVM_MULTICLASS_DIR") + "/svm_multiclass_classify " + examples + " " + model + " " + predictionsPath
        classifier._job = self.connection.submit(classifyCommand, 
                                                 jobDir=os.path.abspath(os.path.dirname(output)), 
                                                 jobName="svm_multiclass_classify-"+os.path.basename(model))
        if finishBeforeReturn:
            self.connection.waitForJob(classifier._job)
            classifier.downloadPredictions()
        return classifier
    
    def optimize(self, examples, outDir, parameters, classifyExamples, classIds, step="BOTH", evaluator=None, threshold=False, timeout=None, downloadAllModels=False):
        assert step in ["BOTH", "SUBMIT", "RESULTS"], step
        outDir = os.path.abspath(outDir)
        # Initialize training (or reconnect to existing jobs)
        combinations = Parameters.getCombinations(Parameters.get(parameters, valueListKey="c")) #Core.OptimizeParameters.getParameterCombinations(parameters)
        trained = []
        for combination in combinations:
            trained.append( self.train(examples, outDir, combination, classifyExamples, replaceRemoteExamples=(len(trained) == 0), dummy=(step == "RESULTS")) )
        if step == "SUBMIT": # Return already
            classifier = copy.copy(self)
            classifier.setState("OPTIMIZE")
            return classifier
        
        # Wait for the training to finish
        finalJobStatus = self.connection.waitForJobs([x.getJob() for x in trained])
        # Evaluate the results
        print >> sys.stderr, "Evaluating results"
        #Stream.setIndent(" ")
        bestResult = None
        if evaluator == None:
            evaluator = self.defaultEvaluator
        for i in range(len(combinations)):
            id = trained[i].parameterIdStr
            #Stream.setIndent(" ")
            # Get predictions
            predictions = None
            if trained[i].getStatus() == "FINISHED":
                predictions = trained[i].downloadPredictions()
            else:
                print >> sys.stderr, "No results for combination" + id
                continue
            if downloadAllModels:
                trained[i].downloadModel()
            # Compare to other results
            print >> sys.stderr, "*** Evaluating results for combination" + id + " ***"
            evaluation = evaluator.evaluate(classifyExamples, predictions, classIds, os.path.join(outDir, "evaluation" + id + ".csv"))
            if threshold:
                print >> sys.stderr, "Thresholding"
                evaluation.determineThreshold(testExamples, predictions)
            if bestResult == None or evaluation.compare(bestResult[0]) > 0: #: averageResult.fScore > bestResult[1].fScore:
                bestResult = [evaluation, trained[i], combinations[i]]
            if not self.connection.isLocal():
                os.remove(predictions) # remove predictions to save space
        #Stream.setIndent()
        print >> sys.stderr, "*** Evaluation complete", finalJobStatus, "***"
        print >> sys.stderr, "Selected parameters", bestResult[-1]
        classifier = copy.copy(bestResult[1])
        classifier.downloadModel()
        return classifier
    
#    @classmethod
#    def test(cls, examples, modelPath, output=None, parameters=None, forceInternal=False, classIds=None): # , timeout=None):
#        """
#        Classify examples with a pre-trained model.
#        
#        @type examples: string (filename) or list (or iterator) of examples
#        @param examples: a list or file containing examples in SVM-format
#        @type modelPath: string
#        @param modelPath: filename of the pre-trained model file
#        @type parameters: a dictionary or string
#        @param parameters: parameters for the classifier
#        @type output: string
#        @param output: the name of the predictions file to be written
#        @type forceInternal: Boolean
#        @param forceInternal: Use python classifier even if SVM Multiclass binary is defined in Settings.py
#        """
#        if forceInternal or Settings.SVM_MULTICLASS_DIR == None:
#            return cls.testInternal(examples, modelPath, output)
#        timer = Timer()
#        if type(examples) == types.ListType:
#            print >> sys.stderr, "Classifying", len(examples), "with SVM-MultiClass model", modelPath
#            examples, predictions = self.filterClassificationSet(examples, False)
#            testPath = self.tempDir+"/test.dat"
#            Example.writeExamples(examples, testPath)
#        else:
#            print >> sys.stderr, "Classifying file", examples, "with SVM-MultiClass model", modelPath
#            testPath = examples
#            #examples = Example.readExamples(examples,False)
#        if os.environ.has_key("METAWRK"):
#            args = [SVMMultiClassClassifier.louhiBinDir+"/svm_multiclass_classify"]
#        else:
#            args = [Settings.SVM_MULTICLASS_DIR+"/svm_multiclass_classify"]
#        if modelPath == None:
#            modelPath = "model"
#        if modelPath.endswith(".gz"):
#            modelPath = tempUnzip(modelPath)
#        if testPath.endswith(".gz"):
#            testPath = tempUnzip(testPath)
##        if parameters != None:
##            parameters = copy.copy(parameters)
##            if parameters.has_key("c"):
##                del parameters["c"]
##            if parameters.has_key("predefined"):
##                parameters = copy.copy(parameters)
##                modelPath = os.path.join(parameters["predefined"][0],"classifier/model")
##                del parameters["predefined"]
##            self.__addParametersToSubprocessCall(args, parameters)
#        if output == None:
#            output = "predictions"
#            logFile = open("svmmulticlass.log","at")
#        else:
#            logFile = open(output+".log","wt")
#        compressOutput = False
#        if output.endswith(".gz"):
#            output = output[:-3]
#            compressOutput = True
#        args += [testPath, modelPath, output]
#        #if timeout == None:
#        #    timeout = -1
#        #print args
#        subprocess.call(args, stdout = logFile, stderr = logFile)
#        
#        predictionsFile = open(output, "rt")
#        lines = predictionsFile.readlines()
#        predictionsFile.close()
#        if compressOutput:
#            subprocess.call("gzip -f " + output, shell=True)
#        
#        predictions = []
#        for i in range(len(lines)):
#            predictions.append( [int(lines[i].split()[0])] + lines[i].split()[1:] )
#            #predictions.append( (examples[i],int(lines[i].split()[0]),"multiclass",lines[i].split()[1:]) )
#        print >> sys.stderr, timer.toString()
#        return predictions                
    
#    @classmethod
#    def testInternal(cls, examples, modelPath, output=None, idStem=None):
#        try:
#            import numpy
#            numpy.array([]) # dummy call to survive networkx
#            numpyAvailable = True
#        except:
#            numpyAvailable = False
#
#        if output == None:
#            output = "predictions"
#        
#        outputDetails = False
#        if idStem != None: # Output detailed classification
#            outputDetails = True
#            from Core.IdSet import IdSet
#            featureSet = IdSet(filename=idStem+".feature_names")
#            classSet = IdSet(filename=idStem+".class_names")
#            
#        assert os.path.exists(modelPath)
#        svs = SVMMultiClassModelUtils.getSupportVectors(modelPath)
#        #SVMMultiClassModelUtils.writeModel(svs, modelPath, output+"-test-model")
#        if type(examples) == types.StringType: # examples are in a file
#            print >> sys.stderr, "Classifying file", examples, "with SVM-MultiClass model (internal classifier)", modelPath        
#            examples = Example.readExamples(examples)
#        else:
#            print >> sys.stderr, "Classifying examples with SVM-MultiClass model (internal classifier)", modelPath
#        if numpyAvailable:
#            print >> sys.stderr, "Numpy available, using"
#        
#        numExamples = 0
#        for example in examples:
#            numExamples += 1
#        
#        counter = ProgressCounter(numExamples, "Classify examples", step=0.1)
#        predFile = open(output, "wt")
#        predictions = []
#        isFirst = True
#        for example in examples:
#            strengthVectors = {}
#            strengths = {}
#            counter.update(1, "Classifying: ")
#            highestPrediction = -sys.maxint
#            highestNonNegPrediction = -sys.maxint
#            predictedClass = None
#            highestNonNegClass = None
#            predictionStrings = []
#            mergedPredictionString = ""
#            features = example[2]
#            featureIds = sorted(features.keys())
#            if numpyAvailable:
#                numpyFeatures = numpy.zeros(len(svs[0]))
#                for k, v in features.iteritems():
#                    try:
#                        # SVM-multiclass feature indices start from 1. However, 
#                        # support vectors in variable svs are of course zero based
#                        # lists. Adding -1 to ids aligns features.
#                        numpyFeatures[k-1] = v
#                    except:
#                        pass
#            for svIndex in range(len(svs)):
#                sv = svs[svIndex]
#                if numpyAvailable:
#                    strengthVector = sv * numpyFeatures
#                    prediction = numpy.sum(strengthVector)
#                    if outputDetails:
#                        strengthVectors[svIndex] = strengthVector
#                        strengths[svIndex] = prediction
#                else:
#                    prediction = 0
#                    for i in range(len(sv)):
#                        if features.has_key(i+1):
#                            prediction += features[i+1] * sv[i]
#                if prediction > highestPrediction:
#                    highestPrediction = prediction
#                    predictedClass = svIndex + 1
#                if svIndex > 0 and prediction > highestNonNegPrediction:
#                    highestNonNegPrediction = prediction
#                    highestNonNegClass = svIndex + 1
#                predictionString = "%.6f" % prediction # use same precision as SVM-multiclass does
#                predictionStrings.append(predictionString)
#                mergedPredictionString += " " + predictionString
#            predictions.append([predictedClass, predictionStrings])
#            if isFirst:
#                isFirst = False
#            else:
#                predFile.write("\n")
#            predFile.write(str(predictedClass) + mergedPredictionString)
#            if outputDetails:
#                if example[1] != 1:
#                    predFile.write(example[0] + " " + str(example[3]) + "\n")
#                    cls.writeDetails(predFile, strengthVectors[0], classSet.getName(0+1) + " " + str(strengths[0]), featureSet)
#                    #if predictedClass != 1:
#                    #    cls.writeDetails(predFile, strengthVectors[predictedClass-1], classSet.getName(predictedClass) + " " + str(strengths[predictedClass]), featureSet)
#                    cls.writeDetails(predFile, strengthVectors[example[1]-1], classSet.getName(example[1]) + " " + str(strengths[example[1]-1]), featureSet)
#                else:
#                    predFile.write(example[0] + " " + str(example[3]) + "\n")
#                    cls.writeDetails(predFile, strengthVectors[0], classSet.getName(0+1) + " " + str(strengths[0]), featureSet)
#                    cls.writeDetails(predFile, strengthVectors[highestNonNegClass-1], classSet.getName(highestNonNegClass) + " " + str(strengths[highestNonNegClass-1]), featureSet)
#        predFile.close()
#    
#    @classmethod
#    def writeDetails(cls, predFile, vec, className, featureSet):
#        predFile.write(className+"\n")
#        tuples = []
#        for i in range(len(vec)):
#            if float(vec[i]) != 0.0:
#                tuples.append( (featureSet.getName(i+1), vec[i], i+1) )
#        import operator
#        index1 = operator.itemgetter(1)
#        tuples.sort(key=index1, reverse=True)
#        for t in tuples:
#            predFile.write(" " + str(t[2]) + " " + t[0] + " " + str(t[1]) + "\n")
#        #for i in range(len(vec)):
#        #    if float(vec[i]) != 0.0:
#        #        predFile.write(" " + str(i+1) + " " + featureSet.getName(i+1) + " " + str(vec[i+1]) + "\n")

    
    @classmethod
    def initTrainAndTestOnLouhi(cls, trainExamples, testExamples, trainParameters, cscConnection, localWorkDir=None, classIds=None):
        if cscConnection.account.find("murska") != -1:
            isMurska = True
        else:
            isMurska = False
        assert( type(trainExamples)==types.StringType ), type(trainExamples)
        assert( type(testExamples)==types.StringType ), type(testExamples)
        trainExampleFileName = os.path.split(trainExamples)[-1]
        testExampleFileName = os.path.split(testExamples)[-1]
        assert(trainExampleFileName != testExampleFileName)
        cscConnection.upload(trainExamples, trainExampleFileName, False, compress=True, uncompress=True)
        cscConnection.upload(testExamples, testExampleFileName, False, compress=True, uncompress=True)
        # use uncompressed file names on the CSC machine
        if trainExampleFileName.endswith(".gz"): trainExampleFileName = trainExampleFileName[:-3]
        if testExampleFileName.endswith(".gz"): testExampleFileName = testExampleFileName[:-3]
        
        idStr = ""
        paramStr = ""
        for key in sorted(trainParameters.keys()):
            idStr += "-" + str(key) + "_" + str(trainParameters[key])
            if key != "classifier":
                paramStr += " -" + str(key) + " " + str(trainParameters[key])
        scriptName = "script"+idStr+".sh"
        if cscConnection.exists(scriptName):
            print >> sys.stderr, "Script already on " + cscConnection.machineName + ", process not queued for", scriptName
            return idStr
        
        # Build script
        scriptFilePath = scriptName
        if localWorkDir != None:
            scriptFilePath = os.path.join(localWorkDir, scriptName)
        scriptFile = open(scriptFilePath, "wt")
        scriptFile.write("#!/bin/bash\ncd " + cscConnection.workDir + "\n")
        if not isMurska: # louhi
            scriptFile.write("aprun -n 1 ")
        #print trainParameters
        if "classifier" in trainParameters and trainParameters["classifier"] == "svmperf":
            scriptFile.write(cls.louhiBinDir + "/svm_perf_learn" + paramStr + " " + cscConnection.workDir + "/" + trainExampleFileName + " " + cscConnection.workDir + "/model" + idStr + "\n")
        else:
            scriptFile.write(cls.louhiBinDir + "/svm_multiclass_learn" + paramStr + " " + cscConnection.workDir + "/" + trainExampleFileName + " " + cscConnection.workDir + "/model" + idStr + "\n")
        if not isMurska: # louhi
            scriptFile.write("aprun -n 1 ")
        if "classifier" in trainParameters and trainParameters["classifier"] == "svmperf":
            scriptFile.write(cls.louhiBinDir + "/svm_perf_classify " + cscConnection.workDir + "/" + testExampleFileName + " " + cscConnection.workDir + "/model" + idStr + " " + cscConnection.workDir + "/predictions" + idStr + "\n")
        else:
            scriptFile.write(cls.louhiBinDir + "/svm_multiclass_classify " + cscConnection.workDir + "/" + testExampleFileName + " " + cscConnection.workDir + "/model" + idStr + " " + cscConnection.workDir + "/predictions" + idStr + "\n")
        scriptFile.close()
        
        cscConnection.upload(scriptFilePath, scriptName, compress=False)
        cscConnection.run("chmod a+x " + cscConnection.workDir + "/" + scriptName)
        cscScriptPath = cscConnection.workDir + "/" + scriptName
        if isMurska:
            runCmd = "bsub -o " + cscScriptPath + "-stdout -e " + cscScriptPath + "-stderr -W 10:0 -M " + str(cscConnection.memory) 
            if cscConnection.cores != 1:
                runCmd += " -n " + str(cscConnection.cores)
            runCmd += " < " + cscScriptPath
            cscConnection.run(runCmd)
        else:
            cscConnection.run("qsub -o " + cscConnection.workDir + "/" + scriptName + "-stdout -e " + cscConnection.workDir + "/" + scriptName + "-stderr " + cscConnection.workDir + "/" + scriptName)
        return idStr
    
#    @classmethod
#    def getLouhiStatus(cls, idStr, cscConnection, counts, classIds=None):
#        stderrStatus = cscConnection.getFileStatus("script" + idStr + ".sh" + "-stderr")
#        if stderrStatus == cscConnection.NOT_EXIST:
#            counts["QUEUED"] += 1
#            return "QUEUED"
#        elif stderrStatus == cscConnection.NONZERO:
#            counts["FAILED"] += 1
#            return "FAILED"
#        elif cscConnection.exists("predictions"+idStr):
#            counts["FINISHED"] += 1
#            return "FINISHED"
#        else:
#            counts["RUNNING"] += 1
#            return "RUNNING"

#    @classmethod
#    def downloadModel(cls, idStr, cscConnection, localWorkDir=None):
#        #if not cls.getLouhiStatus(idStr, cscConnection):
#        #    return None
#        modelFileName = "model"+idStr
#        if localWorkDir != None:
#            modelFileName = os.path.join(localWorkDir, modelFileName)
#        cscConnection.download("model"+idStr, modelFileName)
#        return "model"+idStr
    
#    @classmethod
#    def getLouhiPredictions(cls, idStr, cscConnection, localWorkDir=None, dummy=None):
#        #if not cls.getLouhiStatus(idStr, cscConnection):
#        #    return None
#        predFileName = "predictions"+idStr
#        if localWorkDir != None:
#            predFileName = os.path.join(localWorkDir, predFileName)
#        cscConnection.download("predictions"+idStr, predFileName, compress=True, uncompress=True)
#        if os.path.exists(predFileName):
#            return predFileName
#        else:
#            return None
        
#        predictionsFile = open(predFileName, "rt")
#        lines = predictionsFile.readlines()
#        predictionsFile.close()
#        predictions = []
#        for i in range(len(lines)):
#            predictions.append( [int(lines[i].split()[0])] + lines[i].split()[1:] )
#            #predictions.append( (examples[i],int(lines[i].split()[0]),"multiclass",lines[i].split()[1:]) )
#        return predictions
    #ENDIF
    
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
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-e", "--examples", default=None, dest="examples", help="Example File", metavar="FILE")
    optparser.add_option("-a", "--action", default=None, dest="action", help="TRAIN, CLASSIFY or OPTIMIZE")
    optparser.add_option("--optimizeStep", default="BOTH", dest="optimizeStep", help="BOTH, SUBMIT or RESULTS")
    optparser.add_option("--classifyExamples", default=None, dest="classifyExamples", help="Example File", metavar="FILE")
    optparser.add_option("--classIds", default=None, dest="classIds", help="Class ids", metavar="FILE")
    optparser.add_option("-m", "--model", default=None, dest="model", help="path to model file")
    #optparser.add_option("-w", "--work", default=None, dest="work", help="Working directory for intermediate and debug files")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output directory or file")
    optparser.add_option("-r", "--remote", default=None, dest="remote", help="Remote connection")
    #optparser.add_option("-c", "--classifier", default="SVMMultiClassClassifier", dest="classifier", help="Classifier Class")
    optparser.add_option("-p", "--parameters", default=None, dest="parameters", help="Parameters for the classifier")
    #optparser.add_option("-d", "--ids", default=None, dest="ids", help="")
    optparser.add_option("--install", default=None, dest="install", help="Install directory (or DEFAULT)")
    optparser.add_option("--installFromSource", default=False, action="store_true", dest="installFromSource", help="")
    (options, args) = optparser.parse_args()
    
    if options.install != None:
        downloadDir = None
        destDir = None
        if options.install != "DEFAULT":
            if "," in options.install:
                destDir, downloadDir = options.install.split(",")
            else:
                destDir = options.install
        install(destDir, downloadDir, False, options.installFromSource)
        sys.exit()
    else:
        assert options.action in ["TRAIN", "CLASSIFY", "OPTIMIZE"]
        classifier = SVMMultiClassClassifier(Utils.Connection.Unix.getConnection(options.remote))
        if options.action == "TRAIN":
            import time
            trained = classifier.train(options.examples, options.output, options.parameters, options.classifyExamples)
            status = trained.getStatus()
            while status not in ["FINISHED", "FAILED"]:
                print >> sys.stderr, "Training classifier, status =", status
                time.sleep(10)
                status = trained.getStatus()
            print >> sys.stderr, "Training finished, status =", status
            if trained.getStatus() == "FINISHED":
                trained.downloadPredictions()
                trained.downloadModel()
        elif options.action == "CLASSIFY":
            classified = classifier.classify(options.examples, options.output, options.model, True)
            if classified.getStatus() == "FINISHED":
                classified.downloadPredictions()
        else: # OPTIMIZE
            options.parameters = splitParameters(options.parameters)
            optimized = classifier.optimize(options.examples, options.output, options.parameters, options.classifyExamples, options.classIds, step=options.optimizeStep)
            
    # import classifier
    #print >> sys.stderr, "Importing classifier module"
    #exec "from Classifiers." + options.classifier + " import " + options.classifier + " as Classifier"

    # Create classifier object
#    if options.work != None:
#        classifier = Classifier(workDir = options.output)
#    else:
#        classifier = Classifier()
    
#    if options.train:
#        parameters = getArgs(Classifier.train, options.parameters)
#        print >> sys.stderr, "Training on", options.examples, "Parameters:", parameters
#        startTime = time.time()
#        predictions = classifier.train(options.examples, options.output, **parameters)
#        print >> sys.stderr, "(Time spent:", time.time() - startTime, "s)"
#    else: # Classify
#        #parameters = getArgs(Classifier.classify, options.parameters)
#        #print >> sys.stderr, "Classifying", options.examples, "Parameters:", parameters
#        #startTime = time.time()
#        if options.ids != None:
#            predictions = Classifier.testInternal(options.examples, options.model, options.output, options.ids)
#        else:
#            predictions = Classifier.test(options.examples, options.model, options.output, forceInternal=True)
##        print >> sys.stderr, "(Time spent:", time.time() - startTime, "s)"
##        parameters = getArgs(Classifier.classify, options.parameters)
##        print >> sys.stderr, "Classifying", options.examples, "Parameters:", parameters
##        startTime = time.time()
##        predictions = classifier.classify(options.examples, options.output, **parameters)
##        print >> sys.stderr, "(Time spent:", time.time() - startTime, "s)"

