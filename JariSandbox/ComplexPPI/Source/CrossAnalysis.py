import Core.ExampleUtils as Example
import sys, os
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
#from ExampleBuilders.SimpleDependencyExampleBuilder import SimpleDependencyExampleBuilder
from InteractionXML.CorpusElements import CorpusElements
from Core.SentenceGraph import *
#from Classifiers.SVMLightClassifier import SVMLightClassifier as Classifier
#from Core.Evaluation import Evaluation
from Visualization.CorpusVisualizer import CorpusVisualizer
from Utils.ProgressCounter import ProgressCounter
from Utils.Timer import Timer
from Utils.Parameters import splitParameters
import Utils.TableUtils as TableUtils
from optparse import OptionParser
from SplitAnalysis import *
import subprocess
import time

def zipTree(path, target):
    tempCwd = os.getcwd()
    os.chdir(path)
    #print os.getcwd()
    zipCall = ["zip", "-rmq", target+".zip", target]
    #print zipCall
    subprocess.call(zipCall)
    os.chdir(tempCwd)

def crossValidate(exampleBuilder, corpusElements, examples, options, timer):
    parameterOptimizationSet = None
    constantParameterOptimizationSet = None
    if options.paramOptData != None:
        print >> sys.stderr, "Separating parameter optimization set"
        parameterOptimizationDivision = Example.makeCorpusDivision(corpusElements, float(options.paramOptData))
        exampleSets = Example.divideExamples(examples, parameterOptimizationDivision)
        constantParameterOptimizationSet = exampleSets[0]
        parameterOptimizationSet = constantParameterOptimizationSet
        optDocs = 0
        for k,v in parameterOptimizationDivision.iteritems():
            if v == 0:
                del corpusElements.documentsById[k]
                optDocs += 1
        print >> sys.stderr, "  Documents for parameter optimization:", optDocs
    discardedParameterCombinations = []

    print >> sys.stderr, "Dividing data into folds"
    corpusFolds = Example.makeCorpusFolds(corpusElements, options.folds[0])
    exampleSets = Example.divideExamples(examples, corpusFolds)
    
    keys = exampleSets.keys()
    keys.sort()
    evaluations = []
    for key in keys:
        testSet = exampleSets[key]
        for example in testSet:
            example[3]["visualizationSet"] = key + 1
        trainSet = []
        for key2 in keys:
            if key != key2:
                trainSet.extend(exampleSets[key2])
        print >> sys.stderr, "Fold", str(key + 1)
        # Create classifier object
        if options.output != None:
            if not os.path.exists(options.output+"/fold"+str(key+1)):
                os.mkdir(options.output+"/fold"+str(key+1))
#                if not os.path.exists(options.output+"/fold"+str(key+1)+"/classifier"):
#                    os.mkdir(options.output+"/fold"+str(key+1)+"/classifier")
            classifier = Classifier(workDir = options.output + "/fold"+str(key + 1))
        else:
            classifier = Classifier()
        classifier.featureSet = exampleBuilder.featureSet
        # Optimize ####################
        # Check whether there is need for included param opt set
        if parameterOptimizationSet == None and options.folds[1] == 0: # 8-1-1 folds
            assert(len(keys) > 1)
            if keys.index(key) == 0:
                parameterOptimizationSetKey = keys[-1]
            else:
                parameterOptimizationSetKey = keys[keys.index(key)-1]
            parameterOptimizationSet = exampleSets[parameterOptimizationSetKey]
            trainSet = []
            for key2 in keys:
                if key2 != key and key2 != parameterOptimizationSetKey:
                    trainSet.extend(exampleSets[key2])

        if parameterOptimizationSet != None: # constant external parameter optimization set
            evaluationArgs = {"classSet":exampleBuilder.classSet}
            if options.parameters != None:
                paramDict = splitParameters(options.parameters)
                bestResults = classifier.optimize([trainSet], [parameterOptimizationSet], paramDict, Evaluation, evaluationArgs, combinationsThatTimedOut=discardedParameterCombinations)
            else:
                bestResults = classifier.optimize([trainSet], [parameterOptimizationSet], evaluationClass=Evaluation, evaluationArgs=evaluationArgs, combinationsThatTimedOut=discardedParameterCombinations)
        else: # nested x-fold parameter optimization
            assert (options.folds[1] >= 2)
            optimizationFolds = Example.makeExampleFolds(trainSet, options.folds[1])
            optimizationSets = Example.divideExamples(trainSet, optimizationFolds)
            optimizationSetList = []
            optSetKeys = optimizationSets.keys()
            optSetKeys.sort()
            for optSetKey in optSetKeys:
                optimizationSetList.append(optimizationSets[optSetKey])
            evaluationArgs = {"classSet":exampleBuilder.classSet}
            if options.parameters != None:
                paramDict = splitParameters(options.parameters)
                bestResults = classifier.optimize(optimizationSetList, optimizationSetList, paramDict, Evaluation, evaluationArgs, combinationsThatTimedOut=discardedParameterCombinations)
            else:
                bestResults = classifier.optimize(optimizationSetList, optimizationSetList, evaluationClass=Evaluation, evaluationArgs=evaluationArgs, combinationsThatTimedOut=discardedParameterCombinations)
        
        # Classify
        print >> sys.stderr, "Classifying test data"
        bestParams = bestResults[2]
        if bestParams.has_key("timeout"):
            del bestParams["timeout"]
        print >> sys.stderr, "Parameters:", bestParams
        print >> sys.stderr, "Training",
        startTime = time.time()
        classifier.train(trainSet, bestParams)
        print >> sys.stderr, "(Time spent:", time.time() - startTime, "s)"
        print >> sys.stderr, "Testing",
        startTime = time.time()
        predictions = classifier.classify(testSet)
        print >> sys.stderr, "(Time spent:", time.time() - startTime, "s)"
        
        # Calculate statistics
        evaluation = Evaluation(predictions, classSet=exampleBuilder.classSet)
        print >> sys.stderr, evaluation.toStringConcise()
        print >> sys.stderr, timer.toString()
        evaluations.append(evaluation)
        
        # Save example sets
        if options.output != None:
            print >> sys.stderr, "Saving example sets to", options.output
            Example.writeExamples(exampleSets[0], options.output +"/fold"+str(key+1) + "/examplesTest.txt")
            Example.writeExamples(exampleSets[1], options.output +"/fold"+str(key+1) + "/examplesTrain.txt")
            if parameterOptimizationSet == None:
                for k,v in optimizationSets.iteritems():
                    Example.writeExamples(v, options.output +"/fold"+str(key+1) + "/examplesOptimizationSet" + str(k) + ".txt")
            else:
                Example.writeExamples(parameterOptimizationSet, options.output +"/fold"+str(key+1) + "/examplesOptimizationSetPredefined.txt")
            TableUtils.writeCSV(bestResults[2], options.output +"/fold"+str(key+1) + "/parameters.csv")
            evaluation.saveCSV(options.output +"/fold"+str(key+1) + "/results.csv")
            print >> sys.stderr, "Compressing folder"
            zipTree(options.output, "fold"+str(key+1))
        
        parameterOptimizationSet = constantParameterOptimizationSet
    
    print >> sys.stderr, "Cross-validation Results"
    for i in range(len(evaluations)):
        print >> sys.stderr, evaluations[i].toStringConcise("  Fold "+str(i)+": ")
    averageResult = Evaluation.average(evaluations)
    print >> sys.stderr, averageResult.toStringConcise("  Avg: ")
    pooledResult = Evaluation.pool(evaluations)
    print >> sys.stderr, pooledResult.toStringConcise("  Pool: ")
    if options.output != None:
        averageResult.saveCSV(options.output+"/resultsAverage.csv")
        pooledResult.saveCSV(options.output+"/resultsPooled.csv")
    # Visualize
    if options.visualization != None:
        visualize(sentences, pooledResult.classifications, options, exampleBuilder)

if __name__=="__main__":
    defaultAnalysisFilename = "/usr/share/biotext/ComplexPPI/BioInferForComplexPPI.xml"
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=defaultAnalysisFilename, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output directory, useful for debugging")
    optparser.add_option("-c", "--classifier", default="SVMLightClassifier", dest="classifier", help="Classifier Class")
    optparser.add_option("-t", "--tokenization", default="split_gs", dest="tokenization", help="tokenization")
    optparser.add_option("-p", "--parse", default="split_gs", dest="parse", help="parse")
    optparser.add_option("-x", "--exampleBuilderParameters", default=None, dest="exampleBuilderParameters", help="Parameters for the example builder")
    optparser.add_option("-y", "--parameters", default=None, dest="parameters", help="Parameters for the classifier")
    optparser.add_option("-b", "--exampleBuilder", default="SimpleDependencyExampleBuilder", dest="exampleBuilder", help="Example Builder Class")
    optparser.add_option("-e", "--evaluator", default="BinaryEvaluator", dest="evaluator", help="Prediction evaluator class")
    optparser.add_option("-v", "--visualization", default=None, dest="visualization", help="Visualization output directory. NOTE: If the directory exists, it will be deleted!")
    optparser.add_option("-f", "--folds", default="10", dest="folds", help="X-fold cross validation")
    optparser.add_option("-d", "--paramOptData", default=None, dest="paramOptData", help="The fraction of the corpus to be always used for parameter optimization")
    (options, args) = optparser.parse_args()
    
    timer = Timer()
    print >> sys.stderr, timer.toString()
    
    if options.folds.find(",") != 0:
        options.folds = options.folds.split(",")
        assert(len(options.folds)==2)
        options.folds[0] = int(options.folds[0])
        options.folds[1] = int(options.folds[1])
        if options.paramOptData != None:
            print >> sys.stderr, "Parameter optimization set defined, parameter " + str(options.folds[1]) + "-fold cross validation will not be performed." 
    else:
        options.folds = (int(options.folds),int(options.folds))

    if options.output != None:
        if os.path.exists(options.output):
            print >> sys.stderr, "Output directory exists, removing", options.output
            shutil.rmtree(options.output)
        os.makedirs(options.output)
#        if not os.path.exists(options.output+"/classifier"):
#            os.mkdir(options.output+"/classifier")

    print >> sys.stderr, "Importing modules"
    exec "from ExampleBuilders." + options.exampleBuilder + " import " + options.exampleBuilder + " as ExampleBuilder"
    exec "from Classifiers." + options.classifier + " import " + options.classifier + " as Classifier"
    exec "from Evaluators." + options.evaluator + " import " + options.evaluator + " as Evaluation"
    
    # Load corpus and make sentence graphs
    corpusElements = loadCorpus(options.input, options.parse, options.tokenization)
    sentences = []
    for sentence in corpusElements.sentences:
        sentences.append( [sentence.sentenceGraph,None,None] )
    
    # Build examples
    exampleBuilder = ExampleBuilder(**splitParameters(options.exampleBuilderParameters))
    examples = buildExamples(exampleBuilder, sentences, options)
    
    crossValidate(exampleBuilder, corpusElements, examples, options, timer)
    print >> sys.stderr, timer.toString()
        
        
                