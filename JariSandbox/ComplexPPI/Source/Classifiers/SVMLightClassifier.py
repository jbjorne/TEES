import sys,os
sys.path.append("..")
import shutil
import subprocess
import Core.ExampleUtils as Example
import combine
#from Core.Evaluation import Evaluation
from Core.Classifier import Classifier
from Classifiers.JoachimsSVMBase import JoachimsSVMBase
import copy
import time
import killableprocess
import types

class SVMLightClassifier(JoachimsSVMBase):
    def __init__(self, workDir=None):
        JoachimsSVMBase.__init__(self, workDir=workDir)
        self.binDir = "/home/jari/temp_exec/SVMLight"
        self.trainBin = "/usr/share/biotext/ComplexPPI/SVMLight/svm_learn"
        self.classifyBin = "/usr/share/biotext/ComplexPPI/SVMLight/svm_classify"
        self.type = "binary"
        self.defaultEvaluator = "BinaryEvaluator"
        
    # HACK stuff
    louhiBinDir = "/v/users/jakrbj/svm-light"
    
    @classmethod
    def test(cls, examples, modelPath, output=None, parameters=None, forceInternal=False, classIds=None): # , timeout=None):
        """
        Classify examples with a pre-trained model.
        
        @type examples: string (filename) or list (or iterator) of examples
        @param examples: a list or file containing examples in SVM-format
        @type modelPath: string
        @param modelPath: filename of the pre-trained model file
        @type parameters: a dictionary or string
        @param parameters: parameters for the classifier
        @type output: string
        @param output: the name of the predictions file to be written
        @type forceInternal: Boolean
        @param forceInternal: Use python classifier even if SVM Multiclass binary is defined in Settings.py
        """
        #if forceInternal or Settings.SVMMultiClassDir == None:
        #    return cls.testInternal(examples, modelPath, output)
        timer = Timer()
        if type(examples) == types.ListType:
            print >> sys.stderr, "Classifying", len(examples), "with SVM-Light model", modelPath
            examples, predictions = self.filterClassificationSet(examples, False)
            testPath = self.tempDir+"/test.dat"
            Example.writeExamples(examples, testPath)
        else:
            print >> sys.stderr, "Classifying file", examples, "with SVM-Light model", modelPath
            testPath = examples
            #examples = Example.readExamples(examples,False)
        if os.environ.has_key("METAWRK"):
            args = [SVMMultiClassClassifier.louhiBinDir+"/svm_classify"]
        else:
            args = [self.binDir+"/svm_classify"]
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
            logFile = open("svmlight.log","at")
        else:
            logFile = open(output+".log","wt")
        args += [testPath, modelPath, output]
        #if timeout == None:
        #    timeout = -1
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
        cscConnection.upload(trainExamples, trainExampleFileName, False)
        cscConnection.upload(testExamples, testExampleFileName, False)
        
        idStr = ""
        paramStr = ""
        for key in sorted(trainParameters.keys()):
            idStr += "-" + str(key) + "_" + str(trainParameters[key])
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
        scriptFile.write(cls.louhiBinDir + "/svm_learn" + paramStr + " " + cscConnection.workDir + "/" + trainExampleFileName + " " + cscConnection.workDir + "/model" + idStr + "\n")
        if not isMurska: # louhi
            scriptFile.write("aprun -n 1 ")
        scriptFile.write(cls.louhiBinDir + "/svm_classify " + cscConnection.workDir + "/" + testExampleFileName + " " + cscConnection.workDir + "/model" + idStr + " " + cscConnection.workDir + "/predictions" + idStr + "\n")
        scriptFile.close()
        
        cscConnection.upload(scriptFilePath, scriptName)
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
    
    @classmethod
    def getLouhiStatus(cls, idStr, cscConnection, counts, classIds=None):
        stderrStatus = cscConnection.getFileStatus("script" + idStr + ".sh" + "-stderr")
        if stderrStatus == cscConnection.NOT_EXIST:
            counts["QUEUED"] += 1
            return "QUEUED"
        elif stderrStatus == cscConnection.NONZERO:
            counts["FAILED"] += 1
            return "FAILED"
        elif cscConnection.exists("predictions"+idStr):
            counts["FINISHED"] += 1
            return "FINISHED"
        else:
            counts["RUNNING"] += 1
            return "RUNNING"

    @classmethod
    def downloadModel(cls, idStr, cscConnection, localWorkDir=None):
        modelFileName = "model"+idStr
        if localWorkDir != None:
            modelFileName = os.path.join(localWorkDir, modelFileName)
        cscConnection.download("model"+idStr, modelFileName)
        return "model"+idStr
    
    @classmethod
    def getLouhiPredictions(cls, idStr, cscConnection, localWorkDir=None, dummy=None):
        predFileName = "predictions"+idStr
        if localWorkDir != None:
            predFileName = os.path.join(localWorkDir, predFileName)
        cscConnection.download("predictions"+idStr, predFileName)
        return predFileName
