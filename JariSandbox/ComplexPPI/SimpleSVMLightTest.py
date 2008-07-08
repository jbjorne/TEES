import Example
import Split
import sys, os
import cElementTree as ET
from SimpleDependencyExampleBuilder import SimpleDependencyExampleBuilder
from InteractionXML.CorpusElements import CorpusElements
from SentenceGraph import *
from SVMLightClassifier import *
from Evaluation import Evaluation

if __name__=="__main__":
    defaultInteractionFilename = "Data/BioInferForComplexPPI.xml"
    
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
    division = Split.makeDivision(corpusElements)
    exampleSets = Example.divideExamples(examples, division)
    
    # Classify
    classifier = SVMLightClassifier()
    #classifier.train(exampleSets[0])
    #predictions = classifier.classify(exampleSets[1])
    classifier.optimize(exampleSets[0], exampleSets[1])
    
    # Calculate statistics
    evaluation = Evaluation(predictions)
    print >> sys.stderr, evaluation.toStringConcise()