from SentenceGraph import SentenceGraph
from FeatureSet import FeatureSet
import sys

class ExampleBuilder:
    def __init__(self):
        self.featureSet = FeatureSet()
    
    def buildExamplesForCorpus(self, corpusElements):
        print >> sys.stderr, "Building examples"
        examples = []
        for sentence in corpusElements.sentences:
            print >> sys.stderr, "\rProcessing sentence", sentence.sentence.attrib["id"], "          ",
            graph = SentenceGraph(sentence.sentence, sentence.tokens, sentence.dependencies)
            graph.mapInteractions(sentence.entities, sentence.interactions)
            examples.extend( self.buildExamples(graph) )
        print >> sys.stderr
        return examples
    
    def buildExamples(self, sentenceGraph):
        pass