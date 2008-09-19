import Core.SentenceGraph as SentenceGraph
from optparse import OptionParser
import networkx as NX
import sys

def calculateMainStatistics(corpusElements):
    totalTokens = 0
    totalHeadTokens = 0
    headTokenPairs = 0
    for sentence in corpusElements.sentences:
        sentenceGraph = sentence.sentenceGraph
        totalTokens += len(sentenceGraph.tokens)
        
        headTokens = 0
        for token in sentenceGraph.tokens:
            if sentenceGraph.tokenIsEntityHead[token] != None:
                headTokens += 1
        totalHeadTokens += headTokens
        headTokenPairs += headTokens * headTokens
    print >> sys.stderr, "Tokens:", totalTokens
    print >> sys.stderr, "Head Tokens:", totalHeadTokens
    print >> sys.stderr, "Head Token Pairs:", headTokenPairs

def analyzeLengths(corpusElements):
    interactionEdges = 0
    dependencyEdges = 0
    pathsByLength = {}
    pathsBetweenAllEntitiesByLength = {}
    for sentence in corpusElements.sentences:
        sentenceGraph = sentence.sentenceGraph
        interactionEdges += len(sentenceGraph.interactionGraph.edges())
        dependencyEdges += len(sentenceGraph.dependencyGraph.edges())
        
        undirected = sentenceGraph.dependencyGraph.to_undirected()
        paths = NX.all_pairs_shortest_path(undirected, cutoff=999)
        # Shortest path for interaction edge
        for intEdge in sentenceGraph.interactionGraph.edges():
            if paths.has_key(intEdge[0]) and paths[intEdge[0]].has_key(intEdge[1]):
                path = paths[intEdge[0]][intEdge[1]]
                if not pathsByLength.has_key(len(path)-1):
                    pathsByLength[len(path)-1] = 0
                pathsByLength[len(path)-1] += 1
            else:
                if not pathsByLength.has_key("none"):
                    pathsByLength["none"] = 0
                pathsByLength["none"] += 1
        # Shortest paths between all entities
        for i in range(len(sentenceGraph.tokens)-1):
            for j in range(i+1,len(sentenceGraph.tokens)):
                tI = sentenceGraph.tokens[i]
                tJ = sentenceGraph.tokens[j]
                if sentenceGraph.tokenIsEntityHead[tI] == None or sentenceGraph.tokenIsEntityHead[tJ] == None:
                    continue
                if paths.has_key(tI) and paths[tI].has_key(tJ):
                    path = paths[tI][tJ]
                    if not pathsBetweenAllEntitiesByLength.has_key(len(path)-1):
                        pathsBetweenAllEntitiesByLength[len(path)-1] = 0
                    pathsBetweenAllEntitiesByLength[len(path)-1] += 1
                else:
                    if not pathsBetweenAllEntitiesByLength.has_key("none"):
                        pathsBetweenAllEntitiesByLength["none"] = 0
                    pathsBetweenAllEntitiesByLength["none"] += 1
    
    print >> sys.stderr, "Interaction edges:", interactionEdges
    print >> sys.stderr, "Dependency edges:", dependencyEdges
    print >> sys.stderr, "Shortest path of dependencies for interaction edge:"
    printPathDistribution(pathsByLength)
    print >> sys.stderr, "Shortest path of dependencies between all entities:"
    printPathDistribution(pathsBetweenAllEntitiesByLength)

def printPathDistribution(pathsByLength):
    lengths = pathsByLength.keys()
    lengths.sort()
    totalPaths = 0
    for length in lengths:
        totalPaths += pathsByLength[length]
    print >> sys.stderr, "  Total: " + str(totalPaths)
    for length in lengths:
        print >> sys.stderr, "  " + str(length) + ": " + str(pathsByLength[length]), "(%.2f" % (100*float(pathsByLength[length])/totalPaths) + " %)"

def countMultipleEdges(corpusElements):
    parallelEdgesByType = {}
    circular = 0
    total = 0
    for sentence in corpusElements.sentences:
        sentenceGraph = sentence.sentenceGraph
        for edge in sentenceGraph.interactionGraph.edges():
            isCircular = False
            intEdges = sentenceGraph.interactionGraph.get_edge(edge[0], edge[1])
            if len(intEdges) > 0 and len(sentenceGraph.interactionGraph.get_edge(edge[1], edge[0])) > 0:
                circular += 1
                isCircular = True
            intEdges.extend( sentenceGraph.interactionGraph.get_edge(edge[1], edge[0]) )
            types = []
            for intEdge in intEdges:
                types.append(intEdge.attrib["type"])
            if len(types) > 1:
                total += 1
                types.sort()
                types = tuple(types)
                if not parallelEdgesByType.has_key(types):
                    parallelEdgesByType[types] = [0,0]
                parallelEdgesByType[types][0] += 1
                if isCircular: parallelEdgesByType[types][1] += 1
    types = parallelEdgesByType.keys()
    types.sort()
    print >> sys.stderr, "Parallel edges:"
    print >> sys.stderr, "  Total:", total, "Circular:", circular
    for type in types:
        print >> sys.stderr, "  " + str(type) + ": " + str(parallelEdgesByType[type][0]) + " (circular: " + str(parallelEdgesByType[type][1]) + ")"
                             

if __name__=="__main__":
    defaultAnalysisFilename = "/usr/share/biotext/ComplexPPI/BioInferForComplexPPI.xml"
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=defaultAnalysisFilename, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-t", "--tokenization", default="split_gs", dest="tokenization", help="tokenization")
    optparser.add_option("-p", "--parse", default="split_gs", dest="parse", help="parse")
    (options, args) = optparser.parse_args()
    
    corpusElements = SentenceGraph.loadCorpus(options.input, options.parse, options.tokenization)
    print >> sys.stderr, "tokenization:", options.tokenization
    print >> sys.stderr, "parse:", options.parse
    
    calculateMainStatistics(corpusElements)
    analyzeLengths(corpusElements)
    countMultipleEdges(corpusElements)
