import time, datetime
startTime = time.time()

# most imports are defined in Pipeline
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../CommonUtils") # new CommonUtils
from Pipeline import *
import STFormat.ConvertXML
import STFormat.Compare
import STFormat.STTools
import subprocess
import shutil
from Detectors.EventDetector import EventDetector
from Detectors.StepSelector import StepSelector
from Detectors.Preprocessor import Preprocessor
import tempfile

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-i", "--input", default=None, dest="input", help="input data")
optparser.add_option("-c", "--corpus", default="PMC11", dest="corpus", help="corpus name for preprocessing")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-w", "--workdir", default=None, dest="workdir", help="work directory")
optparser.add_option("-m", "--model", default=None, dest="model", help="model file or directory")
optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
optparser.add_option("--eventTag", default="GE", dest="eventTag", help="")
optparser.add_option("--step", default=None, dest="step", help="")
optparser.add_option("--detectorStep", default=None, dest="detectorStep", help="")
optparser.add_option("--csc", default="", dest="csc", help="")
optparser.add_option("--noLog", default=False, action="store_true", dest="noLog", help="")
optparser.add_option("--clearAll", default=False, action="store_true", dest="clearAll", help="Delete all files")
optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="")
(options, args) = optparser.parse_args()

selector = StepSelector(["PREPROCESS", "EVENTS"], fromStep=options.step)

# Get the input stem, which will be used for naming the output files
options.input = options.input.rstrip("/")
if options.output == None:
    INPUT_TAG = options.input
else:
    if not os.path.exists(options.output):
        os.makedirs(options.output)
    INPUT_TAG = os.path.join(options.output, options.input.rsplit("/", 1)[-1])
#if os.path.isfile(options.input):
#    if INPUT_TAG.endswith(".tar.gz"):
#        INPUT_TAG = INPUT_TAG[:-len(".tar.gz")]
open(INPUT_TAG+"-STARTED", "w").close() # Mark process status
        
# Start logging
WORKDIR = options.workdir
if WORKDIR == None:
    WORKDIR = tempfile.mkdtemp()
workdir(WORKDIR, options.clearAll) # Select a working directory, optionally remove existing files
if not options.noLog:
    log(options.clearAll, True, INPUT_TAG + "-" + options.eventTag + ".log") # Start logging into a file in working directory

eventDetectionInput = None
preprocessor = Preprocessor()
preprocessor.debug = options.debug
preprocessor.source = options.input # This has to be defined already here, needs to be fixed later
preprocessor.compressIntermediateFiles = True # save space
preprocessor.intermediateFilesAtSource = True # create output at source file location
preprocessor.requireEntitiesForParsing = True # parse only sentences which contain BANNER entities
if selector.check("PREPROCESS"):
    if os.path.exists(preprocessor.getOutputPath("FIND-HEADS")):
        print >> sys.stderr, "Preprocessor output", preprocessor.getOutputPath("FIND-HEADS"), "exists, skipping preprocessing."
        eventDetectionInput = preprocessor.getOutputPath("FIND-HEADS")
    else:
        print >> sys.stderr, "Preprocessor output", preprocessor.getOutputPath("FIND-HEADS"), "does not exist"
        print >> sys.stderr, "------------ Preprocessing ------------"
        # Remove some of the unnecessary intermediate files
        preprocessor.setIntermediateFile("CONVERT", None)
        preprocessor.setIntermediateFile("SPLIT-SENTENCES", None)
        preprocessor.setIntermediateFile("PARSE", None)
        preprocessor.setIntermediateFile("CONVERT-PARSE", None)
        preprocessor.setIntermediateFile("SPLIT-NAMES", None)
        # Process input into interaction XML
        eventDetectionInput = preprocessor.process(options.input, options.corpus, options.output, [], fromStep=options.detectorStep, toStep=None, omitSteps=["DIVIDE-SETS"])
        print >> sys.stderr, "Total preprocessing time:", str(datetime.timedelta(seconds=time.time()-startTime))

eventDetector = EventDetector()
eventDetector.stEvaluator = None # ST evaluation won't work for external data
eventDetector.stWriteScores = True # write confidence scores into additional st-format files
eventDetector.setCSCConnection(options.csc, os.path.join("CSCConnection",WORKDIR.lstrip("/")))
if selector.check("EVENTS"):
    print >> sys.stderr, "------------ Event Detection ------------"
    if options.model != None:
        if eventDetectionInput == None:
            #if options.input != None:
            eventDetectionInput = options.input
            #else:
            #    eventDetectionInput = preprocessor.getOutputPath("FIND-HEADS")
        eventDetector.classify(eventDetectionInput, options.model, "events", fromStep=options.detectorStep, parse=options.parse)
        STFormat.STTools.getStatistics("events-events.tar.gz", True, ",")
        # Move final predicted files to output directory
        if os.path.exists("events-modifier-pred.xml.gz"):
            shutil.copy("events-modifier-pred.xml.gz", INPUT_TAG + "-events-"+options.eventTag+"-modifiers.xml.gz")
        else:
            shutil.copy("events-unmerging-pred.xml.gz", INPUT_TAG + "-events-"+options.eventTag+"-unmerged.xml.gz")
        shutil.copy("events-events.tar.gz", INPUT_TAG + "-events-"+options.eventTag+".tar.gz")
        #STFormat.Compare.compare("predicted.tar.gz", "predicted-devel.tar.gz", "a2")
        open(INPUT_TAG+options.eventTag+"-FINISHED", "w").close() # Mark process status
    else:
        print >> sys.stderr, "No model defined, skipping event detection"
    print >> sys.stderr, "Total event detection time:", str(datetime.timedelta(seconds=time.time()-startTime))

if options.workdir == None: # remove temporary working directory
    shutil.rmtree(WORKDIR)
    
print >> sys.stderr, "Total processing time:", str(datetime.timedelta(seconds=time.time()-startTime))
