"""
Edge Examples
"""
__version__ = "$Revision: 1.1 $"

import sys, os
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath,"..")))
from Core.ExampleBuilder import ExampleBuilder
import Core.ExampleBuilder
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
from FeatureBuilders.MultiEdgeFeatureBuilder import MultiEdgeFeatureBuilder
from Core.SimpleGraph import Graph
from FeatureBuilders.TriggerFeatureBuilder import TriggerFeatureBuilder

def findAminoAcid(string):
    global aminoAcids

    string = string.lower()
    for aa in aminoAcids:
        word = string.find(aa[0])
        if word != -1:
            return word, aa
        else:
            tlc = string.find(aa[1]) # three letter code
            if tlc != -1:
                # Three letter code must not be a part of a word (where it could be just a substring)
                if (tlc == 0 or not string[tlc-1].isalpha()) and (tlc + 3 >= len(string) or not string[tlc + 3].isalpha()):
                    return tlc, aa
    return -1, None

def buildAminoAcidFeatures(string):
    index, aa = findAminoAcid(string)
    if aa != None:
        self.setFeature("aminoacid_string")
        self.setFeature("aminoacid_" + aa[1])

# Amino acids from http://www.bio.davidson.edu/courses/genomics/jmol/aatable.html
#amino acid     three letter code     single letter code

aminoAcids = [
    #nonpolar (hydrophobic)
    ("glycine", "gly", "g", "nonpolar", "neutral"), 
    ("alanine", "ala", "a", "nonpolar", "neutral"),
    ("valine", "val", "v", "nonpolar", "neutral"),
    ("leucine", "leu", "l", "nonpolar", "neutral"),
    ("isoleucine", "ile", "i", "nonpolar", "neutral"),
    ("methionine", "met", "m", "nonpolar", "neutral"),
    ("phenylalanine", "phe", "f", "nonpolar", "neutral"),
    ("tryptophan", "trp", "w", "nonpolar", "neutral"),
    ("proline", "pro", "p", "nonpolar", "neutral"), 
    #polar (hydrophilic)
    ("serine", "ser", "s", "hydrophilic", "neutral"),
    ("threonine", "thr", "t", "hydrophilic", "neutral"),
    ("cysteine", "cys", "c", "hydrophilic", "neutral"),
    ("tyrosine", "tyr", "y", "hydrophilic", "neutral"),
    ("asparagine", "asn", "n", "hydrophilic", "neutral"),
    ("glutamine", "gln", "q", "hydrophilic", "neutral"),
    #electrically charged (negative and hydrophilic)
    ("aspartic acid", "asp", "d", "hydrophilic", "negative"),
    ("glutamic acid", "glu", "e", "hydrophilic", "negative"),
    #electrically charged (positive and hydrophilic)
    ("lysine", "lys", "k", "hydrophilic", "positive"),
    ("arginine", "arg", "r", "hydrophilic", "positive"),
    ("histidine", "his", "h", "hydrophilic", "positive")]


class EntityRelationExampleBuilder(ExampleBuilder):
    """
    BioNLP'11 REL subtask examples
    """
    def __init__(self, style=["typed","directed","headsOnly"], featureSet=None, classSet=None):
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
        #if "noAnnType" in self.styles:
        self.multiEdgeFeatureBuilder.noAnnType = True
        #if "noMasking" in self.styles:
        self.multiEdgeFeatureBuilder.maskNamedEntities = False
        #if "maxFeatures" in self.styles:
        self.multiEdgeFeatureBuilder.maximum = True
        self.triggerFeatureBuilder = TriggerFeatureBuilder(self.featureSet)
        self.triggerFeatureBuilder.useNonNameEntities = False

    @classmethod
    def run(cls, input, output, parse, tokenization, style, idFileTag=None):
        """
        An interface for running the example builder without needing to create a class
        """
        classSet, featureSet = cls.getIdSets(idFileTag)
        if style != None:
            e = EntityRelationExampleBuilder(style=style, classSet=classSet, featureSet=featureSet)
        else:
            e = EntityRelationExampleBuilder(classSet=classSet, featureSet=featureSet)
        sentences = cls.getSentences(input, parse, tokenization)
        e.buildExamplesForSentences(sentences, output, idFileTag)
    
    def getCategoryNameFromTokens(self, sentenceGraph, t1, t2, directed=True):
        """
        Example class. Multiple overlapping edges create a merged type.
        """
        types = set()
        intEdges = sentenceGraph.interactionGraph.getEdges(t1, t2)
        if (not directed):
            intEdges = intEdges + sentenceGraph.interactionGraph.getEdges(t2, t1)
        for intEdge in intEdges:
            types.add(intEdge[2].get("type"))
        types = list(types)
        types.sort()
        categoryName = ""
        for name in types:
            if categoryName != "":
                categoryName += "---"
            categoryName += name
        if categoryName != "":
            return categoryName
        else:
            return "neg"
    
#    def isPotentialTargetEntityHead(self, namedEntityToken, token):
#        if token.get("POS") in ["CD","JJ","NN","NNS","RB"]:
#            return True
#        else:
#            return False
            
    def buildExamples(self, sentenceGraph):
        """
        Build examples for a single sentence. Returns a list of examples.
        See Core/ExampleUtils for example format.
        """
        examples = []
        exampleIndex = 0
        
        if "trigger_features" in self.styles: 
            self.triggerFeatureBuilder.initSentence(sentenceGraph)
        
        undirectedDepGraph = sentenceGraph.dependencyGraph.toUndirected()
        
        namedEntities = []
        for entity in sentenceGraph.entities:
            if entity.get("isName") == "True":
                namedEntities.append(entity)
        
        potentialTargetEntities = {}
        for i in range(len(sentenceGraph.tokens)):
            potentialTargetEntities[i] = sentenceGraph.tokens[i].get("POS") in ["CD","JJ","NN","NNS","RB"]

        for namedEntity in namedEntities:
            for i in range(len(sentenceGraph.tokens)):
                if not potentialTargetEntities[i]:
                    continue
                namedEntityToken = sentenceGraph.entityHeadTokenByEntity[namedEntity]
                token = sentenceGraph.tokens[i]
                categoryName = self.getCategoryNameFromTokens(sentenceGraph, namedEntityToken, token, True)
                #if (not "genia_limits" in self.styles) or self.isPotentialRelation(namedEntityToken, token):
                examples.append( self.buildExample(entity, i, undirectedDepGraph, sentenceGraph, categoryName, exampleIndex) )
                exampleIndex += 1
        
        return examples
    
    def buildExample(self, namedEntity, tokenIndex, undirectedDepGraph, sentenceGraph, categoryName, exampleIndex):
        """
        Build a single directed example for the potential edge between token1 and token2
        """
        namedEntityToken = sentenceGraph.entityHeadTokenByEntity[namedEntity]
        token = sentenceGraph.tokens[tokenIndex]
        # define features
        features = {}
        paths = undirectedDepGraph.getPaths(namedEntityToken, token)
        if len(paths) > 0:
            path = paths[0]
        else:
            path = [namedEntityToken, token]
        if "trigger_features" in self.styles:
            self.triggerFeatureBuilder.setFeatureVector(features)
            self.triggerFeatureBuilder.tag = "trg1_"
            self.triggerFeatureBuilder.buildFeatures(namedEntityToken)
            self.triggerFeatureBuilder.tag = "trg2_"
            self.triggerFeatureBuilder.buildFeatures(token)
            self.triggerFeatureBuilder.setFeatureVector(None)
        if not "no_dependency" in self.styles:
            #print "Dep features"
            self.multiEdgeFeatureBuilder.setFeatureVector(features, None, None)
            #self.multiEdgeFeatureBuilder.buildStructureFeatures(sentenceGraph, paths) # remove for fast
            if not "disable_entity_features" in self.styles:
                self.multiEdgeFeatureBuilder.buildEntityFeatures(sentenceGraph)
            self.multiEdgeFeatureBuilder.buildPathLengthFeatures(path)
            if not "disable_terminus_features" in self.styles:
                self.multiEdgeFeatureBuilder.buildTerminusTokenFeatures(path, sentenceGraph) # remove for fast
            if not "disable_single_element_features" in self.styles:
                self.multiEdgeFeatureBuilder.buildSingleElementFeatures(path, sentenceGraph)
            if not "disable_ngram_features" in self.styles:
                #print "NGrams"
                self.multiEdgeFeatureBuilder.buildPathGrams(2, path, sentenceGraph) # remove for fast
                self.multiEdgeFeatureBuilder.buildPathGrams(3, path, sentenceGraph) # remove for fast
                self.multiEdgeFeatureBuilder.buildPathGrams(4, path, sentenceGraph) # remove for fast
            #self.buildEdgeCombinations(path, edges, sentenceGraph, features) # remove for fast
            #if edges != None:
            #    self.multiEdgeFeatureBuilder.buildTerminusFeatures(path[0], edges[0][1]+edges[1][0], "t1", sentenceGraph) # remove for fast
            #    self.multiEdgeFeatureBuilder.buildTerminusFeatures(path[-1], edges[len(path)-1][len(path)-2]+edges[len(path)-2][len(path)-1], "t2", sentenceGraph) # remove for fast
            if not "disable_path_edge_features" in self.styles:
                self.multiEdgeFeatureBuilder.buildPathEdgeFeatures(path, sentenceGraph)
            self.multiEdgeFeatureBuilder.buildSentenceFeatures(sentenceGraph)
            self.multiEdgeFeatureBuilder.setFeatureVector(None)
        if not "no_linear" in self.styles:
            self.tokenFeatureBuilder.setFeatureVector(features)
            for i in range(len(sentenceGraph.tokens)):
                if sentenceGraph.tokens[i] == token1:
                    token1Index = i
                if sentenceGraph.tokens[i] == token2:
                    token2Index = i
            linearPreTag = "linfw_"
            if token1Index > token2Index: 
                token1Index, token2Index = token2Index, token1Index
                linearPreTag = "linrv_"
            self.tokenFeatureBuilder.buildLinearOrderFeatures(token1Index, sentenceGraph, 2, 2, preTag="linTok1")
            self.tokenFeatureBuilder.buildLinearOrderFeatures(token2Index, sentenceGraph, 2, 2, preTag="linTok2")
            # Before, middle, after
#                self.tokenFeatureBuilder.buildTokenGrams(0, token1Index-1, sentenceGraph, "bf")
#                self.tokenFeatureBuilder.buildTokenGrams(token1Index+1, token2Index-1, sentenceGraph, "bw")
#                self.tokenFeatureBuilder.buildTokenGrams(token2Index+1, len(sentenceGraph.tokens)-1, sentenceGraph, "af")
            # before-middle, middle, middle-after
#                    self.tokenFeatureBuilder.buildTokenGrams(0, token2Index-1, sentenceGraph, linearPreTag+"bf", max=2)
#                    self.tokenFeatureBuilder.buildTokenGrams(token1Index+1, token2Index-1, sentenceGraph, linearPreTag+"bw", max=2)
#                    self.tokenFeatureBuilder.buildTokenGrams(token1Index+1, len(sentenceGraph.tokens)-1, sentenceGraph, linearPreTag+"af", max=2)
            self.tokenFeatureBuilder.setFeatureVector(None)
        # define extra attributes
        extra = {"xtype":"entRel","type":"i","t1":namedEntityToken.get("id"),"t2":token.get("id")}
        extra["e1"] = namedEntity.get("id")
        # list gold entities in extra, if present
        e2s = set()
        for entity in sentenceGraph.tokenIsEntityHead[token]:
            e2s.add(entity.get("id"))
        if len(e2s) != 0:
            extra["e2"] = ",".join(sorted(e2s))
        else:
            extra["e2"] = "None"
        extra["categoryName"] = categoryName
        sentenceOrigId = sentenceGraph.sentenceElement.get("origId")
        if sentenceOrigId != None:
            extra["SOID"] = sentenceOrigId       
        # make example
        category = self.classSet.getId(categoryName)
        
        return (sentenceGraph.getSentenceId()+".x"+str(exampleIndex),category,features,extra)