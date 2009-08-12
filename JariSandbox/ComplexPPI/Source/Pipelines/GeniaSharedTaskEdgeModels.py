from Pipeline import *
import os

# define shortcuts for commonly used files
PARSE_TOK="split-McClosky" #"split-Charniak-Lease"
CORPUS_DIR=None
if PARSE_TOK == "split-Charniak-Lease":
    CORPUS_DIR="/usr/share/biotext/GeniaChallenge/xml/old-interaction-xml-files"
elif PARSE_TOK == "split-McClosky":
    CORPUS_DIR="/usr/share/biotext/GeniaChallenge/xml"
assert(CORPUS_DIR != None)
DEVEL_FILE=CORPUS_DIR+"/devel.xml"

EXAMPLEDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/edge-examples"
TRAIN_EXAMPLE_FILE=EXAMPLEDIR+"/edge-train-examples-"+PARSE_TOK
DEVEL_EXAMPLE_FILE=EXAMPLEDIR+"/edge-devel-examples-"+PARSE_TOK
TEST_EXAMPLE_FILE=EXAMPLEDIR+"/edge-test-examples-"+PARSE_TOK
EVERYTHING_FILE=EXAMPLEDIR+"/edge-everything-examples-"+PARSE_TOK
CLASS_NAMES=EXAMPLEDIR+"/genia-edge-ids.class_names"
WORKDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/edge-model-"+PARSE_TOK

CLASSIFIER_PARAMS="c:5000,10000,20000,25000,28000,50000,60000,65000,80000,100000,150000"#,1000000"
optimizeLoop = True # search for a parameter, or use a predefined one

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

###############################################################################
# Trigger example generation
###############################################################################
if optimizeLoop: # search for the best c-parameter
    # The optimize-function takes as parameters a Classifier-class, an Evaluator-class
    # and input and output files
    c = CSCConnection("extension-data/genia/devel-edge-model-"+PARSE_TOK, "jakrbj@murska.csc.fi")
    best = optimize(Cls, Ev, TRAIN_EXAMPLE_FILE, DEVEL_EXAMPLE_FILE,\
        CLASS_NAMES, CLASSIFIER_PARAMS, "devel-edge-param-opt", None, c)
    # The evaluator is needed to access the classifications (will be fixed later)
    evaluator = best[0]
ExampleUtils.writeToInteractionXML(evaluator.classifications, DEVEL_FILE, "devel-predicted-edges.xml", CLASS_NAMES, PARSE_TOK, PARSE_TOK)
ix.splitMergedElements("devel-predicted-edges.xml", "devel-predicted-edges.xml")
ix.recalculateIds("devel-predicted-edges.xml", "devel-predicted-edges.xml", True)
EvaluateInteractionXML.run(Ev, "devel-predicted-edges.xml", DEVEL_FILE, PARSE_TOK, PARSE_TOK)

