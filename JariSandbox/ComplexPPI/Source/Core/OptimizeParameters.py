import sys, os, types
import combine
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Utils.Parameters import *
from Utils.Timer import Timer

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

def optimize(ClassifierClass, EvaluatorModule, trainExamples, testExamples, classIds, parameters, workDir=None, timeout=None):
    print >> sys.stderr, "Optimizing parameters"
    if type(parameters) == types.StringType:
        parameters = splitParameters(parameters)
    combinations = getParameterCombinations(parameters)

    bestResult = None
    combinationCount = 1
    for combination in combinations:
        print >> sys.stderr, " Parameters "+str(combinationCount)+"/"+str(len(combinations))+":", str(combination),
        
        combinationId = getCombinationString(combination)
        classifier = ClassifierClass(workDir=workDir)
        # Train
        trainOutput = "model-" + combinationId
        print >> sys.stderr, "  Training..."
        timer = Timer()
        classifier.train(trainExamples, combination, trainOutput)
        print >> sys.stderr, "  Training Complete, time:", timer.toString()
        # Test
        testOutput = "classifications-" + combinationId
        print >> sys.stderr, "  Testing..."
        timer = Timer()
        classifier.classify(testExamples, trainOutput, combination, testOutput)
        print >> sys.stderr, "  Testing Complete, time:", timer.toString()
        # Evaluate
        evaluationOutput = "evaluation-" + combinationId + ".csv"
        evaluator = EvaluatorModule.run(testExamples, testOutput, classIds, evaluationOutput)
        #print >> sys.stderr, evaluator.toStringConcise("  ")

        if bestResult == None or evaluator.compare(bestResult[0]) > 0: #: averageResult.fScore > bestResult[1].fScore:
            bestResult = [evaluator, trainOutput, testOutput, evaluationOutput, combination]
        combinationCount += 1
    print >> sys.stderr, "Selected parameters", bestResult[-1]
    return bestResult