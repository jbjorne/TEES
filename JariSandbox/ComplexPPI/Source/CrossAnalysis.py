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
import Evaluators.Evaluation as EvaluationBase
from optparse import OptionParser
from SplitAnalysis import *

def crossValidate(exampleBuilder, corpusElements, examples, options):
    print >> sys.stderr, "Dividing data into folds"
    corpusFolds = Example.makeCorpusFolds(corpusElements, options.folds)
    exampleSets = Example.divideExamples(examples, corpusFolds)
    keys = exampleSets.keys()
    keys.sort()
    evaluations = []
    for key in keys:
        testSet = exampleSets[key]
        trainSet = []
        for key2 in keys:
            if key != key2:
                trainSet.extend(exampleSets[key2])
        print >> sys.stderr, "Fold", str(key)
        # Create classifier object
        if options.output != None:
            classifier = Classifier(workDir = options.output + "fold"+str(key)+"/classifier")
        else:
            classifier = Classifier()
        classifier.featureSet = exampleBuilder.featureSet
        # Optimize
        optimizationFolds = Example.makeExampleFolds(trainSet, options.folds)
        optimizationSets = Example.divideExamples(trainSet, optimizationFolds)
        optimizationSetList = []
        optSetKeys = optimizationSets.keys()
        optSetKeys.sort()
        for optSetKey in optSetKeys:
            optimizationSetList.append(optimizationSets[optSetKey])
        evaluationArgs = {"classSet":exampleBuilder.classSet}
        if options.parameters != None:
            paramDict = splitParameters(options.parameters)
            bestResults = classifier.optimize(optimizationSetList, optimizationSetList, paramDict, Evaluation, evaluationArgs)
        else:
            bestResults = classifier.optimize(optimizationSetList, optimizationSetList, evaluationClass=Evaluation, evaluationArgs=evaluationArgs)

        # Save example sets
        if options.output != None:
            print >> sys.stderr, "Saving example sets to", options.output
            Example.writeExamples(exampleSets[0], options.output + "/examplesTest.txt")
            Example.writeExamples(exampleSets[1], options.output + "/examplesTrain.txt")
            Example.writeExamples(optimizationSets[0], options.output + "/examplesOptimizationTest.txt")
            Example.writeExamples(optimizationSets[1], options.output + "/examplesOptimizationTrain.txt")
        
        # Classify
        print >> sys.stderr, "Classifying test data"    
        print >> sys.stderr, "Parameters:", bestResults[2]
        classifier.train(trainSet, bestResults[2])
        predictions = classifier.classify(testSet)
        
        # Calculate statistics
        evaluation = Evaluation(predictions, classSet=exampleBuilder.classSet)
        print >> sys.stderr, evaluation.toStringConcise()
        evaluations.append(evaluation)
    
    averageResult = EvaluationBase.averageEvaluations(evaluations)
    print >> sys.stderr, "Cross-validation Results"
    for i in range(len(evaluations)):
        print >> sys.stderr, evaluations[i].toStringConcise("  Fold "+str(i)+": ")
    print >> sys.stderr, averageResult.toStringConcise("  Avg: ")    
    # Visualize
    if options.visualization != None:
        visualize(sentences, evaluation.classifications, options)

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
    optparser.add_option("-e", "--evaluator", default="Evaluation", dest="evaluator", help="Prediction evaluator class")
    optparser.add_option("-v", "--visualization", default=None, dest="visualization", help="Visualization output directory. NOTE: If the directory exists, it will be deleted!")
    optparser.add_option("-f", "--folds", type="int", default=10, dest="folds", help="X-fold cross validation")
    (options, args) = optparser.parse_args()
    
    if options.output != None:
        if not os.path.exists(options.output):
            os.mkdir(options.output)
        if not os.path.exists(options.output+"/classifier"):
            os.mkdir(options.output+"/classifier")
        for i in range(10):
            if not os.path.exists(options.output+"/fold"+str(i+1)):
                os.mkdir(options.output+"/fold"+str(i+1))
                if not os.path.exists(options.output+"/fold"+str(i+1)+"/classifier"):
                    os.mkdir(options.output+"/fold"+str(i+1)+"/classifier")

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
    
    crossValidate(exampleBuilder, corpusElements, examples, options)    
    
    # Visualize
    if options.visualization != None:
        visualize(sentences, evaluation.classifications, options)
        
        
                