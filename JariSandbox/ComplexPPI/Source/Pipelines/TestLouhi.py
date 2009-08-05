# This file shows a possible pipeline, that resembles the Shared Task.
# It uses the mini-subsets of the Shared Task files, which are faster 
# to process and thus enable rapid testing of the system.

# most imports are defined in Pipeline
from Pipeline import *

# define shortcuts for commonly used files
FULL_TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train.xml"
TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train-mini.xml"
TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-mini.xml"
GOLD_TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-mini.xml"
CLASSIFIER_PARAMS="c:1000, 5000, 10000"
optimizeLoop = True # search for a parameter, or use a predefined one
WORKDIR="/usr/share/biotext/GeniaChallenge/TestLouhi"
PARSE_TOK="split-Charniak-Lease"

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

###############################################################################
# Trigger detection
###############################################################################
c = CSCConnection("remoteTest")
if optimizeLoop: # search for the best c-parameter
    # The optimize-function takes as parameters a Classifier-class, an Evaluator-class
    # and input and output files
    best = optimize(Cls, Ev, "trigger-train-examples", "trigger-test-examples",\
        "ids.class_names", CLASSIFIER_PARAMS, "trigger-param-opt", None, c)
    # The evaluator is needed to access the classifications (will be fixed later)
    evaluator = best[0]
else: # alternatively, use a single parameter (must have only one c-parameter)
    # Train the classifier, and store output into a model file
    Cls.train("trigger-train-examples", CLASSIFIER_PARAMS, "trigger-model")
    # Use the generated model to classify examples
    Cls.test("trigger-test-examples", "trigger-model", "trigger-test-classifications")
    # The evaluator is needed to access the classifications (will be fixed later)
    evaluator = Ev.evaluate("trigger-test-examples", "trigger-test-classifications", "trigger-ids.class_names")

print evaluator