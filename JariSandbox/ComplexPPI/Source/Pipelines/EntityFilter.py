# Optimize parameters for event detection and produce event and trigger model files

# most imports are defined in Pipeline
from Pipeline import *
import sys, os

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-e", "--test", default=Settings.DevelFile, dest="testFile", help="Test file in interaction xml")
optparser.add_option("-r", "--train", default=Settings.TrainFile, dest="trainFile", help="Train file in interaction xml")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-a", "--task", default=1, type="int", dest="task", help="task number")
optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="Tokenization XML element name")
optparser.add_option("-m", "--mode", default="BOTH", dest="mode", help="MODELS (recalculate SVM models), GRID (parameter grid search) or BOTH")
optparser.add_option("-s", "--startFrom", default=0, type="int", dest="startFrom", help="The parameter combination index to start grid search from")
# Id sets
optparser.add_option("-v", "--triggerIds", default=Settings.TriggerIds, dest="triggerIds", help="Trigger detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
# Parameters to optimize
optparser.add_option("-x", "--triggerParams", default="1000,5000,10000,20000,50000,80000,100000,150000,180000,200000,250000,300000,350000,500000,1000000", dest="triggerParams", help="Trigger detector c-parameter values")
optparser.add_option("-y", "--recallAdjustParams", default="0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8", dest="recallAdjustParams", help="Recall adjuster parameter values")
(options, args) = optparser.parse_args()

# Check options
assert options.mode in ["MODELS", "GRID", "BOTH"]
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
}
paramCombinations = getParameterCombinations(ALL_PARAMS)

# These commands will be in the beginning of most pipelines
WORKDIR=options.output
workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

PARSE_TAG = PARSE + "_" + TOK

# Pre-calculate all the required SVM models
if options.mode in ["BOTH", "MODELS"]:
    TRIGGER_IDS = copyIdSetsToWorkdir(options.triggerIds)
    
    ###############################################################################
    # Trigger example generation
    ###############################################################################
    TRIGGER_TRAIN_EXAMPLE_FILE = "trigger-train-examples-"+PARSE_TAG
    TRIGGER_DEVEL_EXAMPLE_FILE = "trigger-devel-examples-"+PARSE_TAG
    print >> sys.stderr, "Trigger examples for parse", PARSE_TAG   
    BinaryEntityExampleBuilder.run(TRAIN_FILE, TRIGGER_TRAIN_EXAMPLE_FILE, PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
    BinaryEntityExampleBuilder.run(DEVEL_FILE, TRIGGER_DEVEL_EXAMPLE_FILE, PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
    
    ###############################################################################
    # Trigger models
    ###############################################################################
    print >> sys.stderr, "Trigger models for parse", PARSE_TAG
    TRIGGER_CLASSIFIER_PARAMS="c:" + ','.join(map(str, ALL_PARAMS["trigger"]))
    c = CSCConnection("EntityFilter/models-"+PARSE_TAG+"/trigger-models", "jakrbj@murska.csc.fi", False)
    optimize(Cls, Ev, TRIGGER_TRAIN_EXAMPLE_FILE, TRIGGER_DEVEL_EXAMPLE_FILE,\
        TRIGGER_IDS+".class_names", TRIGGER_CLASSIFIER_PARAMS, "trigger-models", None, c, downloadAllModels=True)
else:
    # New feature ids may have been defined during example generation, 
    # so use for the grid search the id sets copied to WORKDIR during 
    # model generation. The set files will have the same names as the files 
    # they are copied from
    TRIGGER_IDS = os.path.basename(options.triggerIds)
    #EDGE_IDS = os.path.basename(options.edgeIds)


###############################################################################
# Parameter Grid Search
###############################################################################
if options.mode in ["BOTH", "GRID"]:
    # Pre-made models
    TRIGGER_MODEL_STEM = "trigger-models/model-c_"
    
    count = 0
    BinaryEntityExampleBuilder.run(DEVEL_FILE, "devel-trigger-examples", PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
    bestResults = None
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
        evaluator = Ev.evaluate("devel-trigger-examples", ExampleUtils.loadPredictionsBoost("devel-trigger-classifications", params["booster"]), TRIGGER_IDS+".class_names")
        print >> sys.stderr, "Positive Counts:", ExampleUtils.getPositivesPerSentence("devel-trigger-examples", ExampleUtils.loadPredictionsBoost("devel-trigger-classifications", params["booster"]))
        count += 1
    print >> sys.stderr, "Grid search complete"
    print >> sys.stderr, "Tested", count - options.startFrom, "out of", count, "combinations"
    print >> sys.stderr, "Best parameter combination:", bestResults[0]
    print >> sys.stderr, "Best result:", bestResults[1]
    
