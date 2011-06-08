# Optimize parameters for event detection and produce event and edge model files

# most imports are defined in Pipeline
from Pipeline import *
import sys, os
import STFormat.ConvertXML
from Utils.BioNLP2011 import DDITools

from optparse import OptionParser
optparser = OptionParser()
dataPath = "/home/jari/biotext/DDIExtraction2011/data/"
optparser.add_option("-d", "--devel", default=dataPath+"DrugDDI-devel.xml", dest="develFile", help="Devel file in interaction xml")
optparser.add_option("-e", "--test", default=dataPath+"DrugDDI-test.xml", dest="testFile", help="Test file in interaction xml")
optparser.add_option("-r", "--train", default=dataPath+"DrugDDI-train.xml", dest="trainFile", help="Train file in interaction xml")
optparser.add_option("-b", "--develAndTrain", default=dataPath+"DrugDDI-devel-and-train.xml", dest="develAndTrainFile", help="Devel+train file in interaction xml")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-a", "--task", default=1, type="int", dest="task", help="task number")
optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="Tokenization XML element name")
# Classifier
optparser.add_option("-c", "--classifier", default="Cls", dest="classifier", help="")
optparser.add_option("--csc", default="murska", dest="csc", help="")
# Example builders
optparser.add_option("-f", "--edgeExampleBuilder", default="MultiEdgeExampleBuilder", dest="edgeExampleBuilder", help="")
optparser.add_option("-s", "--styles", default="trigger_features,typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures", dest="edgeStyles", help="")
#optparser.add_option("-g", "--gazetteer", default="none", dest="gazetteer", help="gazetteer options: none, stem, full")
# Id sets
optparser.add_option("-v", "--edgeIds", default=None, dest="edgeIds", help="Trigger detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
# Parameters to optimize
optparser.add_option("-x", "--edgeParams", default="5000,10000,20000,25000,28000,50000,60000,65000,80000,100000,150000", dest="edgeParams", help="Trigger detector c-parameter values")
optparser.add_option("--clearAll", default=False, action="store_true", dest="clearAll", help="Delete all files")
(options, args) = optparser.parse_args()

# Check options
assert options.output != None
assert options.task in [1, 2]

if options.csc.find(",") != -1:
    options.csc = options.csc.split(",")
else:
    options.csc = [options.csc]

exec "CLASSIFIER = " + options.classifier

# Main settings
PARSE=options.parse
TOK=options.tokenization
PARSE_TAG = PARSE + "_" + TOK
TRAIN_FILE = options.trainFile
TEST_FILE = options.testFile
DEVEL_FILE = options.develFile
DEVEL_AND_TRAIN_FILE = options.develAndTrainFile

# These commands will be in the beginning of most pipelines
WORKDIR=options.output
CSC_WORKDIR = os.path.join("CSCConnection",WORKDIR.lstrip("/"))

if options.clearAll and "clear" not in options.csc:
    options.csc.append("clear")
workdir(WORKDIR, options.clearAll) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

# Example generation parameters
#EDGE_FEATURE_PARAMS="style:typed"
EDGE_FEATURE_PARAMS="style:" + options.edgeStyles
print >> sys.stderr, "Edge feature style:", EDGE_FEATURE_PARAMS

EDGE_TRAIN_EXAMPLE_FILE = "edge-train-examples-"+PARSE_TAG
EDGE_TEST_EXAMPLE_FILE = "edge-test-examples-"+PARSE_TAG
EDGE_DEVEL_EXAMPLE_FILE = "edge-devel-examples-"+PARSE_TAG
EDGE_DEVEL_AND_TRAIN_EXAMPLE_FILE = "edge-devel-and-train-examples-"+PARSE_TAG
EDGE_IDS = "edge-ids"
if not "eval" in options.csc:
    EDGE_EXAMPLE_BUILDER = eval(options.edgeExampleBuilder)
    ###############################################################################
    # Edge example generation
    ###############################################################################
    EDGE_EXAMPLE_BUILDER.run(DEVEL_FILE, EDGE_DEVEL_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    EDGE_EXAMPLE_BUILDER.run(TEST_FILE, EDGE_TEST_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    EDGE_EXAMPLE_BUILDER.run(TRAIN_FILE, EDGE_TRAIN_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    EDGE_EXAMPLE_BUILDER.run(DEVEL_AND_TRAIN_FILE, EDGE_DEVEL_AND_TRAIN_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)

print >> sys.stderr, "Edge models for", PARSE_TAG
EDGE_CLASSIFIER_PARAMS="c:" + options.edgeParams
if "local" not in options.csc:
    clear = False
    if "clear" in options.csc: clear = True
    if "louhi" in options.csc:
        c = CSCConnection(CSC_WORKDIR+"/edge-models", "jakrbj@louhi.csc.fi", clear)
    else:
        c = CSCConnection(CSC_WORKDIR+"/edge-models", "jakrbj@murska.csc.fi", clear)
else:
    c = None
    
bestResult = optimize(CLASSIFIER, Ev, EDGE_TRAIN_EXAMPLE_FILE, EDGE_DEVEL_EXAMPLE_FILE,\
EDGE_IDS+".class_names", EDGE_CLASSIFIER_PARAMS, "edge-models", None, c, False)
assert "c" in bestResult[4], bestResult
bestCParam = int(bestResult[4]["c"])
bestEdgeModel = bestResult[1]

print >> sys.stderr, "Classifying devel set with best edge model"
Cls.test(EDGE_DEVEL_EXAMPLE_FILE, bestEdgeModel, "edge-devel-classifications")
develEdgeXML = BioTextExampleWriter.write(EDGE_DEVEL_EXAMPLE_FILE, "edge-devel-classifications", DEVEL_FILE, "devel-predicted-edges.xml", EDGE_IDS+".class_names", PARSE, TOK)
EvaluateInteractionXML.run(Ev, develEdgeXML, DEVEL_FILE, PARSE, TOK)
#STFormat.ConvertXML.toSTFormat(edgeXML, "geniaformat", outputTag="a2")

print >> sys.stderr, "Classifying test set with best devel edge model"
Cls.test(EDGE_TEST_EXAMPLE_FILE, bestEdgeModel, "edge-test-classifications")
testEdgeXML = BioTextExampleWriter.write(EDGE_TEST_EXAMPLE_FILE, "edge-test-classifications", TEST_FILE, "test-predicted-edges.xml", EDGE_IDS+".class_names", PARSE, TOK)
EvaluateInteractionXML.run(Ev, testEdgeXML, TEST_FILE, PARSE, TOK)
print >> sys.stderr, "Writing submission file"
DDITools.makeDDISubmissionFile(testEdgeXML, "ddi-submission.txt")

print >> sys.stderr, "Final model for test set"
EDGE_CLASSIFIER_PARAMS="c:" + str(bestCParam)
if "local" not in options.csc:
    clear = False
    if "clear" in options.csc: clear = True
    if "louhi" in options.csc:
        c = CSCConnection(CSC_WORKDIR+"/devel-and-train-edge-model", "jakrbj@louhi.csc.fi", clear)
    else:
        c = CSCConnection(CSC_WORKDIR+"/devel-and-train-edge-model", "jakrbj@murska.csc.fi", clear)
else:
    c = None
finalEdgeModel = optimize(CLASSIFIER, Ev, EDGE_DEVEL_AND_TRAIN_EXAMPLE_FILE, EDGE_DEVEL_EXAMPLE_FILE,\
EDGE_IDS+".class_names", EDGE_CLASSIFIER_PARAMS, "devel-and-train-edge-model", None, c, False)[1]

print >> sys.stderr, "Classifying test set with best devel+train edge model"
Cls.test(EDGE_TEST_EXAMPLE_FILE, finalEdgeModel, "edge-final-test-classifications")
testEdgeXML = BioTextExampleWriter.write(EDGE_TEST_EXAMPLE_FILE, "edge-final-test-classifications", TEST_FILE, "final-test-predicted-edges.xml", EDGE_IDS+".class_names", PARSE, TOK)
EvaluateInteractionXML.run(Ev, testEdgeXML, TEST_FILE, PARSE, TOK)
print >> sys.stderr, "Writing final submission file"
DDITools.makeDDISubmissionFile(testEdgeXML, "final-ddi-submission.txt")
