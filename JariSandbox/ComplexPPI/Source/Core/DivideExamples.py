import Split
import sys

def getDocumentId(idString):
    return idString.rsplit(".",2)[0]

def getIdFromLine(line):
    assert(line.find("#") != -1)
    return line.split("#")[-1].strip()

if __name__=="__main__":
    from optparse import OptionParser
    defaultAnalysisFilename = "/usr/share/biotext/ComplexPPI/BioInferForComplexPPIVisible.xml"
    optparser = OptionParser(usage="%prog [options]\nCreate an html visualization for a corpus.")
    optparser.add_option("-i", "--input", default=defaultAnalysisFilename, dest="input", help="Corpus in analysis format", metavar="FILE")
    optparser.add_option("-o", "--output", default="", dest="output", help="Output directory")
    optparser.add_option("-f", "--folds", type="int", default=10, dest="folds", help="X-fold cross validation")
    (options, args) = optparser.parse_args()
    
    outputFiles = []
    for i in range(options.folds):
        outputFiles.append(open(options.output + options.input + ".fold" + str(i), "wt"))
    
    print >> sys.stderr, "Reading document ids"
    documentIds = []
    inputFile = open(options.input, "rt")
    try:
        for line in inputFile:
            if len(line) == 0 or line[0] == "#":
                continue
            docId = getDocumentId(getIdFromLine(line))
            if not docId in documentIds:
                documentIds.append(docId)
    finally:
        inputFile.close()

    print >> sys.stderr, "Dividing documents into folds"
    sample = Split.getFolds(len(documentIds),options.folds)
    division = {}
    for i in range(len(documentIds)): 
        division[documentIds[i]] = sample[i]

    print >> sys.stderr, "Dividing examples"
    inputFile = open(options.input, "rt")
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
