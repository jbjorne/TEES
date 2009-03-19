import Core.SentenceGraph as SentenceGraph
from optparse import OptionParser
import networkx as NX
import sys, os
import shutil
import Utils.TableUtils as TableUtils

options = None

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

def analyzeLinearDistance(corpusElements):
    interactionEdges = 0
    interactionLinearDistanceCounts = {}
    allEntitiesLinearDistanceCounts = {}
    for sentence in corpusElements.sentences:
        sentenceGraph = sentence.sentenceGraph
        interactionEdges += len(sentence.interactions)
        
        # Linear distance between end tokens of interaction edges
        for interaction in sentence.interactions:
            e1 = sentence.entitiesById[interaction.get("e1")]
            e2 = sentence.entitiesById[interaction.get("e2")]
            t1 = sentenceGraph.entityHeadTokenByEntity[e1]
            t2 = sentenceGraph.entityHeadTokenByEntity[e2]
            linDistance = int(t1.get("id").split("_")[-1]) - int(t2.get("id").split("_")[-1])
            if linDistance < 0:
                linDistance *= -1
            if not interactionLinearDistanceCounts.has_key(linDistance):
                interactionLinearDistanceCounts[linDistance] = 0
            interactionLinearDistanceCounts[linDistance] += 1

        # Linear distance between all entities
        for i in range(len(sentence.entities)-1):
            for j in range(i+1,len(sentence.entities)):
                tI = sentenceGraph.entityHeadTokenByEntity[sentence.entities[i]]
                tJ = sentenceGraph.entityHeadTokenByEntity[sentence.entities[j]]
                linDistance = int(t1.get("id").split("_")[-1]) - int(t2.get("id").split("_")[-1])
                if linDistance < 0:
                    linDistance *= -1
                if not allEntitiesLinearDistanceCounts.has_key(linDistance):
                    allEntitiesLinearDistanceCounts[linDistance] = 0
                allEntitiesLinearDistanceCounts[linDistance] += 1
    
    print >> sys.stderr, "=== Linear Distance ==="
    print >> sys.stderr, "Interaction edges:", interactionEdges
    print >> sys.stderr, "Entity head token linear distance for interaction edges:"
    printPathDistribution(interactionLinearDistanceCounts)
    if options.output != None:
        interactionLinearDistanceCounts["corpus"] = options.input
        interactionLinearDistanceCounts["parse"] = options.parse
        TableUtils.addToCSV(interactionLinearDistanceCounts, options.output+"/interactionEdgeLinearDistance.csv")
    print >> sys.stderr, "Linear distance between head tokens of all entities:"
    printPathDistribution(allEntitiesLinearDistanceCounts)
    if options.output != None:
        allEntitiesLinearDistanceCounts["corpus"] = options.input
        allEntitiesLinearDistanceCounts["parse"] = options.parse
        TableUtils.addToCSV(allEntitiesLinearDistanceCounts, options.output+"/allEntitiesLinearDistance.csv")

def analyzeLengths(corpusElements):
    interactionEdges = 0
    dependencyEdges = 0
    pathsByLength = {}
    pathsBetweenAllEntitiesByLength = {}
    for sentence in corpusElements.sentences:
        sentenceGraph = sentence.sentenceGraph
        #interactionEdges += len(sentenceGraph.interactionGraph.edges())
        interactionEdges += len(sentence.interactions)
        dependencyEdges += len(sentenceGraph.dependencyGraph.edges())
        
        undirected = sentenceGraph.dependencyGraph.to_undirected()
        paths = NX.all_pairs_shortest_path(undirected, cutoff=999)
        # Shortest path for interaction edge
        for interaction in sentence.interactions:
            e1 = sentence.entitiesById[interaction.attrib["e1"]]
            e2 = sentence.entitiesById[interaction.attrib["e2"]]
            t1 = sentenceGraph.entityHeadTokenByEntity[e1]
            t2 = sentenceGraph.entityHeadTokenByEntity[e2]
            if paths.has_key(t1) and paths[t1].has_key(t2):
                path = paths[t1][t2]
                if not pathsByLength.has_key(len(path)-1):
                    pathsByLength[len(path)-1] = 0
                pathsByLength[len(path)-1] += 1
            else:
                if not pathsByLength.has_key("none"):
                    pathsByLength["none"] = 0
                pathsByLength["none"] += 1

#        for intEdge in sentenceGraph.interactionGraph.edges():
#            if paths.has_key(intEdge[0]) and paths[intEdge[0]].has_key(intEdge[1]):
#                path = paths[intEdge[0]][intEdge[1]]
#                if not pathsByLength.has_key(len(path)-1):
#                    pathsByLength[len(path)-1] = 0
#                pathsByLength[len(path)-1] += 1
#            else:
#                if not pathsByLength.has_key("none"):
#                    pathsByLength["none"] = 0
#                pathsByLength["none"] += 1
        # Shortest paths between all entities
        for i in range(len(sentence.entities)-1):
            for j in range(i+1,len(sentence.entities)):
                tI = sentenceGraph.entityHeadTokenByEntity[sentence.entities[i]]
                tJ = sentenceGraph.entityHeadTokenByEntity[sentence.entities[j]]
                if paths.has_key(tI) and paths[tI].has_key(tJ):
                    path = paths[tI][tJ]
                    if not pathsBetweenAllEntitiesByLength.has_key(len(path)-1):
                        pathsBetweenAllEntitiesByLength[len(path)-1] = 0
                    pathsBetweenAllEntitiesByLength[len(path)-1] += 1
                elif tI == tJ:
                    if not pathsBetweenAllEntitiesByLength.has_key(0):
                        pathsBetweenAllEntitiesByLength[0] = 0
                    pathsBetweenAllEntitiesByLength[0] += 1
                else:
                    if not pathsBetweenAllEntitiesByLength.has_key("none"):
                        pathsBetweenAllEntitiesByLength["none"] = 0
                    pathsBetweenAllEntitiesByLength["none"] += 1

#        for i in range(len(sentenceGraph.tokens)-1):
#            for j in range(i+1,len(sentenceGraph.tokens)):
#                tI = sentenceGraph.tokens[i]
#                tJ = sentenceGraph.tokens[j]
#                if sentenceGraph.tokenIsEntityHead[tI] == None or sentenceGraph.tokenIsEntityHead[tJ] == None:
#                    continue
#                if paths.has_key(tI) and paths[tI].has_key(tJ):
#                    path = paths[tI][tJ]
#                    if not pathsBetweenAllEntitiesByLength.has_key(len(path)-1):
#                        pathsBetweenAllEntitiesByLength[len(path)-1] = 0
#                    pathsBetweenAllEntitiesByLength[len(path)-1] += 1
#                else:
#                    if not pathsBetweenAllEntitiesByLength.has_key("none"):
#                        pathsBetweenAllEntitiesByLength["none"] = 0
#                    pathsBetweenAllEntitiesByLength["none"] += 1
    
    print >> sys.stderr, "Interaction edges:", interactionEdges
    print >> sys.stderr, "Dependency edges:", dependencyEdges
    print >> sys.stderr, "Shortest path of dependencies for interaction edge:"
    printPathDistribution(pathsByLength)
    if options.output != None:
        pathsByLength["corpus"] = options.input
        pathsByLength["parse"] = options.parse
        TableUtils.addToCSV(pathsByLength, options.output+"/pathsByLength.csv")
    print >> sys.stderr, "Shortest path of dependencies between all entities:"
    printPathDistribution(pathsBetweenAllEntitiesByLength)
    if options.output != None:
        pathsByLength["corpus"] = options.input
        pathsByLength["parse"] = options.parse
        TableUtils.addToCSV(pathsBetweenAllEntitiesByLength, options.output+"/pathsBetweenAllEntitiesByLength.csv")

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
    nonParallelEdgesByType = {}
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
            elif len(types) == 1:
                if not nonParallelEdgesByType.has_key(types[0]):
                    nonParallelEdgesByType[types[0]] = 0
                nonParallelEdgesByType[types[0]] += 1
    types = parallelEdgesByType.keys()
    types.sort()
    print >> sys.stderr, "Parallel edges:"
    print >> sys.stderr, "  Total:", total, "Circular:", circular
    for type in types:
        print >> sys.stderr, "  " + str(type) + ": " + str(parallelEdgesByType[type][0]) + " (circular: " + str(parallelEdgesByType[type][1]) + ")"

    types = nonParallelEdgesByType.keys()
    types.sort()
    print >> sys.stderr, "Non-Parallel edges:"
    for type in types:
        print >> sys.stderr, "  " + str(type) + ": " + str(nonParallelEdgesByType[type])

def listEntities(corpusElements):
    entitiesByType = {}
    for sentence in corpusElements.sentences:
        sentenceGraph = sentence.sentenceGraph
        for entity in sentenceGraph.entities:
            type = entity.attrib["type"]
            if not entitiesByType.has_key(type):
                entitiesByType[type] = [0,0,{}]
            entitiesByType[type][0] += 1
            if not entitiesByType[type][2].has_key(entity.get("text")):
                entitiesByType[type][2][entity.get("text")] = 0
            entitiesByType[type][2][entity.get("text")] += 1
            if entity.attrib["isName"] == "True":
                entitiesByType[type][1] += 1
    keys = entitiesByType.keys()
    keys.sort()
    print >> sys.stderr, "Entities (all, named):"
    for k in keys:
        print >> sys.stderr, "  " + k + ": " + str(entitiesByType[k][0]) + ", " + str(entitiesByType[k][1])
        texts = entitiesByType[k][2].keys()
        texts.sort()
        for text in texts:
            print >> sys.stderr, "    " + text + "    (" + str(entitiesByType[k][2][text]) + ")"

def listStructures(corpusElements):
    interactionEdges = 0
    dependencyEdges = 0
    
    structures = {}
    for sentence in corpusElements.sentences:
        sentenceGraph = sentence.sentenceGraph
        #interactionEdges += len(sentenceGraph.interactionGraph.edges())
        interactionEdges += len(sentence.interactions)
        dependencyEdges += len(sentenceGraph.dependencyGraph.edges())
        
        undirected = sentenceGraph.dependencyGraph.to_undirected()
        paths = NX.all_pairs_shortest_path(undirected, cutoff=999)
        # Shortest path for interaction edge
        for interaction in sentence.interactions:
            e1 = sentence.entitiesById[interaction.attrib["e1"]]
            e2 = sentence.entitiesById[interaction.attrib["e2"]]
            t1 = sentenceGraph.entityHeadTokenByEntity[e1]
            t2 = sentenceGraph.entityHeadTokenByEntity[e2]
            if paths.has_key(t1) and paths[t1].has_key(t2):
                path = paths[t1][t2]
                prevToken = None
                structure = ""
                for pathToken in path:
                    if prevToken != None:
                        if sentenceGraph.dependencyGraph.has_edge(prevToken,pathToken):
                            structure += ">" + sentenceGraph.dependencyGraph.get_edge(prevToken,pathToken)[0].attrib["type"] + ">"
                        elif sentenceGraph.dependencyGraph.has_edge(pathToken,prevToken):
                            structure += "<" + sentenceGraph.dependencyGraph.get_edge(pathToken,prevToken)[0].attrib["type"] + "<"
                        else:
                            assert(False)
                    structure += pathToken.attrib["POS"][0:1]
                    prevToken = pathToken
                
                if not structures.has_key(structure):
                    structures[structure] = {}
                if not structures[structure].has_key(interaction.attrib["type"]):
                    structures[structure][interaction.attrib["type"]] = 0
                structures[structure][interaction.attrib["type"]] += 1
    
    print >> sys.stderr, "Structures"
    #keys = sorted(structures.keys())
    for s in sorted(structures.keys()):
        print >> sys.stderr, s + ":"
        for i in sorted(structures[s].keys()):
            print >> sys.stderr, "  " + i + ": " + str(structures[s][i])

if __name__=="__main__":
    defaultAnalysisFilename = "/usr/share/biotext/ComplexPPI/BioInferForComplexPPIVisible_noCL.xml"
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=defaultAnalysisFilename, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-t", "--tokenization", default="split_gs", dest="tokenization", help="tokenization")
    optparser.add_option("-p", "--parse", default="split_gs", dest="parse", help="parse")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output-folder")
    optparser.add_option("-a", "--analyses", default="", dest="analyses", help="selected optional analyses")
    (options, args) = optparser.parse_args()

    if options.output != None:
        if os.path.exists(options.output):
            print >> sys.stderr, "Output directory exists, removing", options.output
            shutil.rmtree(options.output)
        os.makedirs(options.output)
    
    corpusElements = SentenceGraph.loadCorpus(options.input, options.parse, options.tokenization)
    print >> sys.stderr, "tokenization:", options.tokenization
    print >> sys.stderr, "parse:", options.parse
    
    calculateMainStatistics(corpusElements)
    analyzeLengths(corpusElements)
    countMultipleEdges(corpusElements)
    if options.analyses.find("entities") != -1:
        listEntities(corpusElements)
    if options.analyses.find("structures") != -1:
        listStructures(corpusElements)
    if options.analyses.find("linear_distance") != -1:
        analyzeLinearDistance(corpusElements)
