# An experiment with everything/test sets using pre-selected parameter values

from Pipeline import *
import os

# define shortcuts for commonly used files
PARSE_TOK="split-McClosky" #"split-Charniak-Lease"
CORPUSDIR=None
if PARSE_TOK == "split-Charniak-Lease":
    CORPUSDIR="/usr/share/biotext/GeniaChallenge/xml/old-interaction-xml-files"
elif PARSE_TOK == "McClosky":
    CORPUSDIR="/usr/share/biotext/GeniaChallenge/xml"
elif PARSE_TOK == "split-McClosky":
    CORPUSDIR="/usr/share/biotext/GeniaChallenge/xml"
assert(CORPUSDIR != None)

task = 2
if task == 1:
    #TEST_FILE=CORPUSDIR+"/test.xml"
    #EVERYTHING_FILE=CORPUSDIR+"/everything.xml"
    TEST_FILE=CORPUSDIR+"/devel.xml"
    EVERYTHING_FILE=CORPUSDIR+"/train.xml"
    TASK_TAG=""
else: # 2
    #TEST_FILE=CORPUSDIR+"/test.xml"
    #EVERYTHING_FILE=CORPUSDIR+"/everything.xml"
    TEST_FILE=CORPUSDIR+"/devel12.xml"
    EVERYTHING_FILE=CORPUSDIR+"/train12.xml"
    TASK_TAG="-t12"

TRIGGER_EXAMPLEDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/trigger-examples"
#TRIGGER_TEST_EXAMPLE_FILE=TRIGGER_EXAMPLEDIR+"/trigger-test-examples-"+PARSE_TOK
#TRIGGER_EVERYTHING_EXAMPLE_FILE=TRIGGER_EXAMPLEDIR+"/trigger-everything-examples-"+PARSE_TOK
TRIGGER_TEST_EXAMPLE_FILE=TRIGGER_EXAMPLEDIR+"/trigger-devel-examples-"+PARSE_TOK+TASK_TAG
TRIGGER_EVERYTHING_EXAMPLE_FILE=TRIGGER_EXAMPLEDIR+"/trigger-train-examples-"+PARSE_TOK+TASK_TAG
TRIGGER_IDS="genia-trigger-ids"

EDGE_EXAMPLEDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/edge-examples"
#EDGE_TEST_EXAMPLE_FILE=EDGE_EXAMPLEDIR+"/edge-test-examples-"+PARSE_TOK+TASK_TAG
#EDGE_EVERYTHING_EXAMPLE_FILE=EDGE_EXAMPLEDIR+"/edge-everything-examples-"+PARSE_TOK+TASK_TAG
EDGE_TEST_EXAMPLE_FILE=EDGE_EXAMPLEDIR+"/edge-devel-examples-"+PARSE_TOK+TASK_TAG
EDGE_EVERYTHING_EXAMPLE_FILE=EDGE_EXAMPLEDIR+"/edge-train-examples-"+PARSE_TOK+TASK_TAG
EDGE_IDS="genia-edge-ids"

EXPERIMENT_NAME = "extension-data/genia/devel-set-"+PARSE_TOK+"-task2"
WORKDIR="/usr/share/biotext/GeniaChallenge/"+EXPERIMENT_NAME

# {'trigger': 200000, 'edge': 28000, 'booster': '0.65'}

EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"
if PARSE_TOK == "split-Charniak-Lease":
    TRIGGER_CLASSIFIER_PARAMS="c:150000" #"c:300000"
    EDGE_CLASSIFIER_PARAMS="c:25000" #"c:50000"
    RECALL_BOOST_PARAM=0.7 #0.8
elif PARSE_TOK == "split-McClosky":
    TRIGGER_CLASSIFIER_PARAMS="c:200000" #"c:350000"
    EDGE_CLASSIFIER_PARAMS="c:28000" #"c:28000"
    RECALL_BOOST_PARAM=0.65 #0.7#0.9
else: # McClosky
    TRIGGER_CLASSIFIER_PARAMS="c:200000"
    EDGE_CLASSIFIER_PARAMS="c:50000"
    RECALL_BOOST_PARAM=0.7

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

print >> sys.stderr, "Genia Shared Task for the Test Set"
print >> sys.stderr, "Trigger params", TRIGGER_CLASSIFIER_PARAMS
print >> sys.stderr, "Recall Booster params", str(RECALL_BOOST_PARAM)
print >> sys.stderr, "Edge params", EDGE_CLASSIFIER_PARAMS
###############################################################################
# Triggers
###############################################################################
#copyIdSetsToWorkdir(TRIGGER_EXAMPLEDIR+"/genia-trigger-ids")
#copyIdSetsToWorkdir(EDGE_EXAMPLEDIR+"/genia-edge-ids")
#c = CSCConnection(EXPERIMENT_NAME+"/trigger-model", "jakrbj@murska.csc.fi")
#best = optimize(Cls, Ev, TRIGGER_EVERYTHING_EXAMPLE_FILE, TRIGGER_TEST_EXAMPLE_FILE,\
#    TRIGGER_IDS+".class_names", TRIGGER_CLASSIFIER_PARAMS, "test-trigger-param-opt", None, c)
## The evaluator is needed to access the classifications (will be fixed later)
#evaluator = best[0]
#ExampleUtils.writeToInteractionXML(evaluator.classifications, TEST_FILE, "test-predicted-triggers.xml", TRIGGER_IDS+".class_names", PARSE_TOK, PARSE_TOK)
## NOTE: Merged elements must not be split, as recall booster may change their class
##ix.splitMergedElements("devel-predicted-triggers.xml", "devel-predicted-triggers.xml")
#ix.recalculateIds("test-predicted-triggers.xml", "test-predicted-triggers.xml", True)
#
################################################################################
## Edges
################################################################################
#boostedTriggerFile = "test-predicted-triggers-boost.xml"
#RecallAdjust.run("test-predicted-triggers.xml", RECALL_BOOST_PARAM, boostedTriggerFile)
#ix.splitMergedElements(boostedTriggerFile, boostedTriggerFile)
#ix.recalculateIds(boostedTriggerFile, boostedTriggerFile, True)
## Build edge examples
#MultiEdgeExampleBuilder.run(boostedTriggerFile, "devel-edge-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
## Classify with pre-defined model
#c = CSCConnection(EXPERIMENT_NAME+"/edge-model", "jakrbj@murska.csc.fi")
#best = optimize(Cls, Ev, EDGE_EVERYTHING_EXAMPLE_FILE, "devel-edge-examples",\
#    EDGE_IDS+".class_names", EDGE_CLASSIFIER_PARAMS, "test-edge-param-opt", None, c)
## The evaluator is needed to access the classifications (will be fixed later)
#evaluator = best[0]
## Write to interaction xml
#xmlFilename = "test-predicted-edges.xml"
#ExampleUtils.writeToInteractionXML(evaluator.classifications, boostedTriggerFile, xmlFilename, "genia-edge-ids.class_names", PARSE_TOK, PARSE_TOK)
#ix.splitMergedElements(xmlFilename, xmlFilename)
#ix.recalculateIds(xmlFilename, xmlFilename, True)
## EvaluateInteractionXML differs from the previous evaluations in that it can
## be used to compare two separate GifXML-files. One of these is the gold file,
## against which the other is evaluated by heuristically matching triggers and
## edges. Note that this evaluation will differ somewhat from the previous ones,
## which evaluate on the level of examples.
#EvaluateInteractionXML.run(Ev, xmlFilename, TEST_FILE, PARSE_TOK, PARSE_TOK)
## Post-processing
#preserveTask2.run(xmlFilename, "t2.xml", "no-t2.xml", "extract")
#prune.interface(["-i","no-t2.xml","-o","pruned.xml","-c"])
#unflatten.interface(["-i","pruned.xml","-o","unflattened.xml","-a",PARSE_TOK,"-t",PARSE_TOK])
#preserveTask2.run("unflattened.xml", "final.xml", "t2.xml", "insert")
# Output will be stored to the geniaformat-subdirectory, where will also be a
# tar.gz-file which can be sent to the Shared Task evaluation server.
print "Old:"
evaluateSharedTask("geniaformat-base", 12)
print "New:"
gifxmlToGenia("final.xml", "geniaformat-new", 2)
evaluateSharedTask("geniaformat-new", 12)
