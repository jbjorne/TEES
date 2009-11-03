# Builds Bioinfer trigger and edge example files for a specified parse

from Pipeline import *
import sys,os

WORKDIR = "/usr/share/biotext/UnmergingProject/results/BioInferFull"
# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

# define shortcuts for commonly used files
PARSE="stanford-newMC-intra" #"split-Charniak-Lease"
TOK="split-McClosky"
CORPUS_DIR="/usr/share/biotext/UnmergingProject/source"

# xml files without heads
BI_DEVEL_FILE=CORPUS_DIR+"/bioinfer.devel.refRem-eqRem-negRem-metaRes-anonRes.merged.gold.gif.xml"
BI_TEST_FILE=CORPUS_DIR+"/bioinfer.test.refRem-eqRem-negRem-metaRes-anonRes.merged.gold.gif.xml"
BI_TRAIN_FILE=CORPUS_DIR+"/bioinfer.train.refRem-eqRem-negRem-metaRes-anonRes.merged.gold.gif.xml"
BI_TRAIN_AND_DEVEL_FILE=CORPUS_DIR+"/bioinfer.train+devel.refRem-eqRem-negRem-metaRes-anonRes.merged.gold.gif.xml"

# xml files with head tokens
TEST_FILE=WORKDIR+"/bioinfer-test-"+PARSE+".xml"
DEVEL_FILE=WORKDIR+"/bioinfer-devel-"+PARSE+".xml"
TRAIN_FILE=WORKDIR+"/bioinfer-train-"+PARSE+".xml"
TRAIN_AND_DEVEL_FILE=WORKDIR+"/bioinfer-train-and-devel-"+PARSE+".xml"

# example files
TRIGGER_TRAIN_EXAMPLE_FILE="trigger-train-examples-"+PARSE
TRIGGER_DEVEL_EXAMPLE_FILE="trigger-devel-examples-"+PARSE
TRIGGER_TRAIN_AND_DEVEL_EXAMPLE_FILE="trigger-train-and-devel-examples-"+PARSE
TRIGGER_TEST_EXAMPLE_FILE="trigger-test-examples-"+PARSE
TRIGGER_CLASS_NAMES="bioinfer-trigger-ids.class_names"

EDGE_TRAIN_EXAMPLE_FILE="edge-train-examples-"+PARSE
EDGE_DEVEL_EXAMPLE_FILE="edge-devel-examples-"+PARSE
EDGE_TRAIN_AND_DEVEL_EXAMPLE_FILE="edge-train-and-devel-examples-"+PARSE
EDGE_TEST_EXAMPLE_FILE="edge-test-examples-"+PARSE
EDGE_CLASS_NAMES="bioinfer-edge-ids.class_names"

EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,noMasking,maxFeatures,bioinfer_limits"

if False:
    ###############################################################################
    # Head token detection
    ###############################################################################
    
    # Find heads
    sys.path.append("..")
    import Core.SentenceGraph as SentenceGraph
    import cElementTreeUtils as ETUtils
    
    ETUtils.write(SentenceGraph.loadCorpus(BI_TEST_FILE, PARSE, TOK).rootElement, TEST_FILE)
    ETUtils.write(SentenceGraph.loadCorpus(BI_DEVEL_FILE, PARSE, TOK).rootElement, DEVEL_FILE)
    ETUtils.write(SentenceGraph.loadCorpus(BI_TRAIN_FILE, PARSE, TOK).rootElement, TRAIN_FILE)
    ETUtils.write(SentenceGraph.loadCorpus(BI_TRAIN_AND_DEVEL_FILE, PARSE, TOK).rootElement, TRAIN_AND_DEVEL_FILE)
    
    ###############################################################################
    # Trigger example generation
    ###############################################################################
    print >> sys.stderr, "Trigger examples for parse", TOK
    Gazetteer.run(TRAIN_FILE, "gazetteer-train-"+TOK, TOK)
    Gazetteer.run(TRAIN_AND_DEVEL_FILE, "gazetteer-train-and-devel-"+TOK, TOK)
    # Generate example files
    GeneralEntityTypeRecognizerGztr.run(TRAIN_FILE, TRIGGER_TRAIN_EXAMPLE_FILE, PARSE, TOK, "style:typed", "bioinfer-trigger-ids", "gazetteer-train-"+TOK)
    GeneralEntityTypeRecognizerGztr.run(DEVEL_FILE, TRIGGER_DEVEL_EXAMPLE_FILE, PARSE, TOK, "style:typed", "bioinfer-trigger-ids", "gazetteer-train-"+TOK)
    GeneralEntityTypeRecognizerGztr.run(TRAIN_AND_DEVEL_FILE, TRIGGER_TRAIN_AND_DEVEL_EXAMPLE_FILE, PARSE, TOK, "style:typed", "bioinfer-trigger-ids", "gazetteer-train-and-devel-"+TOK)
    GeneralEntityTypeRecognizerGztr.run(TEST_FILE, TRIGGER_TEST_EXAMPLE_FILE, PARSE, TOK, "style:typed", "bioinfer-trigger-ids", "gazetteer-train-and-devel-"+TOK)
    
    ###############################################################################
    # Edge example generation
    ###############################################################################
    print >> sys.stderr, "Edge examples for parse", PARSE
    
    MultiEdgeExampleBuilder.run(TRAIN_FILE, "edge-train-examples-"+PARSE, PARSE, TOK, EDGE_FEATURE_PARAMS, "bioinfer-edge-ids")
    MultiEdgeExampleBuilder.run(DEVEL_FILE, "edge-devel-examples-"+PARSE, PARSE, TOK, EDGE_FEATURE_PARAMS, "bioinfer-edge-ids")
    MultiEdgeExampleBuilder.run(TRAIN_AND_DEVEL_FILE, "edge-train-and-devel-examples-"+PARSE, PARSE, TOK, EDGE_FEATURE_PARAMS, "bioinfer-edge-ids")
    # NOTE! These TEST examples will be based on gold standard triggers!
    MultiEdgeExampleBuilder.run(TEST_FILE, "edge-test-examples-"+PARSE, PARSE, TOK, EDGE_FEATURE_PARAMS, "bioinfer-edge-ids")

if False:
    ###############################################################################
    # Trigger parameter optimization
    ###############################################################################
    TRIGGER_CLASSIFIER_PARAMS="c:10,20,30,40,50,60,70,80,90,100,500,1000,5000,10000,20000,50000,80000,100000,150000,180000,200000, 250000, 300000, 350000, 500000,1000000,5000000,10000000"
    # The optimize-function takes as parameters a Classifier-class, an Evaluator-class
    # and input and output files
    c = CSCConnection("UnmergingProject/results/parameters/triggers-"+PARSE, "jakrbj@louhi.csc.fi", True)
    best = optimize(Cls, Ev, TRIGGER_TRAIN_EXAMPLE_FILE, TRIGGER_DEVEL_EXAMPLE_FILE, TRIGGER_CLASS_NAMES, TRIGGER_CLASSIFIER_PARAMS, "trigger-param-opt", None, c)
    bestTriggerParameters = best[4]
    xmlFilename = "devel-predicted-triggers.xml"
    ExampleUtils.writeToInteractionXML(TRIGGER_DEVEL_EXAMPLE_FILE, best[2], DEVEL_FILE, xmlFilename, TRIGGER_CLASS_NAMES, PARSE, TOK)
    # NOTE: Merged elements must not be split, as recall booster may change their class
    ix.splitMergedElements(xmlFilename, xmlFilename)
    ix.recalculateIds(xmlFilename, xmlFilename, True)

if True:
    ###############################################################################
    # Edge parameter optimization
    ###############################################################################
    EDGE_CLASSIFIER_PARAMS="c:10,20,30,40,50,60,70,80,90,100,500,1000,5000,10000,20000,50000,80000,100000,150000,180000,200000, 250000, 300000, 350000, 500000,1000000"
    print >> sys.stderr, "Determining edge parameter", PARSE
    # The optimize-function takes as parameters a Classifier-class, an Evaluator-class
    # and input and output files
    c = CSCConnection("UnmergingProject/results/parameters/edges-"+PARSE, "jakrbj@louhi.csc.fi", False)
    best = optimize(Cls, Ev, EDGE_TRAIN_EXAMPLE_FILE, EDGE_DEVEL_EXAMPLE_FILE, EDGE_CLASS_NAMES, EDGE_CLASSIFIER_PARAMS, "edge-param-opt", None, c)
    bestEdgeParameters = best[4]
    xmlFilename = "devel-predicted-edges.xml"
    ExampleUtils.writeToInteractionXML(EDGE_DEVEL_EXAMPLE_FILE, best[2], DEVEL_FILE, xmlFilename, EDGE_CLASS_NAMES, PARSE, TOK)
    # NOTE: Merged elements must not be split, as recall booster may change their class
    ix.splitMergedElements(xmlFilename, xmlFilename)
    ix.recalculateIds(xmlFilename, xmlFilename, True)

if True:
    ###############################################################################
    # Devel set predictions with predicted edges
    ###############################################################################
    # Build edge examples on top of predicted triggers
    MultiEdgeExampleBuilder.run("devel-predicted-triggers.xml", "edge-devel-examples-ptrig", PARSE, TOK, EDGE_FEATURE_PARAMS, "bioinfer-edge-ids")
    # Use the generated model to classify examples
    Cls.test("edge-devel-examples-ptrig", best[1], "edge-devel-classifications-ptrig")
    xmlFilename = "devel-predicted-edges-ptrig.xml"
    ExampleUtils.writeToInteractionXML("edge-devel-examples-ptrig", "edge-devel-classifications-ptrig", "devel-predicted-triggers.xml", xmlFilename, "bioinfer-edge-ids.class_names", PARSE, TOK)
    ix.splitMergedElements(xmlFilename, xmlFilename)
    ix.recalculateIds(xmlFilename, xmlFilename, True)
    EvaluateInteractionXML.run(Ev, xmlFilename, TEST_FILE, PARSE, TOK)

if True:
    ###############################################################################
    ###############################################################################
    # Test Set
    ###############################################################################
    ###############################################################################
    
    ###############################################################################
    # Trigger predictions
    ###############################################################################
    # Train the classifier with devel-optimized parameters, and store output into a model file
    Cls.train(TRIGGER_TRAIN_AND_DEVEL_EXAMPLE_FILE, bestTriggerParameters, "train-and-devel-trigger-test-model")
    # Use the generated model to classify examples
    Cls.test(TRIGGER_TEST_EXAMPLE_FILE, "train-and-devel-trigger-test-model", "trigger-test-classifications")
    ExampleUtils.writeToInteractionXML("trigger-test-examples", "trigger-test-classifications", TEST_FILE, "test-predicted-triggers.xml", TRIGGER_IDS+".class_names", PARSE, TOK)
    # NOTE: Merged elements must not be split, as recall booster may change their class
    ix.splitMergedElements("test-predicted-triggers.xml", "test-predicted-triggers.xml")
    ix.recalculateIds("test-predicted-triggers.xml", "test-predicted-triggers.xml", True)
    
    ###############################################################################
    # Edge predictions
    ###############################################################################
    # Build edge examples on top of predicted triggers
    MultiEdgeExampleBuilder.run("test-predicted-triggers.xml", "edge-test-examples-with-pred-triggers", PARSE, TOK, EDGE_FEATURE_PARAMS, "bioinfer-edge-ids")
    # Train the classifier, and store output into a model file
    Cls.train(EDGE_TRAIN_AND_DEVEL_EXAMPLE_FILE, bestEdgeParameters, "train-and-devel-edge-test-model")
    # Use the generated model to classify examples
    Cls.test("edge-test-examples-with-pred-triggers", "train-and-devel-edge-test-model", "edge-test-classifications")
    xmlFilename = "test-predicted-edges.xml"
    ExampleUtils.writeToInteractionXML("edge-test-examples-with-pred-triggers", "edge-test-classifications", "test-predicted-triggers.xml", xmlFilename, "bioinfer-edge-ids.class_names", PARSE, TOK)
    ix.splitMergedElements(xmlFilename, xmlFilename)
    ix.recalculateIds(xmlFilename, xmlFilename, True)
    
    # EvaluateInteractionXML differs from the previous evaluations in that it can
    # be used to compare two separate GifXML-files. One of these is the gold file,
    # against which the other is evaluated by heuristically matching triggers and
    # edges. Note that this evaluation will differ somewhat from the previous ones,
    # which evaluate on the level of examples.
    EvaluateInteractionXML.run(Ev, xmlFilename, TEST_FILE, PARSE, TOK)
