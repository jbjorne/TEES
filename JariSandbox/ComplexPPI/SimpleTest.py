import sys
import cElementTree as ET
from InteractionXML.CorpusElements import CorpusElements
from SentenceGraph import *
import GraphToSVG

if __name__=="__main__":
    defaultInteractionFilename = "Data/BioInferForComplexPPI.xml"
    
    print >> sys.stderr, "Loading corpus file", defaultInteractionFilename
    corpusTree = ET.parse(defaultInteractionFilename)
    corpusRoot = corpusTree.getroot()
    corpusElements = CorpusElements(corpusRoot, "split_gs", "split_gs")
    sentence = corpusElements.sentencesById["BioInfer.d6.s6"]
    print >> sys.stderr, "Building graph"
    graph = SentenceGraph(sentence.tokens, sentence.dependencies)
    print >> sys.stderr, "Mapping interactions"
    graph.mapInteractions(sentence.entities, sentence.interactions)
    print >> sys.stderr, "Drawing"
    svgTokens = GraphToSVG.tokensToSVG(graph.tokens)
    svgDepEdges = GraphToSVG.edgesToSVG(svgTokens, graph.dependencyGraph)
    svgIntEdges = GraphToSVG.edgesToSVG(svgTokens, graph.interactionGraph)
    GraphToSVG.writeSVG(svgTokens, svgDepEdges, "Data/depGraph.svg")
    GraphToSVG.writeSVG(svgTokens, svgIntEdges, "Data/intGraph.svg")