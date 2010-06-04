# Optimize parameters for event detection and produce event and trigger model files

# most imports are defined in Pipeline
from Pipeline import *
import sys, os

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-e", "--test", default=Settings.DevelFile, dest="testFile", help="Test file in interaction xml")
#optparser.add_option("-r", "--train", default=Settings.TrainFile, dest="trainFile", help="Train file in interaction xml")
optparser.add_option("-f", "--goldTest", default=None, dest="goldTestFile", help="Train file in interaction xml")
#optparser.add_option("-g", "--goldTrain", default=None, dest="goldTrainFile", help="Train file in interaction xml")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-a", "--task", default=1, type="int", dest="task", help="task number")
optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="Tokenization XML element name")
# Classifier
optparser.add_option("-c", "--classifier", default="Cls", dest="classifier", help="")
#optparser.add_option("--csc", default="murska", dest="csc", help="")
# Example builders
optparser.add_option("-s", "--styles", default="typed", dest="triggerStyles", help="")
# Id sets
optparser.add_option("-v", "--triggerIds", default=None, dest="triggerIds", help="Trigger detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
# Parameters to optimize
optparser.add_option("-m", "--model", default=None, dest="model", help="")
#optparser.add_option("-x", "--triggerParams", default="0.01,0.1,1,10,100,1000,5000,10000,20000,50000,80000,100000,150000,180000,200000,250000,300000,350000,500000,1000000", dest="triggerParams", help="Trigger detector c-parameter values")
(options, args) = optparser.parse_args()

# Check options
assert options.output != None
assert options.task in [1, 2]

exec "CLASSIFIER = " + options.classifier

# Main settings
PARSE=options.parse
TOK=options.tokenization
PARSE_TAG = PARSE + "_" + TOK
#TRAIN_FILE = options.trainFile
#GOLD_TRAIN_FILE = options.goldTrainFile
TEST_FILE = options.testFile
GOLD_TEST_FILE = options.goldTestFile

# Example generation parameters
#TRIGGER_FEATURE_PARAMS="style:typed"
UNMERGING_FEATURE_PARAMS="style:" + options.triggerStyles

# These commands will be in the beginning of most pipelines
WORKDIR=options.output

workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

UNMERGING_TRAIN_EXAMPLE_FILE = "unmerging-train-examples-"+PARSE_TAG
UNMERGING_TEST_EXAMPLE_FILE = "unmerging-test-examples-"+PARSE_TAG

UNMERGING_IDS = "unmerging-ids"
if False:
    ###############################################################################
    # Trigger example generation
    ###############################################################################
    print >> sys.stderr, "Unmerging examples for parse", PARSE_TAG   
    UNMERGING_IDS = copyIdSetsToWorkdir(options.triggerIds)
    UnmergingExampleBuilder.run(TEST_FILE, GOLD_TEST_FILE, UNMERGING_TEST_EXAMPLE_FILE, PARSE, TOK, UNMERGING_FEATURE_PARAMS, UNMERGING_IDS)
    #UnmergingExampleBuilder.run(TRAIN_FILE, GOLD_TRAIN_FILE, UNMERGING_TRAIN_EXAMPLE_FILE, PARSE, TOK, UNMERGING_FEATURE_PARAMS, UNMERGING_IDS)
    Cls.test(UNMERGING_TEST_EXAMPLE_FILE, options.model, "unmerging-test-classifications")

xml = BioTextExampleWriter.write(UNMERGING_TEST_EXAMPLE_FILE, "unmerging-test-classifications", TEST_FILE, "test-predicted-unmerging.xml", UNMERGING_IDS+".class_names", PARSE, TOK)
gifxmlToGenia(xml, "geniaformat", options.task)
evaluateSharedTask("geniaformat", options.task)
