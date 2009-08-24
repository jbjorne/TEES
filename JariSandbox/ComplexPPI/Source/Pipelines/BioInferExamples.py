# Builds Bioinfer trigger and edge example files for a specified parse

from Pipeline import *
import sys,os

# define shortcuts for commonly used files
PARSE_TOK="stanford-gold" #"split-Charniak-Lease"
if len(sys.argv) > 1: # can be defined from command line
    PARSE_TOK = sys.argv[1]
CORPUS_DIR="/usr/share/biotext/GeniaChallenge/extension-data/bioinfer"

# xml files without heads
BI_BLIND_FILE=CORPUS_DIR+"/bioinfer.blind.metaRes-anonRes.gold.gif.xml"
BI_TEST_FILE=CORPUS_DIR+"/bioinfer.test.metaRes-anonRes.gold.gif.xml"
BI_VISIBLE_FILE=CORPUS_DIR+"/bioinfer.visible.metaRes-anonRes.gold.gif.xml"
BI_VISIBLE_AND_BLIND_FILE=CORPUS_DIR+"/bioinfer.visible+blind.metaRes-anonRes.gold.gif.xml"

# xml files with head tokens
TEST_FILE=CORPUS_DIR+"/with-heads/bioinfer-test-"+PARSE_TOK+".xml"
BLIND_FILE=CORPUS_DIR+"/with-heads/bioinfer-blind-"+PARSE_TOK+".xml"
VISIBLE_FILE=CORPUS_DIR+"/with-heads/bioinfer-visible-"+PARSE_TOK+".xml"
VISIBLE_AND_BLIND_FILE=CORPUS_DIR+"/with-heads/bioinfer-visible-and-blind-"+PARSE_TOK+".xml"
WORKDIR=CORPUS_DIR+"/examples-"+PARSE_TOK

# Find heads
sys.path.append("..")
import Core.SentenceGraph as SentenceGraph
import cElementTreeUtils as ETUtils
if not os.path.exists(TEST_FILE):
    c = SentenceGraph.loadCorpus(BI_TEST_FILE, PARSE_TOK, PARSE_TOK)
    ETUtils.write(c.rootElement, TEST_FILE)
if not os.path.exists(BLIND_FILE):
    c = SentenceGraph.loadCorpus(BI_BLIND_FILE, PARSE_TOK, PARSE_TOK)
    ETUtils.write(c.rootElement, BLIND_FILE)
if not os.path.exists(VISIBLE_FILE):
    c = SentenceGraph.loadCorpus(BI_VISIBLE_FILE, PARSE_TOK, PARSE_TOK)
    ETUtils.write(c.rootElement, VISIBLE_FILE)
if not os.path.exists(VISIBLE_AND_BLIND_FILE):
    c = SentenceGraph.loadCorpus(BI_VISIBLE_AND_BLIND_FILE, PARSE_TOK, PARSE_TOK)
    ETUtils.write(c.rootElement, VISIBLE_AND_BLIND_FILE)

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

###############################################################################
# Trigger example generation
###############################################################################
print >> sys.stderr, "Trigger examples for parse", PARSE_TOK
if not os.path.exists("gazetteer-train-"+PARSE_TOK):
    Gazetteer.run(VISIBLE_FILE, "gazetteer-visible-"+PARSE_TOK, PARSE_TOK)
if not os.path.exists("gazetteer-everything-"+PARSE_TOK):
    Gazetteer.run(VISIBLE_AND_BLIND_FILE, "gazetteer-visible-and-blind-"+PARSE_TOK, PARSE_TOK)
# generate the files for the old charniak
if not os.path.exists("trigger-visible-examples-"+PARSE_TOK):
    GeneralEntityTypeRecognizerGztr.run(VISIBLE_FILE, "trigger-visible-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, "style:typed", "bioinfer-trigger-ids", "gazetteer-visible-"+PARSE_TOK)
if not os.path.exists("trigger-blind-examples-"+PARSE_TOK):
    GeneralEntityTypeRecognizerGztr.run(BLIND_FILE, "trigger-blind-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, "style:typed", "bioinfer-trigger-ids", "gazetteer-visible-"+PARSE_TOK)
if not os.path.exists("trigger-visible-and-blind-examples-"+PARSE_TOK):
    GeneralEntityTypeRecognizerGztr.run(VISIBLE_AND_BLIND_FILE, "trigger-everything-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, "style:typed", "bioinfer-trigger-ids", "gazetteer-visible-and-blind-"+PARSE_TOK)
if not os.path.exists("trigger-test-examples-"+PARSE_TOK):
    GeneralEntityTypeRecognizerGztr.run(TEST_FILE, "trigger-test-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, "style:typed", "bioinfer-trigger-ids", "gazetteer-visible-and-blind-"+PARSE_TOK)

###############################################################################
# Edge example generation
###############################################################################
print >> sys.stderr, "Edge examples for parse", PARSE_TOK
EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,noMasking,maxFeatures"

if not os.path.exists("edge-visible-examples-"+PARSE_TOK):
    MultiEdgeExampleBuilder.run(VISIBLE_FILE, "edge-visible-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "bioinfer-edge-ids")
if not os.path.exists("edge-blind-examples-"+PARSE_TOK):
    MultiEdgeExampleBuilder.run(BLIND_FILE, "edge-blind-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "bioinfer-edge-ids")
if not os.path.exists("edge-visible-and-blind-examples-"+PARSE_TOK):
    MultiEdgeExampleBuilder.run(VISIBLE_AND_BLIND_FILE, "edge-visible-and-blind-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "bioinfer-edge-ids")
# NOTE! These TEST examples will be based on gold standard triggers!
if not os.path.exists("edge-test-examples-"+PARSE_TOK):
    MultiEdgeExampleBuilder.run(TEST_FILE, "edge-test-examples-"+PARSE_TOK, PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "bioinfer-edge-ids")
