""" 
ExampleBuilder is the abstract base class for specialized example builders.
Example builders take some data and convert it to examples usable by e.g. SVMs.
An example builder writes three files, an example-file (in extended Joachim's
SVM format) and .class_names and .feature_names files, which contain the names
for the class and feature id-numbers. An example builder can also be given
pre-existing sets of class and feature ids (optionally in files) so that the
generated examples are consistent with other, previously generated examples.
"""

from SentenceGraph import SentenceGraph
from IdSet import IdSet
import sys, os, types
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Utils.ProgressCounter import ProgressCounter
from Utils.Parameters import getArgs
from Utils.Parameters import splitParameters
import Core.ExampleUtils as ExampleUtils
import SentenceGraph

class ExampleBuilder:
    def __init__(self, classSet=None, featureSet=None):
        if(type(classSet) == types.StringType):
            self.classSet = IdSet(filename=classSet)
        else:
            self.classSet = classSet
        
        if(type(featureSet) == types.StringType):
            self.featureSet = IdSet(filename=featureSet)
        else:
            self.featureSet = featureSet
    
    def preProcessExamples(self, allExamples):
        return allExamples
    
#    def buildExamplesForCorpus(self, corpusElements, visualizer=None):
#        print >> sys.stderr, "Building examples"
#        examples = []
#        for sentence in corpusElements.sentences:
#            print >> sys.stderr, "\rProcessing sentence", sentence.sentence.attrib["id"], "          ",
#            graph = SentenceGraph(sentence.sentence, sentence.tokens, sentence.dependencies)
#            graph.mapInteractions(sentence.entities, sentence.interactions)
#            sentenceExamples = self.buildExamples(graph)
#            examples.extend(sentenceExamples)
#        print >> sys.stderr
#        return examples
    
    def buildExamples(self, sentenceGraph):
        raise NotImplementedError
    
    def definePredictedValueRange(self, sentences, elementName):
        pass
    
    def getPredictedValueRange(self):
        return None

    def buildExamplesForSentences(self, sentences, output, idFileTag=None):            
        examples = []
        counter = ProgressCounter(len(sentences), "Build examples")
        
        calculatePredictedRange(self, sentences)
        
        outfile = open(output, "wt")
        exampleCount = 0
        for sentence in sentences:
            counter.update(1, "Building examples ("+sentence[0].getSentenceId()+"): ")
            examples = self.buildExamples(sentence[0])
            exampleCount += len(examples)
            examples = self.preProcessExamples(examples)
            ExampleUtils.appendExamples(examples, outfile)
        outfile.close()
    
        print >> sys.stderr, "Examples built:", exampleCount
        print >> sys.stderr, "Features:", len(self.featureSet.getNames())
        # Save Ids
        if idFileTag != None: 
            print >> sys.stderr, "Saving class names to", idFileTag + ".class_names"
            self.classSet.write(idFileTag + ".class_names")
            print >> sys.stderr, "Saving feature names to", idFileTag + ".feature_names"
            self.featureSet.write(idFileTag + ".feature_names")
    
    @classmethod
    def getIdSets(self, idFileTag=None):
        if idFileTag != None and os.path.exists(idFileTag + ".feature_names") and os.path.exists(idFileTag + ".class_names"):
            print >> sys.stderr, "Using predefined class and feature names"
            featureSet = IdSet()
            featureSet.load(idFileTag + ".feature_names")
            classSet = IdSet()
            classSet.load(idFileTag + ".class_names")
            return classSet, featureSet
        else:
            print >> sys.stderr, "No predefined class or feature-names"
            assert(not os.path.exists(idFileTag + ".feature_names"))
            assert(not os.path.exists(idFileTag + ".class_names"))
            return None, None
            
    @classmethod
    def getSentences(cls, input, parse, tokenization):    
        if type(input) != types.ListType:
            # Load corpus and make sentence graphs
            corpusElements = SentenceGraph.loadCorpus(input, parse, tokenization)
            sentences = []
            for sentence in corpusElements.sentences:
                sentences.append( [sentence.sentenceGraph,None] )
            return sentences
        else: # assume input is already a list of sentences
            return input

def calculatePredictedRange(exampleBuilder, sentences):
    print >> sys.stderr, "Defining predicted value range:",
    sentenceElements = []
    for sentence in sentences:
        sentenceElements.append(sentence[0].sentenceElement)
    exampleBuilder.definePredictedValueRange(sentenceElements, "entity")
    print >> sys.stderr, exampleBuilder.getPredictedValueRange()

def addBasicOptions(optparser):
    optparser.add_option("-i", "--input", default=defaultAnalysisFilename, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file for the examples")
    optparser.add_option("-t", "--tokenization", default="split-Charniak-Lease", dest="tokenization", help="tokenization")
    optparser.add_option("-p", "--parse", default="split-Charniak-Lease", dest="parse", help="parse")
    optparser.add_option("-x", "--exampleBuilderParameters", default=None, dest="exampleBuilderParameters", help="Parameters for the example builder")
    optparser.add_option("-b", "--exampleBuilder", default="SimpleDependencyExampleBuilder", dest="exampleBuilder", help="Example Builder Class")
    optparser.add_option("-d", "--predefined", default=None, dest="predefined", help="Directory with predefined class_names.txt and feature_names.txt files")

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    from optparse import OptionParser
    defaultAnalysisFilename = "/usr/share/biotext/ComplexPPI/BioInferForComplexPPIVisible.xml"
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    addBasicOptions(optparser)
    (options, args) = optparser.parse_args()
    
    print >> sys.stderr, "Importing modules"
    exec "from ExampleBuilders." + options.exampleBuilder + " import " + options.exampleBuilder + " as ExampleBuilderClass"
    
    run(ExampleBuilderClass, options.input, options.output, options.parse, options.tokenization, options.parameters, options.predefined)
    
#    # Load corpus and make sentence graphs
#    corpusElements = SentenceGraph.loadCorpus(options.input, options.parse, options.tokenization)
#    sentences = []
#    for sentence in corpusElements.sentences:
#        sentences.append( [sentence.sentenceGraph,None] )
#
#    # Build examples
#    if options.predefined != None:
#        print >> sys.stderr, "Using predefined class and feature names"
#        featureSet = IdSet()
#        featureSet.load(os.path.join(options.predefined, ".feature_names"))
#        classSet = IdSet()
#        classSet.load(os.path.join(options.predefined, ".class_names"))
#        exampleBuilder = ExampleBuilderClass(featureSet=featureSet, classSet=classSet, **getValidArgs(ExampleBuilderClass.__init__, splitParameters(options.exampleBuilderParameters)))
#    else:
#        exampleBuilder = ExampleBuilderClass(**getValidArgs(ExampleBuilderClass.__init__, splitParameters(options.exampleBuilderParameters)))
#    
#    buildExamples(exampleBuilder, sentences, options)
#    print >> sys.stderr, "Saving class names to", options.output + ".class_names"
#    exampleBuilder.classSet.write(options.output + ".class_names")
#    print >> sys.stderr, "Saving feature names to", options.output + ".feature_names"
#    exampleBuilder.featureSet.write(options.output + ".feature_names")
