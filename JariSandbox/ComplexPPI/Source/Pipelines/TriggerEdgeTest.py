# Optimize parameters for event detection and produce event and trigger model files

# most imports are defined in Pipeline
from Pipeline import *
import sys, os
import STFormat.ConvertXML

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-e", "--test", default=Settings.DevelFile, dest="testFile", help="Test file in interaction xml")
optparser.add_option("-r", "--train", default=Settings.TrainFile, dest="trainFile", help="Train file in interaction xml")
optparser.add_option("--extraTrain", default=None, dest="extraTrain", help="extra training examples")
optparser.add_option("--extraTrainFor", default="trigger", dest="extraTrainFor", help="extra training examples")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-a", "--task", default="1", dest="task", help="task number")
optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="Tokenization XML element name")
optparser.add_option("-m", "--mode", default="BOTH", dest="mode", help="MODELS (recalculate SVM models), GRID (parameter grid search) or BOTH")
# Classifier
optparser.add_option("-c", "--classifier", default="Cls", dest="classifier", help="")
optparser.add_option("--csc", default="", dest="csc", help="")
# Example builders
optparser.add_option("-f", "--triggerExampleBuilder", default="GeneralEntityTypeRecognizerGztr", dest="triggerExampleBuilder", help="")
optparser.add_option("-g", "--edgeExampleBuilder", default="MultiEdgeExampleBuilder", dest="edgeExampleBuilder", help="")
# Feature params
optparser.add_option("--triggerStyle", default="typed", dest="triggerStyle", help="")
optparser.add_option("--edgeStyle", default=None, dest="edgeStyle", help="")
# Id sets
optparser.add_option("-v", "--triggerIds", default=None, dest="triggerIds", help="Trigger detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
optparser.add_option("-w", "--edgeIds", default=None, dest="edgeIds", help="Edge detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
# Parameters to optimize
optparser.add_option("-x", "--triggerParams", default="1000,5000,10000,20000,50000,80000,100000,150000,180000,200000,250000,300000,350000,500000,1000000", dest="triggerParams", help="Trigger detector c-parameter values")
optparser.add_option("-y", "--recallAdjustParams", default="0.5,0.6,0.65,0.7,0.85,1.0,1.1,1.2", dest="recallAdjustParams", help="Recall adjuster parameter values")
optparser.add_option("-z", "--edgeParams", default="5000,7500,10000,20000,25000,28000,50000,60000,65000", dest="edgeParams", help="Edge detector c-parameter values")
# Shared task evaluation
optparser.add_option("-s", "--sharedTask", default=True, action="store_false", dest="sharedTask", help="Do Shared Task evaluation")
optparser.add_option("--clearAll", default=False, action="store_true", dest="clearAll", help="Delete all files")
(options, args) = optparser.parse_args()

# Check options
assert options.mode in ["MODELS", "FINAL", "BOTH", "GRID"]
assert options.output != None
assert options.task in ["1", "2", "CO", "REL"]

if options.csc.find(",") != -1:
    options.csc = options.csc.split(",")
else:
    options.csc = [options.csc]
if options.clearAll and "clear" not in options.csc:
    options.csc.append("clear")

exec "CLASSIFIER = " + options.classifier

# Main settings
PARSE=options.parse
TOK=options.tokenization
PARSE_TAG = PARSE + "_" + TOK
TRAIN_FILE = options.trainFile
TEST_FILE = options.testFile

# Example generation parameters
if options.sharedTask:
    EDGE_FEATURE_PARAMS="style:trigger_features,typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"
else:
    EDGE_FEATURE_PARAMS="style:trigger_features,typed,directed,no_linear,entities,noMasking,maxFeatures"
if options.edgeStyle != None:
    EDGE_FEATURE_PARAMS="style:"+options.edgeStyle
TRIGGER_FEATURE_PARAMS="style:"+options.triggerStyle #"style:typed"

boosterParams = [float(i) for i in options.recallAdjustParams.split(",")] 

# These commands will be in the beginning of most pipelines
WORKDIR=options.output
CSC_WORKDIR = os.path.join("CSCConnection",WORKDIR.lstrip("/"))

if options.clearAll:
    workdir(WORKDIR, True) # Select a working directory, remove existing files
else:
    workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

print >> sys.stderr, "Edge params:", EDGE_FEATURE_PARAMS
print >> sys.stderr, "Trigger params:", TRIGGER_FEATURE_PARAMS
TRIGGER_EXAMPLE_BUILDER = eval(options.triggerExampleBuilder)
EDGE_EXAMPLE_BUILDER = eval(options.edgeExampleBuilder)

# Pre-calculate all the required SVM models
TRIGGER_IDS = "trigger-ids"
EDGE_IDS = "edge-ids"
TRIGGER_TRAIN_EXAMPLE_FILE = "trigger-train-examples-"+PARSE_TAG
TRIGGER_TEST_EXAMPLE_FILE = "trigger-test-examples-"+PARSE_TAG
TRIGGER_CLASSIFIER_PARAMS="c:" + options.triggerParams
EDGE_TRAIN_EXAMPLE_FILE = "edge-train-examples-"+PARSE_TAG
EDGE_TEST_EXAMPLE_FILE = "edge-test-examples-"+PARSE_TAG
EDGE_CLASSIFIER_PARAMS="c:" + options.edgeParams
if options.mode in ["BOTH", "MODELS"]:
    if options.triggerIds != None:
        TRIGGER_IDS = copyIdSetsToWorkdir(options.triggerIds)
    if options.edgeIds != None:
        EDGE_IDS = copyIdSetsToWorkdir(options.edgeIds)
    
    ###############################################################################
    # Trigger example generation
    ###############################################################################
    print >> sys.stderr, "Trigger examples for parse", PARSE_TAG   
    TRIGGER_EXAMPLE_BUILDER.run(TEST_FILE, TRIGGER_TEST_EXAMPLE_FILE, PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
    TRIGGER_EXAMPLE_BUILDER.run(TRAIN_FILE, TRIGGER_TRAIN_EXAMPLE_FILE, PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
    if options.extraTrain != None and "trigger" in options.extraTrainFor:
        TRIGGER_EXAMPLE_BUILDER.run(options.extraTrain, TRIGGER_TRAIN_EXAMPLE_FILE, "split-McClosky", "split-McClosky", TRIGGER_FEATURE_PARAMS, TRIGGER_IDS, appendIndex=1000)
    
    ###############################################################################
    # Trigger models
    ###############################################################################
    print >> sys.stderr, "Trigger models for parse", PARSE_TAG
    if "local" not in options.csc:
        clear = False
        if "clear" in options.csc: clear = True
        if "louhi" in options.csc:
            c = CSCConnection(CSC_WORKDIR+"/trigger-models", "jakrbj@louhi.csc.fi", clear)
        else:
            c = CSCConnection(CSC_WORKDIR+"/trigger-models", "jakrbj@murska.csc.fi", clear)
    else:
        c = None
    optimize(CLASSIFIER, Ev, TRIGGER_TRAIN_EXAMPLE_FILE, TRIGGER_TEST_EXAMPLE_FILE,\
        TRIGGER_IDS+".class_names", TRIGGER_CLASSIFIER_PARAMS, "trigger-models", None, c, True, steps="SUBMIT")
    
    ###############################################################################
    # Edge example generation
    ###############################################################################
    print >> sys.stderr, "Edge examples for parse", PARSE_TAG  
    EDGE_EXAMPLE_BUILDER.run(TRAIN_FILE, EDGE_TRAIN_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    EDGE_EXAMPLE_BUILDER.run(TEST_FILE, EDGE_TEST_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    #EDGE_EXAMPLE_BUILDER.run(Settings.TrainFile, EDGE_TRAIN_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    #EDGE_EXAMPLE_BUILDER.run(Settings.DevelFile, EDGE_TEST_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    if options.extraTrain != None and "edge" in options.extraTrainFor:
        EDGE_EXAMPLE_BUILDER.run(options.extraTrain, EDGE_TRAIN_EXAMPLE_FILE, "split-McClosky", "split-McClosky", EDGE_FEATURE_PARAMS, EDGE_IDS, appendIndex=1000)
    
    ###############################################################################
    # Edge models
    ###############################################################################
    print >> sys.stderr, "Edge models for parse", PARSE_TAG
    if "local" not in options.csc:
        clear = False
        if "clear" in options.csc: clear = True
        if "louhi" in options.csc:
            c = CSCConnection(CSC_WORKDIR+"/edge-models", "jakrbj@louhi.csc.fi", clear)
        else:
            c = CSCConnection(CSC_WORKDIR+"/edge-models", "jakrbj@murska.csc.fi", clear)
    else:
        c = None
    optimize(CLASSIFIER, Ev, EDGE_TRAIN_EXAMPLE_FILE, EDGE_TEST_EXAMPLE_FILE,\
        EDGE_IDS+".class_names", EDGE_CLASSIFIER_PARAMS, "edge-models", None, c, True, steps="SUBMIT")
else:
    # New feature ids may have been defined during example generation, 
    # so use for the grid search the id sets copied to WORKDIR during 
    # model generation. The set files will have the same names as the files 
    # they are copied from
    if options.triggerIds != None:
        TRIGGER_IDS = os.path.basename(options.triggerIds)
    if options.edgeIds != None:
        EDGE_IDS = os.path.basename(options.edgeIds)

###############################################################################
# Classification with recall boosting
###############################################################################
if options.mode in ["BOTH", "FINAL", "GRID"]:
    # Pre-made models
    #EDGE_MODEL_STEM = "edge-models/model-c_"
    #TRIGGER_MODEL_STEM = "trigger-models/model-c_"
    #bestTriggerModel = "trigger-models/model-c_50000"
    #bestEdgeModel = "edge-models/model-c_7500"
    #bestTriggerModel = "best-trigger-model"
    #bestEdgeModel = "best-edge-model"
    
    if options.mode != "GRID":
        clear = False
        if "local" not in options.csc:
            if "louhi" in options.csc:
                c = CSCConnection(CSC_WORKDIR+"/trigger-models", "jakrbj@louhi.csc.fi", False)
            else:
                c = CSCConnection(CSC_WORKDIR+"/trigger-models", "jakrbj@murska.csc.fi", False)
        else:
            c = None
        bestTriggerModel = optimize(CLASSIFIER, Ev, TRIGGER_TRAIN_EXAMPLE_FILE, TRIGGER_TEST_EXAMPLE_FILE,\
            TRIGGER_IDS+".class_names", TRIGGER_CLASSIFIER_PARAMS, "trigger-models", None, c, True, steps="RESULTS")[1]
        if os.path.exists("best-trigger-model.gz"):
            os.remove("best-trigger-model.gz")
        if os.path.exists(bestTriggerModel):
            print bestTriggerModel
            os.symlink(bestTriggerModel, "best-trigger-model.gz")
            bestTriggerModel = "best-trigger-model.gz"
        else:
            bestTriggerModel = None
        if "local" not in options.csc:
            if "louhi" in options.csc:
                c = CSCConnection(CSC_WORKDIR+"/edge-models", "jakrbj@louhi.csc.fi", False)
            else:
                c = CSCConnection(CSC_WORKDIR+"/edge-models", "jakrbj@murska.csc.fi", False)
        else:
            c = None
        bestEdgeModel = optimize(CLASSIFIER, Ev, EDGE_TRAIN_EXAMPLE_FILE, EDGE_TEST_EXAMPLE_FILE,\
            EDGE_IDS+".class_names", EDGE_CLASSIFIER_PARAMS, "edge-models", None, c, True, steps="RESULTS")[1]
        if os.path.exists("best-edge-model.gz"):
            os.remove("best-edge-model.gz")
        if os.path.exists(bestEdgeModel):
            os.symlink(bestEdgeModel, "best-edge-model.gz")
            bestEdgeModel = "best-edge-model.gz"
        else:
            bestEdgeModel = None

    else:
        bestTriggerModel = "best-trigger-model.gz"
        bestEdgeModel = "best-edge-model.gz"
    
    print >> sys.stderr, "Booster parameter search"
    # Build trigger examples
    TRIGGER_EXAMPLE_BUILDER.run(TEST_FILE, "test-trigger-examples", PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
    CLASSIFIER.test("test-trigger-examples", bestTriggerModel, "test-trigger-classifications")
    if bestTriggerModel != None:
        print >> sys.stderr, "best-trigger-model=", os.path.realpath("best-trigger-model.gz")
    evaluator = Ev.evaluate("test-trigger-examples", "test-trigger-classifications", TRIGGER_IDS+".class_names")
    #boostedTriggerFile = "TEST-predicted-triggers.xml"
    #xml = ExampleUtils.writeToInteractionXML("test-trigger-examples", ExampleUtils.loadPredictionsBoost("test-trigger-classifications", boost), TEST_FILE, None, TRIGGER_IDS+".class_names", PARSE, TOK)    
    #xml = ExampleUtils.writeToInteractionXML("test-trigger-examples", "test-trigger-classifications", TEST_FILE, None, TRIGGER_IDS+".class_names", PARSE, TOK)    
    xml = BioTextExampleWriter.write("test-trigger-examples", "test-trigger-classifications", TEST_FILE, "trigger-pred-best.xml", TRIGGER_IDS+".class_names", PARSE, TOK)
    
    count = 0
    bestResults = None
    for boost in boosterParams:
        print >> sys.stderr, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        print >> sys.stderr, "Processing params", str(count) + "/" + str(len(boosterParams)), boost
        print >> sys.stderr, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
        
        # Boost
        if options.task == "CO":
            print >> sys.stderr, "Binary recall adjust for CO"
            xml = RecallAdjust.run("trigger-pred-best.xml", boost, None, binary=True)
        else:
            xml = RecallAdjust.run("trigger-pred-best.xml", boost, None)
        xml = ix.splitMergedElements(xml, None)
        xml = ix.recalculateIds(xml, None, True)
        
        # Build edge examples
        if options.classifier == "ACCls":
            EDGE_EXAMPLE_BUILDER.run(xml, "test-edge-examples", PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS, gold=TEST_FILE)
        else:
            EDGE_EXAMPLE_BUILDER.run(xml, "test-edge-examples", PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
        # Classify with pre-defined model
        if bestEdgeModel != None:
            print >> sys.stderr, "best-edge-model=", os.path.realpath("best-edge-model.gz")
        CLASSIFIER.test("test-edge-examples", bestEdgeModel, "test-edge-classifications")
        # Write to interaction xml
        evaluator = Ev.evaluate("test-edge-examples", "test-edge-classifications", EDGE_IDS+".class_names")
        if evaluator.getData().getTP() + evaluator.getData().getFP() > 0:
            #xml = ExampleUtils.writeToInteractionXML("test-edge-examples", "test-edge-classifications", xml, None, EDGE_IDS+".class_names", PARSE, TOK)
            xml = BioTextExampleWriter.write("test-edge-examples", "test-edge-classifications", xml, None, EDGE_IDS+".class_names", PARSE, TOK)
            xml = ix.splitMergedElements(xml, None)
            xml = ix.recalculateIds(xml, "flat-" + str(boost) + ".xml", True)
            
            # EvaluateInteractionXML differs from the previous evaluations in that it can
            # be used to compare two separate GifXML-files. One of these is the gold file,
            # against which the other is evaluated by heuristically matching triggers and
            # edges. Note that this evaluation will differ somewhat from the previous ones,
            # which evaluate on the level of examples.
            EvaluateInteractionXML.run(Ev, xml, TEST_FILE, PARSE, TOK)
            
            # Convert to ST-format
            if options.task == "REL":
                STFormat.ConvertXML.toSTFormat(xml, "flat-"+str(boost)+"-geniaformat", "rel")
            else:
                STFormat.ConvertXML.toSTFormat(xml, "flat-"+str(boost)+"-geniaformat", "a2")
            
            if options.sharedTask:
                # Post-processing
                xml = unflatten(xml, PARSE, TOK)
                
                # Output will be stored to the geniaformat-subdirectory, where will also be a
                # tar.gz-file which can be sent to the Shared Task evaluation server.
                gifxmlToGenia(xml, "geniaformat", options.task)
                
                # Evaluation of the Shared Task format
                results = evaluateSharedTask("geniaformat", options.task)
                if bestResults == None or bestResults[1]["approximate"]["ALL-TOTAL"]["fscore"] < results["approximate"]["ALL-TOTAL"]["fscore"]:
                    bestResults = (boost, results)
        else:
            print >> sys.stderr, "No predicted edges"
        count += 1
    print >> sys.stderr, "Booster search complete"
    print >> sys.stderr, "Tested", count, "out of", count, "combinations"
    if options.sharedTask:
        print >> sys.stderr, "Best booster parameter:", bestResults[0]
        print >> sys.stderr, "Best result:", bestResults[1]
    
