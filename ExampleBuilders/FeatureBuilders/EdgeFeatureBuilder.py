"""
Dependency edge features
"""
__version__ = "$Revision: 1.3 $"

from FeatureBuilder import FeatureBuilder
#import Stemming.PorterStemmer as PorterStemmer

class EdgeFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet):
        FeatureBuilder.__init__(self, featureSet)
    
    def buildEdgeFeatures(self, depEdge, sentenceGraph, tag = "dep_", text=True, POS=True, annType=True, maskNames=True):
        self.features[self.featureSet.getId(tag+depEdge[2].attrib["type"])] = 1
        if text:
            if maskNames:
                self.features[self.featureSet.getId(tag+"t1txt_"+sentenceGraph.getTokenText(depEdge[0]))] = 1
                self.features[self.featureSet.getId(tag+"t2txt_"+sentenceGraph.getTokenText(depEdge[1]))] = 1
            else:
                self.features[self.featureSet.getId(tag+"t1txt_"+depEdge[0].attrib["text"])] = 1
                self.features[self.featureSet.getId(tag+"t2txt_"+depEdge[1].attrib["text"])] = 1
        #features[self.featureSet.getId("t1stem_"+PorterStemmer.stem(sentenceGraph.getTokenText(depEdge[0])))] = 1
        #features[self.featureSet.getId("t2stem_"+PorterStemmer.stem(sentenceGraph.getTokenText(depEdge[1])))] = 1
        if POS:
            self.features[self.featureSet.getId(tag+"POS_"+depEdge[0].attrib["POS"])] = 1
            self.features[self.featureSet.getId(tag+"POS_"+depEdge[1].attrib["POS"])] = 1
            self.features[self.featureSet.getId(tag+"t1POS_"+depEdge[0].attrib["POS"])] = 1
            self.features[self.featureSet.getId(tag+"t2POS_"+depEdge[1].attrib["POS"])] = 1
            
        if annType:
            if sentenceGraph.tokenIsEntityHead[depEdge[0]] != None:
                self.features[self.featureSet.getId(tag+"annType_"+sentenceGraph.tokenIsEntityHead[depEdge[0]].attrib["type"])] = 1
                self.features[self.featureSet.getId(tag+"t1AnnType_"+sentenceGraph.tokenIsEntityHead[depEdge[0]].attrib["type"])] = 1
            if sentenceGraph.tokenIsEntityHead[depEdge[1]] != None:
                self.features[self.featureSet.getId(tag+"annType_"+sentenceGraph.tokenIsEntityHead[depEdge[1]].attrib["type"])] = 1
                self.features[self.featureSet.getId(tag+"t2AnnType_"+sentenceGraph.tokenIsEntityHead[depEdge[1]].attrib["type"])] = 1
    
    def buildTerminusFeatures(self, token, sentenceGraph, prefix = "term", text=True, POS=True, annType=True, maskNames=True):
        inEdges = sentenceGraph.dependencyGraph.in_edges(token)
        for edge in inEdges:
            self.features[self.featureSet.getId(prefix+"HangingIn_"+edge[2].attrib["type"])] = 1
            if POS: self.features[self.featureSet.getId(prefix+"HangingIn_"+edge[0].attrib["POS"])] = 1
            if annType and sentenceGraph.tokenIsEntityHead[edge[0]] != None:
                self.features[self.featureSet.getId(prefix+"HangingIn_AnnType_"+sentenceGraph.tokenIsEntityHead[edge[0]].attrib["type"])] = 1
            if text:
                if maskNames: self.features[self.featureSet.getId(prefix+"HangingIn_"+sentenceGraph.getTokenText(edge[0]))] = 1
                else: self.features[self.featureSet.getId(prefix+"HangingIn_"+edge[0].attrib["text"])] = 1
        outEdges = sentenceGraph.dependencyGraph.out_edges(token)
        for edge in outEdges:
            self.features[self.featureSet.getId(prefix+"HangingOut_"+edge[2].attrib["type"])] = 1
            if POS: self.features[self.featureSet.getId(prefix+"HangingOut_"+edge[1].attrib["POS"])] = 1
            if annType and sentenceGraph.tokenIsEntityHead[edge[1]] != None:
                self.features[self.featureSet.getId(prefix+"HangingOut_AnnType_"+sentenceGraph.tokenIsEntityHead[edge[1]].attrib["type"])] = 1
            if text:
                if maskNames: self.features[self.featureSet.getId(prefix+"HangingOut_"+sentenceGraph.getTokenText(edge[1]))] = 1
                else: self.features[self.featureSet.getId(prefix+"HangingOut_"+edge[1].attrib["text"])] = 1
    
    def buildAttachedEdgeFeatures(self, depEdge, sentenceGraph, tag = "", text=True, POS=True, annType=True, maskNames=True):
        self.buildTerminusFeatures(depEdge[0], sentenceGraph, prefix = tag+"t1", text=text, POS=POS, annType=annType, maskNames=maskNames)
        self.buildTerminusFeatures(depEdge[1], sentenceGraph, prefix = tag+"t2", text=text, POS=POS, annType=annType, maskNames=maskNames)
        return
                
    def buildLinearOrderFeatures(self, depEdge):
        t1Position = int(depEdge[0].attrib["id"].split("_")[-1])
        t2Position = int(depEdge[1].attrib["id"].split("_")[-1])
        self.features[self.featureSet.getId("lin_distance")] = t2Position - t1Position

        if t1Position < t2Position:
            self.features[self.featureSet.getId("lin_forward")] = 1
            self.features[self.featureSet.getId("lin_distance")] = abs(t2Position - t1Position)
            #features[self.featureSet.getId("l1txt_"+sentenceGraph.getTokenText(depEdge[0]))] = 1
            #features[self.featureSet.getId("l1POS_"+depEdge[0].attrib["POS"])] = 1
            #features[self.featureSet.getId("l2txt_"+sentenceGraph.getTokenText(depEdge[1]))] = 1
            #features[self.featureSet.getId("l2POS_"+depEdge[1].attrib["POS"])] = 1
        else:
            self.features[self.featureSet.getId("lin_reverse")] = 1
            self.features[self.featureSet.getId("lin_distance")] = abs(t2Position - t1Position)
            #features[self.featureSet.getId("l2txt_"+sentenceGraph.getTokenText(depEdge[0]))] = 1
            #features[self.featureSet.getId("l2POS_"+depEdge[0].attrib["POS"])] = 1
            #features[self.featureSet.getId("l1txt_"+sentenceGraph.getTokenText(depEdge[1]))] = 1
            #features[self.featureSet.getId("l1POS_"+depEdge[1].attrib["POS"])] = 1

