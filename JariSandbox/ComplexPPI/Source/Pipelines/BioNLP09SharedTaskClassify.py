# A test of the task 2 of the GENIA shared task.
# This pipeline uses the mini-subsets of the Shared Task files, which are faster 
# to process and thus enable rapid testing of the system.

# most imports are defined in Pipeline
from Pipeline import *

# define shortcuts for commonly used files
FULL_TRAIN_FILE=Settings.TrainFile
TRAIN_FILE=Settings.TrainFile
TEST_FILE=Settings.DevelFile
GOLD_TEST_FILE=Settings.DevelFile

TRIGGER_MODEL=Settings.DevelTriggerModel
EDGE_MODEL=Settings.DevelEdgeModel

WORKDIR="/usr/share/biotext/GeniaChallenge/SharedTaskClassifiy"
PARSE_TOK="split-McClosky"

RECALL_BOOST_PARAM=0.65

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, True) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory
TRIGGER_IDS=copyIdSetsToWorkdir(Settings.TriggerIds)
EDGE_IDS=copyIdSetsToWorkdir(Settings.EdgeIds)

###############################################################################
# Trigger detection
###############################################################################
if True:
    # The gazetteer will increase example generator speed, and is supposed not to
    # reduce performance. The gazetteer is built from the full training file,
    # even though the mini-sets are used in the slower parts of this demonstration
    # pipeline.
    Gazetteer.run(FULL_TRAIN_FILE, "gazetteer-train", PARSE_TOK, "headOffset", stem=False)
if True:
    # Build an SVM example file for the training corpus.
    # GeneralEntityTypeRecognizerGztr is a version of GeneralEntityTypeRecognizer
    # that can use the gazetteer. The file was split for parallel development, and
    # later GeneralEntityTypeRecognizerGztr will be integrated into GeneralEntityTypeRecognizer.
    # "ids" is the identifier of the class- and feature-id-files. When
    # class and feature ids are reused, models can be reused between experiments.
    # Existing id-files, if present, are automatically reused.
    GeneralEntityTypeRecognizerGztr.run(TEST_FILE, "trigger-test-examples", PARSE_TOK, PARSE_TOK, "style:typed", TRIGGER_IDS, "gazetteer-train")
    Cls.test("trigger-test-examples", TRIGGER_MODEL, "trigger-test-classifications")
    # Evaluate the predictions
    Ev.evaluate("trigger-test-examples", "trigger-test-classifications", TRIGGER_IDS+".class_names")
    # The classifications are combined with the TEST_FILE xml, to produce
    # an interaction-XML file with predicted triggers
    triggerXML = ExampleUtils.writeToInteractionXML("trigger-test-examples", "trigger-test-classifications", TEST_FILE, "test-predicted-triggers.xml", TRIGGER_IDS+".class_names", PARSE_TOK, PARSE_TOK)
    
    # Run the recall booster
    #boostedTriggerFile = "test-predicted-triggers-boost.xml"
    boostedTriggerFile = RecallAdjust.run("test-predicted-triggers.xml", RECALL_BOOST_PARAM, None)
    # Overlapping types (could be e.g. "protein---gene") are split into multiple
    # entities
    boostedTriggerFile = ix.splitMergedElements(boostedTriggerFile)
    # The hierarchical ids are recalculated, since they might be invalid after
    # the generation and modification steps
    boostedTriggerFile = ix.recalculateIds(boostedTriggerFile, None, True)

###############################################################################
# Edge detection
###############################################################################
if True:
    EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"
    # The test file for the edge generation step is now the GifXML-file that was built
    # in the previous step, i.e. the one that has predicted triggers
    MultiEdgeExampleBuilder.run(boostedTriggerFile, "edge-test-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    # Once we have determined the optimal c-parameter (best[1]), we can
    # use it to classify our real examples, i.e. the ones that define potential edges
    # between predicted entities
    Cls.test("edge-test-examples", EDGE_MODEL, "edge-test-classifications")
    # Write the predicted edges to an interaction xml which has predicted triggers.
    # This function handles both trigger and edge example classifications
    edgeXML = ExampleUtils.writeToInteractionXML("edge-test-examples", "edge-test-classifications", boostedTriggerFile, "test-predicted-edges.xml", EDGE_IDS+".class_names", PARSE_TOK, PARSE_TOK)
    # Split overlapping, merged elements (e.g. "Upregulate---Phosphorylate")
    #ix.splitMergedElements("test-predicted-edges.xml", "test-predicted-edges.xml")
    edgeXML = ix.splitMergedElements(edgeXML)
    # Always remember to fix ids
    #ix.recalculateIds("test-predicted-edges.xml", "test-predicted-edges.xml", True)
    edgeXML = ix.recalculateIds(edgeXML, "test-predicted-edges.xml", True)
    # EvaluateInteractionXML differs from the previous evaluations in that it can
    # be used to compare two separate GifXML-files. One of these is the gold file,
    # against which the other is evaluated by heuristically matching triggers and
    # edges. Note that this evaluation will differ somewhat from the previous ones,
    # which evaluate on the level of examples.
    #EvaluateInteractionXML.run(Ev, "test-predicted-edges.xml", GOLD_TEST_FILE, PARSE_TOK, PARSE_TOK)
    EvaluateInteractionXML.run(Ev, edgeXML, GOLD_TEST_FILE, PARSE_TOK, PARSE_TOK)

###############################################################################
# Post-processing
###############################################################################
# Post-processing
prune.interface(["-i","test-predicted-edges.xml","-o","pruned.xml","-c"])
unflatten.interface(["-i","pruned.xml","-o","unflattened.xml","-a",PARSE_TOK,"-t",PARSE_TOK])
# Output will be stored to the geniaformat-subdirectory, where will also be a
# tar.gz-file which can be sent to the Shared Task evaluation server.
gifxmlToGenia("unflattened.xml", "geniaformat", 1)
evaluateSharedTask("geniaformat", 1)
