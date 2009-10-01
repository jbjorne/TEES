# An experiment with train+devel/test sets using pre-selected parameter values

from Pipeline import *
import os

# define shortcuts for commonly used files
PARSE="stanford-newMC-intra"
TOK="split-McClosky"
CORPUS_DIR="/usr/share/biotext/UnmergingProject/source"
TEST_FILE=CORPUS_DIR+"/with-heads/bioinfer-test-"+PARSE+".xml"
TRAIN_AND_DEVEL_FILE=CORPUS_DIR+"/with-heads/bioinfer-train-and-devel-"+PARSE+".xml"

# trigger examples
TRIGGER_EXAMPLEDIR="/usr/share/biotext/UnmergingProject/results/examples-"+PARSE
TRIGGER_TEST_EXAMPLE_FILE=TRIGGER_EXAMPLEDIR+"/trigger-test-examples-"+PARSE
TRIGGER_TRAIN_AND_DEVEL_EXAMPLE_FILE=TRIGGER_EXAMPLEDIR+"/trigger-train-and-devel-examples-"+PARSE
TRIGGER_IDS="bioinfer-trigger-ids"

# edge examples
EDGE_EXAMPLEDIR=TRIGGER_EXAMPLEDIR
EDGE_TEST_EXAMPLE_FILE=EDGE_EXAMPLEDIR+"/edge-test-examples-"+PARSE
EDGE_TRAIN_AND_DEVEL_EXAMPLE_FILE=EDGE_EXAMPLEDIR+"/edge-train-and-devel-examples-"+PARSE
EDGE_IDS="bioinfer-edge-ids"

# choose a name for the experiment
EXPERIMENT_NAME="UnmergingProject/results/test-set-"+PARSE
WORKDIR="/usr/share/biotext/"+EXPERIMENT_NAME

TRIGGER_CLASSIFIER_PARAMS="c:50000"
EDGE_CLASSIFIER_PARAMS="c:150000"
EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,noMasking,maxFeatures,bioinfer_limits"
#RECALL_BOOST_PARAM=0.7

# start the experiment
workdir(WORKDIR, True) # Select a working directory, remove existing files
log() # Start logging into a file in working directory
copyIdSetsToWorkdir(TRIGGER_EXAMPLEDIR+"/bioinfer-trigger-ids")
copyIdSetsToWorkdir(EDGE_EXAMPLEDIR+"/bioinfer-edge-ids")

print >> sys.stderr, "BioInfer Test Set"
print >> sys.stderr, "Trigger params", TRIGGER_CLASSIFIER_PARAMS
#print >> sys.stderr, "Recall Booster params", str(RECALL_BOOST_PARAM)
print >> sys.stderr, "Edge params", EDGE_CLASSIFIER_PARAMS
###############################################################################
# Triggers
###############################################################################
if True:
    c = CSCConnection(EXPERIMENT_NAME+"/trigger-model", "jakrbj@murska.csc.fi")
    best = optimize(Cls, Ev, TRIGGER_TRAIN_AND_DEVEL_EXAMPLE_FILE, TRIGGER_TEST_EXAMPLE_FILE,\
        TRIGGER_IDS+".class_names", TRIGGER_CLASSIFIER_PARAMS, "test-trigger-param-opt", c)
    ExampleUtils.writeToInteractionXML(TRIGGER_TEST_EXAMPLE_FILE, best[2], TEST_FILE, "test-predicted-triggers.xml", TRIGGER_IDS+".class_names", PARSE, TOK)
    # NOTE: Merged elements must not be split, as recall booster may change their class
    ix.splitMergedElements("test-predicted-triggers.xml", "test-predicted-triggers.xml")
    ix.recalculateIds("test-predicted-triggers.xml", "test-predicted-triggers.xml", True)

###############################################################################
# Edges
###############################################################################
if True:
    #boostedTriggerFile = "test-predicted-triggers-boost.xml"
    #RecallAdjust.run("test-predicted-triggers.xml", RECALL_BOOST_PARAM, boostedTriggerFile)
    #ix.splitMergedElements(boostedTriggerFile, boostedTriggerFile)
    #ix.recalculateIds(boostedTriggerFile, boostedTriggerFile, True)
    # Build edge examples
    #MultiEdgeExampleBuilder.run(boostedTriggerFile, "test-edge-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    MultiEdgeExampleBuilder.run("test-predicted-triggers.xml", "test-edge-examples", PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    # Classify with pre-defined model
    #c = CSCConnection(EXPERIMENT_NAME+"/edge-model", "jakrbj@murska.csc.fi")
    best = optimize(Cls, Ev, EDGE_TRAIN_AND_DEVEL_EXAMPLE_FILE, "test-edge-examples",\
        EDGE_IDS+".class_names", EDGE_CLASSIFIER_PARAMS, "test-edge-param-opt", None)#, c)
# Write to interaction xml
xmlFilename = "test-predicted-edges.xml"
ExampleUtils.writeToInteractionXML("test-edge-examples", "test-edge-param-opt/classifications-c_250000", "test-predicted-triggers.xml", xmlFilename, "bioinfer-edge-ids.class_names", PARSE, TOK)
ix.splitMergedElements(xmlFilename, xmlFilename)
ix.recalculateIds(xmlFilename, xmlFilename, True)
# EvaluateInteractionXML differs from the previous evaluations in that it can
# be used to compare two separate GifXML-files. One of these is the gold file,
# against which the other is evaluated by heuristically matching triggers and
# edges. Note that this evaluation will differ somewhat from the previous ones,
# which evaluate on the level of examples.
EvaluateInteractionXML.run(Ev, xmlFilename, TEST_FILE, PARSE, TOK)

###############################################################################
# Post-processing
###############################################################################
#prune.interface(["-i",xmlFilename,"-o","pruned.xml","-c"])
#unflatten.interface(["-i","pruned.xml","-o","unflattened.xml","-a",PARSE_TOK,"-t",PARSE_TOK])
## Output will be stored to the geniaformat-subdirectory, where will also be a
## tar.gz-file which can be sent to the Shared Task evaluation server.
#gifxmlToGenia("unflattened.xml", "geniaformat")
