# Optimize parameters for event detection and produce event and trigger model files

# most imports are defined in Pipeline
from Pipeline import *
import sys, os

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-e", "--test", default=Settings.DevelFile, dest="testFile", help="Test file in interaction xml")
optparser.add_option("-r", "--train", default=Settings.TrainFile, dest="trainFile", help="Train file in interaction xml")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-a", "--task", default=1, type="int", dest="task", help="task number")
optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="Tokenization XML element name")
# Id sets
optparser.add_option("-w", "--edgeIds", default=None, dest="edgeIds", help="Edge detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
# Parameters to optimize
optparser.add_option("-z", "--edgeParams", default="5000,10000,20000,25000,28000,50000,60000,65000,80000,100000,150000", dest="edgeParams", help="Edge detector c-parameter values")
(options, args) = optparser.parse_args()

# Check options
assert options.output != None
assert options.task in [1, 2]

# Main settings
PARSE=options.parse
TOK=options.tokenization
TRAIN_FILE = options.trainFile
DEVEL_FILE = options.testFile

# Example generation parameters
EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"

# Parameters to optimize
ALL_PARAMS={
    "edge":[int(i) for i in options.edgeParams.split(",")]    
}

# These commands will be in the beginning of most pipelines
WORKDIR=options.output
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

PARSE_TAG = PARSE + "_" + TOK

# Pre-calculate all the required SVM models
#EDGE_IDS = copyIdSetsToWorkdir(options.edgeIds)
EDGE_IDS = "unmerged-edge"

###############################################################################
# Edge example generation
###############################################################################
EDGE_TRAIN_EXAMPLE_FILE = "edge-train-examples-"+PARSE_TAG
EDGE_DEVEL_EXAMPLE_FILE = "edge-devel-examples-"+PARSE_TAG
print >> sys.stderr, "Edge examples for parse", PARSE_TAG  
UnmergedEdgeExampleBuilder.run(TRAIN_FILE, EDGE_TRAIN_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
UnmergedEdgeExampleBuilder.run(DEVEL_FILE, EDGE_DEVEL_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)

###############################################################################
# Edge models
###############################################################################
print >> sys.stderr, "Edge models for parse", PARSE_TAG
EDGE_CLASSIFIER_PARAMS="c:" + ','.join(map(str, ALL_PARAMS["edge"]))
c = CSCConnection("UnmergedEdgeTest/models-"+PARSE_TAG+"/trigger-models", "jakrbj@murska.csc.fi", True)
optimize(Cls, Ev, EDGE_TRAIN_EXAMPLE_FILE, EDGE_DEVEL_EXAMPLE_FILE,\
    EDGE_IDS+".class_names", EDGE_CLASSIFIER_PARAMS, "edge-models", None, c)  
