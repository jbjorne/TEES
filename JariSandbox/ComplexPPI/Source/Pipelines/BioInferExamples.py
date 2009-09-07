# Builds Bioinfer trigger and edge example files for a specified parse

from Pipeline import *
import sys,os

# define shortcuts for commonly used files
PARSE="stanford-newMC-intra" #"split-Charniak-Lease"
TOK="split-McClosky"
CORPUS_DIR="/usr/share/biotext/UnmergingProject/source"

# xml files without heads
BI_DEVEL_FILE=CORPUS_DIR+"/bioinfer.devel.refRem-eqRem-negRem-metaRes-anonRes.gold.gif.xml"
BI_TEST_FILE=CORPUS_DIR+"/bioinfer.test.refRem-eqRem-negRem-metaRes-anonRes.gold.gif.xml"
BI_TRAIN_FILE=CORPUS_DIR+"/bioinfer.train.refRem-eqRem-negRem-metaRes-anonRes.gold.gif.xml"
BI_TRAIN_AND_DEVEL_FILE=CORPUS_DIR+"/bioinfer.train+devel.refRem-eqRem-negRem-metaRes-anonRes.gold.gif.xml"

# xml files with head tokens
TEST_FILE=CORPUS_DIR+"/with-heads/bioinfer-test-"+PARSE+".xml"
DEVEL_FILE=CORPUS_DIR+"/with-heads/bioinfer-devel-"+PARSE+".xml"
TRAIN_FILE=CORPUS_DIR+"/with-heads/bioinfer-train-"+PARSE+".xml"
TRAIN_AND_DEVEL_FILE=CORPUS_DIR+"/with-heads/bioinfer-train-and-devel-"+PARSE+".xml"
WORKDIR="/usr/share/biotext/UnmergingProject/results/examples-"+PARSE

# Find heads
sys.path.append("..")
import Core.SentenceGraph as SentenceGraph
import cElementTreeUtils as ETUtils
if not os.path.exists(TEST_FILE):
    c = SentenceGraph.loadCorpus(BI_TEST_FILE, PARSE, TOK)
    ETUtils.write(c.rootElement, TEST_FILE)
if not os.path.exists(DEVEL_FILE):
    c = SentenceGraph.loadCorpus(BI_DEVEL_FILE, PARSE, TOK)
    ETUtils.write(c.rootElement, DEVEL_FILE)
if not os.path.exists(TRAIN_FILE):
    c = SentenceGraph.loadCorpus(BI_TRAIN_FILE, PARSE, TOK)
    ETUtils.write(c.rootElement, TRAIN_FILE)
if not os.path.exists(TRAIN_AND_DEVEL_FILE):
    c = SentenceGraph.loadCorpus(BI_TRAIN_AND_DEVEL_FILE, PARSE, TOK)
    ETUtils.write(c.rootElement, TRAIN_AND_DEVEL_FILE)

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

###############################################################################
# Trigger example generation
###############################################################################
print >> sys.stderr, "Trigger examples for parse", TOK
if not os.path.exists("gazetteer-train-"+TOK):
    Gazetteer.run(TRAIN_FILE, "gazetteer-train-"+TOK, TOK)
if not os.path.exists("gazetteer-train-and-devel-"+TOK):
    Gazetteer.run(TRAIN_AND_DEVEL_FILE, "gazetteer-train-and-devel-"+TOK, TOK)
# generate the files for the old charniak
if not os.path.exists("trigger-train-examples-"+PARSE):
    GeneralEntityTypeRecognizerGztr.run(TRAIN_FILE, "trigger-train-examples-"+PARSE, PARSE, TOK, "style:typed", "bioinfer-trigger-ids", "gazetteer-train-"+PARSE)
if not os.path.exists("trigger-devel-examples-"+PARSE):
    GeneralEntityTypeRecognizerGztr.run(DEVEL_FILE, "trigger-devel-examples-"+PARSE, PARSE, TOK, "style:typed", "bioinfer-trigger-ids", "gazetteer-train-"+PARSE)
if not os.path.exists("trigger-train-and-devel-examples-"+PARSE):
    GeneralEntityTypeRecognizerGztr.run(TRAIN_AND_DEVEL_FILE, "trigger-train-and-devel-examples-"+PARSE, PARSE, TOK, "style:typed", "bioinfer-trigger-ids", "gazetteer-train-and-devel-"+PARSE)
if not os.path.exists("trigger-test-examples-"+PARSE):
    GeneralEntityTypeRecognizerGztr.run(TEST_FILE, "trigger-test-examples-"+PARSE, PARSE, TOK, "style:typed", "bioinfer-trigger-ids", "gazetteer-train-and-devel-"+PARSE)

###############################################################################
# Edge example generation
###############################################################################
print >> sys.stderr, "Edge examples for parse", PARSE
EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,noMasking,maxFeatures,bioinfer_limits"

if not os.path.exists("edge-train-examples-"+PARSE):
    MultiEdgeExampleBuilder.run(TRAIN_FILE, "edge-train-examples-"+PARSE, PARSE, TOK, EDGE_FEATURE_PARAMS, "bioinfer-edge-ids")
if not os.path.exists("edge-devel-examples-"+PARSE):
    MultiEdgeExampleBuilder.run(DEVEL_FILE, "edge-devel-examples-"+PARSE, PARSE, TOK, EDGE_FEATURE_PARAMS, "bioinfer-edge-ids")
if not os.path.exists("edge-train-and-devel-examples-"+PARSE):
    MultiEdgeExampleBuilder.run(TRAIN_AND_DEVEL_FILE, "edge-train-and-devel-examples-"+PARSE, PARSE, TOK, EDGE_FEATURE_PARAMS, "bioinfer-edge-ids")
# NOTE! These TEST examples will be based on gold standard triggers!
if not os.path.exists("edge-test-examples-"+PARSE):
    MultiEdgeExampleBuilder.run(TEST_FILE, "edge-test-examples-"+PARSE, PARSE, TOK, EDGE_FEATURE_PARAMS, "bioinfer-edge-ids")

# older xml-file examples
PARSE="split_Charniak-Lease"
TOK="split_Charniak-Lease"
OLD_IXML_BIOINFER="/usr/share/biotext/ComplexPPI/BioInfer.xml"
if not os.path.exists("edge-examples-old-"+PARSE):
    print >> sys.stderr, "Building examples for old BioInfer"
    MultiEdgeExampleBuilder.run(OLD_IXML_BIOINFER, "edge-examples-old-"+PARSE, PARSE, TOK, EDGE_FEATURE_PARAMS, "bioinfer-edge-ids")
