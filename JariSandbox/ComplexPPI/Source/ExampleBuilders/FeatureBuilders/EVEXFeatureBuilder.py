"""
EVEX Feature Builder
"""
__version__ = "$Revision: 1.5 $"

from FeatureBuilder import FeatureBuilder

class EVEXFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet):
        """
        This is called, when the ExampleBuilder object is created.
        
        @type featureSet: Core.IdSet
        @param featureSet: The feature ids
        """
        FeatureBuilder.__init__(self, featureSet)
    
    def initSentence(self, sentenceGraph):
        """
        This function is called once for each sentence, before any calls to "buildFeatures". It
        should be used to initialize per-sentence data structures.
        
        @type sentenceGraph: Core.SentenceGraph
        @param sentenceGraph: a SentenceGraph object providing access to the aligned semantic and syntactic
                       information of the sentence. The underlying XML can also be accessed through
                       this class.
        """
        ### Sentence initialization code here ###
        pass
    
    def buildEdgeFeatures(self, entity1, entity2, token1, token2, path, sentenceGraph):
        """
        This is the main-function for feature generation. It is called once for each 
        directed entity pair in the sentence.
        
        For defining features, please use the member function "setFeature(self, name, value=1)",
        derived from the parent class. This ensures features get correctly tagged, if needed.
        
        @type entity1: cElementTree.Element
        @param entity1: First entity of the candidate edge, an Interaction XML "entity"-element
        @type entity2: cElementTree.Element
        @param entity2: Second entity of the candidate edge, an Interaction XML "entity"-element
        @type token1: cElementTree.Element
        @param token1: The head token of entity1, an Interaction XML "token"-element
        @type token2: cElementTree.Element
        @param token2: The head token of entity2, an Interaction XML "token"-element
        @type path: list of cElementTree.Elements (when "no_path" style is set, this is always [token1, token2])
        @param path: the shortest connecting path of tokens (Interaction XML "token"-elements)
        @type sentenceGraph: Core.SentenceGraph
        @param sentenceGraph: a SentenceGraph object providing access to the aligned semantic and syntactic
                       information of the sentence. The underlying XML can also be accessed through
                       this class.
        """
        ### Feature generation code here ###
        pass

if __name__=="__main__":
    """
    The main-function is the test program for the EVEX feature builder. It takes as a parameter an
    Interaction XML corpus file, and builds edge-examples using MultiEdgeExampleBuilder. When the
    "evex" style parameter is set, MultiEdgeExampleBuilder will call EVEXFeatureBuilder for feature
    generation.
    """
    import sys
    sys.path.append("../..")
    from Core.IdSet import IdSet
    import Core.ExampleUtils as ExampleUtils
    from ExampleBuilders.MultiEdgeExampleBuilder import MultiEdgeExampleBuilder

    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\nTest EVEX Feature Builder.")
    defaultInput = "/usr/share/biotext/BioNLP2011/data/main-tasks/GE/GE-devel-nodup.xml"
    optparser.add_option("-i", "--input", default=defaultInput, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default="evex-examples.txt", dest="output", help="Output feature file")
    optparser.add_option("-d", "--edgeIds", default="evex-ids", dest="edgeIds", help="Example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
    optparser.add_option("-t", "--tokenization", default="split-mccc-preparsed", dest="tokenization", help="tokenization")
    optparser.add_option("-p", "--parse", default="split-mccc-preparsed", dest="parse", help="parse")
    optparser.add_option("-s", "--styles", default="typed,directed,no_path,no_task,no_dependency,no_linear,entities,genia_limits,noMasking,maxFeatures,evex", dest="edgeStyles", help="")
    (options, args) = optparser.parse_args()
    assert options.input != None
    assert options.output != None
    assert options.edgeIds != None
    
    exampleBuilder = MultiEdgeExampleBuilder()
    exampleBuilder.run(options.input, options.output, options.parse, options.tokenization, "style:"+options.edgeStyles, options.edgeIds)
