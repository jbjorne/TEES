import sys, os
import shutil
import subprocess
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Utils.Timer import Timer
import Core.ExampleUtils as Example
from Utils.Parameters import *
import Settings

class LibLinearPoly2Classifier:
    indent = ""
    #IF LOCAL
    louhiBinDir = "/v/users/jakrbj/classifiers/liblinear-1.5-poly2"
    #ENDIF
    
    @classmethod
    def getParams(cls, parameters):
        # If parameters are defined as a string, extract them
        if type(parameters) == types.StringType:
            parameters = splitParameters(parameters)
            for k, v in parameters.iteritems():
                assert(len(v)) == 1
                parameters[k] = v[0]
        return parameters
    
    @classmethod
    def stripComments(cls, exampleFileName):
        assert( type(exampleFileName)==types.StringType )
        f = open(exampleFileName, "rt")
        fOut = open(exampleFileName+"-without-comments", "wt")
        for line in f:
            fOut.write(line.split("#",1)[0]+"\n")
        f.close()
        fOut.close()
        return exampleFileName+"-without-comments"
    
    @classmethod
    def train(cls, examples, parameters, outputFile=None): #, timeout=None):
        """
        Train the SVM-multiclass classifier on a set of examples.
        
        @type examples: string (filename) or list (or iterator) of examples
        @param examples: a list or file containing examples in SVM-format
        @type parameters: a dictionary or string
        @param parameters: parameters for the classifier
        @type outputFile: string
        @param outputFile: the name of the model file to be written
        """
        timer = Timer()
        parameters = cls.getParams(parameters)
        
        # If examples are in a list, they will be written to a file for SVM-multiclass
        if type(examples) == types.ListType:
            print >> sys.stderr, "Training SVM-MultiClass on", len(examples), "examples"
            trainPath = self.tempDir+"/train.dat"
            examples = self.filterTrainingSet(examples)
            Example.writeExamples(examples, trainPath)
        else:
            print >> sys.stderr, "Training SVM-MultiClass on file", examples
            trainPath = cls.stripComments(examples)
        args = ["/home/jari/Programs/liblinear-1.5-poly2/train"]
        cls.__addParametersToSubprocessCall(args, parameters)
        if outputFile == None:
            args += [trainPath, "model"]
            logFile = open("svmmulticlass.log","at")
        else:
            args += [trainPath, outputFile]
            logFile = open(outputFile+".log","wt")
        rv = subprocess.call(args, stdout = logFile)
        logFile.close()
        print >> sys.stderr, timer.toString()
        return rv
    
    @classmethod
    def test(cls, examples, modelPath, output=None, parameters=None, forceInternal=False): # , timeout=None):
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
        if forceInternal or Settings.SVMMultiClassDir == None:
            return cls.testInternal(examples, modelPath, output)
        timer = Timer()
        if type(examples) == types.ListType:
            print >> sys.stderr, "Classifying", len(examples), "with SVM-MultiClass model", modelPath
            examples, predictions = self.filterClassificationSet(examples, False)
            testPath = self.tempDir+"/test.dat"
            Example.writeExamples(examples, testPath)
        else:
            print >> sys.stderr, "Classifying file", examples, "with SVM-MultiClass model", modelPath
            testPath = cls.stripComments(examples)
            examples = Example.readExamples(examples,False)
        args = ["/home/jari/Programs/liblinear-1.5-poly2/predict"]
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
    def __addParametersToSubprocessCall(cls, args, parameters):
        for k,v in parameters.iteritems():
            args.append("-"+k)
            args.append(str(v))

    @classmethod
    def initTrainAndTestOnLouhi(cls, trainExamples, testExamples, trainParameters, cscConnection, localWorkDir=None):
        if cscConnection.account.find("murska") != -1:
            isMurska = True
        else:
            isMurska = False
        assert( type(trainExamples)==types.StringType )
        assert( type(testExamples)==types.StringType )
        trainExamples = cls.stripComments(trainExamples)
        testExamples = cls.stripComments(testExamples)
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
        scriptFile.write(cls.louhiBinDir + "/train " + paramStr + " " + cscConnection.workDir + "/" + trainExampleFileName + " " + cscConnection.workDir + "/model" + idStr + "\n")
        if not isMurska: # louhi
            scriptFile.write("aprun -n 1 ")
        scriptFile.write(cls.louhiBinDir + "/predict " + cscConnection.workDir + "/" + testExampleFileName + " " + cscConnection.workDir + "/model" + idStr + " " + cscConnection.workDir + "/predictions" + idStr + "\n")
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
    def getLouhiStatus(cls, idStr, cscConnection):
        stderrStatus = cscConnection.getFileStatus("script" + idStr + ".sh" + "-stderr")
        if stderrStatus == cscConnection.NOT_EXIST:
            return "QUEUED"
        elif stderrStatus == cscConnection.NONZERO:
            return "FAILED"
        elif cscConnection.exists("predictions"+idStr):
            return "FINISHED"
        else:
            return "RUNNING"

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
    def getLouhiPredictions(cls, idStr, cscConnection, localWorkDir=None):
        if not cls.getLouhiStatus(idStr, cscConnection):
            return None
        predFileName = "predictions"+idStr
        if localWorkDir != None:
            predFileName = os.path.join(localWorkDir, predFileName)
        cscConnection.download("predictions"+idStr, predFileName)
        return predFileName
