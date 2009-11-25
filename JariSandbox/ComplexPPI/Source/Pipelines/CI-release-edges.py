# most imports are defined in Pipeline
from Pipeline import *
import sys, os

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-n", "--name", default="edges", dest="name", help="experiment name")
optparser.add_option("-t", "--task", default=1, type="int", dest="task", help="task number")
(options, args) = optparser.parse_args()
assert(options.task in [1,2])

# define shortcuts for commonly used files
PARSE_TOK="split-McClosky"
CORPUS_DIR="/usr/share/biotext/GeniaChallenge/xml"

if options.task == 1:
    TRAIN_FILE=CORPUS_DIR+"/train.xml"
    DEVEL_FILE=CORPUS_DIR+"/devel.xml"
    TEST_FILE=CORPUS_DIR+"/test.xml"
    EVERYTHING_FILE=CORPUS_DIR+"/everything.xml"
    TASK_TAG=""
else:
    TRAIN_FILE=CORPUS_DIR+"/train12.xml"
    DEVEL_FILE=CORPUS_DIR+"/devel12.xml"
    TEST_FILE=CORPUS_DIR+"/test.xml"
    EVERYTHING_FILE=CORPUS_DIR+"/everything12.xml"
    TASK_TAG="-t12"

EXPERIMENT_NAME = options.name + TASK_TAG    
WORKDIR="/usr/share/biotext/GeniaChallenge/CI-release/edges/" + EXPERIMENT_NAME

EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

###############################################################################
# Edge example generation
###############################################################################
EDGE_TRAIN_EXAMPLE_FILE = "edge-train-examples-"+PARSE_TOK+TASK_TAG
EDGE_DEVEL_EXAMPLE_FILE = "edge-devel-examples-"+PARSE_TOK+TASK_TAG
if True:
    print >> sys.stderr, "Edge examples for parse", PARSE_TOK, "task", task
    
    MultiEdgeExampleBuilder.run(TRAIN_FILE, EDGE_TRAIN_EXAMPLE_FILE, PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")
    MultiEdgeExampleBuilder.run(DEVEL_FILE, EDGE_DEVEL_EXAMPLE_FILE, PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")
    MultiEdgeExampleBuilder.run(EVERYTHING_FILE, "edge-everything-examples-"+PARSE_TOK+TASK_TAG, PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "genia-edge-ids")

###############################################################################
# Edge models
###############################################################################
EDGE_CLASSIFIER_PARAMS="c:5000,10000,20000,25000,28000,50000,60000,65000,80000,100000,150000"#, 200000, 250000, 300000, 350000, 500000"#,1000000"
if True:
    c = CSCConnection("CI-release/models/"+EXPERIMENT_NAME, "jakrbj@murska.csc.fi", True)
    optimize(Cls, Ev, EDGE_TRAIN_EXAMPLE_FILE, EDGE_DEVEL_EXAMPLE_FILE,\
        "genia-edge-ids.class_names", EDGE_CLASSIFIER_PARAMS, "devel-edge-models", None, c, downloadAllModels=True)
