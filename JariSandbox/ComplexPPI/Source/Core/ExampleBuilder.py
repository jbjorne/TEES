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