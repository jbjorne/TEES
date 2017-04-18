import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
from ExampleBuilder import ExampleBuilder
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils

class KerasExampleBuilder(ExampleBuilder):
    def __init__(self, style=None, classSet=None, featureSet=None, gazetteerFileName=None, skiplist=None):
        if classSet == None:
            classSet = IdSet(1)
        if featureSet == None:
            featureSet = IdSet()
        
        ExampleBuilder.__init__(self, classSet, featureSet)
    
    def processSentence(self, sentence, outfile, goldSentence=None, structureAnalyzer=None):
        #return ExampleBuilder.processSentence(self, sentence, outfile, goldSentence=goldSentence, structureAnalyzer=structureAnalyzer)
    
    def buildExamplesFromGraph(self, sentenceGraph, outfile, goldGraph = None, structureAnalyzer=None):
        """
        Build examples for a single sentence. Returns a list of examples.
        See Core/ExampleUtils for example format.
        """
        #examples = []
        exampleIndex = 0
        # example directionality
        if self.styles["directed"] == None and self.styles["undirected"] == None: # determine directedness from corpus
            examplesAreDirected = structureAnalyzer.hasDirectedTargets()
        elif self.styles["directed"]:
            assert self.styles["undirected"] in [None, False]
            examplesAreDirected = True
        elif self.styles["undirected"]:
            assert self.styles["directed"] in [None, False]
            examplesAreDirected = False
        
        if not self.styles["no_trigger_features"]: 
            self.triggerFeatureBuilder.initSentence(sentenceGraph)
        if self.styles["evex"]: 
            self.evexFeatureBuilder.initSentence(sentenceGraph)
#         if self.styles["sdb_merge"]:
#             self.determineNonOverlappingTypes(structureAnalyzer)
            
        # Filter entities, if needed
        sentenceGraph.mergeInteractionGraph(True)
        entities = sentenceGraph.mergedEntities
        entityToDuplicates = sentenceGraph.mergedEntityToDuplicates
        self.exampleStats.addValue("Duplicate entities skipped", len(sentenceGraph.entities) - len(entities))
        
        # Connect to optional gold graph
        entityToGold = None
        if goldGraph != None:
            entityToGold = EvaluateInteractionXML.mapEntities(entities, goldGraph.entities)
        
        paths = None
        if not self.styles["no_path"]:
            undirected = sentenceGraph.dependencyGraph.toUndirected()
            paths = undirected
            if self.styles["filter_shortest_path"] != None: # For DDI use filter_shortest_path=conj_and
                paths.resetAnalyses() # just in case
                paths.FloydWarshall(self.filterEdge, {"edgeTypes":self.styles["filter_shortest_path"]})
        
        # Generate examples based on interactions between entities or interactions between tokens
        numTokens = len(sentenceGraph.tokens)
        matrix = []
        dim = 30
        for i in range(dim):
            matrix.append([])
            for j in range(dim):
                features = {}
                if dim >= numTokens:
                    pass #features[self.featureSet.getId("padding")] = 1
                elif i == j: # diagonal
                    token = sentenceGraph.tokens[i]
                    features[self.featureSet.getId(token.get("POS"))] = 1
                matrix[-1].append(features)
                eI = None
                eJ = None
                tI = sentenceGraph.tokens[i]
                tJ = sentenceGraph.tokens[j]
                # only consider paths between entities (NOTE! entities, not only named entities)
                if self.styles["headsOnly"]:
                    if (len(sentenceGraph.tokenIsEntityHead[tI]) == 0) or (len(sentenceGraph.tokenIsEntityHead[tJ]) == 0):
                        continue
                
                examples = self.buildExamplesForPair(tI, tJ, paths, sentenceGraph, goldGraph, entityToGold, eI, eJ, structureAnalyzer, examplesAreDirected)
                for categoryName, features, extra in examples:
                    # make example
                    if self.styles["binary"]:
                        if categoryName != "neg":
                            category = 1
                        else:
                            category = -1
                        extra["categoryName"] = "i"
                    else:
                        category = self.classSet.getId(categoryName)
                    example = [sentenceGraph.getSentenceId()+".x"+str(exampleIndex), category, features, extra]
                    ExampleUtils.appendExamples([example], outfile)
                    exampleIndex += 1

        return exampleIndex