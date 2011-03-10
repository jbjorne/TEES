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
optparser.add_option("-p", "--parse", default="split-mccc-preparsed", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default=None, dest="tokenization", help="Tokenization XML element name")
optparser.add_option("--csc", default="", dest="csc", help="")
# Id sets
optparser.add_option("-i", "--task3Ids", default=Settings.Task3Ids, dest="task3Ids", help="Speculation & negation SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
# Parameters to optimize
optparser.add_option("-x", "--speculationParams", default="1000,2500,5000,7500,10000,13000,16000,20000,40000,50000,60000,100000,125000,150000,200000,300000,500000,1000000", dest="speculationParams", help="Speculation SVM c-parameter values")
optparser.add_option("-y", "--negationParams", default="1000,2500,5000,7500,10000,13000,16000,20000,50000", dest="negationParams", help="Negation SVM c-parameter values")
optparser.add_option("--clearAll", default=False, action="store_true", dest="clearAll", help="Delete all files")
(options, args) = optparser.parse_args()

# Check options
assert options.output != None
assert options.task in [13, 123]
if options.csc.find(",") != -1:
    options.csc = options.csc.split(",")
else:
    options.csc = [options.csc]
if options.clearAll and "clear" not in options.csc:
    options.csc.append("clear")

# Main settings
PARSE=options.parse
TOK=options.tokenization
TRAIN_FILES = options.trainFile.split(";")
TEST_FILES = options.testFile.split(";")

# These commands will be in the beginning of most pipelines
WORKDIR=options.output
CSC_WORKDIR = os.path.join("CSCConnection",WORKDIR.lstrip("/"))
workdir(WORKDIR, options.clearAll) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

PARSE_TAG = PARSE # + "_" + TOK

TASK3_IDS = os.path.basename(options.task3Ids)
if not "download" in options.csc and not "upload" in options.csc:
    ###############################################################################
    # Speculation Examples
    ###############################################################################
    TASK3_IDS = copyIdSetsToWorkdir(options.task3Ids)
    print >> sys.stderr, "Speculation train examples for parse", PARSE_TAG
    appendIndex = 0
    for TRAIN_FILE in TRAIN_FILES:
        Task3ExampleBuilder.run(TRAIN_FILE, "speculation-train-examples", PARSE, TOK, "style:typed,speculation", TASK3_IDS, None, appendIndex=appendIndex)
        appendIndex += 1000
    print >> sys.stderr, "Speculation test examples for parse", PARSE_TAG
    appendIndex = 0
    for TEST_FILE in TEST_FILES:
        Task3ExampleBuilder.run(TEST_FILE, "speculation-test-examples", PARSE, TOK, "style:typed,speculation", TASK3_IDS, None, appendIndex=appendIndex)
        appendIndex += 1000
    
    ###############################################################################
    # Negation Examples
    ###############################################################################
    print >> sys.stderr, "Negation train examples for parse", PARSE_TAG  
    appendIndex = 0
    for TRAIN_FILE in TRAIN_FILES:
        Task3ExampleBuilder.run(TRAIN_FILE, "negation-train-examples", PARSE, TOK, "style:typed,negation", TASK3_IDS, None, appendIndex=appendIndex)
        appendIndex += 1000
    print >> sys.stderr, "Negation test examples for parse", PARSE_TAG  
    appendIndex = 0
    for TEST_FILE in TEST_FILES:
        Task3ExampleBuilder.run(TEST_FILE, "negation-test-examples", PARSE, TOK, "style:typed,negation", TASK3_IDS, None, appendIndex=appendIndex)
        appendIndex += 1000

speculationCSC = None
negationCSC = None
if "local" not in options.csc:
    clear = False
    if "clear" in options.csc: clear = True
    cscAccount = "murska"
    if "louhi" in options.csc: cscAccount = "louhi"
    speculationCSC = CSCConnection(CSC_WORKDIR+"/speculation-models", "jakrbj@"+cscAccount+".csc.fi", clear)
    negationCSC = CSCConnection(CSC_WORKDIR+"/negation-models", "jakrbj@"+cscAccount+".csc.fi", clear)

# Upload
if not "download" in options.csc:
    print >> sys.stderr, "Speculation models for parse", PARSE_TAG
    optimize(Cls, Ev, "speculation-train-examples", "speculation-test-examples",\
        TASK3_IDS+".class_names", "c:" + options.speculationParams, "speculation-models", cscConnection=speculationCSC, steps="SUBMIT")
    print >> sys.stderr, "Negation models for parse", PARSE_TAG
    optimize(Cls, Ev, "negation-train-examples", "negation-test-examples",\
        TASK3_IDS+".class_names", "c:" + options.negationParams, "negation-models", cscConnection=negationCSC, steps="SUBMIT")

# Get results
print >> sys.stderr, "Speculation results for parse", PARSE_TAG
optimize(Cls, Ev, "speculation-train-examples", "speculation-test-examples",\
    TASK3_IDS+".class_names", "c:" + options.speculationParams, "speculation-models", cscConnection=speculationCSC, steps="RESULTS")
print >> sys.stderr, "Negation results for parse", PARSE_TAG
optimize(Cls, Ev, "negation-train-examples", "negation-test-examples",\
    TASK3_IDS+".class_names", "c:" + options.negationParams, "negation-models", cscConnection=negationCSC, steps="RESULTS")

