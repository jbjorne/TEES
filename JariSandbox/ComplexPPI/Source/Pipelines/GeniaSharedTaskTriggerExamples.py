# This file shows a possible pipeline, that resembles the Shared Task.
# It uses the mini-subsets of the Shared Task files, which are faster 
# to process and thus enable rapid testing of the system.

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
    TASK_TAG="-gazetteer"
else:
    TRAIN_FILE=CORPUS_DIR+"/train12.xml"
    DEVEL_FILE=CORPUS_DIR+"/devel12.xml"
    TEST_FILE=CORPUS_DIR+"/test.xml"
    EVERYTHING_FILE=CORPUS_DIR+"/everything12.xml"
    TASK_TAG="-NE-t12"
WORKDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/trigger-examples"
TRIGGER_FEATURE_PARAMS="style:typed,names"

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory
print >> sys.stderr, "Trigger example pipeline for parse", PARSE_TOK, "task", task

###############################################################################
# Trigger example generation
###############################################################################
# Old McClosky-Charniak parses
if not os.path.exists("gazetteer-train-"+PARSE_TOK+TASK_TAG):
    Gazetteer.run(TRAIN_FILE, "gazetteer-train-"+PARSE_TOK+TASK_TAG, PARSE_TOK)
if not os.path.exists("gazetteer-everything-"+PARSE_TOK+TASK_TAG):
    Gazetteer.run(EVERYTHING_FILE, "gazetteer-everything-"+PARSE_TOK+TASK_TAG, PARSE_TOK)
# generate the files for the old charniak
if not os.path.exists("trigger-train-examples-"+PARSE_TOK+TASK_TAG):
    GeneralEntityTypeRecognizerGztr.run(TRAIN_FILE, "trigger-train-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, TRIGGER_FEATURE_PARAMS, "genia-trigger-ids", "gazetteer-train-"+PARSE_TOK+TASK_TAG)
if not os.path.exists("trigger-devel-examples-"+PARSE_TOK+TASK_TAG):
    GeneralEntityTypeRecognizerGztr.run(DEVEL_FILE, "trigger-devel-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, TRIGGER_FEATURE_PARAMS, "genia-trigger-ids", "gazetteer-train-"+PARSE_TOK+TASK_TAG)

if not os.path.exists("trigger-everything-examples-"+PARSE_TOK+TASK_TAG):
    GeneralEntityTypeRecognizerGztr.run(EVERYTHING_FILE, "trigger-everything-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, TRIGGER_FEATURE_PARAMS, "genia-trigger-ids", "gazetteer-everything-"+PARSE_TOK+TASK_TAG)
if not os.path.exists("trigger-test-examples-"+PARSE_TOK+TASK_TAG):
    GeneralEntityTypeRecognizerGztr.run(TEST_FILE, "trigger-test-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, TRIGGER_FEATURE_PARAMS, "genia-trigger-ids", "gazetteer-everything-"+PARSE_TOK+TASK_TAG)
