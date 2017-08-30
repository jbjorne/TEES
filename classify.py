#!/usr/bin/env python

"""
Detect events or relations from text.
"""
from train import workdir, getDetector, getSteps
import sys, os
import tempfile
import codecs
import Utils.Settings as Settings
import Utils.Stream as Stream
import Utils.Download
from Utils.Connection.Connection import getConnection
from Detectors.Preprocessor import Preprocessor

def classify(input, model, output, workDir=None, step=None, omitSteps=None, 
             goldInput=None, detector=None, debug=False, clear=False, 
             preprocessorTag="-preprocessed.xml.gz", preprocessorParams=None, bioNLPSTParams=None):
    """
    Detect events or relations from text.
    
    @param input: The input file in either interaction XML or BioNLP ST format. Can also be a PMID or TEES default corpus name.
    @param model: A path to a model file or the name of a TEES default model.
    @param output: The output file stem. Output files will be of the form output-*
    @param workDir: If intermediate files need to be saved, they will go here.
    @param step: A step=substep pair, where the steps are PREPROCESS and CLASSIFY
    @param omitSteps: step=substep parameters, where multiple substeps can be defined.
    @param goldInput: a version of the corpus file with gold annotation. Enables measuring of performance
    @param detector: a Detector object, or a string defining one to be imported. If None, will be read from model.
    @param debug: In debug mode, more output is shown, and some temporary intermediate files are saved
    @param clear: Remove existing workDir
    @param preprocessorTag: preprocessor output file will be output + preprocessorTag
    @param preprocessorParams: Optional parameters controlling preprocessing. If None, will be read from model.
    @param bioNLPSTParams: Optional parameters controlling BioNLP ST format output. If None, will be read from model.
    """
    input = os.path.abspath(input)
    if goldInput != None: goldInput = os.path.abspath(goldInput)
    if model != None: model = os.path.abspath(model)
    # Initialize working directory
    if workDir != None: # use a permanent work directory
        workdir(workDir, clear)
    Stream.openLog(output + "-log.txt") # log in the output directory
    # Get input files
    input, preprocess = getInput(input)
    model = getModel(model)
    # Define processing steps
    selector, detectorSteps, omitDetectorSteps = getSteps(step, omitSteps, ["PREPROCESS", "CLASSIFY"])
    if not preprocess:
        selector.markOmitSteps("PREPROCESS")
    
    classifyInput = input
    if selector.check("PREPROCESS"):
        if preprocessorParams == None:
            preprocessorParams = ["LOAD", "GENIA_SPLITTER", "BANNER", "BLLIP_BIO", "STANFORD_CONVERT", "SPLIT_NAMES", "FIND_HEADS", "SAVE"]
        preprocessor = Preprocessor(preprocessorParams)
        if debug: 
            preprocessor.setArgForAllSteps("debug", True)
        preprocessorOutput = output + preprocessorTag
        #preprocessor.debug = debug
        #preprocessor.source = input # This has to be defined already here, needs to be fixed later
        #preprocessor.requireEntitiesForParsing = True # parse only sentences which contain named entities
        if os.path.exists(preprocessorOutput) and not clear: #os.path.exists(preprocessor.getOutputPath("FIND-HEADS")):
            #print >> sys.stderr, "Preprocessor output", preprocessor.getOutputPath("FIND-HEADS"), "exists, skipping preprocessing."
            print >> sys.stderr, "Preprocessor output", preprocessorOutput, "exists, skipping preprocessing."
            classifyInput = preprocessorOutput # preprocessor.getOutputPath("FIND-HEADS")
        else:
            #print >> sys.stderr, "Preprocessor output", preprocessor.getOutputPath("FIND-HEADS"), "does not exist"
            print >> sys.stderr, "Preprocessor output", preprocessorOutput, "does not exist"
            print >> sys.stderr, "------------ Preprocessing ------------"
            # Remove some of the unnecessary intermediate files
            #preprocessor.setIntermediateFiles({"Convert":None, "SPLIT-SENTENCES":None, "PARSE":None, "CONVERT-PARSE":None, "SPLIT-NAMES":None})
            # Process input into interaction XML
            classifyInput = preprocessor.process(input, preprocessorOutput, model)
    
    if selector.check("CLASSIFY"):
        detector = getDetector(detector, model)[0]() # initialize detector object
        detector.debug = debug
        detector.bioNLPSTParams = detector.getBioNLPSharedTaskParams(bioNLPSTParams, model)
        detector.classify(classifyInput, model, output, goldData=goldInput, fromStep=detectorSteps["CLASSIFY"], omitSteps=omitDetectorSteps["CLASSIFY"], workDir=workDir)

def getModel(model):
    if model == None:
        return None
    if not os.path.exists(model):
        print >> sys.stderr, "Model", model, "doesn't exist, looking for a default model"
        modelName = os.path.basename(model)
        found = None
        if hasattr(Settings, "MODEL_DIR"):
            for suffix in ["", "-test", ".zip", "-test.zip"]:
                predefined = os.path.join(Settings.MODEL_DIR, modelName + suffix)
                if os.path.exists(predefined):
                    print >> sys.stderr, "Classifying with default model", predefined
                    found = predefined
                    model = found
                    break
            if found == None:
                print >> sys.stderr, "No default model found for definition", modelName
        else:
            print >> sys.stderr, "Default model directory MODEL_DIR not defined in Settings"
        if found == None:
            raise Exception("Model " + str(model) + " not found")
    else:
        print >> sys.stderr, "Classifying with model", model
    return os.path.abspath(model)

def getInput(input, model=None):
    if input == None: # Get a corpus corresponding to the model
        assert model != None
        input = model.split(".")[0]

    if os.path.basename(input).isdigit(): # PMID
        print >> sys.stderr, "Classifying PubMed abstract", os.path.basename(input)
        input = Utils.Download.getPubMed(os.path.basename(input))
        preprocess = True
    elif not os.path.exists(input): # Use a predefined corpus
        defaultInput = os.path.basename(input)
        for suffix in ["", ".xml", ".xml.gz"]:
            predefined = os.path.join(Settings.CORPUS_DIR, defaultInput + suffix)
            found = None
            if os.path.exists(predefined):
                print >> sys.stderr, "Classifying default corpus file", predefined
                found = predefined
                preprocess = False
                break
        if found == None:
            raise Exception("Default corpus file for input " + str(defaultInput) + " not found")
        input = found
    else:
        print >> sys.stderr, "Classifying input", input
        preprocess = True
    return os.path.abspath(input), preprocess

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
        
    from optparse import OptionParser
    optparser = OptionParser(description="Predict events/relations")
    optparser.add_option("-i", "--input", default=None, dest="input", help="input")
    optparser.add_option("-o", "--output", default=None, dest="output", help="output file stem")
    optparser.add_option("-w", "--workdir", default=None, dest="workdir", help="output directory")
    optparser.add_option("-m", "--model", default=None, dest="model", help="TEES model")
    optparser.add_option("-d", "--detector", default=None, dest="detector", help="")
    optparser.add_option("-c", "--connection", default=None, dest="connection", help="")
    optparser.add_option("-g", "--gold", default=None, dest="gold", help="annotated version of the input file (optional)")
    optparser.add_option("-p", "--preprocessorParams", default=None, dest="preprocessorParams", help="")
    optparser.add_option("-b", "--bioNLPSTParams", default=None, dest="bioNLPSTParams", help="")
    # Debugging and process control
    optparser.add_option("--step", default=None, dest="step", help="")
    optparser.add_option("--omitSteps", default=None, dest="omitSteps", help="")
    optparser.add_option("--clearAll", default=False, action="store_true", dest="clearAll", help="Delete all files")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="More verbose output")
    (options, args) = optparser.parse_args()
    
    assert options.output != None
    classify(options.input, options.model, options.output, options.workdir, options.step, options.omitSteps, 
             options.gold, options.detector, options.debug, options.clearAll,
             preprocessorParams=options.preprocessorParams, bioNLPSTParams=options.bioNLPSTParams)
