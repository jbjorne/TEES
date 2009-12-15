# Uses task 2 data, but optimizes for task 1

# most imports are defined in Pipeline
from Pipeline import *
import sys, os

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-n", "--name", default="parameters", dest="name", help="experiment name")
optparser.add_option("-t", "--task", default=1, type="int", dest="task", help="task number")
optparser.add_option("-g", "--gazetteer", default="none", dest="gazetteer", help="gazetteer options: none, stem, full")
optparser.add_option("-e", "--entities", default="nonname", dest="entities", help="tokens to include: nonname, alltokens")
optparser.add_option("-s", "--startFrom", default=0, type="int", dest="startFrom", help="The combination index to start from")
(options, args) = optparser.parse_args()
assert(options.task in [1,2])
assert(options.gazetteer in ["none", "full", "stem"])
assert(options.entities in ["nonname", "alltokens"])

# Main settings
PARSE_TOK="split-McClosky"
CORPUS_DIR="/usr/share/biotext/GeniaChallenge/xml"

# Corpus files
if options.task == 1:
    TRAIN_FILE=CORPUS_DIR+"/train.xml"
    DEVEL_FILE=CORPUS_DIR+"/devel.xml"
    TEST_FILE=CORPUS_DIR+"/test.xml"
    EVERYTHING_FILE=CORPUS_DIR+"/everything.xml"
    TRIGGER_TASK_TAG=""
    EDGE_TASK_TAG=""
else:
    TRAIN_FILE=CORPUS_DIR+"/train12.xml"
    DEVEL_FILE=CORPUS_DIR+"/devel12.xml"
    TEST_FILE=CORPUS_DIR+"/test.xml"
    EVERYTHING_FILE=CORPUS_DIR+"/everything12.xml"
    TRIGGER_TASK_TAG="-t12"
    EDGE_TASK_TAG="-t12"

# Task options
if options.gazetteer == "none":
    TRIGGER_FEATURE_PARAMS="style:typed"
elif options.gazetteer == "full":
    TRIGGER_FEATURE_PARAMS="style:typed,exclude_gazetteer"
    stemGazetteer = False
    TRIGGER_TASK_TAG += "-gazfull"
elif options.gazetteer == "stem":
    TRIGGER_FEATURE_PARAMS="style:typed,exclude_gazetteer,stem_gazetteer"
    stemGazetteer = True
    TRIGGER_TASK_TAG += "-gazstem"

if options.entities == "alltokens":
    TRIGGER_FEATURE_PARAMS += ",all_tokens"
    TRIGGER_TASK_TAG += "-alltokens"


# Pre-made models etc
PROJECT_DIR = "/usr/share/biotext/GeniaChallenge/CI-release/"
TRIGGER_DIR = PROJECT_DIR + "/triggers/triggers" + TRIGGER_TASK_TAG
EDGE_DIR = PROJECT_DIR + "/edges/edges" + EDGE_TASK_TAG
EDGE_MODEL_STEM = EDGE_DIR + "/devel-edge-models/model-c_"
TRIGGER_MODEL_STEM = TRIGGER_DIR + "/devel-trigger-models/model-c_"

if options.gazetteer == "none":
    GAZETTEER = None
    GAZETTEER_EVERYTHING = None
else:
    GAZETTEER = TRIGGER_DIR + "/gazetteer-train-" + PARSE_TOK + TRIGGER_TASK_TAG
    GAZETTEER_EVERYTHING = TRIGGER_DIR + "/gazetteer-everything-" + PARSE_TOK + TRIGGER_TASK_TAG

# Parameters
EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"

BEST_PARAMS={
    "trigger":100000, 
    "booster":0.6, 
    "edge":60000
}

# These commands will be in the beginning of most pipelines
EXPERIMENT_NAME = "final-models-triggers" + TRIGGER_TASK_TAG + "-edges" + EDGE_TASK_TAG
WORKDIR="/usr/share/biotext/GeniaChallenge/CI-release/parameters/" + EXPERIMENT_NAME
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
copyIdSetsToWorkdir(TRIGGER_DIR + "/genia-trigger-ids")
copyIdSetsToWorkdir(EDGE_DIR + "/genia-edge-ids")
log() # Start logging into a file in working directory

###############################################################################
# Devel set
###############################################################################

# Build devel trigger examples
GeneralEntityTypeRecognizerGztr.run(DEVEL_FILE, "devel-trigger-examples", PARSE_TOK, PARSE_TOK, TRIGGER_FEATURE_PARAMS, "genia-trigger-ids", GAZETTEER)
GeneralEntityTypeRecognizerGztr.run(TRAIN_FILE, "train-trigger-examples", PARSE_TOK, PARSE_TOK, TRIGGER_FEATURE_PARAMS, "genia-trigger-ids", GAZETTEER)
MultiEdgeExampleBuilder.run(TRAIN_FILE, "train-edge-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")

Cls.train("train-trigger-examples", "c:"+str(BEST_PARAMS["trigger"]), "train-trigger-model")
Cls.test("devel-trigger-examples", "train-trigger-model", "devel-trigger-classifications")
evaluator = Ev.evaluate("devel-trigger-examples", "devel-trigger-classifications", "genia-trigger-ids.class_names")
#boostedTriggerFile = "devel-predicted-triggers.xml"
xml = ExampleUtils.writeToInteractionXML("devel-trigger-examples", "devel-trigger-classifications", DEVEL_FILE, None, "genia-trigger-ids.class_names", PARSE_TOK, PARSE_TOK)    
# Boost
xml = RecallAdjust.run(xml, BEST_PARAMS["booster"], None)
xml = ix.splitMergedElements(xml, None)
xml = ix.recalculateIds(xml, None, True)

# Build edge examples
MultiEdgeExampleBuilder.run(xml, "devel-edge-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")
Cls.train("train-edge-examples", "c:"+str(BEST_PARAMS["edge"]), "train-edge-model")
Cls.test("devel-edge-examples", "train-edge-model", "devel-edge-classifications")
# Write to interaction xml
evaluator = Ev.evaluate("devel-edge-examples", "devel-edge-classifications", "genia-edge-ids.class_names")
    
xml = ExampleUtils.writeToInteractionXML("devel-edge-examples", "devel-edge-classifications", xml, None, "genia-edge-ids.class_names", PARSE_TOK, PARSE_TOK)
xml = ix.splitMergedElements(xml, None)
xml = ix.recalculateIds(xml, "devel-final.xml", True)

EvaluateInteractionXML.run(Ev, xml, DEVEL_FILE, PARSE_TOK, PARSE_TOK)
# Post-processing
#preserveTask2.run(xmlFilename, "t2.xml", "no-t2.xml", "extract")
prune.interface(["-i","devel-final.xml","-o","devel-pruned.xml","-c"])
unflatten.interface(["-i","devel-pruned.xml","-o","devel-unflattened.xml","-a",PARSE_TOK,"-t",PARSE_TOK])
#preserveTask2.run("unflattened.xml", "final.xml", "t2.xml", "insert")
# Output will be stored to the geniaformat-subdirectory, where will also be a
# tar.gz-file which can be sent to the Shared Task evaluation server.
gifxmlToGenia("devel-unflattened.xml", "devel-geniaformat", 1)
evaluateSharedTask("devel-geniaformat", 1) # "UTurku-devel-results-090320"    

###############################################################################
# Test set
###############################################################################

# Build test trigger examples
GeneralEntityTypeRecognizerGztr.run(TEST_FILE, "test-trigger-examples", PARSE_TOK, PARSE_TOK, TRIGGER_FEATURE_PARAMS, "genia-trigger-ids", GAZETTEER_EVERYTHING)
GeneralEntityTypeRecognizerGztr.run(EVERYTHING_FILE, "everything-trigger-examples", PARSE_TOK, PARSE_TOK, TRIGGER_FEATURE_PARAMS, "genia-trigger-ids", GAZETTEER_EVERYTHING)
MultiEdgeExampleBuilder.run(EVERYTHING_FILE, "everything-edge-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")

Cls.train("everything-trigger-examples", "c:"+str(BEST_PARAMS["trigger"]), "everything-trigger-model")
Cls.test("test-trigger-examples", "everything-trigger-model", "test-trigger-classifications")
evaluator = Ev.evaluate("test-trigger-examples", "test-trigger-classifications", "genia-trigger-ids.class_names")
#boostedTriggerFile = "test-predicted-triggers.xml"
xml = ExampleUtils.writeToInteractionXML("test-trigger-examples", "test-trigger-classifications", TEST_FILE, None, "genia-trigger-ids.class_names", PARSE_TOK, PARSE_TOK)    
# Boost
xml = RecallAdjust.run(xml, BEST_PARAMS["booster"], None)
xml = ix.splitMergedElements(xml, None)
xml = ix.recalculateIds(xml, None, True)

# Build edge examples
MultiEdgeExampleBuilder.run(xml, "test-edge-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")
Cls.train("everything-edge-examples", "c:"+str(BEST_PARAMS["edge"]), "everything-edge-model")
Cls.test("test-edge-examples", "everything-edge-model", "test-edge-classifications")
# Write to interaction xml
evaluator = Ev.evaluate("test-edge-examples", "test-edge-classifications", "genia-edge-ids.class_names")
    
xml = ExampleUtils.writeToInteractionXML("test-edge-examples", "test-edge-classifications", xml, None, "genia-edge-ids.class_names", PARSE_TOK, PARSE_TOK)
xml = ix.splitMergedElements(xml, None)
xml = ix.recalculateIds(xml, "test-final.xml", True)

EvaluateInteractionXML.run(Ev, xml, TEST_FILE, PARSE_TOK, PARSE_TOK)
# Post-processing
#preserveTask2.run(xmlFilename, "t2.xml", "no-t2.xml", "extract")
prune.interface(["-i","test-final.xml","-o","test-pruned.xml","-c"])
unflatten.interface(["-i","test-pruned.xml","-o","test-unflattened.xml","-a",PARSE_TOK,"-t",PARSE_TOK])
#preserveTask2.run("unflattened.xml", "final.xml", "t2.xml", "insert")
# Output will be stored to the geniaformat-subdirectory, where will also be a
# tar.gz-file which can be sent to the Shared Task evaluation server.
gifxmlToGenia("test-unflattened.xml", "test-geniaformat", 1)
evaluateSharedTask("test-geniaformat", 1) # "UTurku-test-results-090320"    
