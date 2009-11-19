from Pipeline import *
import os

# define shortcuts for commonly used files
PARSE_TOK="split-McClosky"
CORPUS_DIR="/usr/share/biotext/GeniaChallenge/xml"

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
    TASK_TAG="-t12"

EXAMPLEDIR="/usr/share/biotext/GeniaChallenge/CI-release/examples"

TRIGGER_TRAIN_EXAMPLE_FILE=EXAMPLEDIR+"/trigger-train-examples-"+PARSE_TOK+TASK_TAG
TRIGGER_DEVEL_EXAMPLE_FILE=EXAMPLEDIR+"/trigger-devel-examples-"+PARSE_TOK+TASK_TAG
TRIGGER_TEST_EXAMPLE_FILE=EXAMPLEDIR+"/trigger-test-examples-"+PARSE_TOK+TASK_TAG
TRIGGER_EVERYTHING_FILE=EXAMPLEDIR+"/trigger-everything-examples-"+PARSE_TOK+TASK_TAG
TRIGGER_CLASS_NAMES=EXAMPLEDIR+"/genia-trigger-ids.class_names"

EDGE_TRAIN_EXAMPLE_FILE=EXAMPLEDIR+"/edge-train-examples-"+PARSE_TOK+TASK_TAG
EDGE_DEVEL_EXAMPLE_FILE=EXAMPLEDIR+"/edge-devel-examples-"+PARSE_TOK+TASK_TAG
EDGE_TEST_EXAMPLE_FILE=EXAMPLEDIR+"/edge-test-examples-"+PARSE_TOK+TASK_TAG
EDGE_EVERYTHING_FILE=EXAMPLEDIR+"/edge-everything-examples-"+PARSE_TOK+TASK_TAG
EDGE_CLASS_NAMES=EXAMPLEDIR+"/genia-edge-ids.class_names"

WORKDIR="/usr/share/biotext/GeniaChallenge/CI-release/models/models-"+PARSE_TOK+TASK_TAG

TRIGGER_CLASSIFIER_PARAMS="c:1000,5000,10000,20000,50000,80000,100000,150000,180000,200000, 250000, 300000, 350000, 500000,1000000"
EDGE_CLASSIFIER_PARAMS="c:5000,10000,20000,25000,28000,50000,60000,65000,80000,100000,150000"

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory
print >> sys.stderr, "Model pipeline for parse", PARSE_TOK, "task", task

###############################################################################
# Trigger models
###############################################################################
c = CSCConnection("CI-release/models/models-"+PARSE_TOK+TASK_TAG+"/trigger-models", "jakrbj@murska.csc.fi", True)
optimize(Cls, Ev, TRIGGER_TRAIN_EXAMPLE_FILE, TRIGGER_DEVEL_EXAMPLE_FILE,\
    TRIGGER_CLASS_NAMES, TRIGGER_CLASSIFIER_PARAMS, "devel-trigger-models", None, c, downloadAllModels=True)

###############################################################################
# Edge models
###############################################################################
c = CSCConnection("CI-release/models/models-"+PARSE_TOK+TASK_TAG+"/edge-models", "jakrbj@murska.csc.fi", True)
optimize(Cls, Ev, EDGE_TRAIN_EXAMPLE_FILE, EDGE_DEVEL_EXAMPLE_FILE,\
    EDGE_CLASS_NAMES, EDGE_CLASSIFIER_PARAMS, "devel-edge-models", None, c, downloadAllModels=True)
