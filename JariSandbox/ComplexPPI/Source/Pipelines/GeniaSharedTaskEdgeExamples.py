# Edge detection for Shared Task re-implementation for the Journal Extension

# most imports are defined in Pipeline
from Pipeline import *
import os

# define shortcuts for commonly used files
PARSE_TOK="McClosky" #"split-Charniak-Lease"
CORPUS_DIR=None
if PARSE_TOK == "split-Charniak-Lease":
    CORPUS_DIR="/usr/share/biotext/GeniaChallenge/xml/old-interaction-xml-files"
elif PARSE_TOK == "McClosky":
    CORPUS_DIR="/usr/share/biotext/GeniaChallenge/xml"
assert(CORPUS_DIR != None)

TRAIN_FILE=CORPUS_DIR+"/train.xml"
DEVEL_FILE=CORPUS_DIR+"/devel.xml"
#TEST_FILE="/usr/share/biotext/GeniaChallenge/extension-data/genia/trigger-model/devel-predicted-triggers.xml"
EVERYTHING_FILE=CORPUS_DIR+"/everything.xml"
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
if not os.path.exists("edge-train-examples-"+PARSE_TOK):
    MultiEdgeExampleBuilder.run(TRAIN_FILE, "edge-train-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")
if not os.path.exists("edge-devel-examples-"+PARSE_TOK):
    MultiEdgeExampleBuilder.run(DEVEL_FILE, "edge-devel-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")

if not os.path.exists("edge-everything-examples-"+PARSE_TOK):
    MultiEdgeExampleBuilder.run(EVERYTHING_FILE, "edge-everything-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")

## This one needs predicted triggers
#if not os.path.exists("edge-test-examples-"+PARSE_TOK):
#    MultiEdgeExampleBuilder.run(TEST_FILE, "edge-test-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")
