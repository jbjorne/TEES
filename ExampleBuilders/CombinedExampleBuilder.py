import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
import Stemming.PorterStemmer as PorterStemmer
from Core.IdSet import IdSet
from SimpleDependencyExampleBuilder2 import SimpleDependencyExampleBuilder2
from GeneralEntityRecognizer import GeneralEntityRecognizer

class CombinedExampleBuilder(ExampleBuilder):
    def __init__(self):
        ExampleBuilder.__init__(self)
        self.entityExampleBuilder = GeneralEntityRecognizer()
        self.edgeExampleBuilder = SimpleDependencyExampleBuilder2()
    
    def buildExamples(self, sentenceGraph):
        examples = []
        examples = self.edgeExampleBuilder.buildExamples(sentenceGraph)
        exampleIndex = len(examples)
        examples.extend( self.entityExampleBuilder.buildExamples(sentenceGraph, exampleIndex = 0) )
        return examples