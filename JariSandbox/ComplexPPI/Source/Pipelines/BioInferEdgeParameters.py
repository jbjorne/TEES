from Pipeline import *
import os

# define shortcuts for commonly used files
PARSE="stanford-newMC-intra" #"split-Charniak-Lease"
TOK="split-McClosky"
CORPUS_DIR="/usr/share/biotext/UnmergingProject/source"
DEVEL_FILE=CORPUS_DIR+"/with-heads/bioinfer-devel-"+PARSE+".xml"

EXAMPLEDIR="/usr/share/biotext/UnmergingProject/results/examples-"+PARSE
TRAIN_EXAMPLE_FILE=EXAMPLEDIR+"/edge-train-examples-"+PARSE
DEVEL_EXAMPLE_FILE=EXAMPLEDIR+"/edge-devel-examples-"+PARSE
CLASS_NAMES=EXAMPLEDIR+"/bioinfer-edge-ids.class_names"
WORKDIR="/usr/share/biotext/UnmergingProject/results/parameters/edges-"+PARSE

CLASSIFIER_PARAMS="c:10,20,30,40,50,60,70,80,90,100,500,1000,5000,10000,20000,50000,80000,100000,150000,180000,200000, 250000, 300000, 350000, 500000,1000000,5000000,10000000"

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, True) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory
print >> sys.stderr, "edge model pipeline for parse", PARSE

###############################################################################
# edge example generation
###############################################################################
# The optimize-function takes as parameters a Classifier-class, an Evaluator-class
# and input and output files
c = CSCConnection("UnmergingProject/results/parameters/edges-"+PARSE, "jakrbj@louhi.csc.fi", True)
best = optimize(Cls, Ev, TRAIN_EXAMPLE_FILE, DEVEL_EXAMPLE_FILE, CLASS_NAMES, CLASSIFIER_PARAMS, "edge-param-opt", None, c)
xmlFilename = "predicted-edges-"+PARSE+".xml"
ExampleUtils.writeToInteractionXML(DEVEL_EXAMPLE_FILE, best[2], DEVEL_FILE, xmlFilename, CLASS_NAMES, PARSE, TOK)
# NOTE: Merged elements must not be split, as recall booster may change their class
#ix.splitMergedElements("devel-predicted-edges.xml", "devel-predicted-edges.xml")
ix.recalculateIds(xmlFilename, xmlFilename, True)
