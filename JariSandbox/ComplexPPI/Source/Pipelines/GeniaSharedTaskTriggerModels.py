from Pipeline import *
import os

# define shortcuts for commonly used files
PARSE_TOK="split-Charniak-Lease"
CORPUSDIR="/usr/share/biotext/GeniaChallenge/xml"
DEVEL_FILE=CORPUSDIR+"/devel.xml"

EXAMPLEDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/trigger-examples"
TRAIN_EXAMPLE_FILE=EXAMPLEDIR+"/trigger-train-examples-split-Charniak-Lease"
DEVEL_EXAMPLE_FILE=EXAMPLEDIR+"/trigger-devel-examples-split-Charniak-Lease"
TEST_EXAMPLE_FILE=EXAMPLEDIR+"/trigger-test-examples-split-Charniak-Lease"
EVERYTHING_FILE=EXAMPLEDIR+"/trigger-everything-examples-split-Charniak-Lease"
CLASS_NAMES=EXAMPLEDIR+"/genia-trigger-ids.class_names"
WORKDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/trigger-model"

CLASSIFIER_PARAMS="c:10,20,30,40,50,60,70,80,90,100,500,1000,5000,10000,20000,50000,80000,100000,150000,180000,200000, 250000, 300000, 350000, 500000,1000000,5000000,10000000"
optimizeLoop = True # search for a parameter, or use a predefined one

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory
print >> sys.stderr, "Trigger model pipeline for parse", PARSE_TOK

###############################################################################
# Trigger example generation
###############################################################################
if optimizeLoop: # search for the best c-parameter
    # The optimize-function takes as parameters a Classifier-class, an Evaluator-class
    # and input and output files
    c = CSCConnection("GeniaSharedTaskDevelTriggerModel")
    best = optimize(Cls, Ev, TRAIN_EXAMPLE_FILE, DEVEL_EXAMPLE_FILE,\
        CLASS_NAMES, CLASSIFIER_PARAMS, "devel-trigger-param-opt", None, c)
    # The evaluator is needed to access the classifications (will be fixed later)
    evaluator = best[0]
ExampleUtils.writeToInteractionXML(evaluator.classifications, DEVEL_FILE, "devel-predicted-triggers.xml", CLASS_NAMES, PARSE_TOK, PARSE_TOK)
# NOTE: Merged elements must not be split, as recall booster may change their class
#ix.splitMergedElements("devel-predicted-triggers.xml", "devel-predicted-triggers.xml")
ix.recalculateIds("devel-predicted-triggers.xml", "devel-predicted-triggers.xml", True)
