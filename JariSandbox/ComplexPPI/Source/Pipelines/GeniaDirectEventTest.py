# This file shows a possible pipeline, that resembles the Shared Task.
# It uses the mini-subsets of the Shared Task files, which are faster 
# to process and thus enable rapid testing of the system.

# most imports are defined in Pipeline
from Pipeline import *

# define shortcuts for commonly used files
FULL_TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train.xml"
if True: # mini
    TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train-with-duplicates-mini.xml"
    TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-with-duplicates-mini.xml"
else:
    TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train-with-duplicates.xml"
    TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-with-duplicates.xml"
EDGE_CLASSIFIER_PARAMS="c:0.1,1,10,100,1000,10000,100000,1000000"#"c:10000,28000,50000"
optimizeLoop = True # search for a parameter, or use a predefined one
WORKDIR="/usr/share/biotext/GeniaChallenge/GeniaDirectEventTest"
PARSE_TOK="split-McClosky"

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

goldPassThrough = False
if goldPassThrough: # gold pass-through test
    MyCls = ACCls
else:
    MyCls = Cls

###############################################################################
# Trigger detection
###############################################################################
# The gazetteer will increase example generator speed, and is supposed not to
# reduce performance. The gazetteer is built from the full training file,
# even though the mini-sets are used in the slower parts of this demonstration
# pipeline.
if False:
    Gazetteer.run(FULL_TRAIN_FILE, "gazetteer-train", PARSE_TOK)

###############################################################################
# Edge detection
###############################################################################
if False:
    #EDGE_FEATURE_PARAMS="style:typed,directed,entities,genia_limits,noMasking,maxFeatures"
    EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"
        
    # Build examples, see trigger detection
    DirectEventExampleBuilder.run(TRAIN_FILE, "event-train-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-direct-event-ids", "gazetteer-train")
    DirectEventExampleBuilder.run(TEST_FILE, "event-test-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-direct-event-ids", "gazetteer-train")
    # Run the optimization loop. Note that here we must optimize against the gold
    # standard examples, because we do not know real classes of edge examples built between
    # predicted triggers

if True:
    if goldPassThrough:
        c = None
    else:
        c = CSCConnection("GeniaDirectEventTest-event-model", "jakrbj@murska.csc.fi", False)
    best = optimize(MyCls, Ev, "event-train-examples", "event-test-examples",\
        "genia-direct-event-ids.class_names", EDGE_CLASSIFIER_PARAMS, "event-param-opt", None, c)
    
if False:
    # Write the predicted edges to an interaction xml which has predicted triggers.
    # This function handles both trigger and edge example classifications
    edgeXml = ExampleUtils.writeToInteractionXML("edge-test-examples", "edge-test-classifications", TEST_WITH_PRED_TRIGGERS_FILE, None, "ids.edge.class_names", PARSE_TOK, PARSE_TOK)
    # Split overlapping, merged elements (e.g. "Upregulate---Phosphorylate")
    ix.splitMergedElements(edgeXml)
    ## Always remember to fix ids
    ix.recalculateIds(edgeXml, None, True)
    writeXML(edgeXml, "test-predicted-edges.xml")
    # EvaluateInteractionXML differs from the previous evaluations in that it can
    # be used to compare two separate GifXML-files. One of these is the gold file,
    # against which the other is evaluated by heuristically matching triggers and
    # edges. Note that this evaluation will differ somewhat from the previous ones,
    # which evaluate on the level of examples.
    EvaluateInteractionXML.run(Ev, edgeXml, GOLD_TEST_FILE, PARSE_TOK, PARSE_TOK)
    gifxmlToGenia("test-predicted-edges.xml", "geniaformat")
    evaluateSharedTask("geniaformat", 1)