import sys, os, shutil, time       
import Core.ExampleUtils as Example
import Core.DivideExamples as DivideExamples
from Core.IdSet import IdSet
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
from Utils.Parameters import splitParameters
import Utils.TableUtils as TableUtils
from Utils.Timer import Timer
from optparse import OptionParser
import networkx as NX

def compareToBinary(complexSentencesById, classifications, exampleBuilder, options):
    # Load corpus and make sentence graphs
    print >> sys.stderr, "Calculating performance on binary corpus"
    classificationsBySentence = {}
    for classification in classifications:
        example = classification[0][0]
        sentenceId = example[0].rsplit(".",1)[0]
        sentenceOrigId = complexSentencesById[sentenceId].sentence.attrib["origId"]
        if not classificationsBySentence.has_key(sentenceOrigId):
            classificationsBySentence[sentenceOrigId] = []
        classificationsBySentence[sentenceOrigId].append(classification)
    
    print >> sys.stderr, "Loading Binary corpus"
    binaryCorpusElements = loadCorpus(options.binaryCorpus)
    binaryClassifications = []
    counter = ProgressCounter(len(binaryCorpusElements.sentences), "Build binary classifications")
    for binarySentence in binaryCorpusElements.sentences:
        counter.update(1, "Building binary classifications ("+binarySentence.sentence.attrib["id"]+"): ")
        if(classificationsBySentence.has_key(binarySentence.sentence.attrib["origId"])):
            complexClassificationGraph = NX.XGraph(multiedges = multiedges)
            for token in binarySentence.sentenceGraph.tokens:
                complexClassificationGraph.add_node(token)
            for classification in classificationsBySentence[binarySentence.sentence.attrib["origId"]]:
                if classification[1] > 0:
                    example = classification[0][0]       
                    t1 = example[3]["t1"]
                    t2 = example[3]["t2"]
                    t1Binary = None
                    for token in binarySentence.sentenceGraph.tokens:
                        if token.attrib["charOffset"] == t1.attrib["charOffset"]:
                            t1Binary = token
                    t2Binary = None
                    for token in binarySentence.sentenceGraph.tokens:
                        if token.attrib["charOffset"] == t2.attrib["charOffset"]:
                            t2Binary = token
                    assert(t1Binary != None and t2Binary != None)
                    complexClassificationGraph.add_edge(t1Binary, t2Binary)
            paths = NX.all_pairs_shortest_path(complexClassificationGraph, cutoff=999)
            for pair in binarySentence.pairs:
                t1 = binarySentence.sentenceGraph.entityHeadTokenByEntity[pair.attrib["e1"]]
                t2 = binarySentence.sentenceGraph.entityHeadTokenByEntity[pair.attrib["e2"]]
                assert(pair.attrib["interaction"] == "True" or pair.attrib["interaction"] == "False")
                if pair.attrib["interaction"] == "True":
                    pairClass = 1
                else:
                    pairClass = -1
                extra = {"xtype":"edge","type":"i","t1":t1,"t2":t2}
                if paths.has_key(t1) and paths[t1].has_key(t2):
                    binaryClassifications.append( [[pair.attrib["id"], pairClass, None, extra], 1, "binary"] )
                else:
                    binaryClassifications.append( [[pair.attrib["id"], pairClass, None, extra], -1, "binary"] )
    print >> sys.stderr, "Evaluating binary classifications"
    evaluation = Evaluation(predictions, classSet=exampleBuilder.classSet)
    print >> sys.stderr, evaluation.toStringConcise()
    if options.output != None:
        evaluation.saveCSV(options.output + "/binary_comparison_results.csv")                    

def buildExamples(exampleBuilder, sentences, outfilename):
    timer = Timer()
    examples = []
    if "graph_kernel" in exampleBuilder.styles:
        counter = ProgressCounter(len(sentences), "Build examples", 0)
    else:
        counter = ProgressCounter(len(sentences), "Build examples")
    
    calculatePredictedRange(exampleBuilder, sentences)
    
    outfile = open(outfilename, "wt")
    exampleCount = 0
    for sentence in sentences:
        counter.update(1, "Building examples ("+sentence[0].getSentenceId()+"): ")
        examples = exampleBuilder.buildExamples(sentence[0])
        exampleCount += len(examples)
        examples = exampleBuilder.preProcessExamples(examples)
        Example.appendExamples(examples, outfile)
    outfile.close()

    print >> sys.stderr, "Examples built:", str(exampleCount)
    print >> sys.stderr, "Features:", len(exampleBuilder.featureSet.getNames())
    print >> sys.stderr, "Elapsed", timer.toString()
    
def calculatePredictedRange(exampleBuilder, sentences):
    print >> sys.stderr, "Defining predicted value range:",
    sentenceElements = []
    for sentence in sentences:
        sentenceElements.append(sentence[0].sentenceElement)
    exampleBuilder.definePredictedValueRange(sentenceElements, "entity")
    print >> sys.stderr, exampleBuilder.getPredictedValueRange()

def filterFeatures(featureSet, examples):
    featureCounts = {}
    for key in featureSet.getIds():
        featureCounts[key] = 0
    
    for example in examples:
        for k in example[2].keys():
            featureCounts[k] += 1
    
    for example in examples:
        for k in example[2].keys():
            if featureCounts[k] <= 2:
                del example[2][k]
    return examples

def visualize(sentences, classifications, options, exampleBuilder):   
    print >> sys.stderr, "Making visualization"
    classificationsByExample = {}
    for classification in classifications:
        classificationsByExample[classification[0][0]] = classification
    visualizer = CorpusVisualizer(options.visualization, True)
    visualizer.featureSet = exampleBuilder.featureSet
    visualizer.classSet = exampleBuilder.classSet
    for i in range(len(sentences)):
        sentence = sentences[i]
        print >> sys.stderr, "\rProcessing sentence", sentence[0].getSentenceId(), "          ",
        prevAndNextId = [None,None]
        if i > 0:
            prevAndNextId[0] = sentences[i-1][0].getSentenceId()
        if i < len(sentences)-1:
            prevAndNextId[1] = sentences[i+1][0].getSentenceId()
        visualizer.makeSentencePage(sentence[0],sentence[1],classificationsByExample,prevAndNextId)
    visualizer.makeSentenceListPage()
    print >> sys.stderr

def loadSet(inputFilename, outputFilename, exampleBuilder):
    # Get test data
    tempSentences = []
    assert(inputFilename != None)
    # Load corpus and make sentence graphs
    print >> sys.stderr, "Loading test set corpus"
    tempCorpusElements = loadCorpus(inputFilename, options.parse, options.tokenization)
    tempSentences = []
    for sentence in tempCorpusElements.sentences:
        tempSentences.append( [sentence.sentenceGraph,None] )
    
    # Build examples
    buildExamples(exampleBuilder, tempSentences, outputFilename)
    return tempCorpusElements

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    defaultAnalysisFilename = "/usr/share/biotext/ComplexPPI/BioInferForComplexPPIVisible.xml"
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=defaultAnalysisFilename, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-s", "--test", default=None, dest="input_test", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-g", "--testGold", default=None, dest="input_test_gold", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output directory, useful for debugging")
    optparser.add_option("-c", "--classifier", default="SVMLightClassifier", dest="classifier", help="Classifier Class")
    optparser.add_option("-t", "--tokenization", default="split_gs", dest="tokenization", help="tokenization")
    optparser.add_option("-p", "--parse", default="split_gs", dest="parse", help="parse")
    optparser.add_option("-x", "--exampleBuilderParameters", default=None, dest="exampleBuilderParameters", help="Parameters for the example builder")
    optparser.add_option("-y", "--parameters", default=None, dest="parameters", help="Parameters for the classifier")
    optparser.add_option("-b", "--exampleBuilder", default="SimpleDependencyExampleBuilder", dest="exampleBuilder", help="Example Builder Class")
    optparser.add_option("-e", "--evaluator", default="BinaryEvaluator", dest="evaluator", help="Prediction evaluator class")
    optparser.add_option("-v", "--visualization", default=None, dest="visualization", help="Visualization output directory. NOTE: If the directory exists, it will be deleted!")
    optparser.add_option("-m", "--resultsToXML", default=None, dest="resultsToXML", help="Results in analysis xml. NOTE: for edges, pairs, not interactions")
    (options, args) = optparser.parse_args()
    
    mainTimer = Timer()
    print >> sys.stderr, __file__ + " start, " + mainTimer.toString()
    
    if options.output != None:
        if os.path.exists(options.output):
            print >> sys.stderr, "Output directory exists, removing", options.output
            shutil.rmtree(options.output)
        os.mkdir(options.output)
        if not os.path.exists(options.output+"/classifier"):
            os.mkdir(options.output+"/classifier")
    
    classifierParamDict = splitParameters(options.parameters)

    print >> sys.stderr, "Importing modules"
    exec "from ExampleBuilders." + options.exampleBuilder + " import " + options.exampleBuilder + " as ExampleBuilder"
    exec "from Classifiers." + options.classifier + " import " + options.classifier + " as Classifier"
    exec "from Evaluators." + options.evaluator + " import " + options.evaluator + " as Evaluation"
    
    testCorpusElements = None
    exampleSets = [[],[]]
    if not classifierParamDict.has_key("predefined"):
        print >> sys.stderr, "No-predefined model"
        exampleBuilder = ExampleBuilder(**splitParameters(options.exampleBuilderParameters))
        # Load corpus and make sentence graphs
        trainCorpusElements = loadCorpus(options.input, options.parse, options.tokenization)
        trainSentences = []
        for sentence in trainCorpusElements.sentences:
            trainSentences.append( [sentence.sentenceGraph,None] )
        
        # Build examples
        #calculatePredictedRange(exampleBuilder, trainSentences, options)
        exampleSets[0] = os.path.join(options.output,"examplesTrain.txt")
        buildExamples(exampleBuilder, trainSentences, exampleSets[0])
        # Free memory
        trainSentences = None
        trainCorpusElements = None
        
        # Create classifier object
        classifier = Classifier()
        #if options.output != None:
        #    classifier = Classifier(workDir = options.output + "/classifier")
        #else:
        #    classifier = Classifier()
        classifier.featureSet = exampleBuilder.featureSet
        if hasattr(exampleBuilder,"classSet"):
            classifier.classSet = None
        
        # Optimize
        optimizationSets = []
        optimizationSets.append(exampleSets[0]) #[os.path.join(options.output,"examplesOptimizationTest.txt")]
        if options.input_test_gold != None:
            loadSet(options.input_test_gold, os.path.join(options.output,"examplesTestGold.txt"), exampleBuilder)
            optimizationSets.append(os.path.join(options.output,"examplesTestGold.txt"))
        else:
            exampleSets[1] = os.path.join(options.output,"examplesTest.txt")
            testCorpusElements = loadSet(options.input_test, exampleSets[1], exampleBuilder)
            optimizationSets.append(exampleSets[1]) #[os.path.join(options.output,"examplesOptimizationTrain.txt")]
        
        #DivideExamples.divideExamples(exampleSets[0], optimizationSets)
        evaluationArgs = {"classSet":exampleBuilder.classSet}
        if options.parameters != None:
            paramDict = splitParameters(options.parameters)
            bestResults = classifier.optimize([optimizationSets[0]], [optimizationSets[1]], paramDict, Evaluation, evaluationArgs)
        else:
            bestResults = classifier.optimize([optimizationSets[0]], [optimizationSets[1]], evaluationClass=Evaluation, evaluationArgs=evaluationArgs)
    else:
        print >> sys.stderr, "Using predefined model"
        bestResults = [None,None,{}]
        for k,v in classifierParamDict.iteritems():
            bestResults[2][k] = v
        featureSet = IdSet()
        featureSet.load(os.path.join(classifierParamDict["predefined"][0], "feature_names.txt"))
        classSet = None
        if os.path.exists(os.path.join(classifierParamDict["predefined"][0], "class_names.txt")):
            classSet = IdSet()
            classSet.load(os.path.join(classifierParamDict["predefined"][0], "class_names.txt"))
        exampleBuilder = ExampleBuilder(featureSet=featureSet, classSet=classSet, **splitParameters(options.exampleBuilderParameters))
    # Save training sets
    if options.output != None:
        TableUtils.writeCSV(bestResults[2], options.output +"/best_parameters.csv")
    
    # Optimize and train
    if options.output != None:
        classifier = Classifier(workDir = options.output + "/classifier")
    else:
        classifier = Classifier()
    classifier.featureSet = exampleBuilder.featureSet
    if hasattr(exampleBuilder,"classSet"):
        classifier.classSet = exampleBuilder.classSet
    print >> sys.stderr, "Classifying test data"
    if bestResults[2].has_key("timeout"):
        del bestResults[2]["timeout"]
    print >> sys.stderr, "Parameters:", bestResults[2]
    print >> sys.stderr, "Training",
    startTime = time.time()
    classifier.train(exampleSets[0], bestResults[2])
    print >> sys.stderr, "(Time spent:", time.time() - startTime, "s)"
    
    if testCorpusElements == None:
        exampleSets[1] = os.path.join(options.output,"examplesTest.txt")
        testCorpusElements = loadSet(options.input_test, exampleSets[1], exampleBuilder)
    
    print >> sys.stderr, "Testing",
    startTime = time.time()
    predictions = classifier.classify(exampleSets[1], bestResults[2])
    print >> sys.stderr, "(Time spent:", time.time() - startTime, "s)"
    
    # Calculate statistics
    evaluation = Evaluation(predictions, classSet=exampleBuilder.classSet)
    print >> sys.stderr, evaluation.toStringConcise()
    if options.output != None:
        evaluation.saveCSV(options.output + "/results.csv")
        print >> sys.stderr, "Saving class names to", options.output + ".class_names"
        exampleBuilder.classSet.write(options.output + "/class_names.txt")
        print >> sys.stderr, "Saving feature names to", options.output + "/feature_names.txt"
        exampleBuilder.featureSet.write(options.output + "/feature_names.txt")
        TableUtils.writeCSV(bestResults[2], options.output +"/best_parameters.csv")
    
    # Save interactionXML
    if options.resultsToXML != None:
        classSet = None
        if "typed" in exampleBuilder.styles:
            classSet = exampleBuilder.classSet
        Example.writeToInteractionXML(evaluation.classifications, testCorpusElements, options.resultsToXML, classSet)

#    # Visualize
#    if options.visualization != None:
#        for example in exampleSets[0]:
#            example[3]["visualizationSet"] = "train"
#            #corpusElements.sentencesById[example[0].rsplit(".",1)[0]].sentenceGraph.visualizationSet = "train"
#        for example in exampleSets[1]:
#            example[3]["visualizationSet"] = "test"
#            #corpusElements.sentencesById[example[0].rsplit(".",1)[0]].sentenceGraph.visualizationSet = "test"
#        if len(testSentences) > 0:
#            visualize(testSentences, evaluation.classifications, options, exampleBuilder)
#        else:
#            visualize(sentences, evaluation.classifications, options, exampleBuilder)

    print >> sys.stderr, __file__ + " end, " + mainTimer.toString()