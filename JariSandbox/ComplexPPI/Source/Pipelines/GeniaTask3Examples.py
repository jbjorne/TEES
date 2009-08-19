# This file shows a possible pipeline, that resembles the Shared Task.
# It uses the mini-subsets of the Shared Task files, which are faster 
# to process and thus enable rapid testing of the system.

# most imports are defined in Pipeline
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
WORKDIR="/usr/share/biotext/GeniaChallenge/extension-data/genia/task3-examples"

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, True) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory
print >> sys.stderr, "Task3 example pipeline for parse", PARSE_TOK, "task", task

###############################################################################
# Task 3 example generation
###############################################################################
for task3type in ["speculation","negation"]:
    if task3type == "speculation":
        EXAMPLE_STYLE="style:typed,speculation"
    else: # negation
        EXAMPLE_STYLE="style:typed,negation"
    #if not os.path.exists(task3type+"-devel-examples-"+PARSE_TOK+TASK_TAG):
    Task3ExampleBuilder.run(DEVEL_FILE, task3type+"-devel-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, EXAMPLE_STYLE, "genia-task3-ids")
    #if not os.path.exists(task3type+"-train-examples-"+PARSE_TOK+TASK_TAG):
    Task3ExampleBuilder.run(TRAIN_FILE, task3type+"-train-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, EXAMPLE_STYLE, "genia-task3-ids")
    #if not os.path.exists(task3type+"-everything-examples-"+PARSE_TOK+TASK_TAG):
    Task3ExampleBuilder.run(EVERYTHING_FILE, task3type+"-everything-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, EXAMPLE_STYLE, "genia-task3-ids")
    #if not os.path.exists(task3type+"-test-examples-"+PARSE_TOK+TASK_TAG):
    #    GeneralEntityTypeRecognizerGztr.run(TEST_FILE, task3type+"-test-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, EXAMPLE_STYLE, "genia-task3-ids")
