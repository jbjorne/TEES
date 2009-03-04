import sys, os
from optparse import OptionParser

def getExamples(testFilename):
    testFile = open(testFilename, "rt")
    testLines = testFile.readlines()
    testFile.close()
    examples = []
    for line in testLines:
        if line[0] != "#":
            examplePart, commentPart = line.rsplit("#", 1)
            realClass = examplePart.split(None,1)[0]
            comments = commentPart.split()
            exampleId = None
            for comment in comments:
                key, value = comment.strip().split(":")
                if key == "id":
                    exampleId = value
                    break
            examples.append( (exampleId, realClass) )
    return examples
    
def addToCSV(predictionFilename, examples, csvFile):
    cParameter = predictionFilename.rsplit("_",1)[-1]
    predictionFile = open(predictionFilename, "rt")
    predictionLines = predictionFile.readlines()
    predictionFile.close()
    for i in range(len(predictionLines)):
        line = predictionLines[i]
        predictedClass = line.split(None,1)[0]
        csvFile.write(examples[i][1]+","+predictedClass+","+examples[i][0]+",0,"+cParameter+"\n")

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-i", "--input", default=None, dest="input", help="", metavar="FILE")
    optparser.add_option("-o", "--output", default="results.csv", dest="output", help="")
    (options, args) = optparser.parse_args()
    
    if options.input == None:
        options.input = os.path.join(os.environ["WRKDIR"], "jari-genia")

    filenames = os.listdir(options.input)
    predictionFilenames = []
    for filename in filenames:
        if filename.find("predictions") != -1:
            predictionFilenames.append(os.path.join(options.input,filename))
    predictionFilenames.sort()
    
    examples = getExamples(os.path.join(options.input, "test.ibo"))
    
    csvFilename = os.path.join(options.input, options.output)
    csvFile = open(csvFilename, "wt")
    for predictionFilename in predictionFilenames:
        print >> sys.stderr, "Adding results from", predictionFilename 
        addToCSV(predictionFilename, examples, csvFile)
    csvFile.close()