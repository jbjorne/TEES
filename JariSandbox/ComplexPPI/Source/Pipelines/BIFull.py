# Optimize parameters for event detection and produce event and edge model files

# most imports are defined in Pipeline
from Pipeline import *
import sys, os
import STFormat.ConvertXML

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-e", "--test", default=Settings.DevelFile, dest="testFile", help="Test file in interaction xml")
optparser.add_option("-r", "--train", default=Settings.TrainFile, dest="trainFile", help="Train file in interaction xml")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-a", "--task", default="BI", dest="task", help="task number")
optparser.add_option("-p", "--parse", default="split-mccc-preparsed", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default="split-mccc-preparsed", dest="tokenization", help="Tokenization XML element name")
# Classifier
optparser.add_option("-c", "--classifier", default="Cls", dest="classifier", help="")
optparser.add_option("--csc", default="murska", dest="csc", help="")
# Example builders
optparser.add_option("-f", "--edgeExampleBuilder", default="MultiEdgeExampleBuilder", dest="edgeExampleBuilder", help="")
optparser.add_option("-s", "--styles", default="trigger_features,typed,directed,no_linear,entities,noMasking,maxFeatures,bi_limits", dest="edgeStyles", help="")
#optparser.add_option("-g", "--gazetteer", default="none", dest="gazetteer", help="gazetteer options: none, stem, full")
# Id sets
optparser.add_option("-v", "--edgeIds", default=None, dest="edgeIds", help="Trigger detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
# Parameters to optimize
optparser.add_option("-x", "--edgeParams", default="10,100,1000,2500,5000,7500,10000,20000,25000,28000,50000,60000,65000,80000,100000,150000", dest="edgeParams", help="Trigger detector c-parameter values")
optparser.add_option("--clearAll", default=False, action="store_true", dest="clearAll", help="Delete all files")
(options, args) = optparser.parse_args()

# Check options
assert options.output != None
assert options.task in ["BI"]
dataPath = "/home/jari/biotext/BioNLP2011/data/main-tasks/"
TRAIN_FILE = dataPath + options.task + "/" + options.task + "-train-nodup.xml"
TEST_FILE = dataPath + options.task + "/" + options.task + "-devel-nodup.xml"
EVERYTHING_FILE = dataPath + options.task + "/" + options.task + "-devel-and-train.xml"
FINAL_TEST_FILE = dataPath + options.task + "/" + options.task + "-test.xml"

if options.csc.find(",") != -1:
    options.csc = options.csc.split(",")
else:
    options.csc = [options.csc]
if options.clearAll and "clear" not in options.csc:
    options.csc.append("clear")

exec "CLASSIFIER = " + options.classifier

# Main settings
PARSE=options.parse
TOK=options.tokenization
PARSE_TAG = PARSE + "_" + TOK

# These commands will be in the beginning of most pipelines
WORKDIR=options.output
CSC_WORKDIR = os.path.join("CSCConnection",WORKDIR.lstrip("/"))

workdir(WORKDIR, options.clearAll) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

# Example generation parameters
#EDGE_FEATURE_PARAMS="style:typed"
EDGE_FEATURE_PARAMS="style:" + options.edgeStyles
print >> sys.stderr, "Edge feature style:", EDGE_FEATURE_PARAMS

EDGE_TRAIN_EXAMPLE_FILE = "edge-train-examples-"+PARSE_TAG
EDGE_EVERYTHING_EXAMPLE_FILE = "edge-everything-examples-"+PARSE_TAG
EDGE_TEST_EXAMPLE_FILE = "edge-test-examples-"+PARSE_TAG
EDGE_FINAL_TEST_EXAMPLE_FILE = "edge-final-examples-"+PARSE_TAG
EDGE_IDS = "edge-ids"
#STEPS = [""]
#STEPS = ["themeOnly", "causeAfterTheme"]
#STEPS = ["causeAfterTheme"]
if not "eval" in options.csc:
    EDGE_EXAMPLE_BUILDER = eval(options.edgeExampleBuilder)
    
    ###############################################################################
    # Edge example generation
    ###############################################################################
    EDGE_EXAMPLE_BUILDER.run(TEST_FILE, EDGE_TEST_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    EDGE_EXAMPLE_BUILDER.run(TRAIN_FILE, EDGE_TRAIN_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    EDGE_EXAMPLE_BUILDER.run(EVERYTHING_FILE, EDGE_EVERYTHING_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    EDGE_EXAMPLE_BUILDER.run(FINAL_TEST_FILE, EDGE_FINAL_TEST_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)

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
bestEdgeModel = optimize(CLASSIFIER, Ev, EDGE_TRAIN_EXAMPLE_FILE, EDGE_TEST_EXAMPLE_FILE,\
EDGE_IDS+".class_names", EDGE_CLASSIFIER_PARAMS, "edge-models", None, c, False)

# Check devel classification
Cls.test(EDGE_TEST_EXAMPLE_FILE, bestEdgeModel[1], "edge-test-classifications")
xml = BioTextExampleWriter.write(EDGE_TEST_EXAMPLE_FILE, "edge-test-classifications", TEST_FILE, None, EDGE_IDS+".class_names", PARSE, TOK)
xml = ix.splitMergedElements(xml, None)
xml = ix.recalculateIds(xml, "devel-predicted-edges.xml", True)
EvaluateInteractionXML.run(Ev, xml, TEST_FILE, PARSE, TOK)
STFormat.ConvertXML.toSTFormat(xml, "devel-geniaformat", outputTag="a2")

# Test set classification
if "local" not in options.csc:
    clear = False
    if "clear" in options.csc: clear = True
    if "louhi" in options.csc:
        c = CSCConnection(CSC_WORKDIR+"/edge-everything-models", "jakrbj@louhi.csc.fi", clear)
    else:
        c = CSCConnection(CSC_WORKDIR+"/edge-everything-models", "jakrbj@murska.csc.fi", clear)
else:
    c = None
finalEdgeModel = optimize(CLASSIFIER, Ev, EDGE_EVERYTHING_EXAMPLE_FILE, EDGE_TEST_EXAMPLE_FILE,\
EDGE_IDS+".class_names", "c:"+bestEdgeModel[2].split("_")[-1], "edge-everything-models", None, c, False)[1]
Cls.test(EDGE_FINAL_TEST_EXAMPLE_FILE, finalEdgeModel, "final-edge-test-classifications")
xml = BioTextExampleWriter.write(EDGE_FINAL_TEST_EXAMPLE_FILE, "final-edge-test-classifications", FINAL_TEST_FILE, None, EDGE_IDS+".class_names", PARSE, TOK)
xml = ix.splitMergedElements(xml, None)
xml = ix.recalculateIds(xml, "final-predicted-edges.xml", True)
EvaluateInteractionXML.run(Ev, xml, FINAL_TEST_FILE, PARSE, TOK)
STFormat.ConvertXML.toSTFormat(xml, "final-geniaformat", outputTag="a2")