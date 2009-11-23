# most imports are defined in Pipeline
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
WORKDIR="/usr/share/biotext/GeniaChallenge/CI-release/examples"
TRIGGER_FEATURE_PARAMS="style:typed"
EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory
print >> sys.stderr, "Trigger example pipeline for parse", PARSE_TOK, "task", task

###############################################################################
# Trigger example generation
###############################################################################
if True:
    #Gazetteer.run(TRAIN_FILE, "gazetteer-train-"+PARSE_TOK+TASK_TAG, PARSE_TOK, entityOffsetKey="charOffset", stem=False)
    #Gazetteer.run(EVERYTHING_FILE, "gazetteer-everything-"+PARSE_TOK+TASK_TAG, PARSE_TOK, entityOffsetKey="charOffset", stem=False)
    
    GeneralEntityTypeRecognizerGztr.run(TRAIN_FILE, "trigger-train-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, TRIGGER_FEATURE_PARAMS, "genia-trigger-ids", None)#"gazetteer-train-"+PARSE_TOK+TASK_TAG)
    GeneralEntityTypeRecognizerGztr.run(DEVEL_FILE, "trigger-devel-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, TRIGGER_FEATURE_PARAMS, "genia-trigger-ids", None)#"gazetteer-train-"+PARSE_TOK+TASK_TAG)
    GeneralEntityTypeRecognizerGztr.run(EVERYTHING_FILE, "trigger-everything-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, TRIGGER_FEATURE_PARAMS, "genia-trigger-ids", None)#"gazetteer-everything-"+PARSE_TOK+TASK_TAG)
    GeneralEntityTypeRecognizerGztr.run(TEST_FILE, "trigger-test-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, TRIGGER_FEATURE_PARAMS, "genia-trigger-ids", None)#"gazetteer-everything-"+PARSE_TOK+TASK_TAG)

###############################################################################
# Edge example generation
###############################################################################
if True:
    MultiEdgeExampleBuilder.run(TRAIN_FILE, "edge-train-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")
    MultiEdgeExampleBuilder.run(DEVEL_FILE, "edge-devel-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")
    MultiEdgeExampleBuilder.run(EVERYTHING_FILE, "edge-everything-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")
