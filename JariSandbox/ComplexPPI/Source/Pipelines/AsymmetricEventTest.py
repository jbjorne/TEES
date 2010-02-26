# Optimize parameters for event detection and produce event and trigger model files

# most imports are defined in Pipeline
from Pipeline import *
import sys, os

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-e", "--test", default=Settings.DevelFile, dest="testFile", help="Test file in interaction xml")
optparser.add_option("-r", "--train", default=Settings.TrainFile, dest="trainFile", help="Train file in interaction xml")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-a", "--task", default=1, type="int", dest="task", help="task number")
optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="Tokenization XML element name")
#optparser.add_option("-m", "--mode", default="BOTH", dest="mode", help="MODELS (recalculate SVM models), GRID (parameter grid search) or BOTH")
# Example builders
optparser.add_option("-f", "--triggerExampleBuilder", default="GeneralEntityTypeRecognizerGztr", dest="triggerExampleBuilder", help="")
#optparser.add_option("-g", "--edgeExampleBuilder", default="MultiEdgeExampleBuilder", dest="edgeExampleBuilder", help="")
# Id sets
optparser.add_option("-v", "--triggerIds", default=None, dest="triggerIds", help="Trigger detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
#optparser.add_option("-w", "--edgeIds", default=None, dest="edgeIds", help="Edge detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
# Parameters to optimize
optparser.add_option("-x", "--triggerParams", default="1000,5000,10000,20000,50000,80000,100000,150000,180000,200000,250000,300000,350000,500000,1000000", dest="triggerParams", help="Trigger detector c-parameter values")
#optparser.add_option("-y", "--recallAdjustParams", default="0.5,0.6,0.65,0.7,0.85,1.0", dest="recallAdjustParams", help="Recall adjuster parameter values")
#optparser.add_option("-z", "--edgeParams", default="5000,10000,20000,25000,28000,50000,60000,65000,80000,100000,150000", dest="edgeParams", help="Edge detector c-parameter values")
(options, args) = optparser.parse_args()

# Check options
#assert options.mode in ["MODELS", "FINAL", "BOTH"]
assert options.output != None
assert options.task in [1, 2]

# Main settings
PARSE=options.parse
TOK=options.tokenization
PARSE_TAG = PARSE + "_" + TOK
TRAIN_FILE = options.trainFile
TEST_FILE = options.testFile

# Example generation parameters
TRIGGER_FEATURE_PARAMS="style:typed,directed"

#boosterParams = [float(i) for i in options.recallAdjustParams.split(",")] 

# These commands will be in the beginning of most pipelines
WORKDIR=options.output
CSC_WORKDIR = os.path.join("CSCConnection",WORKDIR.lstrip("/"))

workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

#exec "from Core.ExampleBuilders." + options.triggerExampleBuilder + " import " + options.triggerExampleBuilder
TRIGGER_EXAMPLE_BUILDER = eval(options.triggerExampleBuilder)

# Pre-calculate all the required SVM models
TRIGGER_IDS = "trigger-ids"
if options.triggerIds != None:
    TRIGGER_IDS = copyIdSetsToWorkdir(options.triggerIds)

###############################################################################
# Trigger example generation
###############################################################################
TRIGGER_TRAIN_EXAMPLE_FILE = "trigger-train-examples-"+PARSE_TAG
TRIGGER_TEST_EXAMPLE_FILE = "trigger-test-examples-"+PARSE_TAG
print >> sys.stderr, "Trigger examples for parse", PARSE_TAG   
TRIGGER_EXAMPLE_BUILDER.run(TRAIN_FILE, TRIGGER_TRAIN_EXAMPLE_FILE, PARSE, TOK, TRIGGER_FEATURE_PARAMS+",negFrac_0.1", TRIGGER_IDS)
TRIGGER_EXAMPLE_BUILDER.run(TEST_FILE, TRIGGER_TEST_EXAMPLE_FILE, PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)

###############################################################################
# Trigger models
###############################################################################
print >> sys.stderr, "Trigger models for parse", PARSE_TAG
TRIGGER_CLASSIFIER_PARAMS="c:" + options.triggerParams
c = CSCConnection(CSC_WORKDIR+"/trigger-models", "jakrbj@murska.csc.fi", False)
bestTriggerModel = optimize(Cls, Ev, TRIGGER_TRAIN_EXAMPLE_FILE, TRIGGER_TEST_EXAMPLE_FILE,\
    TRIGGER_IDS+".class_names", TRIGGER_CLASSIFIER_PARAMS, "trigger-models", None, c, True)[1]