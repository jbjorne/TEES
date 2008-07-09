import Core.ExampleUtils as Example
import sys, os
import cElementTree as ET
#from ExampleBuilders.SimpleDependencyExampleBuilder import SimpleDependencyExampleBuilder
from InteractionXML.CorpusElements import CorpusElements
from Core.SentenceGraph import *
#from Classifiers.SVMLightClassifier import SVMLightClassifier as Classifier
from Core.Evaluation import Evaluation
from optparse import OptionParser

if __name__=="__main__":
    defaultAnalysisFilename = "/usr/share/biotext/ComplexPPI/BioInferForComplexPPI.xml"
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=defaultAnalysisFilename, dest="input", help="Corpus", metavar="FILE")
    optparser.add_option("-c", "--classifier", default="SVMLightClassifier", dest="classifier", help="Corpus", metavar="FILE")
    optparser.add_option("-e", "--exampleBuilder", default="SimpleDependencyExampleBuilder", dest="exampleBuilder", help="Corpus", metavar="FILE")
    (options, args) = optparser.parse_args()

    print >> sys.stderr, "Importing modules"
    exec "from ExampleBuilders." + options.exampleBuilder + " import " + options.exampleBuilder + " as ExampleBuilder"
    exec "from Classifiers." + options.classifier + " import " + options.classifier + " as Classifier"
    
    print >> sys.stderr, "Loading corpus file", options.input
    corpusTree = ET.parse(options.input)
    corpusRoot = corpusTree.getroot()
    corpusElements = CorpusElements(corpusRoot, "split_gs", "split_gs")
    
    # Build examples
    examples = []
    exampleBuilder = ExampleBuilder()
    for sentence in corpusElements.sentences:
        print >> sys.stderr, "\rProcessing sentence", sentence.sentence.attrib["id"], "          ",
        #print >> sys.stderr, "Building graph"
        graph = SentenceGraph(sentence.sentence, sentence.tokens, sentence.dependencies)
        #print >> sys.stderr, "Mapping interactions"
        graph.mapInteractions(sentence.entities, sentence.interactions)
        examples.extend( exampleBuilder.buildExamples(graph) )
    print >> sys.stderr
    
    # Make test and training sets
    print >> sys.stderr, "Dividing data into test and training sets"
    corpusDivision = Example.makeCorpusDivision(corpusElements)
    exampleSets = Example.divideExamples(examples, corpusDivision)

    classifier = Classifier()
    
    # Optimize
    print >> sys.stderr, "Optimizing c-parameter"
    optimizationSets = Example.divideExamples(exampleSets[0])
    bestResults = classifier.optimize(optimizationSets[0], optimizationSets[1])
    
    # Classify
    print >> sys.stderr, "Classifying test data"    
    classifier.train(exampleSets[0], bestResults[2])
    predictions = classifier.classify(exampleSets[1])
    
    # Calculate statistics
    evaluation = Evaluation(predictions)
    print >> sys.stderr, evaluation.toStringConcise()