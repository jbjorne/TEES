# This file shows a possible pipeline, that resembles the Shared Task.
# It uses the mini-subsets of the Shared Task files, which are faster 
# to process and thus enable rapid testing of the system.

# most imports are defined in Pipeline
from Pipeline import *

# define shortcuts for commonly used files
FULL_TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train.xml"
if False: # mini
    TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train-with-duplicates-mini.xml"
    TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-with-duplicates-mini.xml"
    GOLD_TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-with-duplicates-mini.xml"
else:
    TRAIN_FILE="/usr/share/biotext/GeniaChallenge/xml/train-with-duplicates.xml"
    TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-with-duplicates.xml"
    GOLD_TEST_FILE="/usr/share/biotext/GeniaChallenge/xml/devel-with-duplicates.xml"
TRIGGER_CLASSIFIER_PARAMS="c:200000"#"c:300000"
RECALL_BOOST_PARAM=0.65
EDGE_CLASSIFIER_PARAMS="c:100,1000,10000,20000,50000,100000,250000,500000,750000,1000000"#"c:10000,28000,50000"
optimizeLoop = True # search for a parameter, or use a predefined one
WORKDIR="/usr/share/biotext/GeniaChallenge/GeniaEventTest"
PARSE_TOK="split-McClosky"

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
copyIdSetsToWorkdir("/usr/share/biotext/GeniaChallenge/extension-data/genia/trigger-examples/genia-trigger-ids")
log() # Start logging into a file in working directory

goldPassThrough = False
if goldPassThrough: # gold pass-through test
    MyCls = ACCls
else:
    MyCls = Cls

###############################################################################
# Trigger detection
###############################################################################
# The gazetteer will increase example generator speed, and is supposed not to
# reduce performance. The gazetteer is built from the full training file,
# even though the mini-sets are used in the slower parts of this demonstration
# pipeline.
if False:
    Gazetteer.run(FULL_TRAIN_FILE, "gazetteer-train", PARSE_TOK)
# Build an SVM example file for the training corpus.
# GeneralEntityTypeRecognizerGztr is a version of GeneralEntityTypeRecognizer
# that can use the gazetteer. The file was split for parallel development, and
# later GeneralEntityTypeRecognizerGztr will be integrated into GeneralEntityTypeRecognizer.
# "ids" is the identifier of the class- and feature-id-files. When
# class and feature ids are reused, models can be reused between experiments.
# Existing id-files, if present, are automatically reused.
if False:
    GeneralEntityTypeRecognizerGztr.run(TRAIN_FILE, "trigger-train-examples", PARSE_TOK, PARSE_TOK, "style:typed", "genia-trigger-ids", "gazetteer-train")
    # Build an SVM example file for the test corpus
    GeneralEntityTypeRecognizerGztr.run(TEST_FILE, "trigger-test-examples", PARSE_TOK, PARSE_TOK, "style:typed", "genia-trigger-ids", "gazetteer-train")
    if optimizeLoop: # search for the best c-parameter
        # The optimize-function takes as parameters a Classifier-class, an Evaluator-class
        # and input and output files
        if goldPassThrough:
            c = None
        else:
            c = CSCConnection("GeniaEventTest-trigger-model", "jakrbj@murska.csc.fi", True)
        best = optimize(MyCls, Ev, "trigger-train-examples", "trigger-test-examples",\
            "genia-trigger-ids.class_names", TRIGGER_CLASSIFIER_PARAMS, "trigger-param-opt", None, c)
    else: # alternatively, use a single parameter (must have only one c-parameter)
        # Train the classifier, and store output into a model file
        Cls.train("trigger-train-examples", TRIGGER_CLASSIFIER_PARAMS, "trigger-model")
        # Use the generated model to classify examples
        Cls.test("trigger-test-examples", "trigger-model", "trigger-test-classifications")
        # The evaluator is needed to access the classifications (will be fixed later)
        Ev.evaluate("trigger-test-examples", "trigger-test-classifications", "genia-trigger-ids.class_names")
    # The classifications are combined with the TEST_FILE xml, to produce
    # an interaction-XML file with predicted triggers
    #triggerXml = ExampleUtils.writeToInteractionXML("trigger-test-examples", "trigger-param-opt/classifications-c_300000", TEST_FILE, "test-predicted-triggers.xml", "genia-trigger-ids.class_names", PARSE_TOK, PARSE_TOK)
    ExampleUtils.writeToInteractionXML("trigger-test-examples", "trigger-param-opt/classifications-c_300000", TEST_FILE, "test-predicted-triggers.xml", "genia-trigger-ids.class_names", PARSE_TOK, PARSE_TOK)
    if True: # boost
        RecallAdjust.run("test-predicted-triggers.xml", RECALL_BOOST_PARAM, "test-predicted-triggers.xml")
    # Overlapping types (could be e.g. "protein---gene") are split into multiple
    # entities
    ix.splitMergedElements("test-predicted-triggers.xml", "test-predicted-triggers.xml")
    # The hierarchical ids are recalculated, since they might be invalid after
    # the generation and modification steps
    ix.recalculateIds("test-predicted-triggers.xml", "test-predicted-triggers.xml", True)

###############################################################################
# Edge detection
###############################################################################
if True:
    #EDGE_FEATURE_PARAMS="style:typed,directed,entities,genia_limits,noMasking,maxFeatures"
    EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"
    # The TEST_FILE for the edge generation step is now the GifXML-file that was built
    # in the previous step, i.e. the one that has predicted triggers
    if goldPassThrough:
        TEST_WITH_PRED_TRIGGERS_FILE = GOLD_TEST_FILE
    else:
        TEST_WITH_PRED_TRIGGERS_FILE = "test-predicted-triggers.xml"
        
    # Build examples, see trigger detection
    EventExampleBuilder.run(TRAIN_FILE, "edge-train-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "ids.edge")
    EventExampleBuilder.run(TEST_WITH_PRED_TRIGGERS_FILE, "edge-test-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "ids.edge")
    # Build an additional set of examples for the gold-standard edge file
    EventExampleBuilder.run(GOLD_TEST_FILE, "edge-gold-test-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, "ids.edge")
    # Run the optimization loop. Note that here we must optimize against the gold
    # standard examples, because we do not know real classes of edge examples built between
    # predicted triggers
    if goldPassThrough:
        c = None
    else:
        c = CSCConnection("GeniaEventTest-event-model", "jakrbj@murska.csc.fi", False)
    best = optimize(MyCls, Ev, "edge-train-examples", "edge-gold-test-examples",\
        "ids.edge.class_names", EDGE_CLASSIFIER_PARAMS, "edge-param-opt", None, c)
    # Once we have determined the optimal c-parameter (best[1]), we can
    # use it to classify our real examples, i.e. the ones that define potential edges
    # between predicted entities
    MyCls.test("edge-test-examples", best[1], "edge-test-classifications")
    # Evaluator is again needed to access classifications, but note that it can't
    # actually evaluate the results, since we don't know the real classes of the edge
    # examples.
    Ev.evaluate("edge-test-examples", "edge-test-classifications", "ids.edge.class_names")
    # Write the predicted edges to an interaction xml which has predicted triggers.
    # This function handles both trigger and edge example classifications
    edgeXml = ExampleUtils.writeToInteractionXML("edge-test-examples", "edge-test-classifications", TEST_WITH_PRED_TRIGGERS_FILE, None, "ids.edge.class_names", PARSE_TOK, PARSE_TOK)
    # Split overlapping, merged elements (e.g. "Upregulate---Phosphorylate")
    ix.splitMergedElements(edgeXml)
    ## Always remember to fix ids
    ix.recalculateIds(edgeXml, None, True)
    writeXML(edgeXml, "test-predicted-edges.xml")
    # EvaluateInteractionXML differs from the previous evaluations in that it can
    # be used to compare two separate GifXML-files. One of these is the gold file,
    # against which the other is evaluated by heuristically matching triggers and
    # edges. Note that this evaluation will differ somewhat from the previous ones,
    # which evaluate on the level of examples.
    EvaluateInteractionXML.run(Ev, edgeXml, GOLD_TEST_FILE, PARSE_TOK, PARSE_TOK)
    gifxmlToGenia("test-predicted-edges.xml", "geniaformat")
    evaluateSharedTask("geniaformat", 1)

###############################################################################
# Post-processing
###############################################################################
if False:
    prune.interface(["-i","test-predicted-edges.xml","-o","pruned.xml","-c"])
    unflatten.interface(["-i","pruned.xml","-o","unflattened.xml","-a",PARSE_TOK,"-t",PARSE_TOK])
    ix.recalculateIds("unflattened.xml", "unflattened.xml", True)
    # Output will be stored to the geniaformat-subdirectory, where will also be a
    # tar.gz-file which can be sent to the Shared Task evaluation server.
    gifxmlToGenia("unflattened.xml", "geniaformat")