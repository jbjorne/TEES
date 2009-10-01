# An experiment with train/devel sets using pre-selected parameter values

from Pipeline import *
import os

# define shortcuts for commonly used files
PARSE="stanford-newMC-intra"
TOK="split-McClosky"
CORPUS_DIR="/usr/share/biotext/UnmergingProject/source"
DEVEL_FILE=CORPUS_DIR+"/with-heads/bioinfer-devel-"+PARSE+".xml"
TRAIN_FILE=CORPUS_DIR+"/with-heads/bioinfer-train-"+PARSE+".xml"

# trigger examples
TRIGGER_EXAMPLEDIR="/usr/share/biotext/UnmergingProject/results/examples-"+PARSE
TRIGGER_DEVEL_EXAMPLE_FILE=TRIGGER_EXAMPLEDIR+"/trigger-devel-examples-"+PARSE
TRIGGER_TRAIN_EXAMPLE_FILE=TRIGGER_EXAMPLEDIR+"/trigger-train-examples-"+PARSE
TRIGGER_IDS="bioinfer-trigger-ids"

# edge examples
EDGE_EXAMPLEDIR=TRIGGER_EXAMPLEDIR
EDGE_DEVEL_EXAMPLE_FILE=EDGE_EXAMPLEDIR+"/edge-devel-examples-"+PARSE
EDGE_TRAIN_EXAMPLE_FILE=EDGE_EXAMPLEDIR+"/edge-train-examples-"+PARSE
EDGE_IDS="bioinfer-edge-ids"

# choose a name for the experiment
EXPERIMENT_NAME="UnmergingProject/results/devel-set-"+PARSE
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

print >> sys.stderr, "BioInfer Devel Set"
print >> sys.stderr, "Trigger params", TRIGGER_CLASSIFIER_PARAMS
#print >> sys.stderr, "Recall Booster params", str(RECALL_BOOST_PARAM)
print >> sys.stderr, "Edge params", EDGE_CLASSIFIER_PARAMS
###############################################################################
# Triggers
###############################################################################
if True:
    c = CSCConnection(EXPERIMENT_NAME+"/trigger-model", "jakrbj@murska.csc.fi", True)
    best = optimize(Cls, Ev, TRIGGER_TRAIN_EXAMPLE_FILE, TRIGGER_DEVEL_EXAMPLE_FILE,\
        TRIGGER_IDS+".class_names", TRIGGER_CLASSIFIER_PARAMS, "devel-trigger-param-opt", c)
    ExampleUtils.writeToInteractionXML(TRIGGER_DEVEL_EXAMPLE_FILE, best[2], DEVEL_FILE, "devel-predicted-triggers.xml", TRIGGER_IDS+".class_names", PARSE, TOK)
    # NOTE: Merged elements must not be split, as recall booster may change their class
    ix.splitMergedElements("devel-predicted-triggers.xml", "devel-predicted-triggers.xml")
    ix.recalculateIds("devel-predicted-triggers.xml", "devel-predicted-triggers.xml", True)

###############################################################################
# Edges
###############################################################################
if True:
    #boostedTriggerFile = "devel-predicted-triggers-boost.xml"
    #RecallAdjust.run("devel-predicted-triggers.xml", RECALL_BOOST_PARAM, boostedTriggerFile)
    #ix.splitMergedElements(boostedTriggerFile, boostedTriggerFile)
    #ix.recalculateIds(boostedTriggerFile, boostedTriggerFile, True)
    # Build edge examples
    #MultiEdgeExampleBuilder.run(boostedTriggerFile, "devel-edge-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    MultiEdgeExampleBuilder.run("devel-predicted-triggers.xml", "devel-edge-examples", PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    # Classify with pre-defined model
    c = CSCConnection(EXPERIMENT_NAME+"/edge-model", "jakrbj@murska.csc.fi", True)
    best = optimize(Cls, Ev, EDGE_TRAIN_EXAMPLE_FILE, "devel-edge-examples",\
        EDGE_IDS+".class_names", EDGE_CLASSIFIER_PARAMS, "devel-edge-param-opt", c)
# Write to interaction xml
xmlFilename = "devel-predicted-edges.xml"
ExampleUtils.writeToInteractionXML("devel-edge-examples", "devel-edge-param-opt/classifications-c_250000", "devel-predicted-triggers.xml", xmlFilename, "bioinfer-edge-ids.class_names", PARSE, TOK)
ix.splitMergedElements(xmlFilename, xmlFilename)
ix.recalculateIds(xmlFilename, xmlFilename, True)
# EvaluateInteractionXML differs from the previous evaluations in that it can
# be used to compare two separate GifXML-files. One of these is the gold file,
# against which the other is evaluated by heuristically matching triggers and
# edges. Note that this evaluation will differ somewhat from the previous ones,
# which evaluate on the level of examples.
EvaluateInteractionXML.run(Ev, xmlFilename, DEVEL_FILE, PARSE, TOK)

###############################################################################
# Post-processing
###############################################################################
#prune.interface(["-i",xmlFilename,"-o","pruned.xml","-c"])
#unflatten.interface(["-i","pruned.xml","-o","unflattened.xml","-a",PARSE_TOK,"-t",PARSE_TOK])
## Output will be stored to the geniaformat-subdirectory, where will also be a
## tar.gz-file which can be sent to the Shared Task evaluation server.
#gifxmlToGenia("unflattened.xml", "geniaformat")
