# Optimize parameters for event detection and produce event and entrel model files

# most imports are defined in Pipeline
from Pipeline import *
from ExampleBuilders.EntityRelationExampleBuilder import EntityRelationExampleBuilder
import sys, os

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-e", "--test", default="/home/jari/biotext/BioNLP2011/data/REL/rel-devel.xml", dest="testFile", help="Test file in interaction xml")
optparser.add_option("-r", "--train", default="/home/jari/biotext/BioNLP2011/data/REL/rel-train.xml", dest="trainFile", help="Train file in interaction xml")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-a", "--task", default=1, type="int", dest="task", help="task number")
optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="Tokenization XML element name")
# Classifier
optparser.add_option("-c", "--classifier", default="Cls", dest="classifier", help="")
optparser.add_option("--csc", default="murska", dest="csc", help="")
# Example builders
optparser.add_option("-f", "--exampleBuilder", default="EntityRelationExampleBuilder", dest="exampleBuilder", help="")
optparser.add_option("-s", "--styles", default="trigger_features,typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures", dest="entrelStyles", help="")
#optparser.add_option("-g", "--gazetteer", default="none", dest="gazetteer", help="gazetteer options: none, stem, full")
# Id sets
optparser.add_option("-v", "--entrelIds", default=None, dest="entrelIds", help="Trigger detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
# Parameters to optimize
optparser.add_option("-x", "--entrelParams", default="0.01,0.1,0,1,10,100,1000,5000,10000,20000,25000,28000,50000,60000,65000,80000,100000,150000,500000,1000000", dest="entrelParams", help="Trigger detector c-parameter values")
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

# Example generation parameters
#ENTREL_FEATURE_PARAMS="style:typed"
ENTREL_FEATURE_PARAMS="style:" + options.entrelStyles

# These commands will be in the beginning of most pipelines
WORKDIR=options.output
CSC_WORKDIR = os.path.join("CSCConnection",WORKDIR.lstrip("/"))

workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

ENTREL_TRAIN_EXAMPLE_FILE = "entrel-train-examples-"+PARSE_TAG
ENTREL_TEST_EXAMPLE_FILE = "entrel-test-examples-"+PARSE_TAG
ENTREL_IDS = "entrel-ids"
if not "eval" in options.csc:
    ENTREL_EXAMPLE_BUILDER = eval(options.exampleBuilder)
    
    ###############################################################################
    # Example generation
    ###############################################################################
    ENTREL_EXAMPLE_BUILDER.run(TEST_FILE, ENTREL_TEST_EXAMPLE_FILE, PARSE, TOK, ENTREL_FEATURE_PARAMS, ENTREL_IDS)
    ENTREL_EXAMPLE_BUILDER.run(TRAIN_FILE, ENTREL_TRAIN_EXAMPLE_FILE, PARSE, TOK, ENTREL_FEATURE_PARAMS, ENTREL_IDS)

print >> sys.stderr, "entrel models for", PARSE_TAG
ENTREL_CLASSIFIER_PARAMS="c:" + options.entrelParams
if "local" not in options.csc:
    clear = False
    if "clear" in options.csc: clear = True
    if "louhi" in options.csc:
        c = CSCConnection(CSC_WORKDIR+"/entrel-models"+PARSE_TAG, "jakrbj@louhi.csc.fi", clear)
    else:
        c = CSCConnection(CSC_WORKDIR+"/entrel-models"+PARSE_TAG, "jakrbj@murska.csc.fi", clear)
else:
    c = None
bestentrelModel = optimize(CLASSIFIER, Ev, ENTREL_TRAIN_EXAMPLE_FILE, ENTREL_TEST_EXAMPLE_FILE,\
    ENTREL_IDS+".class_names", ENTREL_CLASSIFIER_PARAMS, "entrel-models", None, c, False)[1]

Cls.test(ENTREL_TEST_EXAMPLE_FILE, bestentrelModel, "entrel-test-classifications")
#entrelXML = BioTextExampleWriter.write(ENTREL_TEST_EXAMPLE_FILE+tag, "entrel-test-classifications"+tag, entrelXML, "test-predicted-entrels"+tag+".xml", ENTREL_IDS+".class_names", PARSE, TOK)
#EvaluateInteractionXML.run(Ev, entrelXML, TEST_FILE, PARSE, TOK)
#gifxmlToGenia(entrelXML, "geniaformat", options.task)
#evaluateSharedTask("geniaformat", options.task)
