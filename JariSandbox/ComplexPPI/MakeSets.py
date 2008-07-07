import sys
from InteractionXML.CorpusElements import CorpusElements
import cElementTree as ET
import Split

def makeSplit(corpusElements, fraction=0.5):
    documentIds = corpusElements.documentsById.keys()
    sample = Split.getSample(len(documentIds),fraction)
    division = {}
    for i in range(len(documentIds)): 
        division[documentIds[i]] = sample[i]
    return division

def splitExamples(exampleFileName, division):
    f = open(exampleFileName, "rt")
    lines = f.readlines()
    f.close()
    
    divisionFiles = {}
    for line in lines:
        if line[0] == "#":
            continue
        id = line.split("#")[-1].strip()
        documentId = id.rsplit(".",2)[0]
        if not divisionFiles.has_key(division[documentId]):
            divisionFiles[division[documentId]] = open(exampleFileName+"_set"+str(division[documentId]),"wt")
        divisionFiles[division[documentId]].write(line)
    for v in divisionFiles.values():
        v.close()

if __name__=="__main__":
    defaultInteractionFilename = "Data/BioInferForComplexPPI.xml"
    
    print >> sys.stderr, "Loading corpus file", defaultInteractionFilename
    corpusTree = ET.parse(defaultInteractionFilename)
    corpusRoot = corpusTree.getroot()
    corpusElements = CorpusElements(corpusRoot, "split_gs", "split_gs")
    print "Splitting features"
    division = makeSplit(corpusElements)
    splitExamples("Data/FeatureTest.txt", division)