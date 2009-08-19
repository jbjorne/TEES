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
SPEC_TRAIN_EXAMPLE_FILE=EXAMPLEDIR+"/speculation-train-examples-"+PARSE_TOK+TASK_TAG
SPEC_DEVEL_EXAMPLE_FILE=EXAMPLEDIR+"/speculation-devel-examples-"+PARSE_TOK+TASK_TAG
SPEC_TEST_EXAMPLE_FILE=EXAMPLEDIR+"/speculation-test-examples-"+PARSE_TOK+TASK_TAG
SPEC_EVERYTHING_FILE=EXAMPLEDIR+"/speculation-everything-examples-"+PARSE_TOK+TASK_TAG
NEG_TRAIN_EXAMPLE_FILE=EXAMPLEDIR+"/negation-train-examples-"+PARSE_TOK+TASK_TAG
NEG_DEVEL_EXAMPLE_FILE=EXAMPLEDIR+"/negation-devel-examples-"+PARSE_TOK+TASK_TAG
NEG_TEST_EXAMPLE_FILE=EXAMPLEDIR+"/negation-test-examples-"+PARSE_TOK+TASK_TAG
NEG_EVERYTHING_FILE=EXAMPLEDIR+"/negation-everything-examples-"+PARSE_TOK+TASK_TAG
CLASS_NAMES=EXAMPLEDIR+"/genia-task3-ids.class_names"
WORKDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/task3-devel-"+PARSE_TOK+TASK_TAG

optimizeLoop = True # search for a parameter, or use a predefined one

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory
#copyIdSetsToWorkdir(EXAMPLEDIR+"/genia-task3-ids")
#
##SOURCE_XML_FILE="/usr/share/biotext/GeniaChallenge/extension-data/genia/test-set-split-McClosky-develDebug/test-predicted-edges.xml"
SOURCE_XML_FILE="/usr/share/biotext/GeniaChallenge/extension-data/genia/devel-set-split-McClosky-task2/final.xml"
##SOURCE_GOLD_XML_FILE=CORPUS_DIR+"/devel12.xml"
#
################################################################################
## Trigger example generation
################################################################################
## Speculation
#Task3ExampleBuilder.run(SOURCE_XML_FILE, "speculation-examples", PARSE_TOK, PARSE_TOK, "style:typed,speculation", "genia-task3-ids")
if optimizeLoop: # search for the best c-parameter
    c = CSCConnection("extension-data/genia/devel-speculation-model2-"+PARSE_TOK+TASK_TAG, "jakrbj@murska.csc.fi")
    best = optimize(Cls, Ev, SPEC_TRAIN_EXAMPLE_FILE, "speculation-examples",\
        CLASS_NAMES, "c:13000", "speculation-param-opt", None, c)
    evaluator = best[0]
ExampleUtils.writeTask3ToInteractionXML(evaluator.classifications, SOURCE_XML_FILE, "task3-only-speculation.xml", "speculation")

# Negation
#Task3ExampleBuilder.run(SOURCE_XML_FILE, "negation-examples", PARSE_TOK, PARSE_TOK, "style:typed,negation", "genia-task3-ids")
if optimizeLoop: # search for the best c-parameter
    c = CSCConnection("extension-data/genia/devel-negation-model2-"+PARSE_TOK+TASK_TAG, "jakrbj@murska.csc.fi")
    best = optimize(Cls, Ev, NEG_TRAIN_EXAMPLE_FILE, "negation-examples",\
        CLASS_NAMES, "c:10000", "negation-param-opt", None, c)
    evaluator = best[0]
ExampleUtils.writeTask3ToInteractionXML(evaluator.classifications, "task3-only-speculation.xml", "task3.xml", "negation")
#
##EvaluateInteractionXML.run(Ev, "task3.xml", SOURCE_GOLD_XML_FILE, PARSE_TOK, PARSE_TOK)
gifxmlToGenia("task3.xml", "geniaformat", 3)
evaluateSharedTask("geniaformat", 3)

