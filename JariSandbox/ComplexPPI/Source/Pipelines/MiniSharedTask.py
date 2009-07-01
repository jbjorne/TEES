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
CLASSIFIER_PARAMS="c:1000,10000,100000"
optimizeLoop = True # search for a parameter, or use a predefined one
WORKDIR="/usr/share/biotext/GeniaChallenge/MiniSharedTask"
PARSE_TOK="split-Charniak-Lease"

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

###############################################################################
# Trigger detection
###############################################################################
# The gazetteer will increase example generator speed, and is supposed not to
# reduce performance. The gazetteer is built from the full training file,
# even though the mini-sets are used in the slower parts of this demonstration
# pipeline.
Gazetteer.run(FULL_TRAIN_FILE, "gazetteer-train")
# Build an SVM example file for the training corpus.
# GeneralEntityTypeRecognizerGztr is a version of GeneralEntityTypeRecognizer
# that can use the gazetteer. The file was split for parallel development, and
# later GeneralEntityTypeRecognizerGztr will be integrated into GeneralEntityTypeRecognizer.
# "ids" is the identifier of the class- and feature-id-files. When
# class and feature ids are reused, models can be reused between experiments.
# Existing id-files, if present, are automatically reused.
GeneralEntityTypeRecognizerGztr.run(TRAIN_FILE, "trigger-train-examples", PARSE_TOK, PARSE_TOK, "style:typed", "ids", "gazetteer-train")
# Build an SVM example file for the test corpus
GeneralEntityTypeRecognizerGztr.run(TEST_FILE, "trigger-test-examples", PARSE_TOK, PARSE_TOK, "style:typed", "ids", "gazetteer-train")
if optimizeLoop: # search for the best c-parameter
    # The optimize-function takes as parameters a Classifier-class, an Evaluator-class
    # and input and output files
    best = optimize(Cls, Ev, "trigger-train-examples", "trigger-test-examples",\
        "ids.class_names", CLASSIFIER_PARAMS, "trigger-param-opt")
    # The evaluator is needed to access the classifications (will be fixed later)
    evaluator = best[0]
else: # alternatively, use a single parameter (must have only one c-parameter)
    # Train the classifier, and store output into a model file
    Cls.train("trigger-train-examples", CLASSIFIER_PARAMS, "trigger-model")
    # Use the generated model to classify examples
    Cls.test("trigger-test-examples", "trigger-model", "trigger-test-classifications")
    # The evaluator is needed to access the classifications (will be fixed later)
    evaluator = Ev.evaluate("trigger-test-examples", "trigger-test-classifications", "trigger-ids.class_names")
# The classifications are combined with the TEST_FILE xml, to produce
# an interaction-XML file with predicted triggers
ExampleUtils.writeToInteractionXML(evaluator.classifications, TEST_FILE, "test-predicted-triggers.xml", "ids.class_names", PARSE_TOK, PARSE_TOK)
# Overlapping types (could be e.g. "protein---gene") are split into multiple
# entities
ix.splitMergedElements("test-predicted-triggers.xml", "test-predicted-triggers.xml")
# The hierarchical ids are recalculated, since they might be invalid after
# the generation and modification steps
ix.recalculateIds("test-predicted-triggers.xml", "test-predicted-triggers.xml", True)

###############################################################################
# Edge detection
###############################################################################
EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"
# The TEST_FILE for the edge generation step is now the GifXML-file that was built
# in the previous step, i.e. the one that has predicted triggers
TEST_FILE = "test-predicted-triggers.xml"
# The optimal c for edge detection can be very different than the one for triggers
CLASSIFIER_PARAMS="c:100,500,1000"
# Build examples, see trigger detection
MultiEdgeExampleBuilder.run(TRAIN_FILE, "edge-train-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "ids.edge")
MultiEdgeExampleBuilder.run(TEST_FILE, "edge-test-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "ids.edge")
# Build an additional set of examples for the gold-standard edge file
MultiEdgeExampleBuilder.run(GOLD_TEST_FILE, "edge-gold-test-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "ids.edge")
# Run the optimization loop. Note that here we must optimize against the gold
# standard examples, because we do not know real classes of edge examples built between
# predicted triggers
best = optimize(Cls, Ev, "edge-train-examples", "edge-gold-test-examples",\
    "ids.edge.class_names", CLASSIFIER_PARAMS, "edge-param-opt")
# Once we have determined the optimal c-parameter (best[1]), we can
# use it to classify our real examples, i.e. the ones that define potential edges
# between predicted entities
Cls.test("edge-test-examples", best[1], "edge-test-classifications")
# Evaluator is again needed to access classifications, but note that it can't
# actually evaluate the results, since we don't know the real classes of the edge
# examples.
evaluator = Ev.evaluate("edge-test-examples", "edge-test-classifications", "ids.edge.class_names")
# Write the predicted edges to an interaction xml which has predicted triggers.
# This function handles both trigger and edge example classifications
ExampleUtils.writeToInteractionXML(evaluator.classifications, TEST_FILE, "test-predicted-edges.xml", "ids.edge.class_names", PARSE_TOK, PARSE_TOK)
# Split overlapping, merged elements (e.g. "Upregulate---Phosphorylate")
ix.splitMergedElements("test-predicted-edges.xml", "test-predicted-edges.xml")
# Always remember to fix ids
ix.recalculateIds("test-predicted-edges.xml", "test-predicted-edges.xml", True)
# EvaluateInteractionXML differs from the previous evaluations in that it can
# be used to compare two separate GifXML-files. One of these is the gold file,
# against which the other is evaluated by heuristically matching triggers and
# edges. Note that this evaluation will differ somewhat from the previous ones,
# which evaluate on the level of examples.
EvaluateInteractionXML.run(Ev, "test-predicted-edges.xml", GOLD_TEST_FILE, PARSE_TOK, PARSE_TOK)

###############################################################################
# Post-processing
###############################################################################
prune.interface(["-i","test-predicted-edges.xml","-o","pruned.xml","-c"])
unflatten.interface(["-i","pruned.xml","-o","unflattened.xml"])
# Output will be stored to the geniaformat-subdirectory, where will also be a
# tar.gz-file which can be sent to the Shared Task evaluation server.
gifxmlToGenia("unflattened.xml", "geniaformat")