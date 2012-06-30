"""
BioInfer ontology based features
"""
__version__ = "$Revision: 1.2 $"

import sys, os
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import Utils.ElementTreeUtils as ETUtils
from FeatureBuilder import FeatureBuilder

g_bioInferFileName = "../../../BioInfer/data/bioinfer.xml"

def parseNodes(node, ontology):
    for child in node:
        assert(not ontology.has_key(child.attrib["name"]))
        ontology[child.attrib["name"]] = node.attrib["name"]
        parseNodes(child, ontology)

def loadOntologies(bioInferFileName):
    bioInferTree = ET.parse(bioInferFileName)
    bioInferRoot = bioInferTree.getroot()
    ontologyElements = bioInferRoot.findall("ontology")
    ontologies = {}
    for ontologyElement in ontologyElements:
        ontologies[ontologyElement.attrib["type"]] = {}
        for node in ontologyElement:
            parseNodes(node, ontologies[ontologyElement.attrib["type"]])
    return ontologies

def printNode(node, indent=""):
    print indent + node.attrib["name"]
    for child in node:
        printNode(child, indent + " ")

def getParents(term, ontology):
    parents = []
    parent = ontology[node]
    while parent != None:
        parents.append(parent)
        parent = ontology[parent]
    return parent

class BioInferOntologyFeatureBuilder(FeatureBuilder):
    def __init__(self, featureSet):
        global g_bioInferFileName
        FeatureBuilder.__init__(self, featureSet)
        self.ontologies = loadOntologies(g_bioInferFileName)
    
    def getTokenAnnotatedType(self, token, sentenceGraph):    
        if sentenceGraph.tokenIsEntityHead[token] != None:
            return sentenceGraph.tokenIsEntityHead[token].attrib["type"]
        else:
            return None

    def buildOntologyFeaturesForPath(self, sentenceGraph, pathTokens, pathEdges=None):
        for token in pathTokens:
            tokenType = self.getTokenAnnotatedType(token, sentenceGraph)
            if tokenType != None:
                self.buildOntologyFeatures(tokenType, "ont_")
    
    def buildOntologyFeatures(self, term, tag=""):
        features = self.getParents(term)
        for feature in features:
            self.features[tag+feature] = 1
    
    def getParents(self, term):
        returnValues = []
        for k, ontology in self.ontologies.iteritems():
            if ontology.has_key(term):
                parents = []
                parent = term
                while ontology.has_key(parent):
                    parent = ontology[parent]
                    parents.append(parent)
                for parent in parents:
                    returnValues.append(k+"_"+parent)
        return returnValues

if __name__=="__main__":
    ontologies = loadOntologies(g_bioInferFileName)
    for k, v in ontologies.iteritems():
        print k + ":"
        print v