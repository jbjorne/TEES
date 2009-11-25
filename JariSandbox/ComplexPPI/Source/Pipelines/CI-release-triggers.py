# most imports are defined in Pipeline
from Pipeline import *
import sys, os

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-n", "--name", default="triggers", dest="name", help="experiment name")
optparser.add_option("-t", "--task", default=1, type="int", dest="task", help="task number")
optparser.add_option("-g", "--gazetteer", default="none", dest="gazetteer", help="gazetteer options: none, stem, full")
(options, args) = optparser.parse_args()
assert(options.task in [1,2])
assert(options.gazetteer in ["none", "full", "stem"])

# define shortcuts for commonly used files
PARSE_TOK="split-McClosky"
CORPUS_DIR="/usr/share/biotext/GeniaChallenge/xml"

if task == 1:
    TRAIN_FILE=CORPUS_DIR+"/train.xml"
    DEVEL_FILE=CORPUS_DIR+"/devel.xml"
    TEST_FILE=CORPUS_DIR+"/test.xml"
    EVERYTHING_FILE=CORPUS_DIR+"/everything.xml"
    TASK_TAG=""
else:
    TRAIN_FILE=CORPUS_DIR+"/train12.xml"
    DEVEL_FILE=CORPUS_DIR+"/devel12.xml"
    TEST_FILE=CORPUS_DIR+"/test.xml"
    EVERYTHING_FILE=CORPUS_DIR+"/everything12.xml"
    TASK_TAG="-t12"

if options.gazetteer == "none":
    TRIGGER_FEATURE_PARAMS="style:typed"
elif options.gazetteer == "full":
    TRIGGER_FEATURE_PARAMS="style:typed,exclude_gazetteer"
    stemGazetteer = False
    TASK_TAG += "-gazfull"
elif options.gazetteer == "stem":
    TRIGGER_FEATURE_PARAMS="style:typed,exclude_gazetteer,stem_gazetteer"
    stemGazetteer = True
    TASK_TAG += "-gazstem"

EXPERIMENT_NAME = options.name + TASK_TAG    
WORKDIR="/usr/share/biotext/GeniaChallenge/CI-release/triggers/" + EXPERIMENT_NAME

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

###############################################################################
# Trigger example generation
###############################################################################
TRIGGER_TRAIN_EXAMPLE_FILE = "trigger-train-examples-"+PARSE_TOK+TASK_TAG
TRIGGER_DEVEL_EXAMPLE_FILE = "trigger-devel-examples-"+PARSE_TOK+TASK_TAG
if True:
    print >> sys.stderr, "Trigger examples for parse", PARSE_TOK, "task", task
    GAZETTEER_TRAIN = None
    GAZETTEER_EVERYTHING = None
    if options.gazetteer != "none":
        GAZETTEER_TRAIN = "gazetteer-train-"+PARSE_TOK+TASK_TAG
        GAZETTEER_EVERYTHING = "gazetteer-everything-"+PARSE_TOK+TASK_TAG
        Gazetteer.run(TRAIN_FILE, GAZETTEER_TRAIN, PARSE_TOK, entityOffsetKey="charOffset", stem=stemGazetteer)
        Gazetteer.run(EVERYTHING_FILE, GAZETTEER_EVERYTHING, PARSE_TOK, entityOffsetKey="charOffset", stem=stemGazetteer)
    
    GeneralEntityTypeRecognizerGztr.run(TRAIN_FILE, TRIGGER_TRAIN_EXAMPLE_FILE, PARSE_TOK, PARSE_TOK, TRIGGER_FEATURE_PARAMS, "genia-trigger-ids", GAZETTEER_TRAIN)
    GeneralEntityTypeRecognizerGztr.run(DEVEL_FILE, TRIGGER_DEVEL_EXAMPLE_FILE, PARSE_TOK, PARSE_TOK, TRIGGER_FEATURE_PARAMS, "genia-trigger-ids", GAZETTEER_TRAIN)
    GeneralEntityTypeRecognizerGztr.run(EVERYTHING_FILE, "trigger-everything-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, TRIGGER_FEATURE_PARAMS, "genia-trigger-ids", GAZETTEER_EVERYTHING)
    GeneralEntityTypeRecognizerGztr.run(TEST_FILE, "trigger-test-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, TRIGGER_FEATURE_PARAMS, "genia-trigger-ids", GAZETTEER_EVERYTHING)

###############################################################################
# Trigger models
###############################################################################
TRIGGER_CLASSIFIER_PARAMS="c:1000,5000,10000,20000,50000,80000,100000,150000,180000,200000, 250000, 300000, 350000, 500000,1000000"
if True:
    c = CSCConnection("CI-release/models/"+EXPERIMENT_NAME, "jakrbj@murska.csc.fi", True)
    optimize(Cls, Ev, TRIGGER_TRAIN_EXAMPLE_FILE, TRIGGER_DEVEL_EXAMPLE_FILE,\
        "genia-trigger-ids.class_names", TRIGGER_CLASSIFIER_PARAMS, "devel-trigger-models", None, c, downloadAllModels=True)
