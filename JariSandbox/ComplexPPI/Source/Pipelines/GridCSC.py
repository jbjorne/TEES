# Optimize parameters for event detection and produce event and trigger model files

# most imports are defined in Pipeline
from Pipeline import *
import sys, os, time
import Utils.TableUtils as TableUtils

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-e", "--test", default=Settings.DevelFile, dest="testFile", help="Test file in interaction xml")
optparser.add_option("-r", "--train", default=Settings.TrainFile, dest="trainFile", help="Train file in interaction xml")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-a", "--task", default=1, type="int", dest="task", help="task number")
optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default="split-McClosky", dest="tokenization", help="Tokenization XML element name")
optparser.add_option("-m", "--mode", default="BOTH", dest="mode", help="MODELS (recalculate SVM models), GRID (parameter grid search) or BOTH")
# Classifier
optparser.add_option("-c", "--classifier", default="Cls", dest="classifier", help="")
optparser.add_option("--csc", default="", dest="csc", help="")
# Example builders
optparser.add_option("-f", "--triggerExampleBuilder", default="GeneralEntityTypeRecognizerGztr", dest="triggerExampleBuilder", help="")
optparser.add_option("-g", "--edgeExampleBuilder", default="MultiEdgeExampleBuilder", dest="edgeExampleBuilder", help="")
# Id sets
optparser.add_option("-v", "--triggerIds", default=None, dest="triggerIds", help="Trigger detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
optparser.add_option("-w", "--edgeIds", default=None, dest="edgeIds", help="Edge detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
# Parameters to optimize
optparser.add_option("-x", "--triggerParams", default="1000,5000,10000,20000,50000,80000,100000,150000,180000,200000,250000,300000,350000,500000,1000000", dest="triggerParams", help="Trigger detector c-parameter values")
optparser.add_option("-y", "--recallAdjustParams", default="0.5,0.6,0.65,0.7,0.85,1.0", dest="recallAdjustParams", help="Recall adjuster parameter values")
optparser.add_option("-z", "--edgeParams", default="5000,10000,20000,25000,28000,50000,60000,65000,80000,100000,150000", dest="edgeParams", help="Edge detector c-parameter values")
(options, args) = optparser.parse_args()

# Check options
assert options.mode in ["MODELS", "GRID", "BOTH", "DOWNLOAD_MODELS", "GRID_DOWNLOAD", "GRID_EVALUATE"]
assert options.output != None
assert options.task in [1, 2]

if options.csc.find(",") != -1:
    options.csc = options.csc.split(",")
else:
    options.csc = [options.csc]

exec "CLASSIFIER = " + options.classifier

# Main settings
PARSE=options.parse
TOK=options.tokenization
PARSE_TAG = PARSE + "_" + TOK
TRAIN_FILE = options.trainFile
TEST_FILE = options.testFile

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
CSC_WORKDIR = os.path.join("CSCConnection",WORKDIR.lstrip("/"))

workdir(WORKDIR, False) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

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
if options.mode in ["BOTH", "MODELS", "DOWNLOAD_MODELS"]:
    triggerCSC = None
    edgeCSC = None
    if "local" not in options.csc:
        clear = False
        if "clear" in options.csc: clear = True
        cscAccount = "murska"
        if "louhi" in options.csc: cscAccount = "louhi"
        triggerCSC = CSCConnection(CSC_WORKDIR+"/trigger-models", "jakrbj@"+cscAccount+".csc.fi", clear)
        edgeCSC = CSCConnection(CSC_WORKDIR+"/edge-models", "jakrbj@"+cscAccount+".csc.fi", clear)
    
    if options.mode != "DOWNLOAD_MODELS":
        if options.triggerIds != None:
            TRIGGER_IDS = copyIdSetsToWorkdir(options.triggerIds)
        if options.edgeIds != None:
            EDGE_IDS = copyIdSetsToWorkdir(options.edgeIds)
        
        ###############################################################################
        # Trigger example generation
        ###############################################################################
        print >> sys.stderr, "Trigger examples for parse", PARSE_TAG   
        TRIGGER_EXAMPLE_BUILDER.run(TRAIN_FILE, TRIGGER_TRAIN_EXAMPLE_FILE, PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
        TRIGGER_EXAMPLE_BUILDER.run(TEST_FILE, TRIGGER_TEST_EXAMPLE_FILE, PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
        
        ###############################################################################
        # Trigger models
        ###############################################################################
        print >> sys.stderr, "Trigger models for parse", PARSE_TAG
        optimize(CLASSIFIER, Ev, TRIGGER_TRAIN_EXAMPLE_FILE, TRIGGER_TEST_EXAMPLE_FILE,\
            TRIGGER_IDS+".class_names", TRIGGER_CLASSIFIER_PARAMS, "trigger-models", None, triggerCSC, True, steps="SUBMIT")
        
        ###############################################################################
        # Edge example generation
        ###############################################################################
        print >> sys.stderr, "Edge examples for parse", PARSE_TAG  
        EDGE_EXAMPLE_BUILDER.run(TRAIN_FILE, EDGE_TRAIN_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
        EDGE_EXAMPLE_BUILDER.run(TEST_FILE, EDGE_TEST_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
        
        ###############################################################################
        # Edge models
        ###############################################################################
        print >> sys.stderr, "Edge models for parse", PARSE_TAG
        optimize(CLASSIFIER, Ev, EDGE_TRAIN_EXAMPLE_FILE, EDGE_TEST_EXAMPLE_FILE,\
            EDGE_IDS+".class_names", EDGE_CLASSIFIER_PARAMS, "edge-models", None, edgeCSC, True, steps="SUBMIT")
    
    # Wait for results
    print >> sys.stderr, "Trigger model results"
    optimize(CLASSIFIER, Ev, TRIGGER_TRAIN_EXAMPLE_FILE, TRIGGER_TEST_EXAMPLE_FILE,\
        TRIGGER_IDS+".class_names", TRIGGER_CLASSIFIER_PARAMS, "trigger-models", None, triggerCSC, True, steps="RESULTS")
    print >> sys.stderr, "Edge model results"
    optimize(CLASSIFIER, Ev, EDGE_TRAIN_EXAMPLE_FILE, EDGE_TEST_EXAMPLE_FILE,\
        EDGE_IDS+".class_names", EDGE_CLASSIFIER_PARAMS, "edge-models", None, edgeCSC, True, steps="RESULTS")
    
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
if options.mode in ["BOTH", "GRID_SUBMIT"]:
    # Pre-made models
    CSC_TRIGGER_TEST_EXAMPLE_FILE = "trigger-models/" + TRIGGER_TEST_EXAMPLE_FILE
    EDGE_MODEL_STEM = "edge-models/model-c_"
    TRIGGER_MODEL_STEM = "trigger-models/model-c_"
    
    gridCSC = CSCConnection(CSC_WORKDIR, "jakrbj@murska.csc.fi", False)
    if True:
        print >> sys.stderr, "Uploading resources to CSC"
        gridCSC.upload(options.testFile, "remotetestset.xml")
        gridCSC.upload(TRIGGER_IDS+".class_names")
        gridCSC.upload(TRIGGER_IDS+".feature_names")
        gridCSC.upload(EDGE_IDS+".class_names")
        gridCSC.upload(EDGE_IDS+".feature_names")
    
    batchCount = 0
    count = 0
    for params in paramCombinations:
        print >> sys.stderr, "Queueing params", str(count) + "/" + str(len(paramCombinations)), params
        count += 1
        pId = getCombinationString(params) #"-boost_"+str(param)[0:3] # param id
        gridPointDir = "grid/gridpoint-"+pId
        if False:#gridCSC.exists(gridPointDir):
            print >> sys.stderr, "Point already queued"
            continue
        
        gridCSC.mkdir(gridPointDir)

        if batchCount == 0:
            gridCSC.beginJob()
            gridCSC.addCommand("#module load python/2.5.1-gcc \n")
            gridCSC.addCommand("export PATH=$PATH:/v/users/jakrbj/cvs_checkout")
            gridCSC.addCommand("export PYTHONPATH=$PYTHONPATH:/v/users/jakrbj/cvs_checkout/CommonUtils")
            gridCSC.addCommand("cd /v/users/jakrbj/cvs_checkout/JariSandbox/ComplexPPI/Source/Pipelines\n")
        
        gridPointCommand = "/v/users/jakrbj/Python-2.5/bin/python GridPoint.py "
        gridPointCommand += "-e " + "/wrk/jakrbj/" + CSC_WORKDIR + "/" + "remotetestset.xml" + " "
        gridPointCommand += "-o " + "/wrk/jakrbj/" + CSC_WORKDIR + "/" + gridPointDir + " "
        gridPointCommand += "-a " + str(options.task) + " "
        gridPointCommand += "-f " + "/wrk/jakrbj/" + CSC_WORKDIR + "/" + CSC_TRIGGER_TEST_EXAMPLE_FILE + " "
        gridPointCommand += "-x " + "/wrk/jakrbj/" + CSC_WORKDIR + "/" + TRIGGER_MODEL_STEM + str(params["trigger"]) + " "
        gridPointCommand += "-y " + str(params["booster"]) + " "
        gridPointCommand += "-z " + "/wrk/jakrbj/" + CSC_WORKDIR + "/" + EDGE_MODEL_STEM + str(params["edge"]) + " "
        gridPointCommand += "-v " + "/wrk/jakrbj/" + CSC_WORKDIR + "/" + TRIGGER_IDS + " "
        gridPointCommand += "-w " + "/wrk/jakrbj/" + CSC_WORKDIR + "/" + EDGE_IDS + " "
        gridCSC.addCommand(gridPointCommand)
        batchCount += 1
        
        if batchCount >= 20 or (batchCount > 0 and params == paramCombinations[-1]):
            print >> sys.stderr, "Submitting batch file"
            jobScriptPath = "gridjobs/job-" + time.strftime("%Y_%m_%d-%M_%S-")
            jobScriptCount = 0
            while gridCSC.exists(jobScriptPath + str(jobScriptCount) + ".sh"):
                jobScriptCount += 1
            jobScriptPath += str(jobScriptCount) + ".sh"
            gridCSC.submitJob(WORKDIR, jobScriptPath)
            batchCount = 0

if options.mode in ["GRID_DOWNLOAD"]:
    gridCSC = CSCConnection(CSC_WORKDIR, "jakrbj@murska.csc.fi", False)
    finished = False
    count = 0
    while finished == False:
        finished = True
        for params in paramCombinations:
            print >> sys.stderr, "Checking results for params", str(count) + "/" + str(len(paramCombinations)), params
            count += 1
            pId = getCombinationString(params) #"-boost_"+str(param)[0:3] # param id
            gridPointDir = "grid/gridpoint-"+pId
            assert gridCSC.exists(gridPointDir)
            if gridCSC.exists(gridPointDir + "/results.csv"):
                print >> sys.stderr, "Downloading results"
                gridCSC.download(gridPointDir + "/results.csv", "results"+pId+".csv")
            else:
                print >> sys.stderr, "Run not yet finished"
                finished = False
        time.sleep(60)

if options.mode in ["GRID_EVALUATE"]:
    bestResult = (-1, None, None)
    for filename in os.listdir(WORKDIR):
        if filename[-4:] == ".csv" and os.path.getsize(filename) != 0:
            gridRows = TableUtils.readCSV(filename)
            fscore = None
            for row in gridRows:
                if row["eval"] == "approximate" and row["event_class"] == "ALL-TOTAL":
                    fscore = row["fscore"]
                    break
            assert fscore != None, row
            if fscore > bestResult[0]:
                bestResult = (fscore, gridRows, filename)
    print bestResult
            

#if options.mode in ["]
#    print >> sys.stderr, "Grid search complete"
#    print >> sys.stderr, "Tested", count - options.startFrom, "out of", count, "combinations"
#    print >> sys.stderr, "Best parameter combination:", bestResults[0]
#    print >> sys.stderr, "Best result:", bestResults[1]
    
