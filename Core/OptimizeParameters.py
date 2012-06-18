"""
Determine optimal classifier parameter combinations.
"""
import sys, os, types
import combine
import time
import subprocess
import copy
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Utils.Parameters import *
from Utils.Timer import Timer
import Utils.Stream as Stream
#IF LOCAL
#from Murska.CSCConnection import CSCConnection
#ENDIF
import ExampleUtils
from IdSet import IdSet

def getCombinationString(combination):
    string = ""
    for key in sorted(combination.keys()):
        if string != "":
            string += "-"
        string += str(key) + "_" + str(combination[key])
    return string

def getParameterCombinations(parameters):
    parameterNames = parameters.keys()
    parameterNames.sort()
    parameterNames.reverse() # to put trigger parameter first (allows optimized 3-parameter grid)
    parameterValues = []
    for parameterName in parameterNames:
        parameterValues.append([])
        values = parameters[parameterName] 
        if isinstance(values, (list, tuple)):
            for value in values:
                parameterValues[-1].append( (parameterName,value) )
        else:
            parameterValues[-1].append( (parameterName,values) )
    combinationLists = combine.combine(*parameterValues)
    combinations = []
    for combinationList in combinationLists:
        combinations.append({})
        for value in combinationList:
            combinations[-1][value[0]] = value[1]
    return combinations

def optimize(Classifier, Evaluator, trainExamples, testExamples, classIds, parameters, workDir=None, timeout=None, cscConnection=None, downloadAllModels=False, steps="BOTH", threshold=False):
    print >> sys.stderr, "Optimizing parameters"
    if workDir != None:
        if not os.path.exists(workDir):
            print >> sys.stderr, "Creating optimization output directory", workDir
            os.makedirs(workDir)
            
    if type(parameters) == types.StringType:
        parameters = splitParameters(parameters)
    combinations = getParameterCombinations(parameters)
    
    if cscConnection == None:
        return optimizeLocal(Classifier, Evaluator, trainExamples, testExamples, classIds, combinations, workDir, timeout)
    else:
        return optimizeCSC(Classifier, Evaluator, trainExamples, testExamples, classIds, combinations, workDir, timeout, cscConnection, downloadAllModels, steps, threshold=threshold)

def optimizeLocal(Classifier, Evaluator, trainExamples, testExamples, classIds, combinations, workDir=None, timeout=None):
    bestResult = None
    combinationCount = 1
    for combination in combinations:
        Stream.setIndent(" ")
        print >> sys.stderr, "Parameters "+str(combinationCount)+"/"+str(len(combinations))+":", str(combination)
        Stream.setIndent("  ")
        combinationId = getCombinationString(combination)
        # Train
        trainOutput = "model-" + combinationId
        if workDir != None:
            trainOutput = os.path.join(workDir, trainOutput)
        print >> sys.stderr, "Training..."
        timer = Timer()
        Classifier.train(trainExamples, combination, trainOutput)
        print >> sys.stderr, "Training Complete, time:", timer.toString()
        # Test
        testOutput = "classifications-" + combinationId
        if workDir != None:
            testOutput = os.path.join(workDir, testOutput)
        print >> sys.stderr, "Testing..."
        timer = Timer()
        Classifier.test(testExamples, trainOutput, testOutput)
        print >> sys.stderr, "Testing Complete, time:", timer.toString()
        # Evaluate
        evaluationOutput = "evaluation-" + combinationId + ".csv"
        if workDir != None:
            evaluationOutput = os.path.join(workDir, evaluationOutput)
        Stream.setIndent("   ")
        evaluator = Evaluator.evaluate(testExamples, testOutput, classIds, evaluationOutput)
        #print >> sys.stderr, evaluator.toStringConcise("  ")

        if bestResult == None or evaluator.compare(bestResult[0]) > 0: #: averageResult.fScore > bestResult[1].fScore:
            bestResult = [evaluator, trainOutput, testOutput, evaluationOutput, combination]
        combinationCount += 1
    Stream.setIndent()
    print >> sys.stderr, "Selected parameters", bestResult[-1]
    return bestResult

#IF LOCAL
def optimizeCSC(Classifier, Evaluator, trainExamples, testExamples, classIds, combinations, workDir=None, timeout=None, cscConnection=None, downloadAllModels=False, steps="BOTH", threshold=False):
    bestResult = None
    combinationCount = 1
    combinationIds = []
    assert steps in ["BOTH", "SUBMIT", "RESULTS"], steps
    
    if type(classIds) == types.StringType:
        classIds = IdSet(filename=classIds)
    if Classifier.__name__ == "MultiLabelClassifier":
        negClass1 = True
        if "classifier" in combinations[0] and combinations[0]["classifier"] == "svmperf":
            negClass1 = False
        print "negclass1", negClass1
        Classifier.makeClassFiles(trainExamples, testExamples, classIds, negClass1=negClass1)
    
    if steps in ["BOTH", "SUBMIT"]:
        print >> sys.stderr, "Initializing runs"
        for combination in combinations:
            Stream.setIndent(" ")
            print >> sys.stderr, "Parameters "+str(combinationCount)+"/"+str(len(combinations))+":", str(combination)
            # Train
            combinationIds.append(Classifier.initTrainAndTestOnLouhi(trainExamples, testExamples, combination, cscConnection, workDir, classIds) )
            combinationCount += 1
    else:
        for combination in combinations:
            idStr = ""
            for key in sorted(combination.keys()):
                idStr += "-" + str(key) + "_" + str(combination[key])
            combinationIds.append(idStr)
    Stream.setIndent()
    
    if steps in ["BOTH", "RESULTS"]:
        Stream.setIndent(" ")
        print >> sys.stderr, "Waiting for results"
        finished = 0
        louhiTimer = Timer()
        #combinationStatus = {}
        while(True):
            # count finished
            finished = 0
            processStatus = {"FINISHED":0, "QUEUED":0, "FAILED":0, "RUNNING":0}
            for id in combinationIds:
                #status = Classifier.getLouhiStatus(id, cscConnection)
                #combinationStatus[id] = status
                #processStatus[status] += 1
                Classifier.getLouhiStatus(id, cscConnection, processStatus, classIds)
            p = processStatus
            processStatusString = str(p["QUEUED"]) + " queued, " + str(p["RUNNING"]) + " running, " + str(p["FINISHED"]) + " finished, " + str(p["FAILED"]) + " failed"
            if processStatus["QUEUED"] + processStatus["RUNNING"] == 0:
                print >> sys.stderr
                print >> sys.stderr, "All runs done (" + processStatusString + ")"
                break
            # decide what to do
            if timeout == None or louhiTimer.getElapsedTime() < timeout:
                sleepString = " [          ]     "
                print >> sys.stderr, "\rWaiting for " + str(len(combinations)) + " on " + cscConnection.machineName + "(" + processStatusString + "),", louhiTimer.elapsedTimeToString() + sleepString,
                #time.sleep(60)
                sleepTimer = Timer()
                while sleepTimer.getElapsedTime() < 60:
                    steps = int(10 * sleepTimer.getElapsedTime() / 60) + 1
                    sleepString = " [" + steps * "." + (10-steps) * " " + "]     "
                    print >> sys.stderr, "\rWaiting for " + str(len(combinations)) + " on " + cscConnection.machineName + "(" + processStatusString + "),", louhiTimer.elapsedTimeToString() + sleepString,
                    time.sleep(5)                
            else:
                print >> sys.stderr
                print >> sys.stderr, "Timed out, ", louhiTimer.elapsedTimeToString()
                break
        
        print >> sys.stderr, "Evaluating results"
        #if type(testExamples) != types.ListType:
        #    print >> sys.stderr, "Loading examples from file", testExamples
        #    testExamples = ExampleUtils.readExamples(testExamples,False)
        bestCombinationId = None
        for i in range(len(combinationIds)):
            id = combinationIds[i]
            Stream.setIndent(" ")
            # Evaluate
            predictions = Classifier.getLouhiPredictions(id, cscConnection, workDir, classIds)
            if predictions == None:
                print >> sys.stderr, "No results for combination" + id
            else:
                if downloadAllModels:
                    modelFileName = Classifier.downloadModel(id, cscConnection, workDir)
                    if workDir != None:
                        modelFileName = os.path.join(workDir, modelFileName)
                        subprocess.call("gzip -fv " + modelFileName, shell=True)
                print >> sys.stderr, "Evaluating results for combination" + id
                evaluationOutput = "evaluation" + id + ".csv"
                if workDir != None:
                    evaluationOutput = os.path.join(workDir, evaluationOutput)
                evaluator = Evaluator.evaluate(testExamples, predictions, classIds, evaluationOutput)
                if threshold:
                    print >> sys.stderr, "Thresholding"
                    evaluator.determineThreshold(testExamples, predictions)
                if Classifier.__name__ != "MultiLabelClassifier":
                    if bestResult == None or evaluator.compare(bestResult[0]) > 0: #: averageResult.fScore > bestResult[1].fScore:
                        bestResult = [evaluator, None, predictions, evaluationOutput, combinations[i]]
                        bestCombinationId = id
                else:
                    assert Evaluator.__name__ == "MultiLabelEvaluator", Evaluator.__name__
                    if bestResult == None:
                        bestResult = [{}, None]
                        for className in classIds.Ids:
                            if className != "neg" and "---" not in className:
                                bestResult[0][className] = [-1, None, classIds.getId(className), None]
                    for className in classIds.Ids:
                        if className != "neg" and "---" not in className:
                            fscore = evaluator.dataByClass[classIds.getId(className)].fscore
                            if fscore > bestResult[0][className][0]:
                                bestResult[0][className] = [fscore, id, bestResult[0][className][2]]
                                if threshold:
                                    classId = classIds.getId(className, False)
                                    if classId in evaluator.thresholds:
                                        bestResult[0][className].append(evaluator.thresholds[classId])
                                    else:
                                        bestResult[0][className].append(0.0)
                                else:
                                    bestResult[0][className].append(None)
                    bestCombinationId = bestResult
                os.remove(predictions) # remove predictions to save space
        Stream.setIndent()
        print >> sys.stderr, "Selected parameters", bestResult[-1]
        #if Classifier.__name__ == "MultiLabelClassifier":
        #    evaluator = Evaluator.evaluate(testExamples, predictions, classIds, evaluationOutput)
    
        # Download best model and predictions
        modelFileName = Classifier.downloadModel(bestCombinationId, cscConnection, workDir)
        if workDir != None:
            modelFileName = os.path.join(workDir, modelFileName)
        subprocess.call("gzip -fv " + modelFileName, shell=True)
        modelFileName = modelFileName + ".gz"
        #if Classifier.__name__ != "MultiLabelClassifier":
            #bestResult = [None, None]
        bestResult[1] = modelFileName
        return bestResult
#ENDIF
