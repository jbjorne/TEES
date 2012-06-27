from train import workdir, getDetector, getSteps
import sys, os
import Utils.Settings as Settings
import Utils.Stream as Stream
from Utils.Connection.Unix import getConnection

def getModel(model):
    if not os.path.exists(model):
        for suffix in ["", ".zip", "-test.zip"]:
            predefined = os.path.join(Settings.MODEL_DIR, model + suffix)
            found = None
            if os.path.exists(predefined):
                print >> sys.stderr, "Classifying with predefined model", predefined
                found = predefined
                model = found
                break
        if found == None:
            raise Exception("Model " + str(model) + " not found")
    else:
        print >> sys.stderr, "Classifying with model", model
    return model

def getInput(input, model):
    if input == None: # Get a corpus corresponding to the model
        assert model != None
        input = model.split(".")[0]
    if input.isdigit(): # PMID
        print >> sys.stderr, "Classifying PubMed abstract", input
        pass
    elif not os.path.exists(input): # Use a predefined corpus
        for suffix in ["", ".xml", ".xml.gz"]:
            predefined = os.path.join(Settings.CORPUS_DIR, input + suffix)
            found = None
            if os.path.exists(predefined):
                print >> sys.stderr, "Classifying default corpus file", predefined
                found = predefined
                input = found
                preprocess = False
                break
        if found == None:
            raise Exception("Default corpus file for input " + str(input) + " not found")
    else:
        print >> sys.stderr, "Classifying input", input
        preprocess = True
    return input, preprocess

def classify(input, model, output, workDir=None, step=None, omitSteps=None, detector=None, corpusName="TEES", 
             debug=False, writeScores=True, clear=False):
    # Determine if a predefined model should be used
    model = getModel(model)
    input, preprocess = getInput(input, model)
    
    # Define processing steps
    selector, detectorSteps, omitDetectorSteps = getSteps(step, omitSteps, ["PREPROCESS", "CLASSIFY"])
    if not preprocess:
        selector.omitStep("PREPROCESS")
    # Initialize working directory
    if workDir != None: # use a permanent work directory
        workdir(workDir, clear)
    Stream.openLog(output + "-log.txt") # log in the output directory
    
    classifyInput = input
    if selector.check("PREPROCESS"):
        preprocessor = Preprocessor()
        preprocessor.debug = debug
        preprocessor.source = input # This has to be defined already here, needs to be fixed later
        preprocessor.compressIntermediateFiles = True # save space
        preprocessor.intermediateFilesAtSource = False
        preprocessor.requireEntitiesForParsing = True # parse only sentences which contain named entities
        if os.path.exists(preprocessor.getOutputPath("FIND-HEADS")):
            print >> sys.stderr, "Preprocessor output", preprocessor.getOutputPath("FIND-HEADS"), "exists, skipping preprocessing."
            classifyInput = preprocessor.getOutputPath("FIND-HEADS")
        else:
            print >> sys.stderr, "Preprocessor output", preprocessor.getOutputPath("FIND-HEADS"), "does not exist"
            print >> sys.stderr, "------------ Preprocessing ------------"
            # Remove some of the unnecessary intermediate files
            preprocessor.setIntermediateFiles({"Convert":None, "SPLIT-SENTENCES":None, "PARSE":None, "CONVERT-PARSE":None, "SPLIT-NAMES":None})
            # Process input into interaction XML
            classifyInput = preprocessor.process(input, corpusName, output, [], fromStep=detectorSteps["PREPROCESS"], toStep=None, omitSteps=omitDetectorSteps["PREPROCESS"] + ["DIVIDE-SETS"])
            print >> sys.stderr, "Total preprocessing time:", str(datetime.timedelta(seconds=time.time()-startTime))
    
    if selector.check("CLASSIFY"):
        detector = getDetector(detector, model)[0]
        detector = detector() # initialize object
        detector.debug = debug
        detector.stWriteScores = writeScores # write confidence scores into additional st-format files
        # classify
        detector.classify(classifyInput, model, output, fromStep=detectorSteps["CLASSIFY"], omitSteps=omitDetectorSteps["CLASSIFY"], workDir=workDir)


if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
        
    from optparse import OptionParser
    optparser = OptionParser()
    optparser.add_option("-i", "--input", default=None, dest="input", help="input")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output file stem")
    optparser.add_option("-w", "--workdir", default=None, dest="workdir", help="output directory")
    optparser.add_option("-m", "--model", default=None, dest="model", help="TEES model")
    optparser.add_option("-d", "--detector", default=None, dest="detector", help="")
    optparser.add_option("-c", "--connection", default=None, dest="connection", help="")
    optparser.add_option("-n", "--corpusName", default="TEES", dest="corpusName", help="")
    # Debugging and process control
    optparser.add_option("--step", default=None, dest="step", help="")
    optparser.add_option("--omitSteps", default=None, dest="omitSteps", help="")
    optparser.add_option("--writeScores", default=False, action="store_true", dest="writeScores", help="")
    optparser.add_option("--clearAll", default=False, action="store_true", dest="clearAll", help="Delete all files")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="More verbose output")
    (options, args) = optparser.parse_args()
    
    assert options.output != None
    classify(options.input, options.model, options.output, options.workdir, options.step, options.omitSteps, 
             options.detector, options.corpusName, options.debug, options.writeScores, options.clearAll)