import sys, os
import shutil
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Settings
if os.environ.has_key("METAWRK"): # CSC
    Settings.SVMMultiClassDir = "/v/users/jakrbj/svm-multiclass"
    Settings.EverythingTriggerModel = "/v/users/jakrbj/release-files-review-version-models/everything-trigger-model-c_200000"
    Settings.EverythingEdgeModel = "/v/users/jakrbj/release-files-review-version-models/everything-edge-model-c_28000"
    Settings.EverythingSpeculationModel = "/v/users/jakrbj/release-files-review-version-models/everything-speculation-model-c_13000"
    Settings.EverythingNegationModel = "/v/users/jakrbj/release-files-review-version-models/everything-negation-model-c_10000"
    Settings.TriggerIds="/v/users/jakrbj/release-files-review-version-models/genia-trigger-ids"
    Settings.EdgeIds="/v/users/jakrbj/release-files-review-version-models/genia-edge-ids"
    Settings.Task3Ids="/v/users/jakrbj/release-files-review-version-models/genia-task3-ids"

from Pipeline import *
from optparse import OptionParser

optparser = OptionParser()
optparser.add_option("-i", "--input", default=None, dest="input", help="interaction xml input file", metavar="FILE")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory (for final files)")
optparser.add_option("-w", "--workdir", default="/wrk/jakrbj/shared-task-test", dest="workdir", help="working directory")
(options, args) = optparser.parse_args()
assert options.input != None
options.input = os.path.abspath(options.input)
assert options.output != None
options.output = os.path.abspath(options.output)
if not os.path.exists(options.output):
    os.makedirs(options.output)
options.workdir = os.path.abspath(options.workdir)
if not os.path.exists(options.workdir):
    os.makedirs(options.workdir)

# define shortcuts for commonly used files
TEST_FILE = options.input
OUTFILE_STEM = os.path.join(options.output, os.path.basename(options.input))
if OUTFILE_STEM[-7:] == ".xml.gz":
    OUTFILE_STEM = OUTFILE_STEM[:-7]
elif OUTFILE_STEM[-4:] == ".xml":
    OUTFILE_STEM = OUTFILE_STEM[:-4]

# In case there is an error later, make sure input file gets to output 
# directory (even if without predictions). This will usually get overwritten
# during the process
shutil.copy(options.input, OUTFILE_STEM + "-events.xml.gz")

TRIGGER_MODEL=Settings.EverythingTriggerModel
EDGE_MODEL=Settings.EverythingEdgeModel

WORKDIR=options.workdir
PARSE_TOK="split-McClosky"

RECALL_BOOST_PARAM=0.65

logFileName = OUTFILE_STEM+"-log.txt"
count = 2
while os.path.exists(logFileName):
    print >> sys.stderr, "Log file", logFileName, "exists, trying", OUTFILE_STEM + "-log-" + str(count) + ".txt"
    logFileName = OUTFILE_STEM + "-log-" + str(count) + ".txt"
    count += 1

# These commands will be in the beginning of most pipelines
workdir(WORKDIR, True) # Select a working directory, don't remove existing files
log(clear=True, logFile=OUTFILE_STEM+"-log.txt") # Start logging into a file in output (not work) directory
TRIGGER_IDS=copyIdSetsToWorkdir(Settings.TriggerIds)
EDGE_IDS=copyIdSetsToWorkdir(Settings.EdgeIds)

###############################################################################
# Trigger detection
###############################################################################
TEST_FILE = options.input
# Build an SVM example file for the training corpus.
# GeneralEntityTypeRecognizerGztr is a version of GeneralEntityTypeRecognizer
# that can use the gazetteer. The file was split for parallel development, and
# later GeneralEntityTypeRecognizerGztr will be integrated into GeneralEntityTypeRecognizer.
# "ids" is the identifier of the class- and feature-id-files. When
# class and feature ids are reused, models can be reused between experiments.
# Existing id-files, if present, are automatically reused.
GeneralEntityTypeRecognizerGztr.run(TEST_FILE, "trigger-test-examples", PARSE_TOK, PARSE_TOK, "style:typed", TRIGGER_IDS, None)#, skiplist="PubMed100p")
Cls.test("trigger-test-examples", TRIGGER_MODEL, "trigger-test-classifications")
# Evaluate the predictions
#Ev.evaluate("trigger-test-examples", "trigger-test-classifications", TRIGGER_IDS+".class_names")
# The classifications are combined with the TEST_FILE xml, to produce
# an interaction-XML file with predicted triggers
#triggerXML = ExampleUtils.writeToInteractionXML("trigger-test-examples", "trigger-test-classifications", TEST_FILE, "test-predicted-triggers.xml", TRIGGER_IDS+".class_names", PARSE_TOK, PARSE_TOK)
triggerXML = BioTextExampleWriter.write("trigger-test-examples", "trigger-test-classifications", TEST_FILE, None, TRIGGER_IDS+".class_names", PARSE_TOK, PARSE_TOK)

# Run the recall booster
#boostedTriggerFile = "test-predicted-triggers-boost.xml"
boostedTriggerFile = RecallAdjust.run(triggerXML, RECALL_BOOST_PARAM, None)
# Overlapping types (could be e.g. "protein---gene") are split into multiple
# entities
boostedTriggerFile = ix.splitMergedElements(boostedTriggerFile)
# The hierarchical ids are recalculated, since they might be invalid after
# the generation and modification steps
boostedTriggerFile = ix.recalculateIds(boostedTriggerFile, None, True)

###############################################################################
# Edge detection
###############################################################################
EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"
# The test file for the edge generation step is now the GifXML-file that was built
# in the previous step, i.e. the one that has predicted triggers
MultiEdgeExampleBuilder.run(boostedTriggerFile, "edge-test-examples", PARSE_TOK, PARSE_TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
# Once we have determined the optimal c-parameter (best[1]), we can
# use it to classify our real examples, i.e. the ones that define potential edges
# between predicted entities
edgeExampleFileSize = os.path.getsize("edge-test-examples") 
if edgeExampleFileSize != 0: 
    Cls.test("edge-test-examples", EDGE_MODEL, "edge-test-classifications")
    # Write the predicted edges to an interaction xml which has predicted triggers.
    # This function handles both trigger and edge example classifications
    #edgeXML = ExampleUtils.writeToInteractionXML("edge-test-examples", "edge-test-classifications", boostedTriggerFile, "test-predicted-edges.xml", EDGE_IDS+".class_names", PARSE_TOK, PARSE_TOK)
    edgeXML = BioTextExampleWriter.write("edge-test-examples", "edge-test-classifications", boostedTriggerFile, None, EDGE_IDS+".class_names", PARSE_TOK, PARSE_TOK)
    # Split overlapping, merged elements (e.g. "Upregulate---Phosphorylate")
    #ix.splitMergedElements("test-predicted-edges.xml", "test-predicted-edges.xml")
    edgeXML = ix.splitMergedElements(edgeXML)
    # Always remember to fix ids
    #ix.recalculateIds("test-predicted-edges.xml", "test-predicted-edges.xml", True)
    xml = ix.recalculateIds(edgeXML, OUTFILE_STEM + "-events.xml.gz", True)
    # EvaluateInteractionXML differs from the previous evaluations in that it can
    # be used to compare two separate GifXML-files. One of these is the gold file,
    # against which the other is evaluated by heuristically matching triggers and
    # edges. Note that this evaluation will differ somewhat from the previous ones,
    # which evaluate on the level of examples.
    #EvaluateInteractionXML.run(Ev, "test-predicted-edges.xml", GOLD_TEST_FILE, PARSE_TOK, PARSE_TOK)
    #EvaluateInteractionXML.run(Ev, edgeXML, GOLD_TEST_FILE, PARSE_TOK, PARSE_TOK)
else:
    print >> sys.stderr, "No edge examples generated"
    open(OUTFILE_STEM + "-no_events", "w").close() 
    
###############################################################################
# Post-processing and task 3 
###############################################################################
if edgeExampleFileSize != 0:
    # Post-processing
    xml = unflatten(xml, PARSE_TOK, PARSE_TOK, OUTFILE_STEM + "-events_unflattened.xml.gz")

    # Task 3
    SPECULATION_MODEL = Settings.EverythingSpeculationModel
    NEGATION_MODEL = Settings.EverythingNegationModel
    
    # The id-sets will be modified, so create local copies of them.
    # Using always the same id numbers for machine learning classes
    # and examples ensures that the model-files will be compatible
    # with all of your experiments.
    TASK3_IDS = copyIdSetsToWorkdir(Settings.Task3Ids)
    
    # Speculation detection
    print >> sys.stderr, "====== Speculation Detection ======"
    Task3ExampleBuilder.run(xml, "speculation-test-examples", PARSE_TOK, PARSE_TOK, "style:typed,speculation", TASK3_IDS, None)
    Cls.test("speculation-test-examples", SPECULATION_MODEL, "speculation-test-classifications")
    xml = BioTextExampleWriter.write("speculation-test-examples", "speculation-test-classifications", xml, None)
    
    # Negation detection
    print >> sys.stderr, "====== Negation Detection ======"
    Task3ExampleBuilder.run(xml, "negation-test-examples", PARSE_TOK, PARSE_TOK, "style:typed,negation", TASK3_IDS, None)
    Cls.test("negation-test-examples", NEGATION_MODEL, "negation-test-classifications")
    xml = BioTextExampleWriter.write("negation-test-examples", "negation-test-classifications", xml, OUTFILE_STEM + "-events_unflattened_task3.xml.gz")

    # Output will be stored to the geniaformat-subdirectory, where will also be a
    # tar.gz-file which can be sent to the Shared Task evaluation server.
    gifxmlToGenia(xml, OUTFILE_STEM + "-events_geniaformat.tar.gz", 3, strengths=True)
    #evaluateSharedTask("geniaformat", 1)
    
# Remove workdir
if os.environ.has_key("METAWRK"): # CSC
    shutil.rmtree(options.workdir)