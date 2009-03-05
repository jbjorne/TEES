from SentenceGraph import SentenceGraph
from IdSet import IdSet
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")

class ExampleBuilder:
    def __init__(self):
        self.featureSet = IdSet()
        self.classSet = None
    
    def preProcessExamples(self, allExamples):
        return allExamples
    
    def buildExamplesForCorpus(self, corpusElements, visualizer=None):
        print >> sys.stderr, "Building examples"
        examples = []
        for sentence in corpusElements.sentences:
            print >> sys.stderr, "\rProcessing sentence", sentence.sentence.attrib["id"], "          ",
            graph = SentenceGraph(sentence.sentence, sentence.tokens, sentence.dependencies)
            graph.mapInteractions(sentence.entities, sentence.interactions)
            sentenceExamples = self.buildExamples(graph)
            examples.extend(sentenceExamples)
        print >> sys.stderr
        return examples
    
    def buildExamples(self, sentenceGraph):
        pass
    
    def definePredictedValueRange(self, sentences, elementName):
        pass
    
    def getPredictedValueRange(self):
        return None

def calculatePredictedRange(exampleBuilder, sentences):
    print >> sys.stderr, "Defining predicted value range:",
    sentenceElements = []
    for sentence in sentences:
        sentenceElements.append(sentence[0].sentenceElement)
    exampleBuilder.definePredictedValueRange(sentenceElements, "entity")
    print >> sys.stderr, exampleBuilder.getPredictedValueRange()
    
def buildExamples(exampleBuilder, sentences, options):
    examples = []
    if "graph_kernel" in exampleBuilder.styles:
        counter = ProgressCounter(len(sentences), "Build examples", 0)
    else:
        counter = ProgressCounter(len(sentences), "Build examples")
    
    calculatePredictedRange(exampleBuilder, sentences)
    
    outfile = open(options.output, "wt")
    exampleCount = 0
    for sentence in sentences:
        counter.update(1, "Building examples ("+sentence[0].getSentenceId()+"): ")
        examples = exampleBuilder.buildExamples(sentence[0])
        exampleCount += len(examples)
        examples = exampleBuilder.preProcessExamples(examples)
        ExampleUtils.appendExamples(examples, outfile)
    outfile.close()

    print >> sys.stderr, "Examples built:", len(examples)
    print >> sys.stderr, "Features:", len(exampleBuilder.featureSet.getNames())

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    import SentenceGraph
    sys.path.append("..")
    from Utils.ProgressCounter import ProgressCounter
    from Utils.Parameters import splitParameters
    from optparse import OptionParser
    import ExampleUtils
    defaultAnalysisFilename = "/usr/share/biotext/ComplexPPI/BioInferForComplexPPIVisible.xml"
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=defaultAnalysisFilename, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file for the examples")
    optparser.add_option("-t", "--tokenization", default="split-Charniak-Lease", dest="tokenization", help="tokenization")
    optparser.add_option("-p", "--parse", default="split-Charniak-Lease", dest="parse", help="parse")
    optparser.add_option("-x", "--exampleBuilderParameters", default=None, dest="exampleBuilderParameters", help="Parameters for the example builder")
    optparser.add_option("-b", "--exampleBuilder", default="SimpleDependencyExampleBuilder", dest="exampleBuilder", help="Example Builder Class")
    optparser.add_option("-d", "--predefined", default=None, dest="predefined", help="Directory with predefined class_names.txt and feature_names.txt files")
    (options, args) = optparser.parse_args()
    
    print >> sys.stderr, "Importing modules"
    exec "from ExampleBuilders." + options.exampleBuilder + " import " + options.exampleBuilder + " as ExampleBuilderClass"
    
    # Load corpus and make sentence graphs
    corpusElements = SentenceGraph.loadCorpus(options.input, options.parse, options.tokenization)
    sentences = []
    for sentence in corpusElements.sentences:
        sentences.append( [sentence.sentenceGraph,None] )

    # Build examples
    if options.predefined != None:
        print >> sys.stderr, "Using predefined class and feature names"
        featureSet = IdSet()
        featureSet.load(os.path.join(options.predefined, "feature_names.txt"))
        classSet = None
        if os.path.exists(os.path.join(options.predefined, "class_names.txt")):
            classSet = IdSet()
            classSet.load(os.path.join(options.predefined, "class_names.txt"))
        exampleBuilder = ExampleBuilder(featureSet=featureSet, classSet=classSet, **splitParameters(options.exampleBuilderParameters))
    else:
        exampleBuilder = ExampleBuilderClass(**splitParameters(options.exampleBuilderParameters))
    
    buildExamples(exampleBuilder, sentences, options)
    print >> sys.stderr, "Saving class names to", options.output + ".class_names"
    exampleBuilder.classSet.write(options.output + ".class_names")
    print >> sys.stderr, "Saving feature names to", options.output + ".feature_names"
    exampleBuilder.featureSet.write(options.output + ".feature_names")
