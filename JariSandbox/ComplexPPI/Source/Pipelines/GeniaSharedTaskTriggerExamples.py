# This file shows a possible pipeline, that resembles the Shared Task.
# It uses the mini-subsets of the Shared Task files, which are faster 
# to process and thus enable rapid testing of the system.

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
TEST_FILE=CORPUS_DIR+"/test.xml"
EVERYTHING_FILE=CORPUS_DIR+"/everything.xml"
WORKDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/trigger-examples"

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory
print >> sys.stderr, "Trigger example pipeline for parse", PARSE_TOK

###############################################################################
# Trigger example generation
###############################################################################
# Old McClosky-Charniak parses
if not os.path.exists("gazetteer-train-"+PARSE_TOK):
    Gazetteer.run(TRAIN_FILE, "gazetteer-train-"+PARSE_TOK, PARSE_TOK)
if not os.path.exists("gazetteer-everything-"+PARSE_TOK):
    Gazetteer.run(EVERYTHING_FILE, "gazetteer-everything-"+PARSE_TOK, PARSE_TOK)
# generate the files for the old charniak
if not os.path.exists("trigger-train-examples-"+PARSE_TOK):
    GeneralEntityTypeRecognizerGztr.run(TRAIN_FILE, "trigger-train-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, "style:typed", "genia-trigger-ids", "gazetteer-train")
if not os.path.exists("trigger-devel-examples-"+PARSE_TOK):
    GeneralEntityTypeRecognizerGztr.run(DEVEL_FILE, "trigger-devel-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, "style:typed", "genia-trigger-ids", "gazetteer-train")

if not os.path.exists("trigger-everything-examples-"+PARSE_TOK):
    GeneralEntityTypeRecognizerGztr.run(EVERYTHING_FILE, "trigger-everything-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, "style:typed", "genia-trigger-ids", "gazetteer-everything")
if not os.path.exists("trigger-test-examples-"+PARSE_TOK):
    GeneralEntityTypeRecognizerGztr.run(TEST_FILE, "trigger-test-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, "style:typed", "genia-trigger-ids", "gazetteer-everything")
