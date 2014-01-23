import sys,os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import shutil, tempfile
import subprocess
import Core.ExampleUtils as ExampleUtils
import Utils.Libraries.combine as combine
import copy
import tempfile
import atexit
import gzip
import types, copy
from Classifier import Classifier
import Utils.Parameters as Parameters
import Utils.Settings as Settings
import Utils.Connection.Connection as Connection
from Utils.Connection.UnixConnection import UnixConnection

class ExternalClassifier(Classifier):
    """
    A wrapper for external classifier executables.
    """
    
    def __init__(self, connection=None):
        self.defaultEvaluator = None
        if connection == None:
            self.connection = UnixConnection() # A local connection
        else:
            self.connection = connection
        self.parameterGrid = None
        self.state = None
        self._job = None
        self._prevJobStatus = None
        self._filesToRelease = []
        
        self.parameters = None
        self.model = None
        self.predictions = None
        
        self.parameterFormat = "-%k %v"
        self.parameterDefaults = {"train":None, "classify":None}
        self.parameterAllowNew = {"train":True, "classify":True}
        self.parameterValueListKey = {"train":None, "classify":None}
        self.parameterValueLimits = {"train":None, "classify":None}
        self.parameterValueTypes = {"train":None, "classify":None}
        
        self.trainDirSetting = None
        self.trainCommand = None
        self.classifyDirSetting = None
        self.classifyCommand = None
    
    def getJob(self):
        return self._job
    
    def getStatus(self):
        if self._job != None:
            self._prevJobStatus = self.connection.getJobStatus(self._job)
        if self._prevJobStatus in ["FINISHED", "FAILED"]:
            self.state = None
            self._job = None
            for filename in self._filesToRelease:
                ExternalClassifier.getFileCounter(filename, add=-1, createIfNotExist=False)
            self._filesToRelease = []
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
    
    def _getParameterString(self, parameters):
        paramKeys = sorted(parameters.keys())
        idStr = ""
        paramString = ""
        for key in paramKeys:
            if key.startswith("TEES."):
                continue
            if len(paramString) > 0 and not paramString.endswith(" "):
                paramString += " "
            if parameters[key] != None:
                paramString += self.parameterFormat.replace("%k", key).replace("%v", str(parameters[key])).strip()
                idStr += "-" + str(key) + "_" + str(parameters[key])
            else:
                paramString += self.parameterFormat.replace("%k", key).replace("%v", "").strip()
                idStr += "-" + str(key)
        # sanitize id
        idStr = idStr.replace(":", ".")
        idStr = idStr.replace(" ", "_")
        idStr = "".join([c for c in idStr if c.isalnum() or c in ('.','_',"-")]).rstrip()
        return paramString, idStr
    
    def train(self, examples, outDir, parameters, classifyExamples=None, finishBeforeReturn=False, replaceRemoteExamples=True, dummy=False):
        outDir = os.path.abspath(outDir)
        
        examples = self.getExampleFile(examples, replaceRemote=replaceRemoteExamples, dummy=dummy)
        classifyExamples = self.getExampleFile(classifyExamples, replaceRemote=replaceRemoteExamples, dummy=dummy)
        #parameters = Parameters.get(parameters, valueListKey="c")
        trainDir = os.path.normpath(self.connection.getSetting(self.trainDirSetting)) + os.path.sep
        
        # Return a new classifier instance for following the training process and using the model
        classifier = copy.copy(self)
        classifier.setState("TRAIN")
        classifier.parameters = parameters
        classifier._filesToRelease = [examples, classifyExamples]
        # Train
        if not os.path.exists(outDir):
            os.makedirs(outDir)
        #trainCommand = os.path.join(trainDir, self.trainCommand)
        trainCommand = self.trainCommand.replace("%d", trainDir)
        parameters = Parameters.get(parameters, self.parameterDefaults["train"], self.parameterAllowNew["train"], 
                                    self.parameterValueListKey["train"], self.parameterValueLimits["train"], 
                                    self.parameterValueTypes["train"])
        paramString, idStr = self._getParameterString(parameters)
        classifier.parameterIdStr = idStr
        classifier.model = self.connection.getRemotePath(outDir + "/model" + idStr, True)
        modelPath = self.connection.getRemotePath(outDir + "/model" + idStr, False)
        trainCommand = trainCommand.replace("%p", paramString).replace("%e", examples).replace("%m", modelPath).strip()
        self.connection.addCommand(trainCommand)
        # Classify with the trained model (optional)
        if classifyExamples != None:
            classifier.predictions = self.connection.getRemotePath(outDir + "/predictions" + idStr, True)
            predictionsPath = self.connection.getRemotePath(outDir + "/predictions" + idStr, False)
            classifyDir = os.path.normpath(self.connection.getSetting(self.classifyDirSetting)) + os.path.sep
            classifyCommand = self.classifyCommand.replace("%d", classifyDir).replace("%e", classifyExamples).replace("%m", modelPath).replace("%c", predictionsPath).strip()
            self.connection.addCommand(classifyCommand)
        # Run the process
        jobName = self.trainCommand.split()[0].replace("%d", "") + idStr
        logPath = outDir + "/" + jobName
        if dummy: # return a classifier that connects to an existing job
            self.connection.clearCommands()
            classifier._job = self.connection.getJob(jobDir=outDir, jobName=jobName)
        else: # submit the job
            classifier._job = self.connection.submit(jobDir=outDir, jobName=jobName, stdout=logPath+".stdout")
            if finishBeforeReturn:
                self.connection.waitForJob(classifier._job)
                self.getStatus()
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
        classifier._filesToRelease = [examples]
        self.connection.clearCommands()
        classifyDir = os.path.normpath(self.connection.getSetting(self.classifyDirSetting)) + os.path.sep
        classifyCommand = self.classifyCommand.replace("%d", classifyDir).replace("%e", examples).replace("%m", model).replace("%c", predictionsPath).strip()
        self.connection.addCommand(classifyCommand)
        classifier._job = self.connection.submit(jobDir=os.path.abspath(os.path.dirname(output)), 
                                                 jobName=self.classifyCommand.split()[0].replace("%d", "") + "-" + os.path.basename(model))
        if finishBeforeReturn:
            self.connection.waitForJob(classifier._job)
            classifier.downloadPredictions()
        return classifier
    
    def optimize(self, examples, outDir, parameters, classifyExamples, classIds, step="BOTH", evaluator=None, determineThreshold=False, timeout=None, downloadAllModels=False):
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
            threshold = None
            if determineThreshold:
                print >> sys.stderr, "Thresholding, original micro =",
                evaluation = evaluator.evaluate(classifyExamples, predictions, classIds, os.path.join(outDir, "evaluation-before-threshold" + id + ".csv"), verbose=False)
                print >> sys.stderr, evaluation.microF.toStringConcise()
                threshold, bestF = evaluator.threshold(classifyExamples, predictions)
                print >> sys.stderr, "threshold =", threshold, "at binary fscore", str(bestF)[0:6]
            evaluation = evaluator.evaluate(classifyExamples, ExampleUtils.loadPredictions(predictions, threshold=threshold), classIds, os.path.join(outDir, "evaluation" + id + ".csv"))
            if bestResult == None or evaluation.compare(bestResult[0]) > 0: #: averageResult.fScore > bestResult[1].fScore:
                bestResult = [evaluation, trained[i], combinations[i], threshold]
            if not self.connection.isLocal():
                os.remove(predictions) # remove predictions to save space
        #Stream.setIndent()
        if bestResult == None:
            raise Exception("No results for any parameter combination")
        print >> sys.stderr, "*** Evaluation complete", finalJobStatus, "***"
        print >> sys.stderr, "Selected parameters", bestResult[2]
        classifier = copy.copy(bestResult[1])
        classifier.threshold = bestResult[3]
        classifier.downloadModel()
        return classifier