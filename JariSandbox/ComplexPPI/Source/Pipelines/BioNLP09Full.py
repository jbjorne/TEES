# Builds BioNLP09 trigger and edge example files for a specified parse

from Pipeline import *
import sys,os

from optparse import OptionParser

optparser = OptionParser()
optparser.add_option("-p", "--parse", default="stanford-oldMC-intra", dest="parse", help="")
optparser.add_option("-t", "--tokenization", default="split-McClosky-Charniak-old", dest="tokenization", help="")
optparser.add_option("-n", "--name", default="BioNLP09Full", dest="name", help="experiment name")
(options, args) = optparser.parse_args()

WORKDIR = "/usr/share/biotext/UnmergingProject/results/" + options.name
# These commands will be in the beginning of most pipelines
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

# define shortcuts for commonly used files
PARSE=options.parse #"split-Charniak-Lease"
TOK=options.tokenization
CORPUS_DIR="/usr/share/biotext/UnmergingProject/source"

# constants
CONSTANT_CORPUS = 'bionlp09-task1'
CONSTANT_SEMANTIC = 'eqRem-negRem'
CONSTANT_INPUT_POSTFIX = 'merged.gold.gif.xml'

STRING_INPUTFILE = "%s/%s.%%s.%s.%s"%(CORPUS_DIR, CONSTANT_CORPUS, CONSTANT_SEMANTIC, CONSTANT_INPUT_POSTFIX)
STRING_HEADTOKENFILE = "%s/%s-%%s-%s.xml"%(WORKDIR, CONSTANT_CORPUS, PARSE)
STRING_IDS = "%s-%%s-ids"%CONSTANT_CORPUS

# xml files without heads
BI_TRAIN_FILE=STRING_INPUTFILE%"train-train"
BI_DEVEL_FILE=STRING_INPUTFILE%"train-devel"
BI_TRAIN_AND_DEVEL_FILE=STRING_INPUTFILE%"train-train+train-devel"
BI_TEST_FILE=STRING_INPUTFILE%"devel"

# xml files with head tokens
TEST_FILE=STRING_HEADTOKENFILE%'devel'
DEVEL_FILE=STRING_HEADTOKENFILE%'train-devel'
TRAIN_FILE=STRING_HEADTOKENFILE%'train-train'
TRAIN_AND_DEVEL_FILE=STRING_HEADTOKENFILE%'train-train+train-devel'

# example files
TRIGGER_TRAIN_EXAMPLE_FILE="trigger-train-examples-"+PARSE
TRIGGER_DEVEL_EXAMPLE_FILE="trigger-devel-examples-"+PARSE
TRIGGER_TRAIN_AND_DEVEL_EXAMPLE_FILE="trigger-train-and-devel-examples-"+PARSE
TRIGGER_TEST_EXAMPLE_FILE="trigger-test-examples-"+PARSE
TRIGGER_CLASS_NAMES="%s-trigger-ids.class_names"%CONSTANT_CORPUS

EDGE_TRAIN_EXAMPLE_FILE="edge-train-examples-"+PARSE
EDGE_DEVEL_EXAMPLE_FILE="edge-devel-examples-"+PARSE
EDGE_TRAIN_AND_DEVEL_EXAMPLE_FILE="edge-train-and-devel-examples-"+PARSE
EDGE_TEST_EXAMPLE_FILE="edge-test-examples-"+PARSE
EDGE_CLASS_NAMES="%s-edge-ids.class_names"%CONSTANT_CORPUS

EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,noMasking,maxFeatures,genia_limits"

if True:
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
    GeneralEntityTypeRecognizerGztr.run(TRAIN_FILE, TRIGGER_TRAIN_EXAMPLE_FILE, PARSE, TOK, "style:typed", STRING_IDS%'trigger', "gazetteer-train-"+TOK)
    GeneralEntityTypeRecognizerGztr.run(DEVEL_FILE, TRIGGER_DEVEL_EXAMPLE_FILE, PARSE, TOK, "style:typed", STRING_IDS%'trigger', "gazetteer-train-"+TOK)
    GeneralEntityTypeRecognizerGztr.run(TRAIN_AND_DEVEL_FILE, TRIGGER_TRAIN_AND_DEVEL_EXAMPLE_FILE, PARSE, TOK, "style:typed", STRING_IDS%'trigger', "gazetteer-train-and-devel-"+TOK)
    GeneralEntityTypeRecognizerGztr.run(TEST_FILE, TRIGGER_TEST_EXAMPLE_FILE, PARSE, TOK, "style:typed", STRING_IDS%'trigger', "gazetteer-train-and-devel-"+TOK)
    
    ###############################################################################
    # Edge example generation
    ###############################################################################
    print >> sys.stderr, "Edge examples for parse", PARSE
    
    MultiEdgeExampleBuilder.run(TRAIN_FILE, "edge-train-examples-"+PARSE, PARSE, TOK, EDGE_FEATURE_PARAMS, STRING_IDS%'edge')
    MultiEdgeExampleBuilder.run(DEVEL_FILE, "edge-devel-examples-"+PARSE, PARSE, TOK, EDGE_FEATURE_PARAMS, STRING_IDS%'edge')
    MultiEdgeExampleBuilder.run(TRAIN_AND_DEVEL_FILE, "edge-train-and-devel-examples-"+PARSE, PARSE, TOK, EDGE_FEATURE_PARAMS, STRING_IDS%'edge')
    # NOTE! These TEST examples will be based on gold standard triggers!
    MultiEdgeExampleBuilder.run(TEST_FILE, "edge-test-examples-"+PARSE, PARSE, TOK, EDGE_FEATURE_PARAMS, STRING_IDS%'edge')

bestTriggerParameters = None
if True:
    ###############################################################################
    # Trigger parameter optimization
    ###############################################################################
    TRIGGER_CLASSIFIER_PARAMS="c:1000,5000,10000,20000,50000,80000,100000,150000,180000,200000, 250000, 300000, 350000, 500000,1000000,5000000,10000000"
    # The optimize-function takes as parameters a Classifier-class, an Evaluator-class
    # and input and output files
    c = CSCConnection("UnmergingProject/results/" + options.name + "/parameters/triggers-"+PARSE, "jakrbj@murska.csc.fi", True, memory=8388608)
    best = optimize(Cls, Ev, TRIGGER_TRAIN_EXAMPLE_FILE, TRIGGER_DEVEL_EXAMPLE_FILE, TRIGGER_CLASS_NAMES, TRIGGER_CLASSIFIER_PARAMS, "trigger-param-opt", None, c)
    bestTriggerParameters = best[4]
    xmlFilename = "devel-predicted-triggers.xml"
    ExampleUtils.writeToInteractionXML(TRIGGER_DEVEL_EXAMPLE_FILE, best[2], DEVEL_FILE, xmlFilename, TRIGGER_CLASS_NAMES, PARSE, TOK)
    # NOTE: Merged elements must not be split, as recall booster may change their class
    ix.splitMergedElements(xmlFilename, xmlFilename)
    ix.recalculateIds(xmlFilename, xmlFilename, True)

bestEdgeParameters = None
if True:
    ###############################################################################
    # Edge parameter optimization
    ###############################################################################
    EDGE_CLASSIFIER_PARAMS="c:1000,5000,10000,20000,50000,80000,100000,150000,180000,200000, 250000, 300000, 350000, 500000,1000000,5000000"#,10000000"
    print >> sys.stderr, "Determining edge parameter", PARSE
    # The optimize-function takes as parameters a Classifier-class, an Evaluator-class
    # and input and output files
    c = CSCConnection("UnmergingProject/results/" + options.name + "/parameters/edges-"+PARSE, "jakrbj@murska.csc.fi", True, memory=8388608)
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
    MultiEdgeExampleBuilder.run("devel-predicted-triggers.xml", "edge-devel-examples-ptrig", PARSE, TOK, EDGE_FEATURE_PARAMS, STRING_IDS%'edge')
    # Use the generated model to classify examples
    Cls.test("edge-devel-examples-ptrig", best[1], "edge-devel-classifications-ptrig")
    xmlFilename = "devel-predicted-edges-ptrig.xml"
    ExampleUtils.writeToInteractionXML("edge-devel-examples-ptrig", "edge-devel-classifications-ptrig", "devel-predicted-triggers.xml", xmlFilename, EDGE_CLASS_NAMES, PARSE, TOK)
    ix.splitMergedElements(xmlFilename, xmlFilename)
    ix.recalculateIds(xmlFilename, xmlFilename, True)
    print >> sys.stderr, "############################################"
    print >> sys.stderr, "# Devel Set Results"
    print >> sys.stderr, "############################################"
    EvaluateInteractionXML.run(Ev, xmlFilename, DEVEL_FILE, PARSE, TOK)

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
    ExampleUtils.writeToInteractionXML(TRIGGER_TEST_EXAMPLE_FILE, "trigger-test-classifications", TEST_FILE, "test-predicted-triggers.xml", TRIGGER_CLASS_NAMES, PARSE, TOK)
    # NOTE: Merged elements must not be split, as recall booster may change their class
    ix.splitMergedElements("test-predicted-triggers.xml", "test-predicted-triggers.xml")
    ix.recalculateIds("test-predicted-triggers.xml", "test-predicted-triggers.xml", True)
    
    ###############################################################################
    # Edge predictions
    ###############################################################################
    # Build edge examples on top of predicted triggers
    MultiEdgeExampleBuilder.run("test-predicted-triggers.xml", "edge-test-examples-with-pred-triggers", PARSE, TOK, EDGE_FEATURE_PARAMS, STRING_IDS%'edge')
    # Train the classifier, and store output into a model file
    Cls.train(EDGE_TRAIN_AND_DEVEL_EXAMPLE_FILE, bestEdgeParameters, "train-and-devel-edge-test-model")
    # Use the generated model to classify examples
    Cls.test("edge-test-examples-with-pred-triggers", "train-and-devel-edge-test-model", "edge-test-classifications")
    xmlFilename = "test-predicted-edges.xml"
    ExampleUtils.writeToInteractionXML("edge-test-examples-with-pred-triggers", "edge-test-classifications", "test-predicted-triggers.xml", xmlFilename, EDGE_CLASS_NAMES, PARSE, TOK)
    ix.splitMergedElements(xmlFilename, xmlFilename)
    ix.recalculateIds(xmlFilename, xmlFilename, True)
    
    # EvaluateInteractionXML differs from the previous evaluations in that it can
    # be used to compare two separate GifXML-files. One of these is the gold file,
    # against which the other is evaluated by heuristically matching triggers and
    # edges. Note that this evaluation will differ somewhat from the previous ones,
    # which evaluate on the level of examples.
    print >> sys.stderr, "############################################"
    print >> sys.stderr, "# Test Set Results"
    print >> sys.stderr, "############################################"
    EvaluateInteractionXML.run(Ev, xmlFilename, TEST_FILE, PARSE, TOK)
