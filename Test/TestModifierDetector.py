# Optimize parameters for event detection and produce event and edge model files

# most imports are defined in Pipeline
from Pipeline import *
import sys, os
import STFormat.ConvertXML
import STFormat.Compare
from Detectors.SingleStageDetector import SingleStageDetector
from Detectors.StepSelector import StepSelector
from InteractionXML.MakeSubset import makeSubset

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-e", "--test", default=Settings.DevelFile, dest="testFile", help="Test file in interaction xml")
optparser.add_option("-r", "--train", default=Settings.TrainFile, dest="trainFile", help="Train file in interaction xml")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-a", "--task", default="BI", dest="task", help="task number")
optparser.add_option("-p", "--parse", default="gold", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default="gold", dest="tokenization", help="Tokenization XML element name")
# Classifier
optparser.add_option("-c", "--classifier", default="Cls", dest="classifier", help="")
optparser.add_option("--csc", default="murska", dest="csc", help="")
# Example builders
optparser.add_option("--downSampleTrain", default=1.0, type="float", dest="downSampleTrain", help="")
optparser.add_option("--downSampleSeed", default=1, type="int", dest="downSampleSeed", help="")
optparser.add_option("--noTestSet", default=False, action="store_true", dest="noTestSet", help="")
optparser.add_option("-f", "--edgeExampleBuilder", default="MultiEdgeExampleBuilder", dest="edgeExampleBuilder", help="")
optparser.add_option("-s", "--styles", default="multiclass,speculation", dest="edgeStyles", help="")
optparser.add_option("--step", default=None, dest="step", help="")
optparser.add_option("--detectorStep", default=None, dest="detectorStep", help="")
# Parameters to optimize
optparser.add_option("-x", "--edgeParams", default="1000,2500,5000,7500,10000,13000,16000,20000,40000,50000,60000,100000,125000,150000,200000,300000,500000,1000000", dest="edgeParams", help="Trigger detector c-parameter values")
optparser.add_option("--clearAll", default=False, action="store_true", dest="clearAll", help="Delete all files")
(options, args) = optparser.parse_args()

selector = StepSelector(["TRAIN", "DEVEL", "EMPTY", "TEST"], fromStep=options.step)

# Check options
assert options.output != None

exec "CLASSIFIER = " + options.classifier

if options.clearAll and "clear" not in options.csc:
    options.csc += (",clear")

# Main settings
detector = ModifierDetector()

# These commands will be in the beginning of most pipelines
WORKDIR=options.output
CSC_WORKDIR = os.path.join("CSCConnection",WORKDIR.lstrip("/"))

TRAIN_FILES = options.trainFile.split(",")
TEST_FILES = options.testFile.split(",")

workdir(WORKDIR, options.clearAll) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

    
###############################################################################
# Edge example generation and model upload
###############################################################################
if selector.check("TRAIN"):
    print >> sys.stderr, "------------ Train Edge Detector ------------"
    detector.train(TRAIN_FILES, TEST_FILES, "model-devel", "model-test", 
                   options.styles, options.edgeParams, options.parse, options.tokenization,
                   fromStep=options.detectorStep)
if selector.check("DEVEL"):
    print >> sys.stderr, "------------ Check devel classification ------------"
    detector.classify(TEST_FILE, "model-devel", "predicted-devel")
if selector.check("EMPTY"):    
    print >> sys.stderr, "------------ Empty devel classification ------------"
    detector.classify(TEST_FILE.replace(".xml", "-empty.xml"), "model-devel", "predicted-devel-empty")
if not options.noTestSet:
    if selector.check("TEST"):    
        print >> sys.stderr, "------------ Test set classification ------------"
        detector.classify(FINAL_TEST_FILE, "model-test", "predicted-test")
        STFormat.Compare.compare("predicted-test.tar.gz", "predicted-devel.tar.gz", "a2")
