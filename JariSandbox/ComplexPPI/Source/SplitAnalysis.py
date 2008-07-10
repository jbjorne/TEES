import Core.ExampleUtils as Example
import sys, os
import cElementTree as ET
#from ExampleBuilders.SimpleDependencyExampleBuilder import SimpleDependencyExampleBuilder
from InteractionXML.CorpusElements import CorpusElements
from Core.SentenceGraph import *
#from Classifiers.SVMLightClassifier import SVMLightClassifier as Classifier
from Core.Evaluation import Evaluation
from Visualization.CorpusVisualizer import CorpusVisualizer
from optparse import OptionParser

class ProgressCounter:
    def __init__(self, total):
        self.total = float(total)
        self.current = 0
        self.progress = 0.0
        self.prevProgress = -99.0
    
    def update(self, amount=1, string="Processing: "):
        self.current += amount
        self.progress = self.current / self.total * 100.0
        if self.progress >= 100.0 or self.progress - self.prevProgress >= 5.0:
            print >> sys.stderr, "\r" + string + "%.2f" % self.progress + " %",
            self.prevProgress = self.progress
        if self.progress >= 100.0:
            print >> sys.stderr

if __name__=="__main__":
    defaultAnalysisFilename = "/usr/share/biotext/ComplexPPI/BioInferForComplexPPI.xml"
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=defaultAnalysisFilename, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Example output file")
    optparser.add_option("-c", "--classifier", default="SVMLightClassifier", dest="classifier", help="Classifier Class")
    optparser.add_option("-e", "--exampleBuilder", default="SimpleDependencyExampleBuilder", dest="exampleBuilder", help="Example Builder Class")
    optparser.add_option("-v", "--visualization", default=None, dest="visualization", help="Visualization output directory. NOTE: If the directory exists, it will be deleted!")
    (options, args) = optparser.parse_args()

    print >> sys.stderr, "Importing modules"
    exec "from ExampleBuilders." + options.exampleBuilder + " import " + options.exampleBuilder + " as ExampleBuilder"
    exec "from Classifiers." + options.classifier + " import " + options.classifier + " as Classifier"
    
    print >> sys.stderr, "Loading corpus file", options.input
    corpusTree = ET.parse(options.input)
    corpusRoot = corpusTree.getroot()
    corpusElements = CorpusElements(corpusRoot, "split_gs", "split_gs")
    
    # Make sentence graphs
    sentences = []
    counter = ProgressCounter(len(corpusElements.sentences))
    for sentence in corpusElements.sentences:
        counter.update(1, "Making sentence graphs: ")
        graph = SentenceGraph(sentence.sentence, sentence.tokens, sentence.dependencies)
        graph.mapInteractions(sentence.entities, sentence.interactions)
        sentences.append( [graph,None,None] )
    
    # Build examples
    exampleBuilder = ExampleBuilder()
    examples = []
    counter = ProgressCounter(len(sentences))
    for sentence in sentences:
        counter.update(1, "Building examples: ")
        sentence[1] = exampleBuilder.buildExamples(sentence[0])
        examples.extend(sentence[1])
   
    # Save examples
    if options.output != None:
        print >> sys.stderr, "Saving examples to", options.output
        commentLines = []
        commentLines.append("Input file: " + options.input)
        commentLines.append("Example builder: " + options.exampleBuilder)
        commentLines.append("Features:")
        commentLines.extend(exampleBuilder.featureSet.toStrings())
        Example.writeExamples(examples, options.output, commentLines)
    
    # Make test and training sets
    print >> sys.stderr, "Dividing data into test and training sets"
    corpusDivision = Example.makeCorpusDivision(corpusElements)
    exampleSets = Example.divideExamples(examples, corpusDivision)
    
    # Create classifier object
    classifier = Classifier()
    
    # Optimize
    optimizationSets = Example.divideExamples(exampleSets[0])
    bestResults = classifier.optimize(optimizationSets[0], optimizationSets[1])
    
    # Classify
    print >> sys.stderr, "Classifying test data"    
    print >> sys.stderr, "Parameters:", bestResults[2]
    classifier.train(exampleSets[0], bestResults[2])
    predictions = classifier.classify(exampleSets[1])
    
    # Calculate statistics
    evaluation = Evaluation(predictions)
    print >> sys.stderr, evaluation.toStringConcise()
    
    # Visualize
    if options.visualization != None:
        print >> sys.stderr, "Making visualization"
        visualizer = CorpusVisualizer(options.visualization, True)
        for i in range(len(sentences)):
            sentence = sentences[i]
            print >> sys.stderr, "\rProcessing sentence", sentence[0].getSentenceId(), "          ",
            prevAndNextId = [None,None]
            if i > 0:
                prevAndNextId[0] = sentences[i-1][0].getSentenceId()
            if i < len(sentences)-1:
                prevAndNextId[1] = sentences[i+1][0].getSentenceId()
            visualizer.makeSentencePage(sentence[0],sentence[1],prevAndNextId)
        print >> sys.stderr