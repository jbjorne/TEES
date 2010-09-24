from Pipeline import * # All pipelines import this
from optparse import OptionParser # For using command line options

# Read command line options
optparser = OptionParser()
optparser.add_option("-i", "--input", default=Settings.DevelFile, dest="input", help="interaction xml input file", metavar="FILE")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="Tokenization XML element name")
optparser.add_option("-a", "--task", default=1, type="int", dest="task", help="task number")
optparser.add_option("-m", "--triggerModel", default=Settings.TrainTriggerModel, dest="triggerModel", help="SVM-multiclass trigger model")
optparser.add_option("-n", "--edgeModel", default=Settings.TrainEdgeModel, dest="edgeModel", help="SVM-multiclass edge (event argument) model")
optparser.add_option("-v", "--triggerIds", default=Settings.TriggerIds, dest="triggerIds", help="Trigger detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
optparser.add_option("-w", "--edgeIds", default=Settings.EdgeIds, dest="edgeIds", help="Edge detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
optparser.add_option("-r", "--recallBoost", default=0.65, type="float", dest="recallBoost", help="Recall boosting of trigger predictions (1.0 = none)")
(options, args) = optparser.parse_args()

# Check options
assert options.output != None
assert options.task in [1, 2]

# Let's define some shortcuts to make things more readable
TEST_FILE = options.input
PARSE = options.parse
TOK = options.tokenization
TRIGGER_MODEL = options.triggerModel
EDGE_MODEL = options.edgeModel
RECALL_BOOST_PARAM = options.recallBoost

# These commands will be in the beginning of most pipelines
workdir(options.output, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in the working directory

if False:
    # The id-sets will be modified, so create local copies of them.
    # Using always the same id numbers for machine learning classes
    # and examples ensures that the model-files will be compatible
    # with all of your experiments.
    TRIGGER_IDS = copyIdSetsToWorkdir(options.triggerIds)
    EDGE_IDS = copyIdSetsToWorkdir(options.edgeIds)
    
    ###############################################################################
    # Trigger detection
    ###############################################################################
    print >> sys.stderr, "====== Trigger Detection ======"
    # Build an SVM example file for the test data.
    # GeneralEntityTypeRecognizerGztr is a version of GeneralEntityTypeRecognizer
    # that can use the gazetteer. The file was split for parallel development, and
    # later GeneralEntityTypeRecognizerGztr will be integrated into GeneralEntityTypeRecognizer.
    # "ids" is the identifier of the class- and feature-id-files. When
    # class and feature ids are reused, models can be reused between experiments.
    # Existing id-files, if present, are automatically reused.
    TriggerExampleBuilder.run(TEST_FILE, "trigger-test-examples", PARSE, TOK, "style:typed", TRIGGER_IDS, None)
    Cls.test("trigger-test-examples", TRIGGER_MODEL, "trigger-test-classifications")
    # Evaluate the predictions
    print >> sys.stderr, "Evaluating trigger example classifications:"
    Ev.evaluate("trigger-test-examples", "trigger-test-classifications", TRIGGER_IDS+".class_names")
    # The classifications are combined with the TEST_FILE xml, to produce
    # an interaction-XML file with predicted triggers
    triggerXML = BioTextExampleWriter.write("trigger-test-examples", "trigger-test-classifications", TEST_FILE, "test-predicted-triggers.xml", TRIGGER_IDS+".class_names", PARSE, TOK)
    
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
    print >> sys.stderr, "====== Edge Detection ======"
    EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"
    # The test file for the edge generation step is now the GifXML-file that was built
    # in the previous step, i.e. the one that has predicted triggers
    MultiEdgeExampleBuilder.run(boostedTriggerFile, "edge-test-examples", PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    # Once we have determined the optimal c-parameter (best[1]), we can
    # use it to classify our real examples, i.e. the ones that define potential edges
    # between predicted entities
    Cls.test("edge-test-examples", EDGE_MODEL, "edge-test-classifications")
    # Evaluate the predictions
    # Since edge examples are generated on top of predicted triggers, 
    # correct answers are not known. Therefore all positives will be here
    # evaluated as false positives.
    print >> sys.stderr, "Evaluating edge example classifications (all positives will show as false positives):"
    Ev.evaluate("edge-test-examples", "edge-test-classifications", EDGE_IDS+".class_names")
    # Write the predicted edges to an interaction xml which has predicted triggers.
    # This function handles both trigger and edge example classifications
    edgeXML = BioTextExampleWriter.write("edge-test-examples", "edge-test-classifications", boostedTriggerFile, "test-predicted-edges.xml", EDGE_IDS+".class_names", PARSE, TOK)
    # Split overlapping, merged elements (e.g. "Upregulate---Phosphorylate")
    #ix.splitMergedElements("test-predicted-edges.xml", "test-predicted-edges.xml")
    edgeXML = ix.splitMergedElements(edgeXML)
    # Always remember to fix ids
    edgeXML = ix.recalculateIds(edgeXML, "test-predicted-edges.xml", True)
    # EvaluateInteractionXML differs from the previous evaluations in that it can
    # be used to compare two separate GifXML-files. One of these is the gold file,
    # against which the other is evaluated by heuristically matching triggers and
    # edges. Note that this evaluation will differ somewhat from the previous ones,
    # which evaluate on the level of examples.
    print >> sys.stderr, "Evaluating trigger and edge xml elements agains input xml"
    EvaluateInteractionXML.run(Ev, edgeXML, TEST_FILE, PARSE, TOK)

###############################################################################
# Post-processing
###############################################################################
if False:
    print >> sys.stderr, "====== Post-processing ======"
    # Post-processing
    edgeXML = unflatten("test-predicted-edges.xml", PARSE, TOK, "test-predicted-edges-unflattened.xml")
    #edgeXML = unflatten(edgeXML, PARSE, TOK, "test-predicted-edges-unflattened.xml")
    # Shared Task formatted (a2-files) output will be stored to the geniaformat-subdirectory
    gifxmlToGenia(edgeXML, "geniaformat", options.task, strengths=True)
evaluateSharedTask("geniaformat", options.task)