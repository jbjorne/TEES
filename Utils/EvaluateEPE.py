import sys, os
import shutil
mainTEESDir = os.path.abspath(os.path.join(__file__, "../.."))
sys.path.append(mainTEESDir)
from Detectors.Preprocessor import Preprocessor
from collections import defaultdict
from train import train
import Utils.Stream as Stream

def beginLog(outDir, logPath="AUTO"):
    if logPath == "AUTO":
        logPath = os.path.join(outDir, "log.txt")
    elif logPath == "None":
        logPath = None
    if logPath != None:
        if not os.path.exists(os.path.dirname(logPath)):
            os.makedirs(os.path.dirname(logPath))
        Stream.openLog(logPath)
    return logPath

def endLog(logPath):
    if logPath != None:
        Stream.closeLog(logPath)

def combineParses(inDir, outDir, subDirectories):
    print >> sys.stderr, "Parse input directory:", inDir
    counts = defaultdict(int)
    paths = []
    if subDirectories == None:
        paths.append(inDir)
    elif subDirectories == "*":
        paths.append(inDir)
        for filename in os.listdir(inDir):
            fullPath = os.path.join(inDir, filename)
            if os.path.isdir(fullPath):
                paths.append(fullPath)
    else:
        if isinstance(subDirectories, basestring):
            subDirectories = subDirectories.split(",")
        for subDir in subDirectories:
            paths.append(os.path.join(inDir, subDir))
    if os.path.exists(outDir):
        shutil.rmtree(outDir)
    os.makedirs(outDir)
    print >> sys.stderr, "Collecting parses from directories:", paths
    for path in paths:
        for filename in os.listdir(path):
            dst = os.path.join(outDir, filename)
            assert not os.path.exists(dst)
            filePath = os.path.join(path, filename)
            if os.path.isfile(filePath) and filePath.endswith(".epe"):
                shutil.copy2(os.path.join(path, filename), dst)
                counts[path] += 1
    print >> sys.stderr, "Found epe parse files:", dict(counts)
    return outDir    

def ask(question):
    valid = {"yes": True, "y": True, "no": False, "n": False, "":False}
    while True:
        sys.stdout.write(question + " [y/N] ")
        choice = raw_input().lower()
        if choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")

def run(inPath, outPath, subDirs, model, connection, numJobs, subTask=3, posTags=None, useTestSet=False, clear=True, debug=False, force=False, training=True, preprocessorSteps=None, subset=None):
    # Remove existing non-empty work directory, if requested to do so
    if os.path.exists(outPath) and len(os.listdir(outPath)) > 0 and clear:
        if force or ask("Output directory '" + outPath + "' exists, remove?"):
            print >> sys.stderr, "Output directory exists, removing", outPath
            shutil.rmtree(outPath)
    # Create work directory if needed
    if not os.path.exists(outPath):
        print >> sys.stderr, "Making output directory", outPath
        os.makedirs(outPath)
    
    # Begin logging
    logPath = beginLog(outPath)
    
    # Collect the parse files
    parseDir = os.path.join(outPath, "parses")
    if not os.path.exists(parseDir) or len(os.listdir(parseDir)) == 0:
        parseDir = combineParses(inPath, parseDir, subDirs)
    else:
        print >> sys.stderr, "Using collected parses from", parseDir
    
    # Import the parses
    corpusDir = os.path.join(outPath, "corpus")
    if not os.path.exists(corpusDir):
        if preprocessorSteps == None:
            preprocessorSteps = ["MERGE_SETS", "REMOVE_ANALYSES", "REMOVE_HEADS", "MERGE_SENTENCES", "IMPORT_PARSE", "SPLIT_NAMES", "FIND_HEADS", "DIVIDE_SETS"]
        preprocessor = Preprocessor(preprocessorSteps)
        #preprocessor = Preprocessor(["MERGE-SETS", "REMOVE-ANALYSES", "REMOVE-HEADS", "MERGE-SENTENCES", "IMPORT-PARSE", "VALIDATE", "DIVIDE-SETS"])
        preprocessor.setArgForAllSteps("debug", debug)
        preprocessor.getStep("IMPORT_PARSE").setArg("parseDir", parseDir)
        preprocessor.getStep("IMPORT_PARSE").setArg("posTags", posTags)
        modelPattern = model + ".+\.xml" if useTestSet else model + "-devel\.xml|" + model + "-train\.xml"
        preprocessor.process(modelPattern, os.path.join(corpusDir, model), logPath=None)
    else:
        print >> sys.stderr, "Using imported parses from", corpusDir
    
    # Train the model
    if training:
        connection = connection.replace("$JOBS", str(numJobs))
        if subTask > 0:
            model = model + "." + str(subTask)
        train(outPath, model, parse="McCC", debug=debug, connection=connection, corpusDir=corpusDir, subset=subset, log=None) #classifierParams={"examples":None, "trigger":"150000", "recall":None, "edge":"7500", "unmerging":"2500", "modifiers":"10000"})
        
    # Close the log
    endLog(logPath)
    
if __name__== "__main__":
    from optparse import OptionParser
    optparser = OptionParser(description="Train a TEES model using EPE parses")
    optparser.add_option("-i", "--input", default=None, help="Input directory")
    optparser.add_option("-o", "--output", default=None, help="Output directory")
    optparser.add_option("-s", "--subdirs", default="*", help="Input directory subdirectories (optional)")
    optparser.add_option("-n", "--numJobs", default=1, type=int, help="Number of parallel SVM processes to use while training")
    optparser.add_option("-t", "--testSet", default=False, action="store_true", help="Do only the preprocessing")
    optparser.add_option("--connection", default="connection=Unix:jobLimit=$JOBS", help="TEES local or remote training settings")
    optparser.add_option("--model", default="GE09", help="TEES model")
    optparser.add_option("--pos", default="pos,xpos,upos", help="Preferred POS tag attributes")
    optparser.add_option("--subTask", default=3, type=int, help="GE09 subtask (1, 2 or 3)")
    optparser.add_option("--noClear", default=False, action="store_true", help="Continue a previous run")
    optparser.add_option("--debug", default=False, action="store_true", help="Debug mode")
    optparser.add_option("-f", "--force", default=False, action="store_true", help="Force removal of existing output directory")
    optparser.add_option("--preprocessorSteps", default=None, help="List of preprocessing steps")
    optparser.add_option("--subset", default=None, dest="subset", help="")
    optparser.add_option("--noTraining", default=False, action="store_true", help="Do only the preprocessing")
    (options, args) = optparser.parse_args()
    
    run(options.input, options.output, options.subdirs, options.model, options.connection, options.numJobs, options.subTask, options.pos, options.testSet, 
        not options.noClear, options.debug, options.force, training=not options.noTraining, preprocessorSteps=options.preprocessorSteps, subset=options.subset)