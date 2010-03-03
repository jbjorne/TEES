"""
Pseudorandomly distributed subsets
"""
__version__ = "$Revision: 1.4 $"

import Split
import sys

def getDocumentId(idString):
    return idString.rsplit(".",2)[0]

def getIdFromLine(line):
    assert(line.find("#") != -1)
    return line.split("#")[-1].strip()

def getDocumentIds(filename):
    documentIds = []
    inputFile = open(filename, "rt")
    try:
        for line in inputFile:
            if len(line) == 0 or line[0] == "#":
                continue
            docId = getDocumentId(getIdFromLine(line))
            if not docId in documentIds:
                documentIds.append(docId)
    finally:
        inputFile.close()
    return documentIds

def getDocumentFolds(documentIds, folds):
    sample = Split.getFolds(len(documentIds),folds)
    division = {}
    for i in range(len(documentIds)): 
        division[documentIds[i]] = sample[i]
    return division

def divideExamples(filename, outputFilenames):
    print >> sys.stderr, "Reading document ids"
    documentIds = getDocumentIds(filename)

    print >> sys.stderr, "Dividing documents into folds"
    division = getDocumentFolds(documentIds, len(outputFilenames))

    print >> sys.stderr, "Dividing examples"
    
    outputFiles = []
    for name in outputFilenames:
        outputFiles.append(open(name, "wt"))

    inputFile = open(filename, "rt")
    try:
        for line in inputFile:
            if len(line) == 0 or line[0] == "#":
                continue
            docId = getDocumentId(getIdFromLine(line))
            outputFiles[division[docId]].write(line)
    finally:
        inputFile.close()

    for outputFile in outputFiles:
        outputFile.close()
        
if __name__=="__main__":
    from optparse import OptionParser
    defaultAnalysisFilename = "/usr/share/biotext/ComplexPPI/BioInferForComplexPPIVisible.xml"
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=defaultAnalysisFilename, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default="", dest="output", help="Output directory")
    optparser.add_option("-f", "--folds", type="int", default=10, dest="folds", help="X-fold cross validation")
    (options, args) = optparser.parse_args()
    
    outputFilenames = []
    for i in range(options.folds):
        outputFilenames.append(options.output + options.input + ".fold" + str(i))

    divideExamples(options.input, outputFilenames)