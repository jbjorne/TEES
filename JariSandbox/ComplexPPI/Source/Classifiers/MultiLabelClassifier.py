import sys, os
import types
from SVMMultiClassClassifier import SVMMultiClassClassifier
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Core.ExampleUtils as Example
from Utils.Timer import Timer
import combine
import copy
from Core.IdSet import IdSet
import Settings
import subprocess

class MultiLabelClassifier(SVMMultiClassClassifier):
    def __init__(self):
        pass

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
        if parameters != None:
            parameters = copy.copy(parameters)
            if parameters.has_key("c"):
                del parameters["c"]
            if parameters.has_key("predefined"):
                parameters = copy.copy(parameters)
                modelPath = os.path.join(parameters["predefined"][0],"classifier/model")
                del parameters["predefined"]
        # Read model
        if modelPath == None:
            modelPath = "model-multilabel"
        classModels = {}
        f = open(modelPath, "rt")
        for line in f:
            key, value = line.split()
            classModels[key] = value
        f.close()
        mergedPredictions = []
        if type(classIds) == types.StringType:
            classIds = IdSet(filename=classIds)
        #print classModels
        for className in classIds.getNames():
            if className != "neg" and not "---" in className:
                classId = classIds.getId(className)
                args = [Settings.SVMMultiClassDir+"/svm_multiclass_classify"]
                #self.__addParametersToSubprocessCall(args, parameters)
                classOutput = "predictions" + ".cls-" + className
                logFile = open("svmmulticlass" + ".cls-" + className + ".log","at")
                args += [testPath, classModels[str(className)], classOutput]
                subprocess.call(args, stdout = logFile, stderr = logFile)
                cls.addPredictions(classOutput, mergedPredictions, classId, len(classIds.Ids))
        print >> sys.stderr, timer.toString()
        
        predFileName = output
        f = open(predFileName, "wt")
        for mergedPred in mergedPredictions:
            if len(mergedPred[0]) > 1 and "1" in mergedPred[0]:
                mergedPred[0].remove("1")
            mergedPred[1] = str(mergedPred[1])
            mergedPred[0] = ",".join(sorted(list(mergedPred[0])))
            f.write(" " + " ".join(mergedPred) + "\n")
        f.close()
        
        return mergedPredictions
    
    @classmethod
    def divideExamples(cls, classIdSet, examples, outFiles):
        exampleFile = open(examples, "rt")
        for line in exampleFile:
            classId, rest = line.split(" ", 1)
            className = classIdSet.getName(int(classId))
            assert className != None, (classId, className, classIdSet.Ids)
            if className == "neg":
                classNames = []
            elif "---" in className:
                classNames = className.split("---")
            else:
                classNames = [className]
            for outFileName in outFiles:
                if outFileName in classNames:
                    outFiles[outFileName].write("2 " + rest)
                else:
                    outFiles[outFileName].write("1 " + rest)
        exampleFile.close()
    
    @classmethod
    def initTrainAndTestOnLouhi(cls, trainExamples, testExamples, trainParameters, cscConnection, localWorkDir=None, classIds = None):
        assert( type(trainExamples)==types.StringType )
        assert( type(testExamples)==types.StringType )
        trainExampleFileName = os.path.split(trainExamples)[-1]
        testExampleFileName = os.path.split(testExamples)[-1]
        assert(trainExampleFileName != testExampleFileName)
        
        testClassFiles = {}
        for name in classIds.getNames():
            testClassFiles[name] = str(testExamples + ".cls-" + name)
        trainClassFiles = {}
        for name in classIds.getNames():
            trainClassFiles[name] = str(trainExamples + ".cls-" + name)
        
        origCSCWorkdir = cscConnection.workDir
        for name in classIds.getNames():
            if name != "neg" and not "---" in name:
                cscConnection.workDir = origCSCWorkdir
                cscConnection.mkdir(name)
                cscConnection.workDir = os.path.join(origCSCWorkdir, name)
                idStr = SVMMultiClassClassifier.initTrainAndTestOnLouhi(trainClassFiles[name], testClassFiles[name], trainParameters, cscConnection, localWorkDir, None)
        cscConnection.workDir = origCSCWorkdir
        return idStr
    
    @classmethod
    def makeClassFiles(cls, trainExamples, testExamples, classIds):
        print >> sys.stderr, "Building class separated example files"
        testClassFiles = {}
        for name in classIds.getNames():
            if name != "neg" and not "---" in name:
                testClassFiles[name] = open(testExamples + ".cls-" + name, "wt")
        trainClassFiles = {}
        for name in classIds.getNames():
            if name != "neg" and not "---" in name:
                trainClassFiles[name] = open(trainExamples + ".cls-" + name, "wt")       
        cls.divideExamples(classIds, testExamples, testClassFiles)
        cls.divideExamples(classIds, trainExamples, trainClassFiles)
        for x in testClassFiles:
            testClassFiles[x].close()
        for x in trainClassFiles:
            trainClassFiles[x].close()
   
    @classmethod
    def getLouhiStatus(cls, idStr, cscConnection, counts, classIds=None):
        origCSCWorkdir = cscConnection.workDir
        for name in classIds.getNames():
            if name != "neg" and not "---" in name:
                cscConnection.workDir = os.path.join(origCSCWorkdir, name)
                currStatus = SVMMultiClassClassifier.getLouhiStatus(idStr, cscConnection, counts)
        cscConnection.workDir = origCSCWorkdir
    
    @classmethod
    def downloadModel(cls, bestParams, cscConnection, localWorkDir=None):
        #if not cls.getLouhiStatus(idStr, cscConnection):
        #    return None
        bestParams = bestParams[0]
        classModels = {}
        origCSCWorkdir = cscConnection.workDir
        for className in bestParams:
            print (localWorkDir, origCSCWorkdir)
            modelFileName = os.path.join("model"+bestParams[className][1]+".cls-"+className)
            if localWorkDir != None:
                modelFileName = os.path.join(localWorkDir, modelFileName)
            cscConnection.workDir = os.path.join(origCSCWorkdir, className)
            cscConnection.download("model"+bestParams[className][1], modelFileName)
            classModels[className] = modelFileName
        cscConnection.workDir = origCSCWorkdir
        # Create model link file
        f = open(os.path.join(localWorkDir, "model-multilabel"), "wt")
        for key in sorted(classModels.keys()):
            f.write(key + "\t" + classModels[key] + "\n")
        f.close()
        return "model-multilabel"
    
    @classmethod
    def getLouhiPredictions(cls, idStr, cscConnection, localWorkDir=None, classIds=None):
        #if not cls.getLouhiStatus(idStr, cscConnection):
        #    return None
        origCSCWorkdir = cscConnection.workDir
        mergedPredictions = []
        for name in classIds.getNames():
            classId = classIds.getId(name)
            if name == "neg" or "---" in name: # skip merged classes
                continue
            cscConnection.workDir = os.path.join(origCSCWorkdir, name)
            predFileName = "predictions" + idStr + ".cls-" + name
            if localWorkDir != None:
                predFileName = os.path.join(localWorkDir, predFileName)            
            cscConnection.download("predictions"+idStr, predFileName)
            cls.addPredictions(predFileName, mergedPredictions, classId, len(classIds.Ids))
        cscConnection.workDir = origCSCWorkdir
        predFileName = "predictions"+idStr
        f = open(predFileName, "wt")
        for mergedPred in mergedPredictions:
            if len(mergedPred[0]) > 1 and "1" in mergedPred[0]:
                mergedPred[0].remove("1")
            mergedPred[1] = str(mergedPred[1])
            mergedPred[0] = ",".join(sorted(list(mergedPred[0])))
            f.write(" " + " ".join(mergedPred) + "\n")
        f.close()
        return predFileName
    
    @classmethod
    def addPredictions(cls, predFileName, mergedPredictions, classId, numClasses):
        f = open(predFileName)
        count = 0
        strClassId = str(classId)
        for line in f:
            if len(mergedPredictions) <= count:
                mergedPredictions.append([set(["1"])] + [0.0] + ["N/A"] * (numClasses-1))
            predSplits = line.split()
            if predSplits[0] != "1":
                mergedPredictions[count][0].add(strClassId)
                mergedPredictions[count][classId] = predSplits[2]
            else:
                negConfidence = float(predSplits[1])
                if negConfidence > mergedPredictions[count][1]:
                    mergedPredictions[count][1] = negConfidence
            count += 1
        f.close()
            