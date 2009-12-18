from Pipeline import * # All pipelines import this
from optparse import OptionParser # For using command line options

# Read command line options
optparser = OptionParser()
optparser.add_option("-i", "--input", default=Settings.DevelFile, dest="input", help="interaction xml input file", metavar="FILE")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-p", "--parse", default="split_McClosky", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default="split_McClosky", dest="tokenization", help="Tokenization XML element name")
optparser.add_option("-a", "--task", default=1, type="int", dest="task", help="task number")
optparser.add_option("-m", "--triggerModel", default=Settings.TrainTriggerModel, dest="triggerModel", help="SVM-multiclass trigger model")
optparser.add_option("-n", "--edgeModel", default=Settings.TrainEdgeModel, dest="edgeModel", help="SVM-multiclass edge (event argument) model")
optparser.add_option("-r", "--recallBoost", default=0.6, type="float", dest="recallBoost", help="Recall boosting of trigger predictions (1.0 = none)")
(options, args) = optparser.parse_args()

# Check options
assert options.output != None
assert options.task in [1, 2]

def processFile(TEST_FILE, output, PARSE, TOK, TRIGGER_MODEL, EDGE_MODEL, RECALL_BOOST_PARAM):    
    inputFilename = os.path.basename(TEST_FILE)
    assert inputFilename[-7:] == ".xml.gz"
    inputFilename = inputFilename.rsplit(".", 2)[0]
    
    # The id-sets will be modified, so create local copies of them.
    # Using always the same id numbers for machine learning classes
    # and examples ensures that the model-files will be compatible
    # with all of your experiments.
    TRIGGER_IDS = copyIdSetsToWorkdir(Settings.TriggerIds)
    EDGE_IDS = copyIdSetsToWorkdir(Settings.EdgeIds)
    
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
    GeneralEntityTypeRecognizerGztr.run(TEST_FILE, "trigger-test-examples", PARSE, TOK, "style:typed", TRIGGER_IDS, None)
    Cls.test("trigger-test-examples", TRIGGER_MODEL, "trigger-test-classifications")
    # Evaluate the predictions
    print >> sys.stderr, "Evaluating trigger example classifications:"
    triggerEv = Ev.evaluate("trigger-test-examples", "trigger-test-classifications", TRIGGER_IDS+".class_names")
    # The classifications are combined with the TEST_FILE xml, to produce
    # an interaction-XML file with predicted triggers
    triggerXML = ExampleUtils.writeToInteractionXML("trigger-test-examples", "trigger-test-classifications", TEST_FILE, "test-predicted-triggers.xml", TRIGGER_IDS+".class_names", PARSE, TOK)
    
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
    if triggerEv.getData().getTP() + triggerEv.getData().getFP() > 0:
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
        edgeXML = ExampleUtils.writeToInteractionXML("edge-test-examples", "edge-test-classifications", boostedTriggerFile, "test-predicted-edges.xml", EDGE_IDS+".class_names", PARSE, TOK)
        # Split overlapping, merged elements (e.g. "Upregulate---Phosphorylate")
        #ix.splitMergedElements("test-predicted-edges.xml", "test-predicted-edges.xml")
        edgeXML = ix.splitMergedElements(edgeXML)
        # Always remember to fix ids
        edgeXML = ix.recalculateIds(edgeXML, inputFilename + "-events.xml.gz", True)
        # EvaluateInteractionXML differs from the previous evaluations in that it can
        # be used to compare two separate GifXML-files. One of these is the gold file,
        # against which the other is evaluated by heuristically matching triggers and
        # edges. Note that this evaluation will differ somewhat from the previous ones,
        # which evaluate on the level of examples.
        #print >> sys.stderr, "Evaluating trigger and edge xml elements agains input xml"
        #EvaluateInteractionXML.run(Ev, edgeXML, TEST_FILE, PARSE, TOK)
        
        ###############################################################################
        # Post-processing
        ###############################################################################
        print >> sys.stderr, "====== Post-processing ======"
        # Post-processing
        edgeXML = unflatten(edgeXML, PARSE, TOK, inputFilename + "-events-unflattened.xml.gz")
        # Shared Task formatted (a2-files) output will be stored to the geniaformat-subdirectory
        gifxmlToGenia(edgeXML, inputFilename + "-events-geniaformat.tar.gz", options.task)
        #evaluateSharedTask("geniaformat", options.task)
    else:
        print >> sys.stderr, "No positive predicted triggers"

# These commands will be in the beginning of most pipelines
workdir(options.output, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in the working directory

if os.path.isdir(options.input):
    inputFiles = os.listdir(options.input)
    for filename in inputFiles[:]:
        if filename.find("xml.gz") == -1:
            inputFiles.remove(filename)
    count = 1
    for filename in inputFiles:
        print >> sys.stderr, "Processing file", filename, "number", str(count) + "/" + str(len(inputFiles))
        try:
            processFile(os.path.join(options.input, filename), options.output, options.parse, options.tokenization, options.triggerModel, options.edgeModel, options.recallBoost)
        except Exception, e:
            print >> sys.stderr, "Exception caught for file", filename
            print >> sys.stderr, "Exception:", e
        count += 1
else: # single file
    processFile(options.input, options.output, options.parse, options.tokenization, options.triggerModel, options.edgeModel, options.recallBoost)
