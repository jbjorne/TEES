# Optimize parameters for event detection and produce event and edge model files

# most imports are defined in Pipeline
from Pipeline import *
import sys, os
import STFormat.ConvertXML
import STFormat.Compare
from Detectors.ModifierDetector import ModifierDetector
from Detectors.StepSelector import StepSelector
from InteractionXML.MakeSubset import makeSubset

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-e", "--test", default=None, dest="testFile", help="Test file in interaction xml")
optparser.add_option("-r", "--train", default=None, dest="trainFile", help="Train file in interaction xml")
optparser.add_option("-d", "--devel", default=None, dest="develFile", help="Devel file in interaction xml")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-a", "--task", default="GE", dest="task", help="task number")
optparser.add_option("-p", "--parse", default=None, dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default=None, dest="tokenization", help="Tokenization XML element name")
# Classifier
optparser.add_option("-c", "--classifier", default="Cls", dest="classifier", help="")
optparser.add_option("--csc", default="murska", dest="csc", help="")
# Example builders
optparser.add_option("--downSampleTrain", default=1.0, type="float", dest="downSampleTrain", help="")
optparser.add_option("--downSampleSeed", default=1, type="int", dest="downSampleSeed", help="")
optparser.add_option("--noTestSet", default=False, action="store_true", dest="noTestSet", help="")
optparser.add_option("-f", "--edgeExampleBuilder", default="MultiEdgeExampleBuilder", dest="edgeExampleBuilder", help="")
optparser.add_option("-s", "--styles", default="multiclass,speculation", dest="styles", help="")
optparser.add_option("--step", default=None, dest="step", help="")
optparser.add_option("--detectorStep", default=None, dest="detectorStep", help="")
# Parameters to optimize
optparser.add_option("-x", "--params", default="5000,10000,20000,50000,100000", dest="params", help="Trigger detector c-parameter values")
optparser.add_option("--clearAll", default=False, action="store_true", dest="clearAll", help="Delete all files")
(options, args) = optparser.parse_args()

selector = StepSelector(["TRAIN", "DEVEL", "EMPTY", "TEST"], fromStep=options.step)

# Check options
assert options.output != None

exec "CLASSIFIER = " + options.classifier

# Main settings
detector = ModifierDetector()

# These commands will be in the beginning of most pipelines
WORKDIR=options.output

if options.clearAll and "clear" not in options.csc:
    options.csc += (",clear")
CSC_WORKDIR = os.path.join("CSCConnection",WORKDIR.lstrip("/"))
detector.setCSCConnection(options.csc, CSC_WORKDIR)

TRAIN_FILES = options.trainFile.split(",")
DEVEL_FILES = options.develFile.split(",")
EMPTY_DEVEL_FILES = [x.replace(".xml", "-empty.xml") for x in DEVEL_FILES]
if not options.noTestSet:
    TEST_FILE = options.testFile

workdir(WORKDIR, options.clearAll) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

    
###############################################################################
# Edge example generation and model upload
###############################################################################
if selector.check("TRAIN"):
    print >> sys.stderr, "------------ Train Edge Detector ------------"
    detector.train(TRAIN_FILES, DEVEL_FILES, "model-devel", "model-test", 
                   "style:"+options.styles, "c:"+options.params, options.parse, options.tokenization, options.task,
                   fromStep=options.detectorStep)
if selector.check("DEVEL"):
    print >> sys.stderr, "------------ Check devel classification ------------"
    detector.classify(DEVEL_FILES[0], "model-devel", "predicted-devel")
#if selector.check("EMPTY"):    
#    print >> sys.stderr, "------------ Empty devel classification ------------"
#    detector.classify(EMPTY_DEVEL_FILES[0], "model-devel", "predicted-devel-empty")
if not options.noTestSet:
    if selector.check("TEST"):    
        print >> sys.stderr, "------------ Test set classification ------------"
        detector.classify(TEST_FILE, "model-test", "predicted-test")
        STFormat.Compare.compare("predicted-test.tar.gz", "predicted-devel.tar.gz", "a2")
