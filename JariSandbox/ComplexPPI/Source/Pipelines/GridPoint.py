# Optimize parameters for event detection and produce event and trigger model files

# most imports are defined in Pipeline
from Pipeline import *
import sys, os

import Settings
Settings.SVMMultiClassDir = "/v/users/jakrbj/svm-multiclass"

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-e", "--test", default=Settings.DevelFile, dest="testFile", help="Test file in interaction xml")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-a", "--task", default=1, type="int", dest="task", help="task number")
optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="Tokenization XML element name")
# Classifier
optparser.add_option("-c", "--classifier", default="Cls", dest="classifier", help="")
# Example builders
optparser.add_option("-f", "--triggerExampleFile", default=None, dest="triggerExampleFile", help="")
optparser.add_option("-g", "--edgeExampleBuilder", default="MultiEdgeExampleBuilder", dest="edgeExampleBuilder", help="")
# Id sets
optparser.add_option("-v", "--triggerIds", default=None, dest="triggerIds", help="Trigger detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
optparser.add_option("-w", "--edgeIds", default=None, dest="edgeIds", help="Edge detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
# Parameters to optimize
optparser.add_option("-x", "--triggerModel", default="1000", dest="triggerModel", help="Trigger detector c-parameter values")
optparser.add_option("-y", "--recallAdjustParam", default="1.0", dest="recallAdjustParam", help="Recall adjuster parameter values")
optparser.add_option("-z", "--edgeModel", default="1000", dest="edgeModel", help="Edge detector c-parameter values")
(options, args) = optparser.parse_args()

# Check options
assert options.output != None
assert options.task in [1, 2]
options.recallAdjustParam = float(options.recallAdjustParam)

exec "CLASSIFIER = " + options.classifier

# Main settings
PARSE=options.parse
TOK=options.tokenization
PARSE_TAG = PARSE + "_" + TOK
TEST_FILE = options.testFile

# Example generation parameters
EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"
TRIGGER_FEATURE_PARAMS="style:typed"

# These commands will be in the beginning of most pipelines
WORKDIR=options.output
#CSC_WORKDIR = os.path.join("CSCConnection",WORKDIR.lstrip("/"))

workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

TRIGGER_EXAMPLES = options.triggerExampleFile
EDGE_EXAMPLE_BUILDER = eval(options.edgeExampleBuilder)

if options.triggerIds != None:
    TRIGGER_IDS = copyIdSetsToWorkdir(options.triggerIds)
if options.edgeIds != None:
    EDGE_IDS = copyIdSetsToWorkdir(options.edgeIds)

###############################################################################
# Classification with recall boosting
###############################################################################
# Pre-made models
EDGE_MODEL_STEM = "edge-models/model-c_"
TRIGGER_MODEL_STEM = "trigger-models/model-c_"

# Build trigger examples
CLASSIFIER.test(TRIGGER_EXAMPLES, options.triggerModel, "test-trigger-classifications")
evaluator = Ev.evaluate(TRIGGER_EXAMPLES, "test-trigger-classifications", TRIGGER_IDS+".class_names")
xml = BioTextExampleWriter.write(TRIGGER_EXAMPLES, "test-trigger-classifications", TEST_FILE, None, TRIGGER_IDS+".class_names", PARSE, TOK)
# Boost
xml = RecallAdjust.run(xml, options.recallAdjustParam, None)
xml = ix.splitMergedElements(xml, None)
xml = ix.recalculateIds(xml, None, True)

# Build edge examples
EDGE_EXAMPLE_BUILDER.run(xml, "test-edge-examples", PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
# Classify with pre-defined model
CLASSIFIER.test("test-edge-examples", options.edgeModel, "test-edge-classifications")
# Write to interaction xml
evaluator = Ev.evaluate("test-edge-examples", "test-edge-classifications", EDGE_IDS+".class_names")
if evaluator.getData().getTP() + evaluator.getData().getFP() > 0:
    #xml = ExampleUtils.writeToInteractionXML("test-edge-examples", "test-edge-classifications", xml, None, EDGE_IDS+".class_names", PARSE, TOK)
    xml = BioTextExampleWriter.write("test-edge-examples", "test-edge-classifications", xml, None, EDGE_IDS+".class_names", PARSE, TOK)
    xml = ix.splitMergedElements(xml, None)
    xml = ix.recalculateIds(xml, "final.xml", True)
    
    # EvaluateInteractionXML differs from the previous evaluations in that it can
    # be used to compare two separate GifXML-files. One of these is the gold file,
    # against which the other is evaluated by heuristically matching triggers and
    # edges. Note that this evaluation will differ somewhat from the previous ones,
    # which evaluate on the level of examples.
    EvaluateInteractionXML.run(Ev, xml, TEST_FILE, PARSE, TOK)
        
    # Post-processing
    xml = unflatten(xml, PARSE, TOK)
    
    # Output will be stored to the geniaformat-subdirectory, where will also be a
    # tar.gz-file which can be sent to the Shared Task evaluation server.
    gifxmlToGenia(xml, "geniaformat", options.task)
    
    # Evaluation of the Shared Task format
    results = evaluateSharedTask("geniaformat", options.task)
    evaluation.EvaluateSharedTask.resultsToCSV(results, "results.csv")
else:
    print >> sys.stderr, "No predicted edges"
    open("results.csv", "a").close()
    
