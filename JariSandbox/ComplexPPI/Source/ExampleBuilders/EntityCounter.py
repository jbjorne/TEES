import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
from Core.ExampleBuilder import ExampleBuilder
import Core.ExampleBuilder
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from FeatureBuilders.MultiEdgeFeatureBuilder import MultiEdgeFeatureBuilder
import cElementTreeUtils as ETUtils
#import Graph.networkx_v10rc1 as NX10

class EntityCounter(ExampleBuilder):
    def __init__(self, style=["typed","directed","headsOnly"], length=None, types=[], featureSet=None, classSet=None):
        if featureSet == None:
            featureSet = IdSet()
        if classSet == None:
            classSet = IdSet(1)
        else:
            classSet = classSet
        assert( classSet.getId("neg") == 1 )
        
        ExampleBuilder.__init__(self, classSet=classSet, featureSet=featureSet)
        self.styles = style
        
        self.multiEdgeFeatureBuilder = MultiEdgeFeatureBuilder(self.featureSet)
        
        self.counts = {}
        self.countsPerType = {}
        self.untypedCounts = {}
        self.tokenCounts = {}

    @classmethod
    def run(cls, input, output, parse, tokenization, style, idFileTag=None):
        classSet = None
        featureSet = None
        if idFileTag != None:
            classSet, featureSet = cls.getIdSets(idFileTag)
        e = EntityCounter(style=style, classSet=classSet, featureSet=featureSet)
        sentences = cls.getSentences(input, parse, tokenization)
        e.buildExamplesForSentences(sentences, output, idFileTag)
        print "Duplicate entity counts: ", e.counts
        print "Duplicate entity counts (untyped): ", e.untypedCounts
        print "Per type"
        for type in sorted(e.countsPerType.keys()):
            print "  ", type, e.countsPerType[type]
        print "Token counts: ", e.tokenCounts
    
    def nxMultiDiGraphToUndirected(self, graph):
        undirected = NX10.MultiGraph(name=graph.name)
        undirected.add_nodes_from(graph)
        undirected.add_edges_from(graph.edges_iter())
        return undirected
    
    #def buildExamples(self, sentenceGraph):
        
    
    def buildExamples(self, sentenceGraph):
        examples = []
        exampleIndex = 0
        if not self.tokenCounts.has_key(len(sentenceGraph.tokens)):
            self.tokenCounts[len(sentenceGraph.tokens)] = 0
        self.tokenCounts[len(sentenceGraph.tokens)] += 1
        for token in sentenceGraph.tokens:
            entityCounts = {}
            for entity in sentenceGraph.tokenIsEntityHead[token]:
                t = entity.get("type")
                if not entityCounts.has_key(t): entityCounts[t] = 0
                entityCounts[t] += 1
            for k,v in entityCounts.iteritems():
                if not self.counts.has_key(v): self.counts[v] = 0
                self.counts[v] += 1
                # per type
                if not self.countsPerType.has_key(k): self.countsPerType[k] = {}
                if not self.countsPerType[k].has_key(v): self.countsPerType[k][v] = 0
                self.countsPerType[k][v] += 1 
            
            numEntities = len(sentenceGraph.tokenIsEntityHead[token])
            if not self.untypedCounts.has_key(numEntities): self.untypedCounts[numEntities] = 0
            self.untypedCounts[numEntities] += 1
            #count = len(sentenceGraph.tokenIsEntityHead[token])
            #if not self.counts.has_key(count): self.counts[count] = 0
            #self.counts[count] += 1
            if max(entityCounts.values() + [0]) >= 8:
                print "======================================"
                print "Entity", token.get("id")
                for e in sentenceGraph.tokenIsEntityHead[token]:
                    print ETUtils.toStr(e)
                print "======================================"
        
        return []
        
#        for entity in sentenceGraph.entities:
#            if entity
            
        
#        #undirected = sentenceGraph.getUndirectedDependencyGraph()
#        undirected = self.nxMultiDiGraphToUndirected(sentenceGraph.dependencyGraph)
#        ##undirected = sentenceGraph.dependencyGraph.to_undirected()
#        ###undirected = NX10.MultiGraph(sentenceGraph.dependencyGraph) This didn't work
#        paths = NX10.all_pairs_shortest_path(undirected, cutoff=999)
#        
#        # Generate examples based on interactions between entities or interactions between tokens
#        if "entities" in self.styles:
#            loopRange = len(sentenceGraph.entities)
#        else:
#            loopRange = len(sentenceGraph.tokens)
#        for i in range(loopRange-1):
#            for j in range(i+1,loopRange):
#                eI = None
#                eJ = None
#                if "entities" in self.styles:
#                    eI = sentenceGraph.entities[i]