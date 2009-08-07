from Pipeline import *
import os

# define shortcuts for commonly used files
CORPUSDIR="/usr/share/biotext/GeniaChallenge/xml"
PARSE_TOK="split-Charniak-Lease"
TEST_FILE=CORPUSDIR+"/test.xml"
EVERYTHING_FILE=CORPUSDIR+"/everything.xml"

TRIGGER_EXAMPLEDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/trigger-examples"
TRIGGER_TEST_EXAMPLE_FILE=TRIGGER_EXAMPLEDIR+"/trigger-test-examples-"+PARSE_TOK
TRIGGER_EVERYTHING_FILE=TRIGGER_EXAMPLEDIR+"/trigger-everything-examples-"+PARSE_TOK
TRIGGER_IDS="genia-trigger-ids"

EDGE_EXAMPLEDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/edge-examples"
EDGE_TEST_EXAMPLE_FILE=EDGE_EXAMPLEDIR+"/edge-test-examples-"+PARSE_TOK
EDGE_EVERYTHING_FILE=EDGE_EXAMPLEDIR+"/edge-everything-examples-"+PARSE_TOK
EDGE_IDS="genia-edge-ids"

WORKDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/test-set-"+PARSE_TOK

TRIGGER_CLASSIFIER_PARAMS="c:300000"
EDGE_CLASSIFIER_PARAMS="c:50000"
RECALL_BOOST_PARAM=0.7

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

###############################################################################
# Triggers
###############################################################################
c = CSCConnection("GeniaSharedTaskTestTriggerModel")
best = optimize(Cls, Ev, TRIGGER_EVERYTHING_EXAMPLE_FILE, TRIGGER_TEST_EXAMPLE_FILE,\
    TRIGGER_IDS+".class_names", TRIGGER_CLASSIFIER_PARAMS, "test-trigger-param-opt", None, c)
# The evaluator is needed to access the classifications (will be fixed later)
evaluator = best[0]
ExampleUtils.writeToInteractionXML(evaluator.classifications, TEST_FILE, "test-predicted-triggers.xml", TRIGGER_CLASS_NAMES, PARSE_TOK, PARSE_TOK)
# NOTE: Merged elements must not be split, as recall booster may change their class
#ix.splitMergedElements("devel-predicted-triggers.xml", "devel-predicted-triggers.xml")
ix.recalculateIds("test-predicted-triggers.xml", "test-predicted-triggers.xml", True)

###############################################################################
# Edges
###############################################################################
boostedTriggerFile = "test-predicted-triggers-boost.xml"
RecallAdjust.run("test-predicted-triggers.xml", RECALL_BOOST_PARAM, boostedTriggerFile)
ix.splitMergedElements(boostedTriggerFile, boostedTriggerFile)
ix.recalculateIds(boostedTriggerFile, boostedTriggerFile, True)
# Build edge examples
MultiEdgeExampleBuilder.run(boostedTriggerFile, "devel-edge-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
# Classify with pre-defined model
c = CSCConnection("GeniaSharedTaskTestEdgeModel")
best = optimize(Cls, Ev, EDGE_EVERYTHING_EXAMPLE_FILE, EDGE_TEST_EXAMPLE_FILE,\
    EDGE_IDS+".class_names", EDGE_CLASSIFIER_PARAMS, "test-edge-param-opt", None, c)
# The evaluator is needed to access the classifications (will be fixed later)
evaluator = best[0]
# Write to interaction xml
xmlFilename = "test-predicted-edges.xml"
ExampleUtils.writeToInteractionXML(evaluator.classifications, boostedTriggerFile, xmlFilename, "genia-edge-ids.class_names", PARSE_TOK, PARSE_TOK)
ix.splitMergedElements(xmlFilename, xmlFilename)
ix.recalculateIds(xmlFilename, xmlFilename, True)
# EvaluateInteractionXML differs from the previous evaluations in that it can
# be used to compare two separate GifXML-files. One of these is the gold file,
# against which the other is evaluated by heuristically matching triggers and
# edges. Note that this evaluation will differ somewhat from the previous ones,
# which evaluate on the level of examples.
EvaluateInteractionXML.run(Ev, xmlFilename, DEVEL_FILE, PARSE_TOK, PARSE_TOK)
# Post-processing
prune.interface(["-i",xmlFilename,"-o","pruned.xml","-c"])
unflatten.interface(["-i","pruned.xml","-o","unflattened.xml"])
# Output will be stored to the geniaformat-subdirectory, where will also be a
# tar.gz-file which can be sent to the Shared Task evaluation server.
gifxmlToGenia("unflattened.xml", "geniaformat")
