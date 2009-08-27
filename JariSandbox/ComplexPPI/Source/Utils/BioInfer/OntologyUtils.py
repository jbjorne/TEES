import sys, os
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import cElementTree as ET
import cElementTreeUtils as ETUtils
from BioInferTempOntology import getBioInferTempOntology

g_bioInferFileName = os.path.abspath( os.path.split(os.path.abspath(__file__))[0] + "/../../../../../BioInfer/data/bioinfer.xml" )

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
    parent = ontology[term]
    while parent != None:
        parents.append(parent)
        if ontology.has_key(parent):
            parent = ontology[parent]
        else:
            parent = None
    return parents

def hasParent(term, parent, ontology):
    parents = []
    currParent = ontology[term]
    while currParent != None:
        if currParent == parent:
            return True
        if ontology.has_key(currParent):
            currParent = ontology[currParent]
        else:
            return False

if __name__=="__main__":
    o = getBioInferTempOntology()
    print getParents("CONTROL", o)
    print getParents("AFFECT", o)
    print getParents("Amount_property", o)
    print getParents("Protein", o)
    
    print
    
    ontologies = loadOntologies(g_bioInferFileName)
    for k, v in ontologies.iteritems():
        print k + ":"
        print v
    print "test:"
    print getParents("CONTROL", ontologies["Entity"])
    print
    print getParents("Amount_property", ontologies["Entity"])
    print getParents("UPREGULATE", ontologies["Relationship"])
    print getParents("AFFECT", ontologies["Relationship"])
    print getParents("Individual_protein", ontologies["Entity"])
    print hasParent("PHOSPHORYLATION", "Process_entity", ontologies["Entity"])