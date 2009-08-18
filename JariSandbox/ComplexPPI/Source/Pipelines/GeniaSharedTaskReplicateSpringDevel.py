# An experiment with everything/test sets using pre-selected parameter values

from Pipeline import *
import os

# define shortcuts for commonly used files
PARSE_TOK="split-Charniak-Lease"
CORPUSDIR=None
if PARSE_TOK == "split-Charniak-Lease":
    CORPUSDIR="/usr/share/biotext/GeniaChallenge/xml/old-interaction-xml-files"
elif PARSE_TOK == "McClosky":
    CORPUSDIR="/usr/share/biotext/GeniaChallenge/xml"
elif PARSE_TOK == "split-McClosky":
    CORPUSDIR="/usr/share/biotext/GeniaChallenge/xml"
assert(CORPUSDIR != None)
DEVEL_FILE=CORPUSDIR+"/devel.xml"
TRAIN_FILE=CORPUSDIR+"/train.xml"

EDGE_EXAMPLEDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/edge-examples"
EDGE_DEVEL_EXAMPLE_FILE=EDGE_EXAMPLEDIR+"/edge-devel-examples-"+PARSE_TOK
EDGE_TRAIN_EXAMPLE_FILE=EDGE_EXAMPLEDIR+"/edge-train-examples-"+PARSE_TOK
EDGE_IDS="genia-edge-ids"

EXPERIMENT_NAME = "extension-data/genia/replicate-spring-devel"
WORKDIR="/usr/share/biotext/GeniaChallenge/"+EXPERIMENT_NAME

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
copyIdSetsToWorkdir(EDGE_EXAMPLEDIR+"/genia-edge-ids")
log() # Start logging into a file in working directory

print >> sys.stderr, "Replicate Spring Devel"

################################################################################
## Edges
################################################################################
TRIGGER_FILE="/usr/share/biotext/GeniaChallenge/xml/springtriggers/devel-triggers-final.xml"
EDGE_CLASSIFIER_PARAMS="c:50000"
EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"

# Build edge examples
#MultiEdgeExampleBuilder.run(TRIGGER_FILE, "devel-edge-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
# Classify with pre-defined model
c = CSCConnection(EXPERIMENT_NAME+"/edge-model", "jakrbj@murska.csc.fi")
best = optimize(Cls, Ev, EDGE_TRAIN_EXAMPLE_FILE, "devel-edge-examples",\
    EDGE_IDS+".class_names", EDGE_CLASSIFIER_PARAMS, "devel-edge-param-opt", None, c)
# The evaluator is needed to access the classifications (will be fixed later)
evaluator = best[0]
# Write to interaction xml
xmlFilename = "devel-predicted-edges.xml"
ExampleUtils.writeToInteractionXML(evaluator.classifications, TRIGGER_FILE, xmlFilename, "genia-edge-ids.class_names", PARSE_TOK, PARSE_TOK)
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
unflatten.interface(["-i","pruned.xml","-o","unflattened.xml","-a",PARSE_TOK,"-t",PARSE_TOK])
# Output will be stored to the geniaformat-subdirectory, where will also be a
# tar.gz-file which can be sent to the Shared Task evaluation server.
gifxmlToGenia("unflattened.xml", "geniaformat")
evaluateSharedTask("geniaformat", 1)
