import sys
sys.path.append("..")
from Core.ExampleBuilder import ExampleBuilder
import Core.ExampleBuilder
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from FeatureBuilders.MultiEdgeFeatureBuilder import MultiEdgeFeatureBuilder
from Core.Gazetteer import Gazetteer
from Utils.ProgressCounter import ProgressCounter
import networkx as NX
import combine

class PathGazetteer(ExampleBuilder):
    def __init__(self):
        self.multiEdgeFeatureBuilder = MultiEdgeFeatureBuilder(None)
        self.gazetteer = set()
    
    @classmethod
    def build(cls, input, output, parse, tokenization=None):
        p = PathGazetteer()
        sentences = cls.getSentences(input, parse, tokenization)
        
        counter = ProgressCounter(len(sentences), "Build path gazetteer")
        for sentence in sentences:
            counter.update(1, "Building path gazetteer ("+sentence[0].getSentenceId()+"): ")
            p.processSentence(sentence[0])
        
        f = open(output, "wt")
        for string in sorted(list(p.gazetteer)):
            f.write(string + "\n")
        f.close()
    
    @classmethod
    def load(cls, filename):
        gazetteer = set()
        f = open(filename, "rt")
        for line in f.readlines():
            gazetteer.add(line.strip())
        f.close()
        return gazetteer
                        
    def processSentence(self, sentenceGraph):        
        undirected = sentenceGraph.dependencyGraph.to_undirected()
        paths = NX.all_pairs_shortest_path(undirected, cutoff=999)
        self.multiEdgeFeatureBuilder.setFeatureVector()
        
        for interaction in sentenceGraph.interactions:
            e1 = sentenceGraph.entitiesById[interaction.get("e1")]
            e1Token = sentenceGraph.entityHeadTokenByEntity[e1]
            e2 = sentenceGraph.entitiesById[interaction.get("e2")]
            e2Token = sentenceGraph.entityHeadTokenByEntity[e2]
            
            if paths.has_key(e1Token) and paths[e1Token].has_key(e2Token):
                path = paths[e1Token][e2Token]
                for comb in self.multiEdgeFeatureBuilder.getEdgeCombinations(sentenceGraph.dependencyGraph, path):
                    self.gazetteer.add(comb)