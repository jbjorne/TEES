# This file shows a possible pipeline, that resembles the Shared Task.
# It uses the mini-subsets of the Shared Task files, which are faster 
# to process and thus enable rapid testing of the system.

# most imports are defined in Pipeline
from Pipeline import *

# define shortcuts for commonly used files
FULL_TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train.xml"
if False: # mini
    TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train-with-duplicates-mini.xml"
    TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-with-duplicates-mini.xml"
    EMPTY_TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-with-duplicates-mini-empty.xml"
    EXPERIMENT_NAME="GeniaDirectEventTest"
else:
    TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train-with-duplicates.xml"
    TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-with-duplicates.xml"
    EMPTY_TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-with-duplicates-empty.xml"
    EXPERIMENT_NAME="GeniaDirectEventTestFull"
EDGE_CLASSIFIER_PARAMS="c:10000000,50000000,100000000,1000000000"#"c:10000,28000,50000"
#EDGE_CLASSIFIER_PARAMS="c:1,10,100,1000,10000,100000,500000,1000000,5000000,10000000"#"c:10000,28000,50000"
#EDGE_CLASSIFIER_PARAMS="c:0.00001,0.0001,0.001,0.01,0.1,1,10,100"#"c:10000,28000,50000"
optimizeLoop = True # search for a parameter, or use a predefined one
WORKDIR="/usr/share/biotext/GeniaChallenge/" + EXPERIMENT_NAME
PARSE_TOK="split-McClosky"

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
#log() # Start logging into a file in working directory
    
if True:
#    best = [None,None,"event-test-empty-classifications"]
#    #best = [None,None,"event-param-opt/predictions-c_1000000"]
#    # Write the predicted edges to an interaction xml which has predicted triggers.
#    # This function handles both trigger and edge example classifications
#    edgeXml = ExampleUtils.writeToInteractionXML("event-test-empty-examples", best[2], TEST_FILE, None, "genia-direct-event-ids.class_names", PARSE_TOK, PARSE_TOK)
#    # Split overlapping, merged elements (e.g. "Upregulate---Phosphorylate")
#    #ix.splitMergedElements(edgeXml)
#    ## Always remember to fix ids
#    ix.recalculateIds(edgeXml, None, True)
#    writeXML(edgeXml, "test-predicted-events.xml")
#    # EvaluateInteractionXML differs from the previous evaluations in that it can
#    # be used to compare two separate GifXML-files. One of these is the gold file,
#    # against which the other is evaluated by heuristically matching triggers and
#    # edges. Note that this evaluation will differ somewhat from the previous ones,
#    # which evaluate on the level of examples.
#    EvaluateInteractionXML.run(Ev, "test-predicted-events.xml", TEST_FILE, PARSE_TOK, PARSE_TOK)
    prune.interface(["-i","test-predicted-events-merged.xml","-o","pruned.xml","-c"])
    unflatten.interface(["-i","pruned.xml","-o","unflattened.xml","-a",PARSE_TOK,"-t",PARSE_TOK])
    ix.recalculateIds("unflattened.xml", "unflattened.xml", True)
    gifxmlToGenia("unflattened.xml", "geniaformat", 1)
    evaluateSharedTask("geniaformat", 1)