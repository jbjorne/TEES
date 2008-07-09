import Core.ExampleUtils as Example
import sys, os
import cElementTree as ET
from ExampleBuilders.SimpleDependencyExampleBuilder import SimpleDependencyExampleBuilder
from InteractionXML.CorpusElements import CorpusElements
from Core.SentenceGraph import *
from Classifiers.SVMLightClassifier import *
from Core.Evaluation import Evaluation

if __name__=="__main__":
    defaultInteractionFilename = "/usr/share/biotext/ComplexPPI/BioInferForComplexPPI.xml"
    
    print >> sys.stderr, "Loading corpus file", defaultInteractionFilename
    corpusTree = ET.parse(defaultInteractionFilename)
    corpusRoot = corpusTree.getroot()
    corpusElements = CorpusElements(corpusRoot, "split_gs", "split_gs")
    
    # Build examples
    examples = []
    exampleBuilder = SimpleDependencyExampleBuilder()
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

    classifier = SVMLightClassifier()
    
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