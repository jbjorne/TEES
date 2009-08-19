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

task = 123
if task == 13:
    TRAIN_FILE=CORPUS_DIR+"/train13.xml"
    DEVEL_FILE=CORPUS_DIR+"/devel13.xml"
    #TEST_FILE=CORPUS_DIR+"/test.xml"
    EVERYTHING_FILE=CORPUS_DIR+"/everything13.xml"
    TASK_TAG="-t13"
else: # 123
    TRAIN_FILE=CORPUS_DIR+"/train-with-duplicates123.xml"
    DEVEL_FILE=CORPUS_DIR+"/devel-with-duplicates123.xml"
    #TEST_FILE=CORPUS_DIR+"/test.xml"
    EVERYTHING_FILE=CORPUS_DIR+"/everything-with-duplicates123.xml"
    TASK_TAG="-t123"
task3type = "speculation"

EXAMPLEDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/task3-examples"
TRAIN_EXAMPLE_FILE=EXAMPLEDIR+"/"+task3type+"-train-examples-"+PARSE_TOK+TASK_TAG
DEVEL_EXAMPLE_FILE=EXAMPLEDIR+"/"+task3type+"-devel-examples-"+PARSE_TOK+TASK_TAG
TEST_EXAMPLE_FILE=EXAMPLEDIR+"/"+task3type+"-test-examples-"+PARSE_TOK+TASK_TAG
EVERYTHING_FILE=EXAMPLEDIR+"/"+task3type+"-everything-examples-"+PARSE_TOK+TASK_TAG
CLASS_NAMES=EXAMPLEDIR+"/genia-task3-ids.class_names"
WORKDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/"+task3type+"-model-"+PARSE_TOK+TASK_TAG

CLASSIFIER_PARAMS="c:1000,2000,3000,3500,4000,4500,5000,6000,6500,7000,7500,8000,10000, 12000, 13000, 13500, 14000"#,1000000"
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
    c = CSCConnection("extension-data/genia/"+task3type+"-model-"+PARSE_TOK+TASK_TAG, "jakrbj@murska.csc.fi")
    best = optimize(Cls, Ev, TRAIN_EXAMPLE_FILE, DEVEL_EXAMPLE_FILE,\
        CLASS_NAMES, CLASSIFIER_PARAMS, "devel-edge-param-opt", None, c)
    # The evaluator is needed to access the classifications (will be fixed later)
    evaluator = best[0]
#ExampleUtils.writeToInteractionXML(evaluator.classifications, DEVEL_FILE, "devel-predicted-edges.xml", CLASS_NAMES, PARSE_TOK, PARSE_TOK)
#ix.splitMergedElements("devel-predicted-edges.xml", "devel-predicted-edges.xml")
#ix.recalculateIds("devel-predicted-edges.xml", "devel-predicted-edges.xml", True)
#EvaluateInteractionXML.run(Ev, "devel-predicted-edges.xml", DEVEL_FILE, PARSE_TOK, PARSE_TOK)

