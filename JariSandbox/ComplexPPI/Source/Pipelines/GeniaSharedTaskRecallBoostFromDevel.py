# This file shows a possible pipeline, that resembles the Shared Task.
# It uses the mini-subsets of the Shared Task files, which are faster 
# to process and thus enable rapid testing of the system.

# most imports are defined in Pipeline
from Pipeline import *

# define shortcuts for commonly used files
PARSE_TOK="split-McClosky" #"split-Charniak-Lease"
CORPUS_DIR=None
if PARSE_TOK == "split-Charniak-Lease":
    CORPUS_DIR="/usr/share/biotext/GeniaChallenge/xml/old-interaction-xml-files"
elif PARSE_TOK == "McClosky":
    CORPUS_DIR="/usr/share/biotext/GeniaChallenge/xml"
elif PARSE_TOK == "split-McClosky":
    CORPUS_DIR="/usr/share/biotext/GeniaChallenge/xml"
assert(CORPUS_DIR != None)
EXTDIR="/usr/share/biotext/GeniaChallenge/extension-data"
WORKDIR=EXTDIR+"/genia/recall-boost-"+PARSE_TOK+"-t12-"

TRAIN_FILE=CORPUS_DIR+"/train12.xml"
DEVEL_FILE=CORPUS_DIR+"/devel12.xml"
DEVEL_PREDICTED_TRIGGERS_FILE=EXTDIR+"/genia/trigger-model-gazetteer-split-McClosky-gazetteer-t12/devel-predicted-triggers-split-McClosky-gazetteer-t12-"
#DEVEL_PREDICTED_TRIGGERS_FILE=EXTDIR+"/genia/trigger-model-"+PARSE_TOK+"/devel-predicted-triggers-"+PARSE_TOK+"-"
#TRIGGER_CLASSIFIER_PARAMS=[150000,200000,300000]
EDGE_MODEL=EXTDIR+"/genia/edge-model-"+PARSE_TOK+"-t12/devel-edge-param-opt/model-c_" #50000"
#RECALL_ADJUSTER_PARAMS=[0.6,0.7,0.8,0.9]#[0.5,0.6,0.7,0.8,0.9,1.0,1.1,1.2,1.5]
EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"
#EDGE_CLASSIFIER_PARAMS=[50000]

if PARSE_TOK == "split-McClosky":
    #ALL_PARAMS={"trigger":[350000], "booster":["0.9","1.0","1.1"], "edge":[28000]}
    #ALL_PARAMS={"trigger":[80000,200000,350000], "booster":["0.65","0.7","0.8","0.9"], "edge":[10000,28000,50000]}
    #ALL_PARAMS={"trigger":[200000], "booster":["0.5","0.6"], "edge":[28000]}
    #first cube for gazetteer_exclude ALL_PARAMS={"trigger":[100000,150000,200000], "booster":["0.65","0.7","0.8","0.9"], "edge":[10000,28000,50000]}
    ALL_PARAMS={"trigger":[50000,80000,100000], "booster":["0.7","0.9"], "edge":[50000,75000,100000]}
elif PARSE_TOK == "McClosky":
    ALL_PARAMS={"trigger":[80000,200000,350000], "booster":["0.6","0.7","0.8","0.9"], "edge":[10000,25000,50000]}
    #ALL_PARAMS={"trigger":[100000,150000,200000], "booster":["0.6","0.7","0.8","0.9"], "edge":[10000,25000,50000]}
else:
    ALL_PARAMS={"trigger":[150000,200000,300000], "booster":["0.6","0.7","0.8","0.9"], "edge":[10000,25000,50000]}
paramCombinations = getParameterCombinations(ALL_PARAMS)

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
copyIdSetsToWorkdir(EXTDIR+"/genia/trigger-examples/genia-trigger-ids")
copyIdSetsToWorkdir(EXTDIR+"/genia/edge-examples/genia-edge-ids")
log() # Start logging into a file in working directory

count = 0
for params in paramCombinations:
    print >> sys.stderr, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    print >> sys.stderr, "Processing params", str(count) + "/" + str(len(paramCombinations)), params
    print >> sys.stderr, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    pId = getCombinationString(params) #"-boost_"+str(param)[0:3] # param id
    boostedTriggerFile = "devel-predicted-triggers.xml"
    RecallAdjust.run(DEVEL_PREDICTED_TRIGGERS_FILE + str(params["trigger"]) + ".xml", float(params["booster"]), boostedTriggerFile)
    ix.splitMergedElements(boostedTriggerFile, boostedTriggerFile)
    ix.recalculateIds(boostedTriggerFile, boostedTriggerFile, True)
    # Build edge examples
    MultiEdgeExampleBuilder.run(boostedTriggerFile, "devel-edge-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")
    # Classify with pre-defined model
    Cls.test("devel-edge-examples", EDGE_MODEL + str(params["edge"]), "devel-edge-classifications")
    # Write to interaction xml
    evaluator = Ev.evaluate("devel-edge-examples", "devel-edge-classifications", "genia-edge-ids.class_names")
    xmlFilename = "devel-predicted-edges.xml"# + pId + ".xml"
    ExampleUtils.writeToInteractionXML("devel-edge-examples", "devel-edge-classifications", boostedTriggerFile, xmlFilename, "genia-edge-ids.class_names", PARSE_TOK, PARSE_TOK)
    ix.splitMergedElements(xmlFilename, xmlFilename)
    ix.recalculateIds(xmlFilename, xmlFilename, True)
    # EvaluateInteractionXML differs from the previous evaluations in that it can
    # be used to compare two separate GifXML-files. One of these is the gold file,
    # against which the other is evaluated by heuristically matching triggers and
    # edges. Note that this evaluation will differ somewhat from the previous ones,
    # which evaluate on the level of examples.
    EvaluateInteractionXML.run(Ev, xmlFilename, DEVEL_FILE, PARSE_TOK, PARSE_TOK)
    # Post-processing
    preserveTask2.run(xmlFilename, "t2.xml", "no-t2.xml", "extract")
    prune.interface(["-i","no-t2.xml","-o","pruned.xml","-c"])
    unflatten.interface(["-i","pruned.xml","-o","unflattened.xml","-a",PARSE_TOK,"-t",PARSE_TOK])
    preserveTask2.run("unflattened.xml", "final.xml", "t2.xml", "insert")
    # Output will be stored to the geniaformat-subdirectory, where will also be a
    # tar.gz-file which can be sent to the Shared Task evaluation server.
    gifxmlToGenia("final.xml", "geniaformat", 2)
    evaluateSharedTask("geniaformat", 12) # "UTurku-devel-results-090320"
    count += 1
    