"""
Giuliano Feature Builder
"""
__version__ = "$Revision: 1.1 $"

import sys,os
from FeatureBuilder import FeatureBuilder
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"../..")))
import Utils.Range as Range

class GiulianoFeatureBuilder(FeatureBuilder):
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
        self.sentenceGraph = sentenceGraph
        patternForeBetween, patternBetween, patternBetweenAfter = self.getPatterns(entity1, entity2)
        for feature in patternForeBetween:
            self.setFeature("pFB_" + feature, patternForeBetween[feature])
        for feature in patternBetween:
            self.setFeature("pB_" + feature, patternBetween[feature])
        for feature in patternBetweenAfter:
            self.setFeature("pBA_" + feature, patternBetweenAfter[feature])
    
    def buildTriggerFeatures(self, token, sentenceGraph):
        ### Feature generation code here ###
        self.sentenceGraph = sentenceGraph
        patternForeBetween, patternBetween, patternBetweenAfter = self.getPatterns(token, token)
        for feature in patternForeBetween:
            self.setFeature("pFB_" + feature, patternForeBetween[feature])
        for feature in patternBetween:
            self.setFeature("pB_" + feature, patternBetween[feature])
        for feature in patternBetweenAfter:
            self.setFeature("pBA_" + feature, patternBetweenAfter[feature])
        
    def getGlobalContextKernel(self, patterns1, patterns2):
        kernelFB = calculateKernel(patterns1["Fore-Between"], patterns2["Fore-Between"])
        kernelB = calculateKernel(patterns1["Between"], patterns2["Between"])
        kernelBA = calculateKernel(patterns1["Between-After"], patterns2["Between-After"])
        return kernelFB + kernelB + kernelBA

    def getRelativePosition(self, entity1Range, entity2Range, token):
        offset = Range.charOffsetToSingleTuple(token.get("charOffset"))
        if Range.overlap(entity1Range, offset):
            return "Entity1"
        if Range.overlap(entity2Range, offset):
            return "Entity2"
        entitiesRange = (min(entity1Range[0],entity2Range[0]),max(entity1Range[1],entity2Range[1]))
        if offset[1] < entitiesRange[0]:
            return "Fore"
        elif offset[1] > entitiesRange[1]:
            return "After"
        else:
            return "Between"
    
    def getPatterns(self, e1, e2):
        e1Range = Range.charOffsetToSingleTuple(e1.get("charOffset"))
        e2Range = Range.charOffsetToSingleTuple(e2.get("charOffset"))
        
        tokenPositions = {}
        for token in self.sentenceGraph.tokens:
            tokenPositions[token.get("id")] = self.getRelativePosition(e1Range,e2Range,token)
        
        prevTokenText = None
        prevToken2Text = None
        prevPosition = None
        patternForeBetween = {}
        patternBetween = {}
        patternBetweenAfter = {}
        for token in self.sentenceGraph.tokens:
            if self.sentenceGraph.tokenIsName[token]:
                continue
                
            id = token.get("id")
            text = token.get("text").lower()
            
            if prevPosition != tokenPositions[id]:
                prevTokenText = None
                prevToken2Text = None
            
            if tokenPositions[id] == "Fore":
                self.addToPattern(patternForeBetween, text, prevTokenText, prevToken2Text)
            elif tokenPositions[id] == "Between":
                self.addToPattern(patternForeBetween, text, prevTokenText, prevToken2Text)
                self.addToPattern(patternBetween, text, prevTokenText, prevToken2Text)
                self.addToPattern(patternBetweenAfter, text, prevTokenText, prevToken2Text)
            elif tokenPositions[id] == "After":
                self.addToPattern(patternBetweenAfter, text, prevTokenText, prevToken2Text)
            
            prevPosition = tokenPositions[id]
            #if tokenPositions[id].find("Entity") != -1:
            prevToken2Text = prevTokenText
            prevTokenText = text
    
        return patternForeBetween, patternBetween, patternBetweenAfter

    def addToPattern(self, pattern, tokenText, prevTokenText, prevToken2Text):
        if not pattern.has_key(tokenText):
            pattern[tokenText] = 0
        pattern[tokenText] += 1
        
        # Should the n-grams be unordered?
        if prevTokenText != None:
            ngram1 = prevTokenText + "_" + tokenText
            if not pattern.has_key(ngram1):
                pattern[ngram1] = 0
            pattern[ngram1] += 1
        
        if prevToken2Text != None:
            ngram2 = prevToken2Text + "_" + ngram1
            if not pattern.has_key(ngram2):
                pattern[ngram2] = 0
            pattern[ngram2] += 1

    def calculateKernel(self, pattern1, pattern2):
        dotProduct = 0.0
        length1 = 0.0
        length2 = 0.0
        # The dotProduct is the numerator
        for k,v in pattern1.iteritems():
            if pattern2.has_key(k):
               dotProduct += v * pattern2[k]
        # Get the length of the first vector
        for v in pattern1.values():
            length1 += v * v
        length1 = math.sqrt(length1)
        # Get the length of the second vector
        for v in pattern2.values():
            length2 += v * v
        length2 = math.sqrt(length2)
        
        if length1 == 0 or length2 == 0:
            return 0.0
        else:
            return dotProduct / (length1 * length2)

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
