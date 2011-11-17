# Optimize parameters for event detection and produce event and trigger model files

# most imports are defined in Pipeline
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../CommonUtils") # new CommonUtils
from Pipeline import *
import sys, os
import STFormat.ConvertXML
import STFormat.Compare
import subprocess
import shutil

def makeSubset(filename, output, ratio, seed):
    if ratio == 1.0:
        return filename

    print >> sys.stderr, "====== Making subset ======"
    print >> sys.stderr, "Subset for file", filename, "ratio", ratio, "seed", seed
    import cElementTreeUtils as ETUtils
    import Core.Split
    xml = ETUtils.ETFromObj(filename).getroot()

    maxDoc = len(xml.findall("document"))
    totalFolds = min(100, maxDoc)
    selectedFolds = int(ratio * min(100.0, float(maxDoc)))

    count = 0
    sentCount = 0
    for document in xml.findall("document"):
        sentCount += len(document.findall("sentence"))
        count += 1
    division = Core.Split.getFolds(count, totalFolds, seed)
    #print division, selectedFolds - 1
    index = 0
    removeCount = 0
    sentRemoveCount = 0
    for document in xml.findall("document"):
        if division[index] > selectedFolds - 1:
            xml.remove(document)
            sentRemoveCount += len(document.findall("sentence"))
            removeCount += 1
        index += 1
    print "Subset", "doc:", count, "removed:", removeCount, "sent:", sentCount, "sentremoved:", sentRemoveCount
    ETUtils.write(xml, output)
    return output

def task3Classify(classifier, xml, specModel, negModel, task3Ids, task3Tag, parse, goldXML=None):
    # Task 3
    SPECULATION_MODEL = specModel
    assert os.path.exists(SPECULATION_MODEL)
    NEGATION_MODEL = negModel
    assert os.path.exists(NEGATION_MODEL)
    
    # The id-sets will be modified, so create local copies of them.
    # Using always the same id numbers for machine learning classes
    # and examples ensures that the model-files will be compatible
    # with all of your experiments.
    TASK3_IDS = copyIdSetsToWorkdir(task3Ids)
    
    # Speculation detection
    print >> sys.stderr, "====== Speculation Detection ======"
    Task3ExampleBuilder.run(xml, "speculation-"+task3Tag+"-examples", parse, None, "style:typed,speculation", TASK3_IDS, None, gold=goldXML)
    classifier.test("speculation-"+task3Tag+"-examples", SPECULATION_MODEL, "speculation-"+task3Tag+"-classifications")
    xml = BioTextExampleWriter.write("speculation-"+task3Tag+"-examples", "speculation-"+task3Tag+"-classifications", xml, None, TASK3_IDS+".class_names")
    
    # Negation detection
    print >> sys.stderr, "====== Negation Detection ======"
    Task3ExampleBuilder.run(xml, "negation-"+task3Tag+"-examples", parse, None, "style:typed,negation", TASK3_IDS, None, gold=goldXML)
    classifier.test("negation-"+task3Tag+"-examples", NEGATION_MODEL, "negation-"+task3Tag+"-classifications")
    xml = BioTextExampleWriter.write("negation-"+task3Tag+"-examples", "negation-"+task3Tag+"-classifications", xml, task3Tag + "-task3.xml.gz", TASK3_IDS+".class_names")
    return xml

#def evaluateB(sourceDir, corpusName):
#    if corpusName == "BI":
#        subprocess.call("java -jar /home/jari/data/BioNLP11SharedTask/evaluators/BioNLP-ST_2011_bacteria_interactions_evaluation_software/BioNLP-ST_2011_bacteria_interactions_evaluation_software.jar /home/jari/data/BioNLP11SharedTask/main-tasks/BioNLP-ST_2011_bacteria_interactions_dev_data_rev1-remixed/ " + sourceDir, shell=True)
#    elif corpusName == "BB":
#        subprocess.call("java -jar /home/jari/data/BioNLP11SharedTask/evaluators/BioNLP-ST_2011_Bacteria_Biotopes_evaluation_software/BioNLP-ST_2011_Bacteria_Biotopes_evaluation_software.jar /home/jari/data/BioNLP11SharedTask/main-tasks/BioNLP-ST_2011_Bacteria_Biotopes_dev_data_rev1 " + sourceDir, shell=True)
#    else:
#        assert False, corpusName

def updateModel(model, linkName):
    modelPath = model[1]
    if modelPath.endswith(".gz") and not linkName.endswith(".gz"):
        linkName += ".gz"
    f = open(linkName + "-parameter", "wt")
    f.write(model[2])
    f.close()
    if os.path.exists(linkName):
        os.remove(linkName)
    if os.path.exists(modelPath):
        print "Linking to best model", modelPath
        os.symlink(modelPath, linkName)
        return linkName
    else:
        print "Warning, best model does not exist"
        return None

def saveBoostParam(boost):
    f = open("best-boost-parameter", "wt")
    f.write(str(boost))
    f.close()

def getParameter(linkName):
    f = open(linkName + "-parameter", "rt")
    lines = f.readlines()
    f.close()
    assert len(lines) == 1
    return lines[0].strip()

def getA2FileTag(task, subTask):
    if task == "REL":
        return "rel"
    if task == "OLD":
        if subTask == 1:
            return "a2.t1"
        else:
            return "a2.t12"
        assert False
    return "a2"

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("--classify", default=None, dest="classify", help="classify with existing experiments models")
# files
optparser.add_option("--trainFile", default=None, dest="trainFile", help="")
optparser.add_option("--develFile", default=None, dest="develFile", help="")
optparser.add_option("--everythingFile", default=None, dest="everythingFile", help="")
optparser.add_option("--testFile", default=None, dest="testFile", help="")
# extras
optparser.add_option("--extraTag", default="", dest="extraTag", help="extra tag for input files")
optparser.add_option("--extraTrain", default=None, dest="extraTrain", help="extra training examples")
optparser.add_option("--extraTrainFor", default="trigger,edge", dest="extraTrainFor", help="extra training examples")
optparser.add_option("--extraTrainStyle", default="", dest="extraTrainStyle", help="extra training examples")
optparser.add_option("--extraTrainParse", default="split-mccc-preparsed", dest="extraTrainParse", help="Parse XML element name")
optparser.add_option("--extraTrainTokenization", default=None, dest="extraTrainTokenization", help="Tokenization XML element name")
#optparser.add_option("--extraTrainOnly", default=False, action="store_true", dest="extraTrainOnly", help="Only self training examples")
#optparser.add_option("-e", "--test", default=Settings.DevelFile, dest="testFile", help="Test file in interaction xml")
#optparser.add_option("-r", "--train", default=Settings.TrainFile, dest="trainFile", help="Train file in interaction xml")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-a", "--task", default="1", dest="task", help="task number")
optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default=None, dest="tokenization", help="Tokenization XML element name")
optparser.add_option("-m", "--mode", default="BOTH", dest="mode", help="MODELS (recalculate SVM models), GRID (parameter grid search) or BOTH")
# Classifier
optparser.add_option("-c", "--classifier", default="Cls", dest="classifier", help="")
optparser.add_option("--csc", default="", dest="csc", help="")
# Example builders
optparser.add_option("-f", "--triggerExampleBuilder", default="GeneralEntityTypeRecognizerGztr", dest="triggerExampleBuilder", help="")
optparser.add_option("-g", "--edgeExampleBuilder", default="MultiEdgeExampleBuilder", dest="edgeExampleBuilder", help="")
# Feature params
optparser.add_option("--triggerStyle", default=None, dest="triggerStyle", help="")
optparser.add_option("--edgeStyle", default=None, dest="edgeStyle", help="")
# Id sets
optparser.add_option("-v", "--triggerIds", default=None, dest="triggerIds", help="Trigger detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
optparser.add_option("-w", "--edgeIds", default=None, dest="edgeIds", help="Edge detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
# Parameters to optimize
optparser.add_option("-x", "--triggerParams", default="1000,5000,10000,20000,50000,80000,100000,150000,180000,200000,250000,300000,350000,500000,1000000", dest="triggerParams", help="Trigger detector c-parameter values")
optparser.add_option("-y", "--recallAdjustParams", default="0.5,0.6,0.65,0.7,0.85,1.0,1.1,1.2", dest="recallAdjustParams", help="Recall adjuster parameter values")
optparser.add_option("-z", "--edgeParams", default="5000,7500,10000,20000,25000,27500,28000,29000,30000,35000,40000,50000,60000,65000", dest="edgeParams", help="Edge detector c-parameter values")
optparser.add_option("--uParams", default="1,10,100,500,1000,1500,2500,5000,10000,20000,50000,80000,100000", dest="uParams", help="Unmerging c-parameter values")
optparser.add_option("--downSampleTrain", default=1.0, type="float", dest="downSampleTrain", help="")
optparser.add_option("--downSampleSeed", default=1, type="int", dest="downSampleSeed", help="")
optparser.add_option("--fullGrid", default=False, action="store_true", dest="fullGrid", help="Full grid search for parameters")
# Shared task evaluation
#optparser.add_option("-s", "--sharedTask", default=True, action="store_false", dest="sharedTask", help="Do Shared Task evaluation")
optparser.add_option("--password", default=None, dest="password", help="password or prompt")
optparser.add_option("--noLog", default=False, action="store_true", dest="noLog", help="")
optparser.add_option("--noTestSet", default=False, action="store_true", dest="noTestSet", help="")
optparser.add_option("--clearAll", default=False, action="store_true", dest="clearAll", help="Delete all files")
optparser.add_option("-u", "--unmerging", default=False, action="store_true", dest="unmerging", help="SVM unmerging")
# Task 3
optparser.add_option("--speculationModel", default=os.path.expanduser("~/biotext/BioNLP2011/tests/task3/task3TrainGE-EPI-ID/speculation-models/model-c_150000"), dest="speculationModel", help="SVM-multiclass speculation model")
optparser.add_option("--negationModel", default=os.path.expanduser("~/biotext/BioNLP2011/tests/task3/task3TrainGE-EPI-ID/negation-models/model-c_16000"), dest="negationModel", help="SVM-multiclass negation model")
optparser.add_option("--task3Ids", default=os.path.expanduser("~/biotext/BioNLP2011/tests/task3/task3TrainGE-EPI-ID/genia-task3-ids"), dest="task3Ids", help="Speculation & negation SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
(options, args) = optparser.parse_args()

if options.password != None and options.password.lower() == "prompt":
    options.password = raw_input("password:")

# Check options
assert options.mode in ["EXAMPLES", "MODELS", "FINAL", "BOTH", "DOWNLOAD", "POST-DOWNLOAD", "UNMERGING", "GRID", "POST-GRID"]
if options.classify:
    print "Classifying with existing models"
    options.mode = "POST-GRID"
assert options.output != None
assert options.task in ["OLD.1", "OLD.2", "CO", "REL", "GE", "GE.1", "GE.2", "EPI", "ID", "BB"]
subTask = 2
if "." in options.task:
    options.task, subTask = options.task.split(".")
    subTask = int(subTask)
#dataPath = "/home/jari/biotext/BioNLP2011/data/main-tasks/"
if options.task == "REL":
    dataPath = os.path.expanduser("~/biotext/BioNLP2011/data/REL/")
    TRAIN_FILE = dataPath + "rel-train.xml"
    TEST_FILE = dataPath + "rel-devel.xml"
    EVERYTHING_FILE = dataPath + "rel-devel-and-train.xml"
    FINAL_TEST_FILE = dataPath + "rel-test.xml"
elif options.task == "CO":
    dataPath = os.path.expanduser("~/biotext/BioNLP2011/data/CO/")
    TRAIN_FILE = dataPath + "co-train.xml"
    TEST_FILE = dataPath + "co-devel.xml"
    EVERYTHING_FILE = dataPath + "co-devel-and-train.xml"
    FINAL_TEST_FILE = dataPath + "co-test.xml"
else:
    dataPath = os.path.expanduser("~/biotext/BioNLP2011/data/main-tasks/")
    TRAIN_FILE = dataPath + options.task + "/" + options.task + "-train-nodup" + options.extraTag + ".xml"
    TEST_FILE = dataPath + options.task + "/" + options.task + "-devel-nodup" + options.extraTag + ".xml"
    EVERYTHING_FILE = dataPath + options.task + "/" + options.task + "-devel-and-train-nodup" + options.extraTag + ".xml"
    FINAL_TEST_FILE = dataPath + options.task + "/" + options.task + "-test.xml" # test set never uses extratag
# Optional overrides for input files
if options.trainFile != None: TRAIN_FILE = options.trainFile
if options.develFile != None: TEST_FILE = options.develFile
if options.everythingFile != None: EVERYTHING_FILE = options.everythingFile
if options.testFile != None: FINAL_TEST_FILE = options.testFile

exec "CLASSIFIER = " + options.classifier

# Main settings
PARSE=options.parse
TOK=options.tokenization
PARSE_TAG = PARSE
#TRAIN_FILE = options.trainFile
#TEST_FILE = options.testFile

# Example generation parameters
if options.edgeStyle != None:
    EDGE_FEATURE_PARAMS="style:"+options.edgeStyle
else:
    if options.task in ["OLD", "GE"]:
        EDGE_FEATURE_PARAMS="style:trigger_features,typed,directed,no_linear,entities,genia_limits,noMasking,maxFeatures"
        if subTask == 1:
            EDGE_FEATURE_PARAMS += ",genia_task1"
    elif options.task in ["BB"]:
        EDGE_FEATURE_PARAMS="style:trigger_features,typed,directed,no_linear,entities,bb_limits,noMasking,maxFeatures"
    elif options.task == "EPI":
        EDGE_FEATURE_PARAMS="style:trigger_features,typed,directed,no_linear,entities,epi_limits,noMasking,maxFeatures"
    elif options.task == "ID":
        EDGE_FEATURE_PARAMS="style:trigger_features,typed,directed,no_linear,entities,id_limits,noMasking,maxFeatures"
    elif options.task == "REL":
        EDGE_FEATURE_PARAMS="trigger_features,typed,directed,no_linear,entities,noMasking,maxFeatures,rel_limits,rel_features"
    elif options.task == "CO":
        EDGE_FEATURE_PARAMS="trigger_features,typed,directed,no_linear,entities,noMasking,maxFeatures,co_limits"
    else:
        EDGE_FEATURE_PARAMS="style:trigger_features,typed,directed,no_linear,entities,noMasking,maxFeatures"
if options.triggerStyle != None:  
    TRIGGER_FEATURE_PARAMS="style:"+options.triggerStyle #"style:typed"
else:
    TRIGGER_FEATURE_PARAMS="style:typed"
    if options.task in ["OLD", "GE"] and subTask == 1:
        TRIGGER_FEATURE_PARAMS += ",genia_task1"
    elif options.task in ["BB"]:
        TRIGGER_FEATURE_PARAMS += ",bb_features,build_for_nameless,wordnet"
    elif options.task == "REL":
        TRIGGER_FEATURE_PARAMS += ",rel_features"
        options.edgeParams = "10,100,1000,5000,7500,10000,20000,25000,28000,50000,60000,65000,100000,500000,1000000"
    elif options.task == "CO":
        options.triggerExampleBuilder = "PhraseTriggerExampleBuilder"
        options.edgeParams = "10,100,1000,5000,7500,10000,20000,25000,28000,50000,60000,65000,100000,500000,1000000"
        options.recallAdjustParams = "0.8,0.9,0.95,1.0"
UNMERGING_IDS = "unmerging-ids"
UNMERGING_CLASSIFIER_PARAMS="c:" + options.uParams
UNMERGING_FEATURE_PARAMS="style:typed"

boosterParams = [float(i) for i in options.recallAdjustParams.split(",")]
if options.task == "CO":
    BINARY_RECALL_MODE = True
else:
    BINARY_RECALL_MODE = False

# These commands will be in the beginning of most pipelines
WORKDIR=options.output

# CSC Settings
CSC_WORKDIR = os.path.join("CSCConnection",WORKDIR.lstrip("/"))
if "," in options.csc:
    options.csc = options.csc.split(",")
else:
    options.csc = [options.csc]
if options.clearAll and "clear" not in options.csc:
    options.csc.append("clear")
if "local" not in options.csc:
    CSC_CLEAR = False
    if "clear" in options.csc: CSC_CLEAR = True
    if "louhi" in options.csc:
        CSC_ACCOUNT="jakrbj@louhi.csc.fi"
    else:
        CSC_ACCOUNT="jakrbj@murska.csc.fi"

# Start logging
workdir(WORKDIR, options.clearAll) # Select a working directory, optionally remove existing files
if not options.noLog:
    log() # Start logging into a file in working directory

# Make downsampling for learning curve
downSampleTag = "-r" + str(options.downSampleTrain) + "_s" + str(options.downSampleSeed)
newTrainFile = makeSubset(TRAIN_FILE, options.task + "-train-nodup" + options.extraTag + downSampleTag + ".xml", options.downSampleTrain, options.downSampleSeed)
makeSubset(TRAIN_FILE.replace("-nodup", ""), options.task + "-train" + options.extraTag + downSampleTag + ".xml", options.downSampleTrain, options.downSampleSeed)
TRAIN_FILE = newTrainFile

if subTask != None:
    print >> sys.stderr, "Task:", options.task + "." + str(subTask)
else:
    print >> sys.stderr, "Task:", options.task
print >> sys.stderr, "Edge params:", EDGE_FEATURE_PARAMS
print >> sys.stderr, "Trigger params:", TRIGGER_FEATURE_PARAMS
TRIGGER_EXAMPLE_BUILDER = eval(options.triggerExampleBuilder)
EDGE_EXAMPLE_BUILDER = eval(options.edgeExampleBuilder)

# Pre-calculate all the required SVM models
TRIGGER_IDS = "trigger-ids"
EDGE_IDS = "edge-ids"
TRIGGER_TRAIN_EXAMPLE_FILE = "trigger-train-examples-"+PARSE_TAG+".gz"
TRIGGER_TEST_EXAMPLE_FILE = "trigger-test-examples-"+PARSE_TAG+".gz"
TRIGGER_EVERYTHING_EXAMPLE_FILE = "trigger-everything-examples-"+PARSE_TAG+".gz"
TRIGGER_CLASSIFIER_PARAMS="c:" + options.triggerParams
EDGE_TRAIN_EXAMPLE_FILE = "edge-train-examples-"+PARSE_TAG+".gz"
EDGE_TEST_EXAMPLE_FILE = "edge-test-examples-"+PARSE_TAG+".gz"
EDGE_EVERYTHING_EXAMPLE_FILE = "edge-everything-examples-"+PARSE_TAG+".gz"
EDGE_CLASSIFIER_PARAMS="c:" + options.edgeParams
if options.mode in ["BOTH", "EXAMPLES", "MODELS"]:
    if options.mode in ["BOTH", "EXAMPLES"]:
        if options.triggerIds != None:
            TRIGGER_IDS = copyIdSetsToWorkdir(options.triggerIds)
        if options.edgeIds != None:
            EDGE_IDS = copyIdSetsToWorkdir(options.edgeIds)
    
        ###############################################################################
        # Edge example generation
        ###############################################################################
        print >> sys.stderr, "Edge examples for parse", PARSE_TAG  
        EDGE_EXAMPLE_BUILDER.run(TEST_FILE, EDGE_TEST_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
        EDGE_EXAMPLE_BUILDER.run(TRAIN_FILE, EDGE_TRAIN_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
        if not options.noTestSet:
            EDGE_EXAMPLE_BUILDER.run(EVERYTHING_FILE, EDGE_EVERYTHING_EXAMPLE_FILE, PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
        if options.extraTrain != None and "edge" in options.extraTrainFor:
            EDGE_EXAMPLE_BUILDER.run(options.extraTrain, EDGE_TRAIN_EXAMPLE_FILE, options.extraTrainParse, options.extraTrainTokenization, EDGE_FEATURE_PARAMS+options.extraTrainStyle+",iterate", EDGE_IDS, appendIndex=1000)
            if not options.noTestSet:
                EDGE_EXAMPLE_BUILDER.run(options.extraTrain, EDGE_EVERYTHING_EXAMPLE_FILE, options.extraTrainParse, options.extraTrainTokenization, EDGE_FEATURE_PARAMS+options.extraTrainStyle+",iterate", EDGE_IDS, appendIndex=1000)
                
        ###############################################################################
        # Trigger example generation
        ###############################################################################
        print >> sys.stderr, "Trigger examples for parse", PARSE_TAG   
        TRIGGER_EXAMPLE_BUILDER.run(TEST_FILE, TRIGGER_TEST_EXAMPLE_FILE, PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
        TRIGGER_EXAMPLE_BUILDER.run(TRAIN_FILE, TRIGGER_TRAIN_EXAMPLE_FILE, PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
        if not options.noTestSet:
            TRIGGER_EXAMPLE_BUILDER.run(EVERYTHING_FILE, TRIGGER_EVERYTHING_EXAMPLE_FILE, PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
        if options.extraTrain != None and "trigger" in options.extraTrainFor:
            TRIGGER_EXAMPLE_BUILDER.run(options.extraTrain, TRIGGER_TRAIN_EXAMPLE_FILE, options.extraTrainParse, options.extraTrainTokenization, TRIGGER_FEATURE_PARAMS+options.extraTrainStyle+",iterate", TRIGGER_IDS, appendIndex=1000)
            if not options.noTestSet:
                TRIGGER_EXAMPLE_BUILDER.run(options.extraTrain, TRIGGER_EVERYTHING_EXAMPLE_FILE, options.extraTrainParse, options.extraTrainTokenization, TRIGGER_FEATURE_PARAMS+options.extraTrainStyle+",iterate", TRIGGER_IDS, appendIndex=1000)
    else:
        if options.triggerIds != None:
            TRIGGER_IDS = os.path.basename(options.triggerIds)
        if options.edgeIds != None:
            EDGE_IDS = os.path.basename(options.edgeIds)
    
    ###############################################################################
    # Trigger models
    ###############################################################################
    print >> sys.stderr, "Trigger models for parse", PARSE_TAG
    c = None
    if "local" not in options.csc:
        c = CSCConnection(CSC_WORKDIR+"/trigger-models", CSC_ACCOUNT, CSC_CLEAR, password=options.password)
    optimize(CLASSIFIER, Ev, TRIGGER_TRAIN_EXAMPLE_FILE, TRIGGER_TEST_EXAMPLE_FILE,\
        TRIGGER_IDS+".class_names", TRIGGER_CLASSIFIER_PARAMS, "trigger-models", None, c, False, steps="SUBMIT")
    
    ###############################################################################
    # Edge models
    ###############################################################################
    print >> sys.stderr, "Edge models for parse", PARSE_TAG
    c = None
    if "local" not in options.csc:
        c = CSCConnection(CSC_WORKDIR+"/edge-models", CSC_ACCOUNT, CSC_CLEAR, password=options.password)
    optimize(CLASSIFIER, Ev, EDGE_TRAIN_EXAMPLE_FILE, EDGE_TEST_EXAMPLE_FILE,\
        EDGE_IDS+".class_names", EDGE_CLASSIFIER_PARAMS, "edge-models", None, c, False, steps="SUBMIT")
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
bestTriggerModel = "best-trigger-model.gz"
bestEdgeModel = "best-edge-model.gz"
bestUnmergingModel = "best-unmerging-model.gz"
if options.mode in ["BOTH", "FINAL", "DOWNLOAD", "POST-DOWNLOAD", "UNMERGING", "GRID", "POST-GRID"]:
    if options.mode not in ["GRID", "POST-GRID"]:
        # Get edge and trigger models from CSC
        if options.mode != "UNMERGING":
            if options.mode != "POST-DOWNLOAD":
                print >> sys.stderr, "------------ Downloading best trigger/edge models ------------"
                c = None
                if "local" not in options.csc:
                    c = CSCConnection(CSC_WORKDIR+"/trigger-models", CSC_ACCOUNT, False, password=options.password)
                bestTriggerModelFull = optimize(CLASSIFIER, Ev, TRIGGER_TRAIN_EXAMPLE_FILE, TRIGGER_TEST_EXAMPLE_FILE,\
                    TRIGGER_IDS+".class_names", TRIGGER_CLASSIFIER_PARAMS, "trigger-models", None, c, options.fullGrid, steps="RESULTS")
                bestTriggerModel = updateModel(bestTriggerModelFull, "best-trigger-model.gz")
                c = None
                if "local" not in options.csc:
                    c = CSCConnection(CSC_WORKDIR+"/edge-models", CSC_ACCOUNT, False, password=options.password)
                bestEdgeModelFull = optimize(CLASSIFIER, Ev, EDGE_TRAIN_EXAMPLE_FILE, EDGE_TEST_EXAMPLE_FILE,\
                    EDGE_IDS+".class_names", EDGE_CLASSIFIER_PARAMS, "edge-models", None, c, options.fullGrid, steps="RESULTS")
                bestEdgeModel = updateModel(bestEdgeModelFull, "best-edge-model.gz")
            
            # POST-DOWNLOAD
            ###############################################################################
            # Submit final models
            ###############################################################################
            if options.classifier != "ACCls" and (not options.noTestSet) and not options.fullGrid:
                print >> sys.stderr, "------------ Submitting final models ------------"
                print >> sys.stderr, "Everything models for parse", PARSE_TAG
                c = None
                if "local" not in options.csc: c = CSCConnection(CSC_WORKDIR+"/everything-trigger-models", CSC_ACCOUNT, True, password=options.password)
                optimize(CLASSIFIER, Ev, TRIGGER_EVERYTHING_EXAMPLE_FILE, TRIGGER_TEST_EXAMPLE_FILE,\
                    TRIGGER_IDS+".class_names", "c:"+getParameter(bestTriggerModel).split("_")[-1], "everything-trigger-models", None, c, False, steps="SUBMIT")
                if "local" not in options.csc: c = CSCConnection(CSC_WORKDIR+"/everything-edge-models", CSC_ACCOUNT, True, password=options.password)
                optimize(CLASSIFIER, Ev, EDGE_EVERYTHING_EXAMPLE_FILE, EDGE_TEST_EXAMPLE_FILE,\
                    EDGE_IDS+".class_names", "c:"+getParameter(bestEdgeModel).split("_")[-1], "everything-edge-models", None, c, False, steps="SUBMIT")
                print >> sys.stderr, "Everything models submitted"
        # UNMERGING
        ###############################################################################
        # Unmerging learning
        ###############################################################################
        if options.unmerging:
            bestTriggerModel = "best-trigger-model.gz"
            bestEdgeModel = "best-edge-model.gz"
            bestUnmergingModel = "best-unmerging-model.gz"
            UNMERGING_IDS = "unmerging-ids"
            print >> sys.stderr, "------------ Unmerging models ------------"
            # Self-classified train data for unmerging
            TRIGGER_EXAMPLE_BUILDER.run(TRAIN_FILE, "unmerging-extra-trigger-examples", PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
            if bestTriggerModel != None: print >> sys.stderr, "best-trigger-model=", os.path.realpath("best-trigger-model.gz")
            CLASSIFIER.test("unmerging-extra-trigger-examples", bestTriggerModel, "unmerging-extra-trigger-classifications")
            Ev.evaluate("unmerging-extra-trigger-examples", "unmerging-extra-trigger-classifications", TRIGGER_IDS+".class_names")
            xml = BioTextExampleWriter.write("unmerging-extra-trigger-examples", "unmerging-extra-trigger-classifications", TRAIN_FILE, "unmerging-extra-triggers.xml", TRIGGER_IDS+".class_names", PARSE, TOK)
            xml = ix.splitMergedElements(xml, None)
            xml = ix.recalculateIds(xml, None, True)
            EDGE_EXAMPLE_BUILDER.run(xml, "unmerging-extra-edge-examples", PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
            if bestEdgeModel != None: print >> sys.stderr, "best-edge-model=", os.path.realpath("best-edge-model.gz")
            CLASSIFIER.test("unmerging-extra-edge-examples", bestEdgeModel, "unmerging-extra-edge-classifications")
            Ev.evaluate("unmerging-extra-edge-examples", "unmerging-extra-edge-classifications", EDGE_IDS+".class_names")
            xml = BioTextExampleWriter.write("unmerging-extra-edge-examples", "unmerging-extra-edge-classifications", xml, None, EDGE_IDS+".class_names", PARSE, TOK)
            xml = ix.splitMergedElements(xml, None)
            xml = ix.recalculateIds(xml, "unmerging-extra-edges.xml", True)
            EvaluateInteractionXML.run(Ev, xml, TRAIN_FILE, PARSE, TOK)
            ###############################################################################
            # Unmerging example generation
            ###############################################################################
            UNMERGING_TRAIN_EXAMPLE_FILE = "unmerging-train-examples-"+PARSE_TAG+".gz"
            UNMERGING_TEST_EXAMPLE_FILE = "unmerging-test-examples-"+PARSE_TAG+".gz"
            print >> sys.stderr, "Unmerging examples for parse", PARSE_TAG
            GOLD_TEST_FILE = TEST_FILE.replace("-nodup", "")
            GOLD_TRAIN_FILE = TRAIN_FILE.replace("-nodup", "")
            UnmergingExampleBuilder.run(TEST_FILE, GOLD_TEST_FILE, UNMERGING_TEST_EXAMPLE_FILE, PARSE, TOK, UNMERGING_FEATURE_PARAMS, UNMERGING_IDS)
#            # Build extra test examples
#            print >> sys.stderr, "Extra test examples"
#            # NOTE: Temporarily back to old data for replicating 110310 experiment
#            PRED_TEST_FILE = "/home/jari/biotext/BioNLP2011/tests/main-tasks/OLD/full/fulltest110308/flat-0.85.xml"
#            #PRED_TEST_FILE = "/home/jari/biotext/BioNLP2011/tests/FINAL/GE-full-110310/flat-0.7.xml"
#            UnmergingExampleBuilder.run(PRED_TEST_FILE, GOLD_TEST_FILE, UNMERGING_TEST_EXAMPLE_FILE, PARSE, TOK, UNMERGING_FEATURE_PARAMS, UNMERGING_IDS, append=True)
            UnmergingExampleBuilder.run(TRAIN_FILE, GOLD_TRAIN_FILE, UNMERGING_TRAIN_EXAMPLE_FILE, PARSE, TOK, UNMERGING_FEATURE_PARAMS, UNMERGING_IDS)
            UnmergingExampleBuilder.run(xml, GOLD_TRAIN_FILE, UNMERGING_TRAIN_EXAMPLE_FILE, PARSE, TOK, UNMERGING_FEATURE_PARAMS, UNMERGING_IDS, append=True)
            xml = None
            #UnmergingExampleBuilder.run("/home/jari/biotext/EventExtension/TrainSelfClassify/test-predicted-edges.xml", GOLD_TRAIN_FILE, UNMERGING_TRAIN_EXAMPLE_FILE, PARSE, TOK, UNMERGING_FEATURE_PARAMS, UNMERGING_IDS, append=True)
            ###############################################################################
            # Unmerging models
            ###############################################################################
            print >> sys.stderr, "Unmerging models for parse", PARSE_TAG
            c = None
            if "local" not in options.csc: c = CSCConnection(CSC_WORKDIR+"/unmerging-models", CSC_ACCOUNT, CSC_CLEAR)
            bestUnmergingModelFull = optimize(CLASSIFIER, Ev, UNMERGING_TRAIN_EXAMPLE_FILE, UNMERGING_TEST_EXAMPLE_FILE,\
                    UNMERGING_IDS+".class_names", UNMERGING_CLASSIFIER_PARAMS, "unmerging-models", None, c, False, steps="BOTH")
            bestUnmergingModel = updateModel(bestUnmergingModelFull, "best-unmerging-model.gz")
            print >> sys.stderr, "------------ Unmerging models done ------------"
    else:
        bestTriggerModel = "best-trigger-model.gz"
        bestEdgeModel = "best-edge-model.gz"
        bestUnmergingModel = "best-unmerging-model.gz"

    # GOTO: GRID
    if options.mode != "POST-GRID":
        print >> sys.stderr, "--------- Booster parameter search ---------"
        # Build trigger examples
        if not options.fullGrid:
            TRIGGER_EXAMPLE_BUILDER.run(TEST_FILE, "test-trigger-examples", PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
            CLASSIFIER.test("test-trigger-examples", bestTriggerModel, "test-trigger-classifications")
            if bestTriggerModel != None:
                print >> sys.stderr, "best-trigger-model=", os.path.realpath("best-trigger-model.gz")
            evaluator = Ev.evaluate("test-trigger-examples", "test-trigger-classifications", TRIGGER_IDS+".class_names")
            BioTextExampleWriter.write("test-trigger-examples", "test-trigger-classifications", TEST_FILE, "trigger-pred-best.xml", TRIGGER_IDS+".class_names", PARSE, TOK)
        
        count = 0
        bestResults = None
        if options.fullGrid:
            # Parameters to optimize
            ALL_PARAMS={
                "trigger":[int(i) for i in options.triggerParams.split(",")], 
                "booster":[float(i) for i in options.recallAdjustParams.split(",")], 
                "edge":[int(i) for i in options.edgeParams.split(",")] }
        else:
            ALL_PARAMS={"trigger":["BEST"],
                        "booster":[float(i) for i in options.recallAdjustParams.split(",")],
                        "edge":["BEST"]}
        paramCombinations = getParameterCombinations(ALL_PARAMS)
        #for boost in boosterParams:
        prevTriggerParam = "BEST"
        EDGE_MODEL_STEM = "edge-models/model-c_"
        TRIGGER_MODEL_STEM = "trigger-models/model-c_"
        for params in paramCombinations:
            print >> sys.stderr, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            print >> sys.stderr, "Processing params", str(count+1) + "/" + str(len(paramCombinations)), params
            print >> sys.stderr, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            
            # Triggers
            if params["trigger"] != prevTriggerParam:
                # Build trigger examples
                print >> sys.stderr, "Rebuilding trigger examples for parameter", params["trigger"]
                TRIGGER_EXAMPLE_BUILDER.run(TEST_FILE, "test-trigger-examples", PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
                CLASSIFIER.test("test-trigger-examples", TRIGGER_MODEL_STEM+str(params["trigger"])+".gz", "test-trigger-classifications")
                evaluator = Ev.evaluate("test-trigger-examples", "test-trigger-classifications", TRIGGER_IDS+".class_names")
                BioTextExampleWriter.write("test-trigger-examples", "test-trigger-classifications", TEST_FILE, "trigger-pred-best.xml", TRIGGER_IDS+".class_names", PARSE, TOK)
            prevTriggerParam = params["trigger"]
            
            # Boost
            xml = RecallAdjust.run("trigger-pred-best.xml", params["booster"], None, binary=BINARY_RECALL_MODE)
            xml = ix.splitMergedElements(xml, None)
            xml = ix.recalculateIds(xml, None, True)
            
            # Build edge examples
            if options.classifier == "ACCls":
                EDGE_EXAMPLE_BUILDER.run(xml, "test-edge-examples", PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS, gold=TEST_FILE)
            else:
                EDGE_EXAMPLE_BUILDER.run(xml, "test-edge-examples", PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
            # Classify with pre-defined model
            if params["edge"] == "BEST":
                if bestEdgeModel != None:
                    print >> sys.stderr, "best-edge-model=", os.path.realpath("best-edge-model.gz")
                CLASSIFIER.test("test-edge-examples", bestEdgeModel, "test-edge-classifications")
            else:
                CLASSIFIER.test("test-edge-examples", EDGE_MODEL_STEM+str(params["edge"])+".gz", "test-edge-classifications")
            # Write to interaction xml
            evaluator = Ev.evaluate("test-edge-examples", "test-edge-classifications", EDGE_IDS+".class_names")
            if evaluator.getData().getTP() + evaluator.getData().getFP() > 0:
                #xml = ExampleUtils.writeToInteractionXML("test-edge-examples", "test-edge-classifications", xml, None, EDGE_IDS+".class_names", PARSE, TOK)
                xml = BioTextExampleWriter.write("test-edge-examples", "test-edge-classifications", xml, None, EDGE_IDS+".class_names", PARSE, TOK)
                xml = ix.splitMergedElements(xml, None)
                #xml = ix.recalculateIds(xml, "flat-" + str(boost) + ".xml.gz", True)
                xml = ix.recalculateIds(xml, "flat-devel.xml.gz", True)
                
                # EvaluateInteractionXML differs from the previous evaluations in that it can
                # be used to compare two separate GifXML-files. One of these is the gold file,
                # against which the other is evaluated by heuristically matching triggers and
                # edges. Note that this evaluation will differ somewhat from the previous ones,
                # which evaluate on the level of examples.
                EIXMLResult = EvaluateInteractionXML.run(Ev, xml, TEST_FILE, PARSE, TOK)
                # Convert to ST-format
                if os.path.exists("flat-devel-geniaformat"):
                    shutil.rmtree("flat-devel-geniaformat")
                STFormat.ConvertXML.toSTFormat(xml, "flat-devel-geniaformat", getA2FileTag(options.task, subTask))
                
                if options.task in ["OLD", "GE", "EPI", "ID"]:
                    assert options.unmerging
                    if options.unmerging:
                        if os.path.exists("unmerged-devel-geniaformat"):
                            shutil.rmtree("unmerged-devel-geniaformat")
                        print >> sys.stderr, "--------- ML Unmerging ---------"
                        GOLD_TEST_FILE = TEST_FILE.replace("-nodup", "")
                        UnmergingExampleBuilder.run("flat-devel.xml.gz", GOLD_TEST_FILE, "unmerging-grid-examples", PARSE, TOK, UNMERGING_FEATURE_PARAMS, UNMERGING_IDS)
                        CLASSIFIER.test("unmerging-grid-examples", bestUnmergingModel, "unmerging-grid-classifications")
                        unmergedXML = BioTextExampleWriter.write("unmerging-grid-examples", "unmerging-grid-classifications", "flat-devel.xml.gz", "unmerged-devel.xml.gz", UNMERGING_IDS+".class_names", PARSE, TOK)
                        STFormat.ConvertXML.toSTFormat(unmergedXML, "unmerged-devel-geniaformat", getA2FileTag(options.task, subTask))
                        if options.task == "OLD":
                            results = evaluateSharedTask("unmerged-devel-geniaformat", subTask)
                        elif options.task == "GE":
                            results = evaluateBioNLP11Genia("unmerged-devel-geniaformat", subTask)
                        elif options.task in ["EPI", "ID"]:
                            results = evaluateEPIorID("unmerged-devel-geniaformat", options.task)
                        else:
                            assert False
                        if options.task in ["OLD", "GE"]:
                            if bestResults == None or bestResults[1]["approximate"]["ALL-TOTAL"]["fscore"] < results["approximate"]["ALL-TOTAL"]["fscore"]:
                                bestResults = (params, results)
                        else:
                            if bestResults == None or bestResults[1]["TOTAL"]["fscore"] < results["TOTAL"]["fscore"]:
                                bestResults = (params, results)
                    if options.task in ["OLD"]: # rule-based unmerging
                        print >> sys.stderr, "--------- Rule based unmerging ---------"
                        # Post-processing
                        unmergedXML = unflatten(xml, PARSE, TOK)
                        # Output will be stored to the geniaformat-subdirectory, where will also be a
                        # tar.gz-file which can be sent to the Shared Task evaluation server.
                        #gifxmlToGenia(unmergedXML, "rulebased-unmerging-geniaformat", subTask)
                        if os.path.exists("rulebased-unmerging-geniaformat"):
                            shutil.rmtree("rulebased-unmerging-geniaformat")
                        STFormat.ConvertXML.toSTFormat(unmergedXML, "rulebased-unmerging-geniaformat", getA2FileTag(options.task, subTask))
                        # Evaluation of the Shared Task format
                        results = evaluateSharedTask("rulebased-unmerging-geniaformat", subTask)
                        #if bestResults == None or bestResults[1]["approximate"]["ALL-TOTAL"]["fscore"] < results["approximate"]["ALL-TOTAL"]["fscore"]:
                        #    bestResults = (boost, results)
                elif options.task == "BB":
                    results = evaluateBX("flat-devel-geniaformat", "BB")
                    if bestResults == None or results["fscore"]  > bestResults[1]["fscore"]:
                        bestResults = (params, results)
                else:
                    if bestResults == None or EIXMLResult.getData().fscore > bestResults[1].getData().fscore:
                        bestResults = (params, EIXMLResult)
            else:
                print >> sys.stderr, "No predicted edges"
            count += 1
        print >> sys.stderr, "Booster search complete"
        print >> sys.stderr, "Tested", count, "out of", count, "combinations"
        print >> sys.stderr, "Best parameters:", bestResults[0]
        saveBoostParam(bestResults[0]["booster"])
        if options.fullGrid: # define best models
            bestTriggerModel = updateModel((None, TRIGGER_MODEL_STEM+str(bestResults[0]["trigger"])+".gz", str(bestResults[0]["trigger"])), "best-trigger-model.gz")
            bestEdgeModel = updateModel((None, EDGE_MODEL_STEM+str(bestResults[0]["edge"])+".gz", str(bestResults[0]["edge"])), "best-edge-model.gz")
        if options.task in ["OLD", "GE"]:
            print >> sys.stderr, "Best result:", bestResults[1]
        # Final models with full grid
        if options.classifier != "ACCls" and (not options.noTestSet) and options.fullGrid:
            print >> sys.stderr, "------------ Submitting final models ------------"
            print >> sys.stderr, "Everything models for parse", PARSE_TAG
            c = None
            if "local" not in options.csc: c = CSCConnection(CSC_WORKDIR+"/everything-trigger-models", CSC_ACCOUNT, True, password=options.password)
            optimize(CLASSIFIER, Ev, TRIGGER_EVERYTHING_EXAMPLE_FILE, TRIGGER_TEST_EXAMPLE_FILE,\
                TRIGGER_IDS+".class_names", "c:"+getParameter(bestTriggerModel).split("_")[-1], "everything-trigger-models", None, c, False, steps="SUBMIT")
            if "local" not in options.csc: c = CSCConnection(CSC_WORKDIR+"/everything-edge-models", CSC_ACCOUNT, True, password=options.password)
            optimize(CLASSIFIER, Ev, EDGE_EVERYTHING_EXAMPLE_FILE, EDGE_TEST_EXAMPLE_FILE,\
                EDGE_IDS+".class_names", "c:"+getParameter(bestEdgeModel).split("_")[-1], "everything-edge-models", None, c, False, steps="SUBMIT")
            print >> sys.stderr, "Everything models submitted"
    
    # GOTO: POST-GRID
    if options.classify:
        # classify with existing models
        TRIGGER_IDS = copyIdSetsToWorkdir(os.path.join(options.classify, "trigger-ids"))
        EDGE_IDS = copyIdSetsToWorkdir(os.path.join(options.classify, "edge-ids"))
        UNMERGING_IDS = copyIdSetsToWorkdir(os.path.join(options.classify, "unmerging-ids"))
        bestTriggerModel = os.path.join(options.classify, "best-trigger-model")
        bestEdgeModel = os.path.join(options.classify, "best-edge-model")
        bestUnmergingModel = os.path.join(options.classify, "best-unmerging-model")
        bestBoost = float(getParameter(os.path.join(options.classify, "best-boost")))
    else:
        bestBoost = float(getParameter("best-boost"))
    ###############################################################################
    # Classify empty devel set
    ###############################################################################
    print >> sys.stderr, "--------- Classify empty devel set ---------"
    # Trigger Detection
    if options.classifier != "ACCls":
        TRIGGER_EXAMPLE_BUILDER.run(TEST_FILE.replace(".xml", "-empty.xml"), "empty-test-trigger-examples", PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
    else: # use the normal, non-empty data
        TRIGGER_EXAMPLE_BUILDER.run(TEST_FILE, "empty-test-trigger-examples", PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
    CLASSIFIER.test("empty-test-trigger-examples", bestTriggerModel, "empty-test-trigger-classifications")
    if bestTriggerModel != None: print >> sys.stderr, "best-trigger-model=", os.path.realpath("best-trigger-model")
    Ev.evaluate("empty-test-trigger-examples", "empty-test-trigger-classifications", TRIGGER_IDS+".class_names")
    xml = BioTextExampleWriter.write("empty-test-trigger-examples", "empty-test-trigger-classifications", TEST_FILE.replace(".xml", "-empty.xml"), "empty-triggers.xml", TRIGGER_IDS+".class_names", PARSE, TOK)
    # Boost
    xml = RecallAdjust.run(xml, bestBoost, None, binary=BINARY_RECALL_MODE)
    xml = ix.splitMergedElements(xml, None)
    xml = ix.recalculateIds(xml, None, True)
    # Edge Detection
    if options.classifier == "ACCls":
        EDGE_EXAMPLE_BUILDER.run(xml, "empty-test-edge-examples", PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS, gold=TEST_FILE)
    else:
        EDGE_EXAMPLE_BUILDER.run(xml, "empty-test-edge-examples", PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    if bestEdgeModel != None: print >> sys.stderr, "best-edge-model=", os.path.realpath("best-edge-model")
    CLASSIFIER.test("empty-test-edge-examples", bestEdgeModel, "empty-test-edge-classifications")
    Ev.evaluate("empty-test-edge-examples", "empty-test-edge-classifications", EDGE_IDS+".class_names")
    xml = BioTextExampleWriter.write("empty-test-edge-examples", "empty-test-edge-classifications", xml, None, EDGE_IDS+".class_names", PARSE, TOK)
    xml = ix.splitMergedElements(xml, None)
    xml = ix.recalculateIds(xml, "empty-edges.xml", True)
    # Unmerging
    if options.unmerging:
        if options.classifier != "ACCls":
            GOLD_TEST_FILE = None
        else:
            GOLD_TEST_FILE = TEST_FILE.replace("-nodup", "")
        UnmergingExampleBuilder.run(xml, GOLD_TEST_FILE, "unmerging-empty-examples", PARSE, TOK, UNMERGING_FEATURE_PARAMS, UNMERGING_IDS)
        CLASSIFIER.test("unmerging-empty-examples", bestUnmergingModel, "unmerging-empty-classifications")
        unmergedXML = BioTextExampleWriter.write("unmerging-empty-examples", "unmerging-empty-classifications", xml, "empty-unmerged.xml", UNMERGING_IDS+".class_names", PARSE, TOK)
        EMPTY_GENIAFORMAT_DIR = "empty-unmerged-geniaformat"
        STFormat.ConvertXML.toSTFormat(unmergedXML, EMPTY_GENIAFORMAT_DIR, getA2FileTag(options.task, subTask))
        xml = unmergedXML
    else:
        EMPTY_GENIAFORMAT_DIR = "empty-edges-geniaformat"
        STFormat.ConvertXML.toSTFormat(xml, EMPTY_GENIAFORMAT_DIR, getA2FileTag(options.task, subTask))
    print >> sys.stderr, "======== Evaluating empty devel set ========"
    EvaluateInteractionXML.run(Ev, xml, TEST_FILE, PARSE, TOK)
    if options.task == "OLD": evaluateSharedTask(EMPTY_GENIAFORMAT_DIR, subTask)
    elif options.task == "GE": evaluateBioNLP11Genia(EMPTY_GENIAFORMAT_DIR, subTask)
    elif options.task in ["EPI", "ID"]: evaluateEPIorID(EMPTY_GENIAFORMAT_DIR, options.task)
    elif options.task == "BB": evaluateBX(EMPTY_GENIAFORMAT_DIR, "BB")
    if options.task in ["OLD", "GE", "EPI", "ID"]:
        print >> sys.stderr, "======== Task 3 for empty devel set ========"
        if options.classifier == "ACCls":
            xml = task3Classify(CLASSIFIER, xml, options.speculationModel, options.negationModel, options.task3Ids, "empty", PARSE, goldXML=TEST_FILE)
        else:
            xml = task3Classify(CLASSIFIER, xml, options.speculationModel, options.negationModel, options.task3Ids, "empty", PARSE)
        STFormat.ConvertXML.toSTFormat(xml, EMPTY_GENIAFORMAT_DIR+"-task3", getA2FileTag(options.task, subTask))
        print >> sys.stderr, "======== Evaluating empty devel set (task 3) ========"
        EvaluateInteractionXML.run(Ev, xml, TEST_FILE, PARSE, TOK)
        if options.task == "OLD": evaluateSharedTask(EMPTY_GENIAFORMAT_DIR+"-task3", subTask)
        elif options.task == "GE": evaluateBioNLP11Genia(EMPTY_GENIAFORMAT_DIR+"-task3", subTask)
        elif options.task in ["EPI", "ID"]: evaluateEPIorID(EMPTY_GENIAFORMAT_DIR+"-task3", options.task)
        elif options.task == "BB": evaluateBX(EMPTY_GENIAFORMAT_DIR+"-task3", "BB")
    
    if options.classifier == "ACCls":
        print >> sys.stderr, "No test set classification with AllCorrectClassifier"
        sys.exit()
    ###############################################################################
    # Classify test set
    ###############################################################################
    if options.noTestSet:
        sys.exit()
    print >> sys.stderr, "--------- Classify test set ---------"
    if not options.classify:
        print >> sys.stderr, "Downloading everything models for parse", PARSE_TAG
        c = None
        if "local" not in options.csc: c = CSCConnection(CSC_WORKDIR+"/everything-trigger-models", CSC_ACCOUNT, False, password=options.password)
        bestTriggerModel = optimize(CLASSIFIER, Ev, TRIGGER_EVERYTHING_EXAMPLE_FILE, TRIGGER_TEST_EXAMPLE_FILE,\
            TRIGGER_IDS+".class_names", "c:"+getParameter(bestTriggerModel).split("_")[-1], "everything-trigger-models", None, c, False, steps="RESULTS")[1]
        if "local" not in options.csc: c = CSCConnection(CSC_WORKDIR+"/everything-edge-models", CSC_ACCOUNT, False, password=options.password)
        bestEdgeModel = optimize(CLASSIFIER, Ev, EDGE_EVERYTHING_EXAMPLE_FILE, EDGE_TEST_EXAMPLE_FILE,\
            EDGE_IDS+".class_names", "c:"+getParameter(bestEdgeModel).split("_")[-1], "everything-edge-models", None, c, False, steps="RESULTS")[1]
    else:
        # classify with existing models
        bestTriggerModel = None
        for filename in os.listdir(options.classify + "/everything-trigger-models"):
            if filename.startswith("model"):
                bestTriggerModel = os.path.join(options.classify, "everything-trigger-models", filename)
                break
        bestEdgeModel = None
        for filename in os.listdir(options.classify + "/everything-edge-models"):
            if filename.startswith("model"):
                bestEdgeModel = os.path.join(options.classify, "everything-edge-models", filename)
                break
    print >> sys.stderr, "Building test-set examples"
    # Trigger Detection
    TRIGGER_EXAMPLE_BUILDER.run(FINAL_TEST_FILE, "final-test-trigger-examples", PARSE, TOK, TRIGGER_FEATURE_PARAMS, TRIGGER_IDS)
    CLASSIFIER.test("final-test-trigger-examples", bestTriggerModel, "final-test-trigger-classifications")
    if bestTriggerModel != None: print >> sys.stderr, "best-trigger-model=", os.path.realpath("best-trigger-model")
    Ev.evaluate("final-test-trigger-examples", "final-test-trigger-classifications", TRIGGER_IDS+".class_names")
    xml = BioTextExampleWriter.write("final-test-trigger-examples", "final-test-trigger-classifications", FINAL_TEST_FILE, "final-triggers.xml", TRIGGER_IDS+".class_names", PARSE, TOK)
    # Boost
    xml = RecallAdjust.run(xml, bestBoost, None, binary=BINARY_RECALL_MODE)
    xml = ix.splitMergedElements(xml, None)
    xml = ix.recalculateIds(xml, None, True)
    # Edge Detection
    EDGE_EXAMPLE_BUILDER.run(xml, "final-test-edge-examples", PARSE, TOK, EDGE_FEATURE_PARAMS, EDGE_IDS)
    if bestEdgeModel != None: print >> sys.stderr, "best-edge-model=", os.path.realpath("best-edge-model")
    CLASSIFIER.test("final-test-edge-examples", bestEdgeModel, "final-test-edge-classifications")
    Ev.evaluate("final-test-edge-examples", "final-test-edge-classifications", EDGE_IDS+".class_names")
    xml = BioTextExampleWriter.write("final-test-edge-examples", "final-test-edge-classifications", xml, None, EDGE_IDS+".class_names", PARSE, TOK)
    xml = ix.splitMergedElements(xml, None)
    xml = ix.recalculateIds(xml, "final-edges.xml.gz", True)
    STFormat.ConvertXML.toSTFormat(xml, "final-edges-geniaformat", getA2FileTag(options.task, subTask))
    # Unmerging
    if options.unmerging:
        GOLD_TEST_FILE = FINAL_TEST_FILE.replace("-nodup", "")
        UnmergingExampleBuilder.run(xml, GOLD_TEST_FILE, "unmerging-final-examples", PARSE, TOK, UNMERGING_FEATURE_PARAMS, UNMERGING_IDS)
        CLASSIFIER.test("unmerging-final-examples", bestUnmergingModel, "unmerging-final-classifications")
        unmergedXML = BioTextExampleWriter.write("unmerging-final-examples", "unmerging-final-classifications", xml, "final-unmerged.xml.gz", UNMERGING_IDS+".class_names", PARSE, TOK)
        STFormat.ConvertXML.toSTFormat(unmergedXML, "final-unmerged-geniaformat", getA2FileTag(options.task, subTask))
        xml = unmergedXML
        # Sanity Check
        STFormat.Compare.compare("final-unmerged-geniaformat", EMPTY_GENIAFORMAT_DIR, getA2FileTag(options.task, subTask))
    else:
        # Sanity Check
        STFormat.Compare.compare("final-edges-geniaformat", EMPTY_GENIAFORMAT_DIR, getA2FileTag(options.task, subTask))
    # Task 3
    if options.task in ["OLD", "GE", "EPI", "ID"]:
        print >> sys.stderr, "======== Task 3 for test set ========"
        xml = task3Classify(CLASSIFIER, xml, options.speculationModel, options.negationModel, options.task3Ids, "final", PARSE)
        STFormat.ConvertXML.toSTFormat(xml, "final-task3", getA2FileTag(options.task, subTask))
        # Sanity Check
        STFormat.Compare.compare("final-task3", EMPTY_GENIAFORMAT_DIR+"-task3", getA2FileTag(options.task, subTask))
