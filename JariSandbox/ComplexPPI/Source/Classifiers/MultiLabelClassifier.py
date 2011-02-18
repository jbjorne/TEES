from SVMMultiClassClassifier import SVMMultiClassClassifier

class MultiLabelClassifier(SVMMultiClassClassifier):
    def __init__(self):
        pass
    
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
        for name in classIds.getNames():
            idStr = SVMMultiClassClassifier.initTrainAndTestOnLouhi(trainClassFiles[name], testClassFiles[name], cscConnection, localWorkDir)
    
    @classmethod
    def getLouhiStatus(cls, idStr, cscConnection, counts, classIds=None):
        for name in classIds.getNames():
            currStatus = SVMMultiClassClassifier.getLouhiStatus(idStr, cscConnection, counts)
    
    @classmethod
    def downloadModel(cls, idStr, cscConnection, localWorkDir=None):
        #if not cls.getLouhiStatus(idStr, cscConnection):
        #    return None
        for name in classIds.getNames():
            modelFileName = "model"+idStr
            if localWorkDir != None:
                modelFileName = os.path.join(localWorkDir, modelFileName)
            cscConnection.download("model"+idStr, modelFileName)
            return "model"+idStr
    
    @classmethod
    def getLouhiPredictions(cls, idStr, cscConnection, localWorkDir=None):
        #if not cls.getLouhiStatus(idStr, cscConnection):
        #    return None
        predFileName = "predictions"+idStr
        if localWorkDir != None:
            predFileName = os.path.join(localWorkDir, predFileName)
        cscConnection.download("predictions"+idStr, predFileName)
        return predFileName