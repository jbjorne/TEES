import Core.ExampleUtils as Example
import sys, os, shutil, time
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

def buildExamples(exampleBuilder, sentences, options):
    print >> sys.stderr, "Defining predicted value range:",
    sentenceElements = []
    for sentence in sentences:
        sentenceElements.append(sentence[0].sentenceElement)
    exampleBuilder.definePredictedValueRange(sentenceElements, "entity")
    print >> sys.stderr, exampleBuilder.getPredictedValueRange()
    
    examples = []
    if hasattr(exampleBuilder, "styles") and "graph_kernel" in exampleBuilder.styles:
        counter = ProgressCounter(len(sentences), "Build examples", 0)
    else:
        counter = ProgressCounter(len(sentences), "Build examples")
    for sentence in sentences:
        counter.update(1, "Building examples ("+sentence[0].getSentenceId()+"): ")
        sentence[1] = exampleBuilder.buildExamples(sentence[0])
        examples.extend(sentence[1])
    print >> sys.stderr, "Examples built:", len(examples)
    print >> sys.stderr, "Features:", len(exampleBuilder.featureSet.getNames())
    print >> sys.stderr, "Preprocessing examples:"
    examples = exampleBuilder.preProcessExamples(examples)
    # Save examples
    if options.output != None:
        print >> sys.stderr, "Saving examples to", options.output + "/examples.txt"
        commentLines = []
        commentLines.append("Input file: " + options.input)
        commentLines.append("Example builder: " + options.exampleBuilder)
        commentLines.append("Features:")
        commentLines.extend(exampleBuilder.featureSet.toStrings())
        Example.writeExamples(examples, options.output + "/examples.txt", commentLines)
    #examples = filterFeatures(exampleBuilder.featureSet, examples)
    #Example.normalizeFeatureVectors(examples)
    return examples

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

if __name__=="__main__":
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
    
    if options.output != None:
        if os.path.exists(options.output):
            print >> sys.stderr, "Output directory exists, removing", options.output
            shutil.rmtree(options.output)
        os.mkdir(options.output)
        if not os.path.exists(options.output+"/classifier"):
            os.mkdir(options.output+"/classifier")

    print >> sys.stderr, "Importing modules"
    exec "from ExampleBuilders." + options.exampleBuilder + " import " + options.exampleBuilder + " as ExampleBuilder"
    exec "from Classifiers." + options.classifier + " import " + options.classifier + " as Classifier"
    exec "from Evaluators." + options.evaluator + " import " + options.evaluator + " as Evaluation"
    
    # Load corpus and make sentence graphs
    corpusElements = loadCorpus(options.input, options.parse, options.tokenization)
    sentences = []
    for sentence in corpusElements.sentences:
        sentences.append( [sentence.sentenceGraph,None] )
    
    # Build examples
    exampleBuilder = ExampleBuilder(**splitParameters(options.exampleBuilderParameters))
    examples = buildExamples(exampleBuilder, sentences, options)
    
    testSentences = []
    if options.input_test == None:               
        # Make test and training sets
        print >> sys.stderr, "Dividing data into test and training sets"
        corpusDivision = Example.makeCorpusDivision(corpusElements)
        exampleSets = Example.divideExamples(examples, corpusDivision)
    else: # pre-defined test-set
        # Load corpus and make sentence graphs
        print >> sys.stderr, "Loading test set corpus"
        corpusElements = loadCorpus(options.input_test, options.parse, options.tokenization)
        testSentences = []
        for sentence in corpusElements.sentences:
            testSentences.append( [sentence.sentenceGraph,None] )
        
        # Build examples
        testExamples = buildExamples(exampleBuilder, testSentences, options)
        
        # Define test and training sets
        exampleSets = [examples, testExamples]        
    
    # Create classifier object
    if options.output != None:
        classifier = Classifier(workDir = options.output + "/classifier")
    else:
        classifier = Classifier()
    classifier.featureSet = exampleBuilder.featureSet
    if hasattr(exampleBuilder,"classSet"):
        classifier.classSet = None
    
    # Optimize
    optimizationSets = Example.divideExamples(exampleSets[0])
    evaluationArgs = {"classSet":exampleBuilder.classSet}
    if options.parameters != None:
        paramDict = splitParameters(options.parameters)
        bestResults = classifier.optimize([optimizationSets[0]], [optimizationSets[1]], paramDict, Evaluation, evaluationArgs)
    else:
        bestResults = classifier.optimize([optimizationSets[0]], [optimizationSets[1]], evaluationClass=Evaluation, evaluationArgs=evaluationArgs)

    # Save example sets
    if options.output != None:
        print >> sys.stderr, "Saving example sets to", options.output
        Example.writeExamples(exampleSets[0], options.output + "/examplesTest.txt")
        Example.writeExamples(exampleSets[1], options.output + "/examplesTrain.txt")
        Example.writeExamples(optimizationSets[0], options.output + "/examplesOptimizationTest.txt")
        Example.writeExamples(optimizationSets[1], options.output + "/examplesOptimizationTrain.txt")
        print >> sys.stderr, "Saving class names to", options.output + ".class_names"
        exampleBuilder.classSet.write(options.output + "/class_names.txt")
        print >> sys.stderr, "Saving feature names to", options.output + "/feature_names.txt"
        exampleBuilder.featureSet.write(options.output + "/feature_names.txt")
        TableUtils.writeCSV(bestResults[2], options.output +"/best_parameters.csv")
    
    # Classify
    print >> sys.stderr, "Classifying test data"
    if bestResults[2].has_key("timeout"):
        del bestResults[2]["timeout"]
    print >> sys.stderr, "Parameters:", bestResults[2]
    print >> sys.stderr, "Training",
    startTime = time.time()
    classifier.train(exampleSets[0], bestResults[2])
    print >> sys.stderr, "(Time spent:", time.time() - startTime, "s)"
    print >> sys.stderr, "Testing",
    startTime = time.time()
    predictions = classifier.classify(exampleSets[1])
    print >> sys.stderr, "(Time spent:", time.time() - startTime, "s)"
    
    ## Map to gold, if using predicted entities
    #if options.input_test_gold != None:
    #    print >> sys.stderr, "Loading test set corpus gold standard version"
    #    goldCorpusElements = loadCorpus(options.input_test_gold, options.parse, options.tokenization)
    #    goldSentences = []
    #    for sentence in goldCorpusElements.sentences:
    #        goldSentences.append( [sentence.sentenceGraph,None] )
    
    # Calculate statistics
    evaluation = Evaluation(predictions, classSet=exampleBuilder.classSet)
    print >> sys.stderr, evaluation.toStringConcise()
    if options.output != None:
        evaluation.saveCSV(options.output + "/results.csv")
    
    # Save interactionXML
    if options.resultsToXML != None:
        classSet = None
        if "typed" in exampleBuilder.styles:
            classSet = exampleBuilder.classSet
        Example.writeToInteractionXML(evaluation.classifications, corpusElements, options.resultsToXML, classSet)

#    # Compare to binary
#    if options.binaryCorpus != None:
#        compareToBinary(corpusElements.sentencesById, predictions, exampleBuilder, options)
        
    # Visualize
    for example in exampleSets[0]:
        example[3]["visualizationSet"] = "train"
        #corpusElements.sentencesById[example[0].rsplit(".",1)[0]].sentenceGraph.visualizationSet = "train"
    for example in exampleSets[1]:
        example[3]["visualizationSet"] = "test"
        #corpusElements.sentencesById[example[0].rsplit(".",1)[0]].sentenceGraph.visualizationSet = "test"
    if options.visualization != None:
        if len(testSentences) > 0:
            visualize(testSentences, evaluation.classifications, options, exampleBuilder)
        else:
            visualize(sentences, evaluation.classifications, options, exampleBuilder)