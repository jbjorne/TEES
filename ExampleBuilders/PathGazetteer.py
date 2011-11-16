import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
import Core.ExampleBuilder
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from FeatureBuilders.MultiEdgeFeatureBuilder import MultiEdgeFeatureBuilder
from Core.Gazetteer import Gazetteer
from Utils.ProgressCounter import ProgressCounter
#import networkx as NX
import Graph.networkx_v10rc1 as NX10
import combine

class PathGazetteer(ExampleBuilder):
    def __init__(self, includeNeg=False):
        self.multiEdgeFeatureBuilder = MultiEdgeFeatureBuilder(None)
        self.gazetteer = {}
        self.includeNeg = includeNeg
    
    @classmethod
    def build(cls, input, output, parse, tokenization=None, includeNeg=False):
        p = PathGazetteer(includeNeg)
        sentences = cls.getSentences(input, parse, tokenization)
        
        counter = ProgressCounter(len(sentences), "Build path gazetteer")
        for sentence in sentences:
            counter.update(1, "Building path gazetteer ("+sentence[0].getSentenceId()+"): ")
            p.processSentence(sentence[0])
        p.calculateFractions()
        
        f = open(output, "wt")
        for key in sorted(p.gazetteer.keys()):
            v = p.gazetteer[key]
            f.write(key + " " + str(v[0]) + " " + str(v[1]) + " " + str(v[2]) + " " + str(v[3]) + "\n")
        f.close()
    
    @classmethod
    def load(cls, filename):
        gazetteer = {}
        f = open(filename, "rt")
        for line in f.readlines():
            splits = line.split()
            gazetteer[splits[0]] = (splits[1], splits[2], splits[3], splits[4])
        f.close()
        return gazetteer
    
    @classmethod
    def getDependencies(cls, gazetteer):
        dependencies = set()
        for k in gazetteer.keys():
            k = k.strip()
            k = k.replace("<","")
            k = k.replace(">","")
            for dep in k.split("."):
                dependencies.add(dep)
        return dependencies
    
    @classmethod
    def getPairs(self, gazetteer):
        pairs = []
        for k in gazetteer.keys():
            k = k.strip()
            k = k.replace("<","")
            k = k.replace(">","")
            splits = k.split(".")
            pairs.append( (splits[0], splits[-1]) )
        return pairs
    
    def calculateFractions(self):
        numInstances = 0
        numPos = 0
        numNeg = 0
        for v in self.gazetteer.values():
            numInstances += v[2] + v[3]
            numPos += v[2]
            numNeg += v[3]
        print >> sys.stderr, "Total paths:", numInstances
        print >> sys.stderr, "Positives:", numPos
        print >> sys.stderr, "Negatives:", numNeg
        
        for v in self.gazetteer.values():
            assert v[0] == None and v[1] == None
            if v[3] == None:
                assert v[2] != None
                v[0] = 1
            else:
                v[0] = float(v[2]) / float(v[2] + v[3])
            v[1] = float(v[2] + v[3]) / float(numInstances)

    def nxMultiDiGraphToUndirected(self, graph):
        undirected = NX10.MultiGraph(name=graph.name)
        undirected.add_nodes_from(graph)
        undirected.add_edges_from(graph.edges_iter())
        return undirected
                        
    def processSentence(self, sentenceGraph):        
        #undirected = sentenceGraph.dependencyGraph.to_undirected()
        undirected = self.nxMultiDiGraphToUndirected(sentenceGraph.dependencyGraph)
        paths = NX10.all_pairs_shortest_path(undirected, cutoff=999)
        self.multiEdgeFeatureBuilder.setFeatureVector()
        
        positivePaths = {} # per sentence, a path may still be negative in another sentence
        for interaction in sentenceGraph.interactions:
            e1 = sentenceGraph.entitiesById[interaction.get("e1")]
            e1Token = sentenceGraph.entityHeadTokenByEntity[e1]
            e2 = sentenceGraph.entitiesById[interaction.get("e2")]
            e2Token = sentenceGraph.entityHeadTokenByEntity[e2]
            
            if paths.has_key(e1Token) and paths[e1Token].has_key(e2Token):
                if not positivePaths.has_key(e1Token): 
                    positivePaths[e1Token] = {}
                positivePaths[e1Token][e2Token] = True
                
                path = paths[e1Token][e2Token]
                for comb in self.multiEdgeFeatureBuilder.getEdgeCombinations(sentenceGraph.dependencyGraph, path):
                    if not self.gazetteer.has_key(comb):
                        self.gazetteer[comb] = [None,None,0,0]
                    self.gazetteer[comb][2] += 1
        
        if self.includeNeg:
            for t1 in sentenceGraph.tokens:
                for t2 in sentenceGraph.tokens:
                    if t1 == t2:
                        continue
                    if positivePaths.has_key(t1) and positivePaths[t1].has_key(t2):
                        continue
                    
                    if paths.has_key(t1) and paths[t1].has_key(t2):
                        path = paths[t1][t2]
                        for comb in self.multiEdgeFeatureBuilder.getEdgeCombinations(sentenceGraph.dependencyGraph, path):
                            if not self.gazetteer.has_key(comb):
                                self.gazetteer[comb] = [None,None,0,0]
                            self.gazetteer[comb][3] += 1
