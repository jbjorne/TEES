# Optimize parameters for task 3 and produce speculation and negation model files

# most imports are defined in Pipeline
from Pipeline import *
import sys, os

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-e", "--test", default=Settings.DevelFileWithDuplicates, dest="testFile", help="Test file in interaction xml")
optparser.add_option("-r", "--train", default=Settings.TrainFileWithDuplicates, dest="trainFile", help="Train file in interaction xml")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-a", "--task", default=123, type="int", dest="task", help="task number")
optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="Tokenization XML element name")
# Id sets
optparser.add_option("-i", "--task3Ids", default=Settings.Task3Ids, dest="task3Ids", help="Speculation & negation SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
# Parameters to optimize
optparser.add_option("-x", "--speculationParams", default="1000,5000,10000,13000,16000,20000,50000", dest="speculationParams", help="Speculation SVM c-parameter values")
optparser.add_option("-y", "--negationParams", default="1000,5000,10000,13000,16000,20000,50000", dest="negationParams", help="Negation SVM c-parameter values")
(options, args) = optparser.parse_args()

# Check options
assert options.output != None
assert options.task in [13, 123]

# Main settings
PARSE=options.parse
TOK=options.tokenization
TRAIN_FILE = options.trainFile
TEST_FILE = options.testFile

# These commands will be in the beginning of most pipelines
WORKDIR=options.output
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

PARSE_TAG = PARSE + "_" + TOK
TASK3_IDS = copyIdSetsToWorkdir(options.task3Ids)

###############################################################################
# Speculation
###############################################################################
print >> sys.stderr, "Speculation examples for parse", PARSE_TAG  
Task3ExampleBuilder.run(TRAIN_FILE, "speculation-train-examples", PARSE, TOK, "style:typed,speculation", TASK3_IDS, None)
Task3ExampleBuilder.run(TEST_FILE, "speculation-test-examples", PARSE, TOK, "style:typed,speculation", TASK3_IDS, None)
print >> sys.stderr, "Speculation models for parse", PARSE_TAG
optimize(Cls, Ev, "speculation-train-examples", "speculation-test-examples",\
    TASK3_IDS+".class_names", "c:" + options.speculationParams, "speculation-models")

###############################################################################
# Negation
###############################################################################
print >> sys.stderr, "Negation examples for parse", PARSE_TAG  
Task3ExampleBuilder.run(TRAIN_FILE, "negation-train-examples", PARSE, TOK, "style:typed,negation", TASK3_IDS, None)
Task3ExampleBuilder.run(TEST_FILE, "negation-test-examples", PARSE, TOK, "style:typed,negation", TASK3_IDS, None)
print >> sys.stderr, "Negation models for parse", PARSE_TAG
optimize(Cls, Ev, "negation-train-examples", "negation-test-examples",\
    TASK3_IDS+".class_names", "c:" + options.negationParams, "negation-models")
