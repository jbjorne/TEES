import sys, os

def getLines(lines, boundaries):
    for begin, end in boundaries:
        subset = None
        endFound = False
        for line in lines:
            if subset == None and begin in line:
                subset = []
            elif end in line:
                endFound = True
                assert subset != None
                break
            elif subset != None:
                subset.append(line)
        assert endFound
        lines = subset
    return subset

def getGENIAResults(lines, outPath=None):
    lines = getLines(lines, [("------------ Empty devel classification ------------", "=== EXIT STEP EMPTY"), 
                             ("Finished!", "=== EXIT STEP ST-CONVERT")])
    fullResults = [x.split("\t", 1)[-1] for x in lines]
    mainResult = getLines(fullResults, [("##### approximate span and recursive mode #####", "##### event decomposition in the approximate span mode #####")])
    for line in mainResult:
        if "==[ALL-TOTAL]==" in line:
            mainResult = line
            break
    if outPath != None:
        with open(outPath, "wt") as f:
            f.write("------------ Primary Result ------------\n")
            f.write(mainResult)
            f.write("\n")
            f.write("------------ All Results ------------\n")
            for line in fullResults:
                f.write(line)
    return fullResults, mainResult                   

def collectResults(inDir, inPattern, outDir):
    print >> sys.stderr, "Collecting results from:", inDir
    models = []
    for filename in os.listdir(inDir):
        fullPath = os.path.join(inDir, filename)
        if os.path.isdir(fullPath) and (inPattern is None or inPattern.match(filename)):
            models.append(fullPath)
    print >> sys.stderr, "Collecting parses for models:", models
    for model in models:
        modelName = os.path.basename(model)
        print >> sys.stderr, "Reading model:", modelName
        logPath = os.path.join(model, "log.txt")
        assert os.path.exists(logPath), logPath
        with open(logPath, "rt") as f:
            fullResults, mainResult = getGENIAResults(f.readlines(), outDir)
            print >> sys.stderr, mainResult.strip()

if __name__== "__main__":
    from optparse import OptionParser
    optparser = OptionParser(description="Collect TEES results from log files and models")
    optparser.add_option("-i", "--input", default=None, help="Input directory")
    optparser.add_option("-o", "--output", default=None, help="Output directory")
    optparser.add_option("-p", "--pattern", default=None, help="Input directory subdirectories (optional)")
    (options, args) = optparser.parse_args()

    collectResults(options.input, options.pattern, options.output)