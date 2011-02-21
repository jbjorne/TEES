from SVMMultiClassClassifier import SVMMultiClassClassifier

class MultiLabelClassifier(SVMMultiClassClassifier):
    def __init__(self):
        pass

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
            classModels[key] = os.path.join(modelPath, value)
        f.close()
        mergedPredictions = []
        for classId in classIds:
            className = classIds.getName(classId)
            args = [Settings.SVMMultiClassDir+"/svm_multiclass_classify"]
            self.__addParametersToSubprocessCall(args, parameters)
            if output == None:
                output = "predictions" + cls + "-" + className
                logFile = open("svmmulticlass" + cls + "-" + className + ".log","at")
            else:
                logFile = open(output+".log","wt")
            args += [testPath, classModels[className], output]
            subprocess.call(args, stdout = logFile, stderr = logFile)
            addPredictions(output, mergedPredictions, classId, len(classIds.Ids))
        print >> sys.stderr, timer.toString()
        return mergedPredictions
    
    @classmethod
    def makeClassFiles(cls, classIdSet, examples, outFiles):
        for line in examples:
            classId, rest = line.split(" ", 1)
            className = classIdSet.getName(classId)
            for outFile in outFiles:
                if outFile[0] == className:
                    outFile[1].write(classId + " " + rest)
                else:
                    outFile[1].write("1 " + rest)
    
    @classmethod
    def initTrainAndTestOnLouhi(cls, trainExamples, testExamples, trainParameters, cscConnection, localWorkDir=None):
        assert( type(trainExamples)==types.StringType )
        assert( type(testExamples)==types.StringType )
        trainExampleFileName = os.path.split(trainExamples)[-1]
        testExampleFileName = os.path.split(testExamples)[-1]
        assert(trainExampleFileName != testExampleFileName)
        
        testClassFiles = []
        for name in classIds.getNames():
            testClassFiles.append(name, open(testExamples + ".cls-" + name, "wt"))
        trainClassFiles = []
        for name in classIds.getNames():
            trainClassFiles.append(name, open(trainExamples + ".cls-" + name, "wt"))
                
        cls.makeClassFiles(classIds, testExamples, testClassFiles)
        cls.makeClassFiles(classIds, trainExamples, trainClassFiles)
        origCSCWorkdir = cscConnection.workDir
        for name in classIds.getNames():
            cscConnection.workDir = os.path.join(origCSCWorkdir, name)
            idStr = SVMMultiClassClassifier.initTrainAndTestOnLouhi(trainClassFiles[name], testClassFiles[name], cscConnection, localWorkDir)
        cscConnection.workDir = origCSCWorkdir
    
    @classmethod
    def getLouhiStatus(cls, idStr, cscConnection, counts, classIds=None):
        origCSCWorkdir = cscConnection.workDir
        for name in classIds.getNames():
            cscConnection.workDir = os.path.join(origCSCWorkdir, name)
            currStatus = SVMMultiClassClassifier.getLouhiStatus(idStr, cscConnection, counts)
        cscConnection.workDir = origCSCWorkdir
    
    @classmethod
    def downloadModel(cls, bestParams, cscConnection, localWorkDir=None):
        #if not cls.getLouhiStatus(idStr, cscConnection):
        #    return None
        classModels = {}
        for classId in bestParams.Ids:
            className = bestParams[classId][2],
            modelFileName = os.path.join(className, "model"+bestParams[classId][1])
            if localWorkDir != None:
                modelFileName = os.path.join(localWorkDir, modelFileName)
            cscConnection.download(modelFileName, modelFileName)
            classModels[className] = modelFileName
        # Create model link file
        f = open("model-multilabel", "wt")
        for key in sorted(classModels.keys()):
            f.write(key + ": " + classModels[key] + "\n")
        f.close()
        return "model-multilabel"       
    
    @classmethod
    def getLouhiPredictions(cls, idStr, cscConnection, localWorkDir=None):
        #if not cls.getLouhiStatus(idStr, cscConnection):
        #    return None
        origCSCWorkdir = cscConnection.workDir
        mergedPredictions = []
        for name in classIds.getNames():
            classId = classIds.getId(name)
            if "---" in name: # skip merged classes
                continue
            cscConnection.workDir = os.path.join(origCSCWorkdir, name)
            predFileName = "predictions" + idStr + "cls-" + name
            if localWorkDir != None:
                predFileName = os.path.join(localWorkDir, predFileName)            
            cscConnection.download("predictions"+idStr, predFileName)
            addPredictions(predFileName, mergedPredictions, classId, len(classIds.Ids))
        cscConnection.workDir = origCSCWorkdir
        predFileName = "predictions"+idStr
        f = open(predFileName)
        for mergedPred in mergedPredictions:
            if len(mergedPred[0]) > 1 and "1" in mergedPred[0]:
                mergedPred[0].remove("1")
            mergedPred[0] = ",".join(sorted(list(mergedPred[0])))
            f.write(" ".join(mergedPred) + "\n")
        f.close()
        return predFileName
    
    def addPredictions(self, predFileName, mergedPredictions, classId, numClasses):
        f = open(predFileName)
        for line in f:
            if len(mergedPredictions) <= count:
                mergedPredictions.append([set(["1"])] + ["N/A"] * numClasses)
            predSplits = line.split()
            mergedPredictions[count][0].add(predSplits[0])
            mergedPredictions[count][classId] = predSplits[2]
            count += 1
        f.close()
            