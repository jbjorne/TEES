def initTrainAndTestOnLouhi(trainExamples, testExamples, trainParameters, cscConnection, localWorkDir=None):
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
    scriptFile.write(cls.louhiBinDir + "/svm_multiclass_learn" + paramStr + " " + cscConnection.workDir + "/" + trainExampleFileName + " " + cscConnection.workDir + "/model" + idStr + "\n")
    if not isMurska: # louhi
        scriptFile.write("aprun -n 1 ")
    scriptFile.write(cls.louhiBinDir + "/svm_multiclass_classify " + cscConnection.workDir + "/" + testExampleFileName + " " + cscConnection.workDir + "/model" + idStr + " " + cscConnection.workDir + "/predictions" + idStr + "\n")
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

def getLouhiStatus(idStr, cscConnection):
    stderrStatus = cscConnection.getFileStatus("script" + idStr + ".sh" + "-stderr")
    if stderrStatus == cscConnection.NOT_EXIST:
        return "QUEUED"
    elif stderrStatus == cscConnection.NONZERO:
        return "FAILED"
    elif cscConnection.exists("predictions"+idStr):
        return "FINISHED"
    else:
        return "RUNNING"

def runModels():
    pass

if __name__=="__main__":
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default=None, dest="input", help="input directory")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
    optparser.add_option("-w", "--workdir", default="/wrk/jakrbj/shared-task-test", dest="workdir", help="working directory")
    optparser.add_option("-l", "--log", default=None, dest="log", help="Process Manager log file")
    (options, args) = optparser.parse_args()
    assert options.input != None
    assert os.path.exists(options.input)
    assert options.output != None
    assert os.path.exists(options.output)
    
    if options.log != None:
        logFile = open(options.log, "at")
    update(options.input, options.output, options.workdir, 10)
    if options.log != None:
        logFile.close()