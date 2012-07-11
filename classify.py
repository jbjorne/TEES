from train import workdir, getDetector, getSteps
import sys, os
import tempfile
import codecs
import Utils.Settings as Settings
import Utils.Stream as Stream
import Utils.Download
from Utils.Connection.Unix import getConnection
from Detectors.Preprocessor import Preprocessor

def classify(input, model, output, workDir=None, step=None, omitSteps=None, 
             goldInput=None, detector=None, 
             debug=False, writeScores=True, clear=False, 
             preprocessorTag="-preprocessed.xml.gz", preprocessorParams=None):
    input, preprocess = getInput(input)
    # Define processing steps
    selector, detectorSteps, omitDetectorSteps = getSteps(step, omitSteps, ["PREPROCESS", "CLASSIFY"])
    if not preprocess:
        selector.markOmitSteps("PREPROCESS")
    # Initialize working directory
    if workDir != None: # use a permanent work directory
        workdir(workDir, clear)
    Stream.openLog(output + "-log.txt") # log in the output directory
    
    classifyInput = input
    if selector.check("PREPROCESS"):
        preprocessor = Preprocessor()
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
            classifyInput = preprocessor.process(input, preprocessorOutput, preprocessorParams, model, [], fromStep=detectorSteps["PREPROCESS"], toStep=None, omitSteps=omitDetectorSteps["PREPROCESS"])
    
    if selector.check("CLASSIFY"):
        model = getModel(model)
        detector = getDetector(detector, model)[0]() # initialize detector object
        detector.debug = debug
        detector.stWriteScores = writeScores # write confidence scores into additional st-format files
        detector.classify(classifyInput, model, output, goldData=goldInput, fromStep=detectorSteps["CLASSIFY"], omitSteps=omitDetectorSteps["CLASSIFY"], workDir=workDir)

def getModel(model):
    if not os.path.exists(model):
        print >> sys.stderr, "Model", model, "doesn't exist, looking for a default model"
        found = None
        if hasattr(Settings, "MODEL_DIR"):
            for suffix in ["", ".zip", "-test.zip"]:
                predefined = os.path.join(Settings.MODEL_DIR, model + suffix)
                if os.path.exists(predefined):
                    print >> sys.stderr, "Classifying with default model", predefined
                    found = predefined
                    model = found
                    break
            if found == None:
                print >> sys.stderr, "No default model found for definition", model
        else:
            print >> sys.stderr, "Default model directory MODEL_DIR not defined in Settings"
        if found == None:
            raise Exception("Model " + str(model) + " not found")
    else:
        print >> sys.stderr, "Classifying with model", model
    return model

def getInput(input, model=None):
    if input == None: # Get a corpus corresponding to the model
        assert model != None
        input = model.split(".")[0]

    if input.isdigit(): # PMID
        print >> sys.stderr, "Classifying PubMed abstract", input
        input = getPubMed(input)
        preprocess = True
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

def getPubMed(pmid):
    print >> sys.stderr, "Downloading PubMed abstract", pmid
    tempDir = tempfile.gettempdir()
    url = "http://www.ncbi.nlm.nih.gov/pubmed/" + str(pmid) + "?report=xml"
    downloaded = os.path.join(tempDir, "pmid-" + str(pmid))
    Download.download(url, downloaded + ".xml", False)
    # Read the text from the XML
    f = codecs.open(downloaded, "rt", "utf-8")
    for line in f:
        line = line.strip()
        textElements = []
        for tag in ["<ArticleTitle>", "<AbstractText>"]:
            if line.startswith(tag):
                textElements.append(line.split(">", 1)[1].split("<")[0])
    f.close()
    # Save the text file
    f = codecs.open(downloaded + ".txt", "wt", "utf-8")
    f.write("\n".join(textElements))
    f.close()
    # Return text file name
    return downloaded + ".txt"

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
    optparser.add_option("-g", "--gold", default=None, dest="gold", help="annotated version of the input file (optional)")
    optparser.add_option("-p", default=None, dest="preprocessorParams", help="")
    # Debugging and process control
    optparser.add_option("--step", default=None, dest="step", help="")
    optparser.add_option("--omitSteps", default=None, dest="omitSteps", help="")
    optparser.add_option("--writeScores", default=False, action="store_true", dest="writeScores", help="")
    optparser.add_option("--clearAll", default=False, action="store_true", dest="clearAll", help="Delete all files")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="More verbose output")
    (options, args) = optparser.parse_args()
    
    assert options.output != None
    classify(options.input, options.model, options.output, options.workdir, options.step, options.omitSteps, 
             options.gold, options.detector, options.debug, options.writeScores, options.clearAll,
             preprocessorParams=options.preprocessorParams)