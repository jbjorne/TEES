import sys,os
import types
import shutil
import filecmp
import subprocess
import tempfile
import tarfile
import codecs
mainTEESDir = os.path.abspath(os.path.join(__file__, "../.."))
print mainTEESDir
sys.path.append(mainTEESDir)
import Utils.InteractionXML.Catenate as Catenate
import Utils.Libraries.stats as stats
import Utils.Convert.DDITools as DDITools
from collections import defaultdict
import Core.ExampleUtils as ExampleUtils
from Core.IdSet import IdSet
import STFormat.STTools as STTools

def listExecutables(filter=["Core", "FeatureBuilders", "InteractionXML", "GeniaEventsToSharedTask"]):
    tableTitleLines = "| Program | Location | Description |\n"
    tableTitleLines += "|:-----------|:-----------|:-----------|"
    mainTableTitleLines = "| Program | Description |\n"
    mainTableTitleLines += "|:-----------|:-----------|"
    categories = ["Main Programs", "Tool Wrappers", "Other Programs"]
    programs = {}
    for category in categories:
        programs[category] = []
    for triple in os.walk(mainTEESDir):
        for filename in sorted(triple[2]):
            skip = False
            for filterRule in filter:
                if filterRule in os.path.join(triple[0], filename):
                    skip = True
                    break
            if skip:
                continue
            if filename.endswith(".py"):
                f = open(os.path.join(triple[0], filename), "rt")
                lines = f.readlines()
                f.close()
                isExecutable = False
                description = ""
                for line in lines:
                    if "optparser = OptionParser(" in line:
                        assert line.count("\"") in [0, 2], line
                        if line.count("\"") == 2:
                            description = line.split("\"")[1]
                            description = description.split("\\n", 1)[-1]
                            description = description.split(".")[0]
                            description = description.strip()
                        isExecutable = True
                if isExecutable:
                    subDir = triple[0][len(mainTEESDir)+1:].strip()
                    if subDir == "":
                        category = "Main Programs"
                    elif "Tools" in subDir or "Preprocessor" in filename:
                        category = "Tool Wrappers"
                    else:
                        category = "Other Programs"
                    programs[category].append( [subDir, filename, description] )
    
    for category in categories:
        print "##", category
        if category == "Main Programs":
            print mainTableTitleLines
        else:
            print tableTitleLines
        for program in sorted(programs[category]):
            if program[0] == "":
                print "|", program[1], "|", program[2], "|"
            else:
                print "|", program[1], "|", program[0], "|", program[2], "|"
        print

def hasTask(subdir, tasks):
    for task in tasks:
        if task in subdir:
            return True
    return False

def extractModels(input, output, tasks, classificationOutput=None, preserveOutput=False):
    assert input != None
    assert output != None
    assert input != output
    if os.path.exists(output) and not preserveOutput:
        shutil.rmtree(output)
    if not os.path.exists(output):
        os.makedirs(output)
    for subDir in os.listdir(input):
        subDirAbs = os.path.join(input, subDir)
        if os.path.isdir(subDirAbs) and hasTask(subDir, tasks): #subDir.split(".")[0] in tasks:
            for suffix in ["devel", "test"]:
                if os.path.exists(os.path.join(subDirAbs, "model-" + suffix)):
                    src = os.path.join(subDirAbs, "model-" + suffix)
                    dst = os.path.join(output, subDir + "-" + suffix) #subDir.split(".")[0] + "-" + suffix)
                    print >> sys.stderr, "Copying model", src, "to", dst
                    shutil.copytree(src, dst)
                if os.path.exists(os.path.join(subDirAbs, "log.txt")):
                    print >> sys.stderr, "Copying training log for", subDir
                    shutil.copy2(os.path.join(subDirAbs, "log.txt"), os.path.join(output, subDir + "-train-log.txt"))
                if classificationOutput != None:
                    if os.path.exists(os.path.join(subDirAbs, "classification-" + suffix)):
                        src = os.path.join(subDirAbs, "classification-" + suffix + "/" + suffix + "-events.tar.gz")
                        dst = os.path.join(classificationOutput, subDir + "-" + suffix + "-events.tar.gz")
                        print src
                        if os.path.exists(src):
                            print >> sys.stderr, "Copying classification", src, "to", dst
                            if not os.path.exists(os.path.dirname(dst)):
                                os.makedirs(os.path.dirname(dst))
                            shutil.copy2(src, dst)
                
def linkDuplicates(input, output=None):
    if output != None:
        if os.path.exists(output):
            print >> sys.stderr, "Removing output directory"
            shutil.rmtree(output)
        print >> sys.stderr, "Copying input directory"
        shutil.copytree(input, output)
    else:
        output = input
    print >> sys.stderr, "Listing files"
    files = []
    for triple in os.walk(output):
        for filename in triple[2]:
            filePath = os.path.join(triple[0], filename)
            if os.path.isfile(filePath):
                files.append(filePath)
    print >> sys.stderr, "Detecting duplicates"
    duplicates = {}
    for i in range(len(files)-1):
        if os.path.getsize(files[i]) > 1000:
            print >> sys.stderr, "Processing", files[i]
            for j in range(i+1, len(files)):
                if filecmp.cmp(files[i], files[j], shallow=False):
                    if files[i] not in duplicates:
                        duplicates[files[i]] = []
                    duplicates[files[i]].append(files[j])
        else:
            print >> sys.stderr, "Skipping small file", files[i]
    print >> sys.stderr, "Duplicates found:"
    for key in sorted(duplicates.keys()):
        print key, sorted(duplicates[key])
    print >> sys.stderr, "Replacing duplicates with links"
    for original in sorted(duplicates.keys()):
        for duplicate in duplicates[original]:
            os.remove(duplicate)
            relPath = os.path.relpath(original, os.path.commonprefix((original, duplicate)))
            lnCommand = "cd " + os.path.dirname(duplicate) + "; ln -s " + relPath + " " + os.path.basename(duplicate) + "; cd -"
            print >> sys.stderr, "Linking:", lnCommand
            subprocess.call(lnCommand, shell=True)

def packageItems(input, archiveName):
    if not os.path.exists(os.path.dirname(archiveName)):
        os.makedirs(os.path.dirname(archiveName))
    tarCommand = lnCommand = "cd " + input + "; tar cvfj " + archiveName + " *; cd -"
    print >> sys.stderr, "Packaging:", tarCommand
    subprocess.call(tarCommand, shell=True)

def makeModelPackage(input, output, tasks, archiveName):
    modelPath = os.path.join(options.output, "models")
    extractModels(options.input, modelPath, options.tasks, options.output + "/classification")
    linkDuplicates(modelPath)
    packageItems(modelPath, archiveName)
    
def extractSubmissionFiles(src, outDir, task, dataset, includeTags=[".a2", ".rel"], questionnairePath=None):
    # extract
    tempdir = os.path.abspath(tempfile.mkdtemp())
    f = tarfile.open(src, "r")
    f.extractall(tempdir)
    f.close()
    # repackage
    allFiles = os.listdir(tempdir)
    tarFiles = []
    for file in allFiles:
        for tag in includeTags:
            if file.endswith(tag):
                f = codecs.open(os.path.join(tempdir, file), "rt", "utf-8")
                lines = f.readlines()
                f.close()
                keptLines = []
                for line in lines:
                    if line[0] != "X":
                        keptLines.append(line)
                f = codecs.open(os.path.join(tempdir, file), "wt", "utf-8")
                for line in keptLines:
                    f.write(line)
                f.close()
                tarFiles.append(file)
                break
    if questionnairePath != None and os.path.exists(questionnairePath) and dataset == "test":
        shutil.copy(questionnairePath, os.path.join(tempdir, "questionnaire.txt"))
        tarFiles.append("questionnaire.txt")
    outputFile = os.path.join(outDir, task + "-" + dataset + "-submit.tar.gz")
    packageFile = tarfile.open(outputFile, "w:gz")
    tempCwd = os.getcwd()
    os.chdir(tempdir)
    for file in tarFiles:
        packageFile.add(file)
    os.chdir(tempCwd)
    packageFile.close()
    shutil.rmtree(tempdir)

def getBioNLPSubmissionFiles(input, output, tasks, preserveOutput=False, includeTags=[".a2"]):
    assert input != None
    assert output != None
    assert input != output
    if os.path.exists(output) and not preserveOutput:
        shutil.rmtree(output)
    if not os.path.exists(output):
        os.makedirs(output)
    for subDir in os.listdir(input):
        subDirAbs = os.path.join(input, subDir)
        if os.path.isdir(subDirAbs) and hasTask(subDir, tasks):
            if os.path.exists(os.path.join(subDirAbs, "log.txt")):
                print >> sys.stderr, "Copying training log for", subDir
                shutil.copy2(os.path.join(subDirAbs, "log.txt"), os.path.join(output, subDir + "-train-log.txt"))
            for suffix in ["devel", "test"]:
                src = os.path.join(subDirAbs, "classification-" + suffix, suffix + "-events.tar.gz")
                if os.path.exists(src):
                    dst = os.path.join(output, subDir + "-" + suffix + "-scores.tar.gz")
                    print >> sys.stderr, "Copying file", src, "to", dst
                    shutil.copyfile(src, dst)
                    # process for submission
                    extractSubmissionFiles(src, output, subDir, suffix)
    
def getBioNLP13SubmissionFiles(input, output, tasks, preserveOutput=False, includeTags=[".a2"]):
    assert input != None
    assert output != None
    assert input != output
    if os.path.exists(output) and not preserveOutput:
        shutil.rmtree(output)
    if not os.path.exists(output):
        os.makedirs(output)
    questionnairePath = os.path.abspath(os.path.join(input, "questionnaire.txt"))
    for subDir in os.listdir(input):
        subDirAbs = os.path.join(input, subDir)
        if os.path.isdir(subDirAbs) and hasTask(subDir, tasks):
            if os.path.exists(os.path.join(subDirAbs, "log.txt")):
                print >> sys.stderr, "Copying training log for", subDir
                shutil.copy2(os.path.join(subDirAbs, "log.txt"), os.path.join(output, subDir + "-train-log.txt"))
            for suffix in ["devel", "test"]:
                src = os.path.join(subDirAbs, "classification-" + suffix, suffix + "-events.tar.gz")
                if os.path.exists(src):
                    dst = os.path.join(output, subDir + "-" + suffix + "-scores.tar.gz")
                    print >> sys.stderr, "Copying file", src, "to", dst
                    shutil.copyfile(src, dst)
                    # process for submission
                    # extract
                    tempdir = os.path.abspath(tempfile.mkdtemp())
                    f = tarfile.open(dst, "r")
                    f.extractall(tempdir)
                    f.close()
                    # repackage
                    allFiles = os.listdir(tempdir)
                    tarFiles = []
                    for file in allFiles:
                        for tag in includeTags:
                            if file.endswith(tag):
                                f = codecs.open(os.path.join(tempdir, file), "rt", "utf-8")
                                lines = f.readlines()
                                f.close()
                                keptLines = []
                                for line in lines:
                                    if line[0] != "X":
                                        keptLines.append(line)
                                f = codecs.open(os.path.join(tempdir, file), "wt", "utf-8")
                                for line in keptLines:
                                    f.write(line)
                                f.close()
                                tarFiles.append(file)
                                break
                    if os.path.exists(questionnairePath) and suffix == "test":
                        shutil.copy(questionnairePath, os.path.join(tempdir, "questionnaire.txt"))
                        tarFiles.append("questionnaire.txt")
                    outputFile = os.path.join(output, subDir + "-" + suffix + "-a2s.tar.gz")
                    packageFile = tarfile.open(outputFile, "w:gz")
                    tempCwd = os.getcwd()
                    os.chdir(tempdir)
                    for file in tarFiles:
                        packageFile.add(file)
                    os.chdir(tempCwd)
                    packageFile.close()
                    shutil.rmtree(tempdir)
    

def makeSoftwarePackage(input, output):
    if not os.path.exists(output):
        os.makedirs(output)
    setupCommand = "cd " + input + " ; "
    setupCommand += "python setup.py sdist -d " + output
    setupCommand += " ; cd - "
    print >> sys.stderr, "Packaging software:", setupCommand
    subprocess.call(setupCommand, shell=True)
    
def buildModels(output, tasks, connection, jobConnection, extra, dummy=False):
    """
    Build the release models.
    
    This function should be run on the cluster, so the connection argument is the
    same for both the batch system and the train-program it runs.
    """
    global mainTEESDir
    from batch import batch
    for task in tasks:
        taskName = task
        if task in ["GE11", "GE09"]:
            taskName += ".2"
        command = "python " + os.path.join(mainTEESDir, "train.py") + " -t " + taskName + " -o %o/%j -c " + jobConnection + " --clearAll"
        if extra != None:
            command += " " + extra
        batch(command, input=None, connection=connection, jobTag=task, output=output, debug=True, dummy=dummy)

def getResultLine(logPath, tagPaths):
    f = open(logPath, "rt")
    lines = f.readlines()
    f.close()
    
    for tagPath in tagPaths:
        currentTagIndex = 0
        for line in lines:
            if tagPath[currentTagIndex] in line:
                #print line, currentTagIndex, tagPath
                if currentTagIndex < len(tagPath) - 1:
                    currentTagIndex += 1
                else:
                    return line.split("\t", 1)[-1].strip()
    return "No result"

def getResults(output, tasks):
    for task in tasks:
        taskName = task
        if task in ["GE11", "GE09"]:
            taskName += ".2"
        logPath = output + "/" + task + "/log.txt"
        if not os.path.exists(logPath):
            print taskName + ": No log file"
            continue
        tagPaths = []
        BioNLPEvaluatorBase = ["------------ Empty devel classification ------------", "BioNLP task "]
        tagPaths.append(BioNLPEvaluatorBase + ["##### approximate span and recursive mode #####", "==[ALL-TOTAL]=="]) # GE11
        tagPaths.append(BioNLPEvaluatorBase + ["====[TOTAL]===="]) # EPI11, ID11
        tagPaths.append(BioNLPEvaluatorBase + ["Global scores:", "f-score ="]) # BI11
        tagPaths.append(BioNLPEvaluatorBase + ["INFO", "F-score ="]) # BB11
        tagPaths.append(BioNLPEvaluatorBase + ["Relaxed F-score"]) # REN11
        tagPaths.append(BioNLPEvaluatorBase + ["EVALUATION OF MENTION LINKING", "F = "]) # CO11
        tagPaths.append(["------------ Check devel classification ------------", "##### EvaluateInteractionXML #####", "Interactions", "micro p/n:"])
        print taskName + ": " + getResultLine(logPath, tagPaths)

def buildDDI13(output, connection, dummy=False, numFolds=10, extraParameters="", testPath=""):
    global mainTEESDir
    from batch import batch
    
    commandBase = "python " + os.path.join(mainTEESDir, "train.py") + " -t DDI13 -o %o/%j -c " + connection + " --clearAll"
    for fold in range(numFolds):
        develFolds = [str(x) for x in (range(numFolds) + range(numFolds))[fold+1:fold+2+1] ]
        trainFolds = [str(x) for x in (range(numFolds) + range(numFolds))[fold+3:fold+9+1] ]
        foldParameter = " --folds test=train" + str(fold) + ":devel=train" + ",train".join(develFolds) + ":train=train" + ",train".join(trainFolds)
        command = commandBase + foldParameter + " " + extraParameters
        batch(command.strip(), input=None, connection=connection, jobTag="DDI13-fold" + str(fold), output=output, debug=True, dummy=dummy)
    
    if testPath != "":
        testFolds = " --folds devel=train0,train1,train2,train3,train4:train=train5,train6,train7,train8,train9"
        testCommand = commandBase + testFolds + " --testFile " + os.path.join(testPath, "DDI13-test-task9.1.xml") + " " + extraParameters
        batch(testCommand.strip(), input=None, connection=connection, jobTag="DDI13-test9.1", output=output, debug=True, dummy=dummy)
        testCommand = commandBase + testFolds + " --testFile " + os.path.join(testPath, "DDI13-test-task9.2.xml") + " " + extraParameters
        batch(testCommand.strip(), input=None, connection=connection, jobTag="DDI13-test9.2", output=output, debug=True, dummy=dummy)

def getDDI13ResultLine(logPath, tag, scores=None):
    parameterPaths = [[":TRAIN:END-MODEL", "Selected parameters"]]
    parameterLine = getResultLine(logPath, parameterPaths)
    print tag, "c: " + parameterLine
    parameter = int(parameterLine.strip().split("'")[-2])
    
    tagPaths = [[":TRAIN:END-MODEL", "combination-c_"+str(parameter)+" ***", "micro p/n:"]]
    scoreLine = getResultLine(logPath, tagPaths)
    print tag + ": " + scoreLine
    if scores != None:
        scores.append(float(scoreLine.strip().split("/")[-1]))
        
#    tagPaths = [["------------ Test set classification ------------", "##### EvaluateInteractionXML #####", "Interactions", "micro p/n:"]]
#    scoreLine = getResultLine(logPath, tagPaths)
#    if scoreLine != "No result" and not scoreLine.strip().endswith("p/r/f:0.0/0.0/0"):
#        print tag + ": " + scoreLine
#        if scores != None:
#            scores.append(float(scoreLine.strip().split("/")[-1]))
#    else:
#        tagPaths = [["------------ Test set classification ------------", "##### EvaluateInteractionXML #####", "Entities", "micro p/n:"]]
#        scoreLine = getResultLine(logPath, tagPaths)
#        print tag + ": " + scoreLine
#        if scoreLine != "No result" and scores != None:
#            scores.append(float(scoreLine.strip().split("/")[-1]))

def matrixToString(matrix, usePercentage=False):
    if usePercentage:
        percentages = defaultdict(lambda:defaultdict(int))
        for key1 in matrix:
            total = 0
            for key2 in matrix[key1]:
                total += matrix[key1][key2]
            if total == 0:
                total = 1
            total = float(total)
            for key2 in matrix[key1]:
                percentages[key1][key2] = matrix[key1][key2] / total
    
    string = "Error Matrix\n"
    maxKey = len(max(matrix.keys(), key=len))
    string += " " * maxKey + "|"
    for key1 in matrix:
        string += key1.ljust(maxKey) + "|"
    string += "\n"
    for key1 in matrix:
        string += key1.ljust(maxKey) + "|"
        for key2 in matrix[key1]:
            if usePercentage:
                string += ('%.2f' % (percentages[key1][key2] * 100.0)).ljust(maxKey) + "|"
            else:
                string += str(matrix[key1][key2]).ljust(maxKey) + "|"
        string += "\n"
    return string

def addExamples(exampleFile, predictionFile, classFile, matrix):
    classSet = IdSet(filename=classFile)
    f = open(predictionFile, "rt")
    for example in ExampleUtils.readExamples(exampleFile, False):
        pred = int(f.readline().split()[0])
        predClasses = classSet.getName(pred)
        goldClasses = classSet.getName(example[1])
        for predClass in predClasses.split("---"):
            for goldClass in goldClasses.split("---"):
                matrix[predClass][goldClass]
                matrix[goldClass][predClass] += 1
    f.close()
    

def getDDI13Result(output, numFolds=10, catenate=False):
    global mainTEESDir
    foldPaths = []
    scores = []
    matrix = defaultdict(lambda:defaultdict(int))
    for fold in range(numFolds):
        foldPath = os.path.join(output, "DDI13-fold" + str(fold), "classification-test", "test-pred.xml.gz")
        foldPaths.append(foldPath)
        
        logPath = os.path.join(output, "DDI13-fold" + str(fold), "log.txt")
        getDDI13ResultLine(logPath, "DDI13-fold" + str(fold), scores)
        
        foldPath = os.path.join(output, "DDI13-fold" + str(fold), "classification-test")
        classPath = os.path.join(output, "DDI13-fold" + str(fold), "model-test", "trigger-ids.classes")
        if not os.path.exists(classPath):
            classPath = os.path.join(output, "DDI13-fold" + str(fold), "model-test", "edge-ids.classes")
            addExamples(os.path.join(foldPath, "test-edge-examples.gz"), os.path.join(foldPath, "test-edge-classifications"), classPath, matrix)
        else:
            addExamples(os.path.join(foldPath, "test-trigger-examples.gz"), os.path.join(foldPath, "test-trigger-classifications"), classPath, matrix)
        
        #parameterPaths = [[":TRAIN:END-MODEL", "Selected parameters"]]
        #print "DDI13-fold" + str(fold) + ": " + getResultLine(logPath, parameterPaths)
    print "-----"
    for testSet in ["DDI13-test9.1", "DDI13-test9.2"]:
        logPath = os.path.join(output, testSet, "log.txt")
        getDDI13ResultLine(logPath, testSet)
        #parameterPaths = [[":TRAIN:END-MODEL", "Selected parameters"]]
        #print testSet + ": " + getResultLine(logPath, parameterPaths)
        
        predPath = os.path.join(output, testSet, "classification-test", "test-pred.xml.gz")
        DDITools.makeDDI13SubmissionFile(predPath, os.path.join(output, testSet + "-interactions.txt"), "interactions")
        DDITools.makeDDI13SubmissionFile(predPath, os.path.join(output, testSet + "-entities.txt"), "entities")
    print "-----"
    print "Avg-score: ", stats.mean(scores), "stdev", stats.stdev(scores)
    
    print "-----"
    print matrixToString(matrix)
    print matrixToString(matrix, True)
    
    if catenate and len(foldPaths) > 1:
        catPath = os.path.join(output, "DDI13-train-analyses.xml.gz")
        Catenate.catenate(foldPaths, catPath, fast=True)
        DDITools.makeDDI13SubmissionFile(catPath, os.path.join(output, "DDI13-train-interactions.txt"), "interactions")
        DDITools.makeDDI13SubmissionFile(catPath, os.path.join(output, "DDI13-train-entities.txt"), "entities")

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    from optparse import OptionParser
    optparser = OptionParser(description="Make TEES release files.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="")
    optparser.add_option("-o", "--output", default=None, dest="output", help="")
    optparser.add_option("-a", "--action", default=None, dest="action", help="")
    optparser.add_option("-t", "--tasks", default="GE11,EPI11,ID11,BB11,BI11,BI11-FULL,GE09,CO11,REL11,REN11,DDI11,DDI11-FULL", dest="tasks", help="")
    optparser.add_option("-c", "--connection", default=None, dest="connection", help="")
    optparser.add_option("--jobConnection", default=None, dest="jobConnection", help="")
    optparser.add_option("-d", "--dummy", action="store_true", default=False, dest="dummy", help="")
    optparser.add_option("-p", "--preserve", action="store_true", default=False, dest="preserve", help="")
    optparser.add_option("-e", "--extra", default=None, dest="extra", help="Extra parameters for the training process")
    optparser.add_option("--catenate", action="store_true", default=False, dest="catenate", help="")
    optparser.add_option("--classificationOutput", default=None, dest="classificationOutput", help="")
    optparser.add_option("--archiveName", default=None, dest="archiveName", help="")
    optparser.add_option("--numFolds", default=10, dest="numFolds", help="")
    optparser.add_option("--ddi13TestPath", default="/wrk/jakrbj/TEESBioNLP13/DDI13TestCorpora130203/", dest="ddi13TestPath", help="")
    optparser.add_option("--ddi13ExtraParameters", default="", dest="ddi13ExtraParameters", help="")
    (options, args) = optparser.parse_args()
    
    if options.jobConnection == None:
        options.jobConnection = options.connection
    
    assert options.action in ["CONVERT_CORPORA", 
                              "BUILD_MODELS", 
                              "GET_RESULTS", 
                              "BUILD_DDI13", 
                              "GET_DDI13_RESULT", 
                              "EXTRACT_MODELS", 
                              "LINK_MODELS",
                              "PACKAGE",
                              "PACKAGE_MODELS",
                              "BUILD_APIDOC", 
                              "LIST_EXECUTABLES",
                              "GET_BIONLP13_SUBMISSION_FILES",
                              "GET_SUBMISSION_FILES",
                              "PACKAGE_SOFTWARE"]
    options.tasks = options.tasks.replace("COMPLETE", "GE09,ALL11,ALL13,DDI11,DDI11-FULL,DDI13T91,DDI13T92,DDI13-FULL")
    options.tasks = options.tasks.replace("ALL11", "GE11,EPI11,ID11,BB11,BI11,BI11-FULL,CO11,REL11,REN11")
    options.tasks = options.tasks.replace("ALL13", "GE13,CG13,PC13,GRO13,GRN13,BB13T2,BB13T3")
    options.tasks = options.tasks.split(",")
    
    if options.action == "LIST_EXECUTABLES":
        listExecutables()
    elif options.action == "BUILD_MODELS":
        buildModels(options.output, options.tasks, options.connection, options.jobConnection, options.extra, options.dummy)
    elif options.action == "GET_RESULTS":
        getResults(options.output, options.tasks)
    elif options.action == "BUILD_DDI13":
        buildDDI13(options.output, options.connection, options.dummy, int(options.numFolds), options.ddi13ExtraParameters, options.ddi13TestPath)
    elif options.action == "GET_DDI13_RESULT":
        getDDI13Result(options.output, int(options.numFolds), options.catenate)
    elif options.action == "EXTRACT_MODELS":
        extractModels(options.input, options.output, options.tasks, options.classificationOutput, options.preserve)
    elif options.action == "LINK_MODELS":
        linkDuplicates(options.input, options.output)
    elif options.action == "PACKAGE":
        packageItems(options.input, options.output)
    elif options.action == "PACKAGE_MODELS":
        makeModelPackage(options.input, options.output, options.tasks, options.archiveName)
    elif options.action == "GET_BIONLP13_SUBMISSION_FILES":
        getBioNLP13SubmissionFiles(options.input, options.output, options.tasks, options.preserve)
    elif options.action == "GET_SUBMISSION_FILES":
        getBioNLPSubmissionFiles(options.input, options.output, options.tasks)
    elif options.action == "PACKAGE_SOFTWARE":
        if options.input == None:
            options.input = mainTEESDir
        makeSoftwarePackage(options.input, options.output)
