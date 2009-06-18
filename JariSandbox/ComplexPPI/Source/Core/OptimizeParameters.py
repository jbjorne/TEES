import sys, os, types
import combine
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Utils.Parameters import *
from Utils.Timer import Timer
import Utils.Stream as Stream

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
    parameterValues = []
    for parameterName in parameterNames:
        parameterValues.append([])
        for value in parameters[parameterName]:
            parameterValues[-1].append( (parameterName,value) )
    combinationLists = combine.combine(*parameterValues)
    combinations = []
    for combinationList in combinationLists:
        combinations.append({})
        for value in combinationList:
            combinations[-1][value[0]] = value[1]
    return combinations

def optimize(Classifier, Evaluator, trainExamples, testExamples, classIds, parameters, workDir=None, timeout=None):
    print >> sys.stderr, "Optimizing parameters"
    if workDir != None:
        if not os.path.exists(workDir):
            print >> sys.stderr, "Creating optimization output directory", workDir
            os.mkdir(workDir)
            
    if type(parameters) == types.StringType:
        parameters = splitParameters(parameters)
    combinations = getParameterCombinations(parameters)

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