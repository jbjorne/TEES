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
# Classifier
optparser.add_option("-c", "--classifier", default="Cls", dest="classifier", help="")
optparser.add_option("--csc", default="murska", dest="csc", help="")
# Example builders
optparser.add_option("-f", "--triggerExampleBuilder", default="GeneralEntityTypeRecognizerGztr", dest="triggerExampleBuilder", help="")
optparser.add_option("-s", "--styles", default="typed", dest="triggerStyles", help="")
optparser.add_option("-g", "--gazetteer", default="none", dest="gazetteer", help="gazetteer options: none, stem, full")
# Id sets
optparser.add_option("-v", "--triggerIds", default=None, dest="triggerIds", help="Trigger detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
# Parameters to optimize
optparser.add_option("-x", "--triggerParams", default="1000,5000,10000,20000,50000,80000,100000,150000,180000,200000,250000,300000,350000,500000,1000000", dest="triggerParams", help="Trigger detector c-parameter values")
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
#TRIGGER_FEATURE_PARAMS="style:typed"
TRIGGER_FEATURE_PARAMS="style:" + options.triggerStyles

# These commands will be in the beginning of most pipelines
WORKDIR=options.output
CSC_WORKDIR = os.path.join("CSCConnection",WORKDIR.lstrip("/"))

workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

TRIGGER_TRAIN_EXAMPLE_FILE = "trigger-train-examples-"+PARSE_TAG
TRIGGER_TEST_EXAMPLE_FILE = "trigger-test-examples-"+PARSE_TAG
TRIGGER_IDS = "trigger-ids"
if not "eval" in options.csc:
    TRIGGER_EXAMPLE_BUILDER = eval(options.triggerExampleBuilder)
    
    # Pre-calculate all the required SVM models
    if options.triggerIds != None:
        TRIGGER_IDS = copyIdSetsToWorkdir(options.triggerIds)
    
    ###############################################################################
    # Gazetteer
    ###############################################################################
    if options.gazetteer == "none":
        pass
    elif options.gazetteer == "full":
        stemGazetteer = False
        GAZ_TAG = "-gazfull"
    elif options.gazetteer == "stem":
        stemGazetteer = True
        GAZ_TAG = "-gazstem"
        
    GAZETTEER_TRAIN = None
    if options.gazetteer != "none":
        GAZETTEER_TRAIN = "gazetteer-train-"+PARSE_TAG+GAZ_TAG
        Gazetteer.run(TRAIN_FILE, GAZETTEER_TRAIN, TOK, entityOffsetKey="charOffset", stem=stemGazetteer)
    
    ###############################################################################
    # Trigger example generation
    ###############################################################################
    print >> sys.stderr, "Trigger examples for parse", PARSE_TAG   
    print >> sys.stderr, "Trigger style:", options.triggerStyles
    TRIGGER_EXAMPLE_BUILDER.run(TEST_FILE, TRIGGER_TEST_EXAMPLE_FILE, PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS, GAZETTEER_TRAIN)
    TRIGGER_EXAMPLE_BUILDER.run(TRAIN_FILE, TRIGGER_TRAIN_EXAMPLE_FILE, PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS, GAZETTEER_TRAIN)

###############################################################################
# Trigger models
###############################################################################
print >> sys.stderr, "Trigger models for parse", PARSE_TAG
TRIGGER_CLASSIFIER_PARAMS="c:" + options.triggerParams
if "local" not in options.csc:
    clear = False
    if "clear" in options.csc: clear = True
    if "louhi" in options.csc:
        c = CSCConnection(CSC_WORKDIR+"/trigger-models", "jakrbj@louhi.csc.fi", clear)
    else:
        c = CSCConnection(CSC_WORKDIR+"/trigger-models", "jakrbj@murska.csc.fi", clear)
else:
    c = None
bestTriggerModel = optimize(CLASSIFIER, Ev, TRIGGER_TRAIN_EXAMPLE_FILE, TRIGGER_TEST_EXAMPLE_FILE,\
    TRIGGER_IDS+".class_names", TRIGGER_CLASSIFIER_PARAMS, "trigger-models", None, c, False)[1]

Cls.test(TRIGGER_TEST_EXAMPLE_FILE, bestTriggerModel, "trigger-test-classifications")
triggerXML = BioTextExampleWriter.write(TRIGGER_TEST_EXAMPLE_FILE, "trigger-test-classifications", TEST_FILE, "test-predicted-triggers.xml", TRIGGER_IDS+".class_names", PARSE, TOK)
