import sys, os
import shutil
mainTEESDir = os.path.abspath(os.path.join(__file__, "../.."))
sys.path.append(mainTEESDir)
from Detectors.Preprocessor import Preprocessor
from collections import defaultdict

def combineParses(inDir, outDir, subDirectories):
    print >> sys.stderr, "Collecting parses from", inDir
    counts = defaultdict(int)
    paths = []
    if subDirectories == None:
        paths.append(inDir)
    else:
        if isinstance(subDirectories, basestring):
            subDirectories = subDirectories.split(",")
        for subDir in subDirectories:
            paths.append(os.path.join(inDir, subDir))
    if os.path.exists(outDir):
        shutil.rmtree(outDir)
    os.makedirs(outDir)
    for path in paths:
        for filename in os.listdir(path):
            dst = os.path.join(outDir, filename)
            assert not os.path.exists(dst)
            shutil.copy2(os.path.join(path, filename), dst)
            counts[path] += 1
    print >> sys.stderr, dict(counts)
    return outDir    

def run(inPath, outPath, pattern, connection, numJobs, clear, debug):
    model = "GE09"
    # Remove existing work directory, if requested to do so
    if os.path.exists(outPath) and clear:
        print >> sys.stderr, "Output directory exists, removing", outPath
        shutil.rmtree(outPath)
    # Create work directory if needed
    if not os.path.exists(outPath):
        print >> sys.stderr, "Making output directory", outPath
        os.makedirs(outPath)
        
    parseDir = combineParses(inPath, os.path.join(outPath, "parses"), pattern)
        
    #preprocessor = Preprocessor(["MERGE-SETS", "REMOVE-ANALYSES", "REMOVE-HEADS", "MERGE-SENTENCES", "IMPORT-PARSE", "SPLIT-NAMES", "FIND-HEADS", "DIVIDE-SETS"])
    preprocessor = Preprocessor(["MERGE-SETS", "REMOVE-ANALYSES", "REMOVE-HEADS", "MERGE-SENTENCES", "IMPORT-PARSE", "VALIDATE", "DIVIDE-SETS"])
    preprocessor.setArgForAllSteps("debug", options.debug)
    preprocessor.stepArgs("IMPORT-PARSE")["parseDir"] = parseDir
    preprocessor.process(model + ".+\.xml", os.path.join(outPath, "corpus/" + model))

if __name__== "__main__":
    from optparse import OptionParser
    optparser = OptionParser(description="Predict events/relations")
    optparser.add_option("-i", "--input", default=None, help="input directory")
    optparser.add_option("-o", "--output", default=None, help="output directory")
    optparser.add_option("-p", "--pattern", default=None, help="input directory pattern")
    optparser.add_option("-n", "--numJobs", default=1, type=int, help="")
    optparser.add_option("-c", "--connection", default="connection=Unix:jobLimit=$JOBS", help="")
    # Debugging and process control
    optparser.add_option("--clear", default=False, action="store_true", help="Delete all output files")
    optparser.add_option("--debug", default=False, action="store_true", help="Debug mode")
    (options, args) = optparser.parse_args()
    
    run(options.input, options.output, options.pattern, options.connection, options.numJobs, options.clear, options.debug)