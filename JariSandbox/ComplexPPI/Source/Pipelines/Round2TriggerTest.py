# Optimize parameters for event detection and produce event and trigger model files

# most imports are defined in Pipeline
from Pipeline import *
import sys, os

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-e", "--test", default=Settings.DevelFile, dest="testFile", help="Test file in interaction xml")
optparser.add_option("-r", "--train", default=Settings.TrainFile, dest="trainFile", help="Train file in interaction xml")
optparser.add_option("-f", "--goldTest", default=None, dest="goldTestFile", help="Train file in interaction xml")
optparser.add_option("-g", "--goldTrain", default=None, dest="goldTrainFile", help="Train file in interaction xml")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-a", "--task", default=1, type="int", dest="task", help="task number")
optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="Tokenization XML element name")
# Classifier
optparser.add_option("-c", "--classifier", default="Cls", dest="classifier", help="")
optparser.add_option("--csc", default="murska", dest="csc", help="")
optparser.add_option("-d", "--evaluator", default="Ev", dest="evaluator", help="")
# Example builders
optparser.add_option("-s", "--styles", default="typed", dest="triggerStyles", help="")
# Id sets
optparser.add_option("-v", "--triggerIds", default=None, dest="triggerIds", help="Trigger detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
# Parameters to optimize
#optparser.add_option("-x", "--triggerParams", default="0.01,0.1,1,10,100,1000,5000,10000,20000,50000,80000,100000,150000,180000,200000,250000,300000,350000,500000,1000000", dest="triggerParams", help="Trigger detector c-parameter values")
optparser.add_option("-x", "--triggerParams", default="0.01,0.1,1,10,100,1000,5000,10000,20000,50000,100000,1000000", dest="triggerParams", help="Trigger detector c-parameter values")
#optparser.add_option("-x", "--triggerParams", default="100,1000,2500,4000,5000,6000,7500,10000,20000", dest="triggerParams", help="Trigger detector c-parameter values")
(options, args) = optparser.parse_args()

# Check options
assert options.output != None
assert options.task in [1, 2]

if options.csc.find(",") != -1:
    options.csc = options.csc.split(",")
else:
    options.csc = [options.csc]

exec "CLASSIFIER = " + options.classifier
exec "EVALUATOR = " + options.evaluator

# Main settings
PARSE=options.parse
TOK=options.tokenization
PARSE_TAG = PARSE + "_" + TOK
TRAIN_FILE = options.trainFile
GOLD_TRAIN_FILE = options.goldTrainFile
TEST_FILE = options.testFile
GOLD_TEST_FILE = options.goldTestFile

# Example generation parameters
#TRIGGER_FEATURE_PARAMS="style:typed"
TRIGGER_FEATURE_PARAMS="style:" + options.triggerStyles

# These commands will be in the beginning of most pipelines
WORKDIR=options.output
CSC_WORKDIR = os.path.join("CSCConnection",WORKDIR.lstrip("/"))

workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

TRIGGER_TRAIN_EXAMPLE_FILE = "round2-trigger-train-examples-"+PARSE_TAG
TRIGGER_TEST_EXAMPLE_FILE = "round2-trigger-test-examples-"+PARSE_TAG
TRIGGER_IDS = "round2-trigger-ids"
TRIGGER_CLASSIFIER_PARAMS="c:" + options.triggerParams

###############################################################################
# Trigger example generation
###############################################################################
if not "eval" in options.csc and not "upload" in options.csc:
    print >> sys.stderr, "Round 2 trigger examples for parse", PARSE_TAG   
    Round2TriggerExampleBuilder.run(TEST_FILE, GOLD_TEST_FILE, TRIGGER_TEST_EXAMPLE_FILE, PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
    Round2TriggerExampleBuilder.run(TRAIN_FILE, GOLD_TRAIN_FILE, TRIGGER_TRAIN_EXAMPLE_FILE, PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
    
print >> sys.stderr, "Round 2 trigger models for parse", PARSE_TAG

if "local" not in options.csc:
    clear = False
    if "clear" in options.csc: clear = True
    if "louhi" in options.csc:
        c = CSCConnection(CSC_WORKDIR+"/round2-trigger-models", "jakrbj@louhi.csc.fi", clear)
    else:
        c = CSCConnection(CSC_WORKDIR+"/round2-trigger-models", "jakrbj@murska.csc.fi", clear)
else:
    c = None

if options.evaluator == "STEv":
    EVALUATOR.setOptions("temp", options.task, TEST_FILE, parse=PARSE, tokenization=TOK, ids=TRIGGER_IDS)

steps = "BOTH"
if "eval" in options.csc:
    steps = "RESULTS"
bestTriggerModel = optimize(CLASSIFIER, EVALUATOR, TRIGGER_TRAIN_EXAMPLE_FILE, TRIGGER_TEST_EXAMPLE_FILE,\
    TRIGGER_IDS+".class_names", TRIGGER_CLASSIFIER_PARAMS, "round2-trigger-models", None, c, False, steps=steps)[1]

Cls.test(TRIGGER_TEST_EXAMPLE_FILE, bestTriggerModel, "round2-trigger-test-classifications")
#triggerXML = BioTextExampleWriter.write(TRIGGER_TEST_EXAMPLE_FILE, "trigger-test-classifications", TEST_FILE, "test-predicted-triggers.xml", TRIGGER_IDS+".class_names", PARSE, TOK)
