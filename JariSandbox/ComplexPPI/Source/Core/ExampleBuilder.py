from SentenceGraph import SentenceGraph
from IdSet import IdSet
import sys

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
    
def buildExamples(exampleBuilder, sentences, options):
    examples = []
    if "graph_kernel" in exampleBuilder.styles:
        counter = ProgressCounter(len(sentences), "Build examples", 0)
    else:
        counter = ProgressCounter(len(sentences), "Build examples")
    
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
    optparser.add_option("-t", "--tokenization", default="split_gs", dest="tokenization", help="tokenization")
    optparser.add_option("-p", "--parse", default="split_gs", dest="parse", help="parse")
    optparser.add_option("-x", "--exampleBuilderParameters", default=None, dest="exampleBuilderParameters", help="Parameters for the example builder")
    optparser.add_option("-b", "--exampleBuilder", default="SimpleDependencyExampleBuilder", dest="exampleBuilder", help="Example Builder Class")
    (options, args) = optparser.parse_args()
    
    print >> sys.stderr, "Importing modules"
    exec "from ExampleBuilders." + options.exampleBuilder + " import " + options.exampleBuilder + " as ExampleBuilderClass"
    
    # Load corpus and make sentence graphs
    corpusElements = SentenceGraph.loadCorpus(options.input, options.parse, options.tokenization)
    sentences = []
    for sentence in corpusElements.sentences:
        sentences.append( [sentence.sentenceGraph,None] )

    # Build examples
    exampleBuilder = ExampleBuilderClass(**splitParameters(options.exampleBuilderParameters))
    buildExamples(exampleBuilder, sentences, options)
