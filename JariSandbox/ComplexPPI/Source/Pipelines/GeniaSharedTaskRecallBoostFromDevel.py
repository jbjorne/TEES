# This file shows a possible pipeline, that resembles the Shared Task.
# It uses the mini-subsets of the Shared Task files, which are faster 
# to process and thus enable rapid testing of the system.

# most imports are defined in Pipeline
from Pipeline import *

# define shortcuts for commonly used files
XMLDIR="/usr/share/biotext/GeniaChallenge/xml"
EXTDIR="/usr/share/biotext/GeniaChallenge/extension-data"
WORKDIR=EXTDIR+"/genia/recall-boost"

TRAIN_FILE=XMLDIR+"/train.xml"
DEVEL_FILE=XMLDIR+"/devel.xml"
DEVEL_PREDICTED_TRIGGERS_FILE=EXTDIR+"/genia/trigger-model/devel-predicted-triggers.xml"
EDGE_MODEL=EXTDIR+"/genia/edge-model/devel-edge-param-opt/model-c_50000"
RECALL_ADJUSTER_PARAMS=[0.5,0.6,0.7,0.8,0.9,1.0,1.1,1.2,1.5]
EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"
PARSE_TOK="split-Charniak-Lease"

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

for param in RECALL_ADJUSTER_PARAMS:
    print >> sys.stderr, "Processing recall booster param", param
    pId = "-boost_"+str(param)[0:3] # param id
    boostedTriggerFile = "devel-predicted-triggers"+pId+".xml"
    RecallAdjust.run(DEVEL_PREDICTED_TRIGGERS_FILE, param, boostedTriggerFile)
    ix.splitMergedElements(boostedTriggerFile, boostedTriggerFile)
    ix.recalculateIds(boostedTriggerFile, boostedTriggerFile, True)
    # Build edge examples
    MultiEdgeExampleBuilder.run(boostedTriggerFile, "devel-edge-examples"+pId, PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")
    # Classify with pre-defined model
    Cls.test("devel-edge-examples"+pId, EDGE_MODEL, "devel-edge-classifications"+pId)
    # Write to interaction xml
    evaluator = Ev.evaluate("devel-edge-examples"+pId, "devel-edge-classifications"+pId, "genia-edge-ids.class_names")
    xmlFilename = "devel-predicted-edges" + pId + ".xml"
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
    prune.interface(["-i",xmlFilename,"-o","pruned"+pId+".xml","-c"])
    unflatten.interface(["-i","pruned"+pId+".xml","-o","unflattened"+pId+".xml"])
    # Output will be stored to the geniaformat-subdirectory, where will also be a
    # tar.gz-file which can be sent to the Shared Task evaluation server.
    gifxmlToGenia("unflattened"+pId+".xml", "geniaformat"+pId)
    evaluateSharedTask("geniaformat"+pId, 1) # "UTurku-devel-results-090320"
    