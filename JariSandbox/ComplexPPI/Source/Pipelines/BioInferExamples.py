# This file shows a possible pipeline, that resembles the Shared Task.
# It uses the mini-subsets of the Shared Task files, which are faster 
# to process and thus enable rapid testing of the system.

# most imports are defined in Pipeline
from Pipeline import *
import os

# define shortcuts for commonly used files
PARSE_TOK="stanford-gold" #"split-Charniak-Lease"
CORPUS_DIR="/usr/share/biotext/GeniaChallenge/extension-data/bioinfer"
assert(CORPUS_DIR != None)

BI_BLIND_FILE=CORPUS_DIR+"/bioinfer.blind.metaRes-anonRes.gold.gif.xml"
BI_TEST_FILE=CORPUS_DIR+"/bioinfer.test.metaRes-anonRes.gold.gif.xml"
BI_VISIBLE_FILE=CORPUS_DIR+"/bioinfer.visible.metaRes-anonRes.gold.gif.xml"
BI_VISIBLE_AND_BLIND_FILE=CORPUS_DIR+"/bioinfer.visible+blind.metaRes-anonRes.gold.gif.xml"

TEST_FILE=CORPUS_DIR+"/bioinfer-test-"+PARSE_TOK+".xml"
DEVEL_FILE=CORPUS_DIR+"/bioinfer-devel-"+PARSE_TOK+".xml"
TRAIN_FILE=CORPUS_DIR+"/bioinfer-train-"+PARSE_TOK+".xml"
EVERYTHING_FILE=CORPUS_DIR+"/bioinfer-everything-"+PARSE_TOK+".xml"
WORKDIR=CORPUS_DIR+"/trigger-examples"

# Find heads
sys.path.append("..")
import Core.SentenceGraph as SentenceGraph
import cElementTreeUtils as ETUtils
if not os.path.exists(TEST_FILE):
    c = SentenceGraph.loadCorpus(BI_BLIND_FILE, PARSE_TOK, PARSE_TOK)
    ETUtils.write(c.rootElement, TEST_FILE)
if not os.path.exists(DEVEL_FILE):
    c = SentenceGraph.loadCorpus(BI_TEST_FILE, PARSE_TOK, PARSE_TOK)
    ETUtils.write(c.rootElement, DEVEL_FILE)
if not os.path.exists(TRAIN_FILE):
    c = SentenceGraph.loadCorpus(BI_VISIBLE_FILE, PARSE_TOK, PARSE_TOK)
    ETUtils.write(c.rootElement, TRAIN_FILE)
if not os.path.exists(EVERYTHING_FILE):
    c = SentenceGraph.loadCorpus(BI_VISIBLE_AND_BLIND_FILE, PARSE_TOK, PARSE_TOK)
    ETUtils.write(c.rootElement, EVERYTHING_FILE)

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory
print >> sys.stderr, "Trigger example pipeline for parse", PARSE_TOK

###############################################################################
# Trigger example generation
###############################################################################
if not os.path.exists("gazetteer-train-"+PARSE_TOK):
    Gazetteer.run(TRAIN_FILE, "gazetteer-train-"+PARSE_TOK, PARSE_TOK)
if not os.path.exists("gazetteer-everything-"+PARSE_TOK):
    Gazetteer.run(EVERYTHING_FILE, "gazetteer-everything-"+PARSE_TOK, PARSE_TOK)
# generate the files for the old charniak
if not os.path.exists("trigger-train-examples-"+PARSE_TOK):
    GeneralEntityTypeRecognizerGztr.run(TRAIN_FILE, "trigger-train-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, "style:typed", "bioinfer-trigger-ids", "gazetteer-visible-"+PARSE_TOK)
if not os.path.exists("trigger-devel-examples-"+PARSE_TOK):
    GeneralEntityTypeRecognizerGztr.run(DEVEL_FILE, "trigger-devel-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, "style:typed", "bioinfer-trigger-ids", "gazetteer-visible-"+PARSE_TOK)
if not os.path.exists("trigger-everything-examples-"+PARSE_TOK):
    GeneralEntityTypeRecognizerGztr.run(EVERYTHING_FILE, "trigger-everything-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, "style:typed", "bioinfer-trigger-ids", "gazetteer-everything-"+PARSE_TOK)
if not os.path.exists("trigger-test-examples-"+PARSE_TOK):
    GeneralEntityTypeRecognizerGztr.run(TEST_FILE, "trigger-test-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, "style:typed", "bioinfer-trigger-ids", "gazetteer-everything-"+PARSE_TOK)
