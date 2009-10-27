from Pipeline import *
import os

# define shortcuts for commonly used files
PARSE_TOK="split-McClosky" #"split-Charniak-Lease"
CORPUS_DIR=None
if PARSE_TOK == "split-Charniak-Lease":
    CORPUS_DIR="/usr/share/biotext/GeniaChallenge/xml/old-interaction-xml-files"
elif PARSE_TOK == "split-McClosky":
    CORPUS_DIR="/usr/share/biotext/GeniaChallenge/xml"
assert(CORPUS_DIR != None)
DEVEL_FILE=CORPUS_DIR+"/devel.xml"

task = 2
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
    TASK_TAG="-stemgazetteer-t12"

EXAMPLEDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/trigger-examples"
TRAIN_EXAMPLE_FILE=EXAMPLEDIR+"/trigger-train-examples-"+PARSE_TOK+TASK_TAG
DEVEL_EXAMPLE_FILE=EXAMPLEDIR+"/trigger-devel-examples-"+PARSE_TOK+TASK_TAG
TEST_EXAMPLE_FILE=EXAMPLEDIR+"/trigger-test-examples-"+PARSE_TOK+TASK_TAG
EVERYTHING_FILE=EXAMPLEDIR+"/trigger-everything-examples-"+PARSE_TOK+TASK_TAG
CLASS_NAMES=EXAMPLEDIR+"/genia-trigger-ids.class_names"
WORKDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/trigger-model-gazetteer-"+PARSE_TOK+TASK_TAG

CLASSIFIER_PARAMS="c:1000,5000,10000,20000,50000,80000,100000,150000,180000,200000, 250000, 300000, 350000, 500000,1000000"#,5000000,10000000"
#CLASSIFIER_PARAMS="c:50000"
optimizeLoop = True # search for a parameter, or use a predefined one

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory
print >> sys.stderr, "Trigger model pipeline for parse", PARSE_TOK, "task", task

###############################################################################
# Trigger example generation
###############################################################################
if optimizeLoop: # search for the best c-parameter
    # The optimize-function takes as parameters a Classifier-class, an Evaluator-class
    # and input and output files
    c = CSCConnection("extension-data/genia/devel-trigger-model-gazetteer-"+PARSE_TOK+TASK_TAG, "jakrbj@murska.csc.fi")
    best = optimize(Cls, Ev, TRAIN_EXAMPLE_FILE, DEVEL_EXAMPLE_FILE,\
        CLASS_NAMES, CLASSIFIER_PARAMS, "devel-trigger-param-opt", None, c)
xmlFilename = "devel-predicted-triggers-"+PARSE_TOK+TASK_TAG+".xml"
ExampleUtils.writeToInteractionXML(DEVEL_EXAMPLE_FILE, best[2], DEVEL_FILE, xmlFilename, CLASS_NAMES, PARSE_TOK, PARSE_TOK)
# NOTE: Merged elements must not be split, as recall booster may change their class
#ix.splitMergedElements("devel-predicted-triggers.xml", "devel-predicted-triggers.xml")
ix.recalculateIds(xmlFilename, xmlFilename, True)
