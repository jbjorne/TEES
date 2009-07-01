# most imports are defined in Pipeline
from Pipeline import *

# define shortcuts for commonly used files
TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train.xml"
TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/test-predicted-triggers-split-recids.xml"
GOLD_TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel.xml"
CLASSIFIER_PARAMS="c:1000,10000,30000,100000,200000"
WORKDIR="/usr/share/biotext/GeniaChallenge/SharedTaskEdgeTest"
PARSE_TOK="split-Charniak-Lease"
EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory


###############################################################################
# Edge detection
###############################################################################
MultiEdgeExampleBuilder.run(TRAIN_FILE, "edge-train-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "ids.edge")
MultiEdgeExampleBuilder.run(TEST_FILE, "edge-test-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "ids.edge")
MultiEdgeExampleBuilder.run(GOLD_TEST_FILE, "edge-gold-test-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "ids.edge")
best = optimize(Cls, Ev, "edge-train-examples", "edge-gold-test-examples",\
    "ids.edge.class_names", CLASSIFIER_PARAMS, "edge-param-opt")
Cls.test("edge-test-examples", best[1], "edge-test-classifications")
evaluator = Ev.evaluate("edge-test-examples", "edge-test-classifications", "ids.edge.class_names")
ExampleUtils.writeToInteractionXML(evaluator.classifications, TEST_FILE, "test-predicted-edges.xml", "ids.edge.class_names", PARSE_TOK, PARSE_TOK)
ix.splitMergedElements("test-predicted-edges.xml", "test-predicted-edges.xml")
ix.recalculateIds("test-predicted-edges.xml", "test-predicted-edges.xml", True)
EvaluateInteractionXML.run(Ev, "test-predicted-edges.xml", GOLD_TEST_FILE, PARSE_TOK, PARSE_TOK)

###############################################################################
# Post-processing
###############################################################################
prune.interface(["-i","test-predicted-edges.xml","-o","pruned.xml","-c"])
unflatten.interface(["-i","pruned.xml","-o","unflattened.xml"])
gifxmlToGenia("unflattened.xml", "geniaformat")