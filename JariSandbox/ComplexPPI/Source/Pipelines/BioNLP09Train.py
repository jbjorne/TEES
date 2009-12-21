# Optimize parameters for event detection and produce event and trigger model files

# most imports are defined in Pipeline
from Pipeline import *
import sys, os

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-e", "--test", default=Settings.TrainFile, dest="trainFile", help="Train file in interaction xml")
optparser.add_option("-r", "--train", default=Settings.DevelFile, dest="testFile", help="Test file in interaction xml")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-a", "--task", default=1, type="int", dest="task", help="task number")
optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="Tokenization XML element name")
optparser.add_option("-m", "--models", default=True, action="store_false", dest="models", help="Don't recalculate models")
optparser.add_option("-s", "--startFrom", default=0, type="int", dest="startFrom", help="The parameter combination index to start grid search from")
# Id sets
optparser.add_option("-v", "--triggerIds", default=Settings.TriggerIds, dest="triggerIds", help="Trigger detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
optparser.add_option("-w", "--edgeIds", default=Settings.EdgeIds, dest="edgeIds", help="Edge detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
# Parameters to optimize
optparser.add_option("-x", "--triggerParams", default="1000,5000,10000,20000,50000,80000,100000,150000,180000,200000,250000,300000,350000,500000,1000000", dest="triggerParams", help="Trigger detector c-parameter values")
optparser.add_option("-y", "--recallAdjustParams", default="0.5,0.6,0.7,0.85,1.0", dest="recallAdjustParams", help="Recall adjuster parameter values")
optparser.add_option("-z", "--edgeParams", default="5000,10000,20000,25000,28000,50000,60000,65000,80000,100000,150000", dest="edgeParams", help="Edge detector c-parameter values")
(options, args) = optparser.parse_args()

# Check options
assert options.output != None
assert options.task in [1, 2]

# Main settings
PARSE=options.parse
TOK=options.tokenization
TRAIN_FILE = options.trainFile
DEVEL_FILE = options.testFile

# Example generation parameters
EDGE_FEATURE_PARAMS="style:typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"
TRIGGER_FEATURE_PARAMS="style:typed"

# Parameters to optimize
ALL_PARAMS={
    "trigger":[int(i) for i in options.triggerParams.split(",")], 
    "booster":[float(i) for i in options.recallAdjustParams.split(",")], 
    "edge":[int(i) for i in options.edgeParams.split(",")]    
}
paramCombinations = getParameterCombinations(ALL_PARAMS)

# These commands will be in the beginning of most pipelines
WORKDIR=options.output
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

PARSE_TAG = PARSE + "_" + TOK

# Pre-calculate all the required SVM models
if options.models:
    TRIGGER_IDS = copyIdSetsToWorkdir(options.triggerIds)
    EDGE_IDS = copyIdSetsToWorkdir(options.edgeIds)
    
    ###############################################################################
    # Trigger example generation
    ###############################################################################
    TRIGGER_TRAIN_EXAMPLE_FILE = "trigger-train-examples-"+PARSE_TAG
    TRIGGER_DEVEL_EXAMPLE_FILE = "trigger-devel-examples-"+PARSE_TAG
    print >> sys.stderr, "Trigger examples for parse", PARSE_TAG   
    GeneralEntityTypeRecognizerGztr.run(TRAIN_FILE, TRIGGER_TRAIN_EXAMPLE_FILE, PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
    GeneralEntityTypeRecognizerGztr.run(DEVEL_FILE, TRIGGER_DEVEL_EXAMPLE_FILE, PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
    
    ###############################################################################
    # Trigger models
    ###############################################################################
    print >> sys.stderr, "Trigger models for parse", PARSE_TAG
    TRIGGER_CLASSIFIER_PARAMS="c:" + ','.join(map(str, ALL_PARAMS["trigger"]))
    optimize(Cls, Ev, TRIGGER_TRAIN_EXAMPLE_FILE, TRIGGER_DEVEL_EXAMPLE_FILE,\
        TRIGGER_IDS+".class_names", TRIGGER_CLASSIFIER_PARAMS, "devel-trigger-models")
    
    ###############################################################################
    # Edge example generation
    ###############################################################################
    EDGE_TRAIN_EXAMPLE_FILE = "edge-train-examples-"+PARSE_TAG
    EDGE_DEVEL_EXAMPLE_FILE = "edge-devel-examples-"+PARSE_TAG
    print >> sys.stderr, "Edge examples for parse", PARSE_TAG  
    MultiEdgeExampleBuilder.run(TRAIN_FILE, EDGE_TRAIN_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    MultiEdgeExampleBuilder.run(DEVEL_FILE, EDGE_DEVEL_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    
    ###############################################################################
    # Edge models
    ###############################################################################
    print >> sys.stderr, "Edge models for parse", PARSE_TAG
    EDGE_CLASSIFIER_PARAMS="c:" + ','.join(map(str, ALL_PARAMS["edge"]))
    optimize(Cls, Ev, EDGE_TRAIN_EXAMPLE_FILE, EDGE_DEVEL_EXAMPLE_FILE,\
        EDGE_IDS+".class_names", EDGE_CLASSIFIER_PARAMS, "devel-edge-models")
else:
    # New feature ids may have been defined during example generation, 
    # so use for the grid search the id sets copied to WORKDIR during 
    # model generation. The set files will have the same names as the files 
    # they are copied from
    TRIGGER_IDS = os.path.basename(options.triggerIds)
    EDGE_IDS = os.path.basename(options.edgeIds)


###############################################################################
# Parameter Grid Search
###############################################################################

# Pre-made models
EDGE_MODEL_STEM = "devel-edge-models/model-c_"
TRIGGER_MODEL_STEM = "devel-trigger-models/model-c_"

count = 0
GeneralEntityTypeRecognizerGztr.run(DEVEL_FILE, "devel-trigger-examples", PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
for params in paramCombinations:
    if count < options.startFrom:
        count += 1
        continue

    print >> sys.stderr, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    print >> sys.stderr, "Processing params", str(count) + "/" + str(len(paramCombinations)), params
    print >> sys.stderr, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    pId = getCombinationString(params) #"-boost_"+str(param)[0:3] # param id
    
    # Build trigger examples
    Cls.test("devel-trigger-examples", TRIGGER_MODEL_STEM + str(params["trigger"]), "devel-trigger-classifications")
    evaluator = Ev.evaluate("devel-trigger-examples", "devel-trigger-classifications", TRIGGER_IDS+".class_names")
    #boostedTriggerFile = "devel-predicted-triggers.xml"
    xml = ExampleUtils.writeToInteractionXML("devel-trigger-examples", "devel-trigger-classifications", DEVEL_FILE, None, TRIGGER_IDS+".class_names", PARSE, TOK)    
    # Boost
    xml = RecallAdjust.run(xml, params["booster"], None)
    xml = ix.splitMergedElements(xml, None)
    xml = ix.recalculateIds(xml, None, True)
    
    # Build edge examples
    MultiEdgeExampleBuilder.run(xml, "devel-edge-examples", PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    # Classify with pre-defined model
    Cls.test("devel-edge-examples", EDGE_MODEL_STEM + str(params["edge"]), "devel-edge-classifications")
    # Write to interaction xml
    evaluator = Ev.evaluate("devel-edge-examples", "devel-edge-classifications", EDGE_IDS+".class_names")
    if evaluator.getData().getTP() + evaluator.getData().getFP() > 0:
        xml = ExampleUtils.writeToInteractionXML("devel-edge-examples", "devel-edge-classifications", xml, None, EDGE_IDS+".class_names", PARSE, TOK)
        xml = ix.splitMergedElements(xml, None)
        xml = ix.recalculateIds(xml, "final.xml", True)
        
        # EvaluateInteractionXML differs from the previous evaluations in that it can
        # be used to compare two separate GifXML-files. One of these is the gold file,
        # against which the other is evaluated by heuristically matching triggers and
        # edges. Note that this evaluation will differ somewhat from the previous ones,
        # which evaluate on the level of examples.
        EvaluateInteractionXML.run(Ev, xml, DEVEL_FILE, PARSE, TOK)
        # Post-processing
        xml = unflatten(xml, PARSE, TOK)
        # Output will be stored to the geniaformat-subdirectory, where will also be a
        # tar.gz-file which can be sent to the Shared Task evaluation server.
        gifxmlToGenia(xml, "geniaformat", options.task)
        evaluateSharedTask("geniaformat", options.task)
    else:
        print >> sys.stderr, "No predicted edges"
    count += 1
    
