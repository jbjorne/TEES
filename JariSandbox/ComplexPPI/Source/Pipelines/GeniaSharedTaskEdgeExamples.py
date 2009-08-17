# Edge detection for Shared Task re-implementation for the Journal Extension

# most imports are defined in Pipeline
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

task = 2
if task == 1:
    TRAIN_FILE=CORPUS_DIR+"/train.xml"
    DEVEL_FILE=CORPUS_DIR+"/devel.xml"
    TEST_FILE=CORPUS_DIR+"/test.xml"
    EVERYTHING_FILE=CORPUS_DIR+"/everything.xml"
else:
    TRAIN_FILE=CORPUS_DIR+"/train12.xml"
    DEVEL_FILE=CORPUS_DIR+"/devel12.xml"
    TEST_FILE=CORPUS_DIR+"/test12.xml"
    EVERYTHING_FILE=CORPUS_DIR+"/everything12.xml"
    TASK_TAG="-t12"
WORKDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/edge-examples"
EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

###############################################################################
# Edge example generation
###############################################################################
# Old McClosky-Charniak parses
# generate the files for the old charniak
if not os.path.exists("edge-train-examples-"+PARSE_TOK+TASK_TAG):
    MultiEdgeExampleBuilder.run(TRAIN_FILE, "edge-train-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")
if not os.path.exists("edge-devel-examples-"+PARSE_TOK+TASK_TAG):
    MultiEdgeExampleBuilder.run(DEVEL_FILE, "edge-devel-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")

if not os.path.exists("edge-everything-examples-"+PARSE_TOK+TASK_TAG):
    MultiEdgeExampleBuilder.run(EVERYTHING_FILE, "edge-everything-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")

## This one needs predicted triggers
#if not os.path.exists("edge-test-examples-"+PARSE_TOK):
#    MultiEdgeExampleBuilder.run(TEST_FILE, "edge-test-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")
