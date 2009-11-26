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
PROJECT_DIR = "/usr/share/biotext/GeniaChallenge/CI-release"
TRIGGER_DIR = PROJECT_DIR + "/triggers/triggers" + TRIGGER_TASK_TAG
EDGE_DIR = PROJECT_DIR + "/edges/edges" + EDGE_TASK_TAG
EDGE_MODEL_STEM = EDGE_DIR + "/devel-edge-models/model-c_"
TRIGGER_MODEL_STEM = TRIGGER_DIR + "/devel-trigger-models/model-c_"

if options.gazetteer == "none":
    GAZETTEER = None
else:
    GAZETTEER = TRIGGER_DIR + "/gazetteer-train-" + PARSE_TOK + TRIGGER_TASK_TAG

# Parameters
EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"

ALL_PARAMS={
    "trigger":[100000,150000,180000,200000, 250000, 300000, 350000, 500000,1000000], 
    "booster":[0.7, 0.85, 1.0], 
    "edge":[5000,10000,20000,25000,28000,50000,60000,65000,80000,100000,150000]
}
paramCombinations = getParameterCombinations(ALL_PARAMS)

# These commands will be in the beginning of most pipelines
EXPERIMENT_NAME = "parameters-triggers" + TRIGGER_TASK_TAG + "-edges" + EDGE_TASK_TAG
WORKDIR="/usr/share/biotext/GeniaChallenge/CI-release/parameters/" + EXPERIMENT_NAME
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
copyIdSetsToWorkdir(TRIGGER_DIR + "/genia-trigger-ids")
copyIdSetsToWorkdir(EDGE_DIR + "/genia-edge-ids")
log() # Start logging into a file in working directory

count = 0
for params in paramCombinations:
    print >> sys.stderr, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    print >> sys.stderr, "Processing params", str(count) + "/" + str(len(paramCombinations)), params
    print >> sys.stderr, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    pId = getCombinationString(params) #"-boost_"+str(param)[0:3] # param id
    
    # Build trigger examples
    GeneralEntityTypeRecognizerGztr.run(DEVEL_FILE, "devel-trigger-examples", PARSE_TOK, PARSE_TOK, TRIGGER_FEATURE_PARAMS, "genia-trigger-ids.class_names", GAZETTEER)#"gazetteer-train-"+PARSE_TOK+TASK_TAG)
    Cls.test("devel-trigger-examples", TRIGGER_MODEL_STEM + str(params["trigger"]), "devel-trigger-classifications")
    evaluator = Ev.evaluate("devel-trigger-examples", "devel-trigger-classifications", "genia-trigger-ids.class_names")
    #boostedTriggerFile = "devel-predicted-triggers.xml"
    xml = ExampleUtils.writeToInteractionXML("devel-trigger-examples", "devel-trigger-classifications", DEVEL_FILE, None, "genia-trigger-ids.class_names", PARSE_TOK, PARSE_TOK)    
    # Boost
    xml = RecallAdjust.run(xml, params["booster"], None)
    xml = ix.splitMergedElements(xml, None)
    xml = ix.recalculateIds(xml, None, True)
    
    # Build edge examples
    MultiEdgeExampleBuilder.run(xml, "devel-edge-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")
    # Classify with pre-defined model
    Cls.test("devel-edge-examples", EDGE_MODEL_STEM + str(params["edge"]), "devel-edge-classifications")
    # Write to interaction xml
    evaluator = Ev.evaluate("devel-edge-examples", "devel-edge-classifications", "genia-edge-ids.class_names")
    #xmlFilename = "devel-predicted-edges.xml"# + pId + ".xml"
    xml = ExampleUtils.writeToInteractionXML("devel-edge-examples", "devel-edge-classifications", xml, None, "genia-edge-ids.class_names", PARSE_TOK, PARSE_TOK)
    xml = ix.splitMergedElements(xml, None)
    xml = ix.recalculateIds(xml, "final.xml", True)
    
    # EvaluateInteractionXML differs from the previous evaluations in that it can
    # be used to compare two separate GifXML-files. One of these is the gold file,
    # against which the other is evaluated by heuristically matching triggers and
    # edges. Note that this evaluation will differ somewhat from the previous ones,
    # which evaluate on the level of examples.
    EvaluateInteractionXML.run(Ev, xml, DEVEL_FILE, PARSE_TOK, PARSE_TOK)
    # Post-processing
    #preserveTask2.run(xmlFilename, "t2.xml", "no-t2.xml", "extract")
    prune.interface(["-i","final.xml","-o","pruned.xml","-c"])
    unflatten.interface(["-i","pruned.xml","-o","unflattened.xml","-a",PARSE_TOK,"-t",PARSE_TOK])
    #preserveTask2.run("unflattened.xml", "final.xml", "t2.xml", "insert")
    # Output will be stored to the geniaformat-subdirectory, where will also be a
    # tar.gz-file which can be sent to the Shared Task evaluation server.
    gifxmlToGenia("unflattened.xml", "geniaformat", 1)
    evaluateSharedTask("geniaformat", 1) # "UTurku-devel-results-090320"
    count += 1
    