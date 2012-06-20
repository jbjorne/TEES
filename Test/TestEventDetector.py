# Optimize parameters for event detection and produce event and trigger model files

# most imports are defined in Pipeline
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../CommonUtils") # new CommonUtils
from InteractionXML.DeleteElements import getEmptyCorpus
#from Pipeline import *
import Utils.Stream as Stream
from Utils.Connection.Unix import getConnection
import STFormat.ConvertXML
import STFormat.Compare
import subprocess
import shutil
import atexit
from Detectors.EventDetector import EventDetector
from Detectors.StepSelector import StepSelector
from InteractionXML.MakeSubset import makeSubset

def workdir(path, deleteIfExists=True):
    if os.path.exists(path):
        if deleteIfExists:
            print >> sys.stderr, "Output directory exists, removing", path
            shutil.rmtree(path)
            os.makedirs(path)
    else:
        os.makedirs(path)
    origDir = os.getcwd()
    os.chdir(path)
    atexit.register(os.chdir, origDir)

#def task3Classify(classifier, xml, specModel, negModel, task3Ids, task3Tag, parse, goldXML=None):
#    # Task 3
#    SPECULATION_MODEL = specModel
#    assert os.path.exists(SPECULATION_MODEL)
#    NEGATION_MODEL = negModel
#    assert os.path.exists(NEGATION_MODEL)
#    
#    # The id-sets will be modified, so create local copies of them.
#    # Using always the same id numbers for machine learning classes
#    # and examples ensures that the model-files will be compatible
#    # with all of your experiments.
#    TASK3_IDS = copyIdSetsToWorkdir(task3Ids)
#    
#    # Speculation detection
#    print >> sys.stderr, "====== Speculation Detection ======"
#    Task3ExampleBuilder.run(xml, "speculation-"+task3Tag+"-examples", parse, None, "style:typed,speculation", TASK3_IDS, goldXML)
#    classifier.test("speculation-"+task3Tag+"-examples", SPECULATION_MODEL, "speculation-"+task3Tag+"-classifications")
#    xml = BioTextExampleWriter.write("speculation-"+task3Tag+"-examples", "speculation-"+task3Tag+"-classifications", xml, None, TASK3_IDS+".class_names")
#    
#    # Negation detection
#    print >> sys.stderr, "====== Negation Detection ======"
#    Task3ExampleBuilder.run(xml, "negation-"+task3Tag+"-examples", parse, None, "style:typed,negation", TASK3_IDS, goldXML)
#    classifier.test("negation-"+task3Tag+"-examples", NEGATION_MODEL, "negation-"+task3Tag+"-classifications")
#    xml = BioTextExampleWriter.write("negation-"+task3Tag+"-examples", "negation-"+task3Tag+"-classifications", xml, task3Tag + "-task3.xml.gz", TASK3_IDS+".class_names")
#    return xml

#def getA2FileTag(task, subTask):
#    if task == "REL":
#        return "rel"
#    if task == "OLD":
#        if subTask == 1:
#            return "a2.t1"
#        else:
#            return "a2.t12"
#        assert False
#    return "a2"

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("--classify", default=None, dest="classify", help="classify with existing experiments models")
# files
optparser.add_option("--trainFile", default=None, dest="trainFile", help="")
optparser.add_option("--develFile", default=None, dest="develFile", help="")
optparser.add_option("--everythingFile", default=None, dest="everythingFile", help="")
optparser.add_option("--testFile", default=None, dest="testFile", help="")
# models
optparser.add_option("--develModel", default="model-devel", dest="develModel", help="")
optparser.add_option("--testModel", default="model-test", dest="testModel", help="")
# extras
optparser.add_option("--extraTag", default="", dest="extraTag", help="extra tag for input files")
optparser.add_option("--extraTrain", default=None, dest="extraTrain", help="extra training examples")
optparser.add_option("--extraTrainFor", default="trigger,edge", dest="extraTrainFor", help="extra training examples")
optparser.add_option("--extraTrainStyle", default="", dest="extraTrainStyle", help="extra training examples")
optparser.add_option("--extraTrainParse", default="split-mccc-preparsed", dest="extraTrainParse", help="Parse XML element name")
optparser.add_option("--extraTrainTokenization", default=None, dest="extraTrainTokenization", help="Tokenization XML element name")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-a", "--task", default="1", dest="task", help="task number")
optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default=None, dest="tokenization", help="Tokenization XML element name")
optparser.add_option("--step", default=None, dest="step", help="")
#optparser.add_option("--detectorStep", default=None, dest="detectorStep", help="")
optparser.add_option("--copyFrom", default=None, dest="copyFrom", help="Copy this directory as template")
# Classifier
#optparser.add_option("-c", "--classifier", default="Cls", dest="classifier", help="")
#optparser.add_option("--csc", default="", dest="csc", help="")
optparser.add_option("-c", "--connection", default=None, dest="connection", help="")
# Example builders
optparser.add_option("-f", "--triggerExampleBuilder", default="GeneralEntityTypeRecognizerGztr", dest="triggerExampleBuilder", help="")
optparser.add_option("-g", "--edgeExampleBuilder", default="MultiEdgeExampleBuilder", dest="edgeExampleBuilder", help="")
# Feature params
optparser.add_option("--triggerStyle", default=None, dest="triggerStyle", help="")
optparser.add_option("--edgeStyle", default=None, dest="edgeStyle", help="")
optparser.add_option("--modifierStyle", default=None, dest="modifierStyle", help="")
# Id sets
optparser.add_option("-v", "--triggerIds", default=None, dest="triggerIds", help="Trigger detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
optparser.add_option("-w", "--edgeIds", default=None, dest="edgeIds", help="Edge detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
# Parameters to optimize
optparser.add_option("-x", "--triggerParams", default="1000,5000,10000,20000,50000,80000,100000,150000,180000,200000,250000,300000,350000,500000,1000000", dest="triggerParams", help="Trigger detector c-parameter values")
optparser.add_option("-y", "--recallAdjustParams", default="0.5,0.6,0.65,0.7,0.85,1.0,1.1,1.2", dest="recallAdjustParams", help="Recall adjuster parameter values")
optparser.add_option("-z", "--edgeParams", default="5000,7500,10000,20000,25000,27500,28000,29000,30000,35000,40000,50000,60000,65000", dest="edgeParams", help="Edge detector c-parameter values")
optparser.add_option("--uParams", default="1,10,100,500,1000,1500,2500,5000,10000,20000,50000,80000,100000", dest="uParams", help="Unmerging c-parameter values")
optparser.add_option("--modifierParams", default="5000,10000,20000,50000,100000", dest="modifierParams", help="Modifier c-parameter values")
optparser.add_option("--downSampleTrain", default=1.0, type="float", dest="downSampleTrain", help="")
optparser.add_option("--downSampleSeed", default=1, type="int", dest="downSampleSeed", help="")
optparser.add_option("--fullGrid", default=False, action="store_true", dest="fullGrid", help="Full grid search for parameters")
# Shared task evaluation
optparser.add_option("--noLog", default=False, action="store_true", dest="noLog", help="")
optparser.add_option("--noTestSet", default=False, action="store_true", dest="noTestSet", help="")
optparser.add_option("--clearAll", default=False, action="store_true", dest="clearAll", help="Delete all files")
optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="More verbose output")
optparser.add_option("-u", "--unmerging", default=False, action="store_true", dest="unmerging", help="SVM unmerging")
optparser.add_option("-m", "--modifiers", default=False, action="store_true", dest="modifiers", help="Train model for modifier detection")
# Task 3
optparser.add_option("--speculationModel", default=os.path.expanduser("~/biotext/BioNLP2011/tests/task3/task3TrainGE-EPI-ID/speculation-models/model-c_150000"), dest="speculationModel", help="SVM-multiclass speculation model")
optparser.add_option("--negationModel", default=os.path.expanduser("~/biotext/BioNLP2011/tests/task3/task3TrainGE-EPI-ID/negation-models/model-c_16000"), dest="negationModel", help="SVM-multiclass negation model")
optparser.add_option("--task3Ids", default=os.path.expanduser("~/biotext/BioNLP2011/tests/task3/task3TrainGE-EPI-ID/genia-task3-ids"), dest="task3Ids", help="Speculation & negation SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
(options, args) = optparser.parse_args()

step = options.step
detectorStep = {"TRAIN":None, "DEVEL":None, "EMPTY":None, "TEST":None} # TRAIN substep
if options.step != None and "." in options.step:
    step = options.step.split(".")[0]
    detectorStep[step] = options.step.split(".")[1]
selector = StepSelector(["TRAIN", "DEVEL", "EMPTY", "TEST"], fromStep=step)

# Check options
if options.classify:
    print "Classifying with existing models"
    options.mode = "POST-GRID"
assert options.output != None
assert options.task in ["OLD.1", "OLD.2", "CO", "REL", "GE", "GE.1", "GE.2", "EPI", "ID", "BB"]
fullTaskId = options.task
subTask = 2
if "." in options.task:
    options.task, subTask = options.task.split(".")
    subTask = int(subTask)
#dataPath = "/home/jari/biotext/BioNLP2011/data/main-tasks/"
if options.task == "REL":
    dataPath = os.path.expanduser("~/biotext/BioNLP2011/data/supporting-tasks/REL/")
    TRAIN_FILE = dataPath + "rel-train.xml"
    TEST_FILE = dataPath + "rel-devel.xml"
    FINAL_TEST_FILE = dataPath + "rel-test.xml"
elif options.task == "CO":
    dataPath = os.path.expanduser("~/biotext/BioNLP2011/data/CO/")
    TRAIN_FILE = dataPath + "co-train.xml"
    TEST_FILE = dataPath + "co-devel.xml"
    FINAL_TEST_FILE = dataPath + "co-test.xml"
else:
    dataPath = os.path.expanduser("~/biotext/BioNLP2011/data/main-tasks/")
    TRAIN_FILE = dataPath + options.task + "/" + options.task + "-train" + options.extraTag + ".xml"
    TEST_FILE = dataPath + options.task + "/" + options.task + "-devel" + options.extraTag + ".xml"
    #FINAL_TEST_FILE = dataPath + options.task + "/" + options.task + "-test.xml" # test set never uses extratag
    FINAL_TEST_FILE = dataPath + options.task + "/" + options.task + "-test" + options.extraTag + ".xml" # test set never uses extratag
# Optional overrides for input files
if options.trainFile != None: TRAIN_FILE = options.trainFile
if options.develFile != None: TEST_FILE = options.develFile
if options.testFile != None: FINAL_TEST_FILE = options.testFile


# Example generation parameters
if options.edgeStyle != None:
    EDGE_FEATURE_PARAMS=options.edgeStyle
else:
    if options.task in ["OLD", "GE"]:
        EDGE_FEATURE_PARAMS="trigger_features:typed:directed:no_linear:entities:genia_limits:noMasking:maxFeatures" #,multipath"
        if subTask == 1:
            EDGE_FEATURE_PARAMS += ":genia_task1"
    elif options.task in ["BB"]:
        EDGE_FEATURE_PARAMS="trigger_features:typed:directed:no_linear:entities:bb_limits:noMasking:maxFeatures"
    elif options.task == "EPI":
        EDGE_FEATURE_PARAMS="trigger_features:typed:directed:no_linear:entities:epi_limits:noMasking:maxFeatures"
    elif options.task == "ID":
        EDGE_FEATURE_PARAMS="trigger_features:typed:directed:no_linear:entities:id_limits:noMasking:maxFeatures"
    elif options.task == "REL":
        EDGE_FEATURE_PARAMS="trigger_features:typed,directed:no_linear:entities:noMasking:maxFeatures:rel_limits:rel_features"
    elif options.task == "CO":
        EDGE_FEATURE_PARAMS="trigger_features:typed:directed:no_linear:entities:noMasking:maxFeatures:co_limits"
    else:
        EDGE_FEATURE_PARAMS="trigger_features:typed:directed:no_linear:entities:noMasking:maxFeatures"
if options.triggerStyle != None:  
    TRIGGER_FEATURE_PARAMS=options.triggerStyle #"style:typed"
else:
    TRIGGER_FEATURE_PARAMS=None
    if options.task in ["OLD", "GE"] and subTask == 1:
        TRIGGER_FEATURE_PARAMS = "genia_task1"
    elif options.task in ["BB"]:
        TRIGGER_FEATURE_PARAMS = "bb_features:build_for_nameless:wordnet"
    elif options.task == "REL":
        TRIGGER_FEATURE_PARAMS = "rel_features"
        options.edgeParams = "10,100,1000,5000,7500,10000,20000,25000,28000,50000,60000,65000,100000,500000,1000000"
    elif options.task == "CO":
        options.triggerExampleBuilder = "PhraseTriggerExampleBuilder"
        options.edgeParams = "10,100,1000,5000,7500,10000,20000,25000,28000,50000,60000,65000,100000,500000,1000000"
        options.recallAdjustParams = "0.8,0.9,0.95,1.0"

# These commands will be in the beginning of most pipelines
WORKDIR=options.output
if options.copyFrom != None and (options.clearAll or not os.path.exists(WORKDIR)):
    if options.clearAll and os.path.exists(WORKDIR):
        shutil.rmtree(WORKDIR)
    print >> sys.stderr, "Copying template from", options.copyFrom
    shutil.copytree(options.copyFrom, WORKDIR)
# Start logging
workdir(WORKDIR, options.clearAll) # Select a working directory, optionally remove existing files
if not options.noLog:
    Stream.openLog("log.txt")
    #log() # Start logging into a file in working directory

## Make downsampling for learning curve
#downSampleTag = "-r" + str(options.downSampleTrain) + "_s" + str(options.downSampleSeed)
#newTrainFile = makeSubset(TRAIN_FILE, options.task + "-train-nodup" + options.extraTag + downSampleTag + ".xml", options.downSampleTrain, options.downSampleSeed)
#makeSubset(TRAIN_FILE.replace("-nodup", ""), options.task + "-train" + options.extraTag + downSampleTag + ".xml", options.downSampleTrain, options.downSampleSeed)
#TRAIN_FILE = newTrainFile

if subTask != None:
    print >> sys.stderr, "Task:", options.task + "." + str(subTask)
else:
    print >> sys.stderr, "Task:", options.task

eventDetector = EventDetector()
eventDetector.debug = options.debug
eventDetector.stWriteScores = True # write confidence scores into additional st-format files
#eventDetector.setCSCConnection(options.csc, os.path.join("CSCConnection",WORKDIR.lstrip("/")))
eventDetector.setConnection(getConnection(options.connection)).debug = options.debug
# Pre-calculate all the required SVM models
if selector.check("TRAIN"):
    print >> sys.stderr, "----------------------------------------------------"
    print >> sys.stderr, "--------------- Train Event Detector ---------------"
    print >> sys.stderr, "----------------------------------------------------"
    eventDetector.train(TRAIN_FILE, TEST_FILE, options.develModel, options.testModel,
                        TRIGGER_FEATURE_PARAMS, EDGE_FEATURE_PARAMS, "", options.modifierStyle,
                        options.triggerParams, options.edgeParams, 
                        options.uParams, options.modifierParams,
                        options.recallAdjustParams, options.unmerging, options.modifiers, 
                        options.fullGrid, fullTaskId,
                        options.parse, options.tokenization,
                        fromStep=detectorStep["TRAIN"],
                        workDir="training")
if selector.check("DEVEL"):
    print >> sys.stderr, "----------------------------------------------------"
    print >> sys.stderr, "------------ Check devel classification ------------"
    print >> sys.stderr, "----------------------------------------------------"
    eventDetector.classify(TEST_FILE, options.develModel, "classification/devel", fromStep=detectorStep["DEVEL"])
if selector.check("EMPTY"):
    # By passing an emptied devel set through the prediction system, we can check that we get the same predictions
    # as in the DEVEL step, ensuring the model does not use leaked information.
    print >> sys.stderr, "----------------------------------------------------"
    print >> sys.stderr, "------------ Empty devel classification ------------"
    print >> sys.stderr, "----------------------------------------------------"
    #eventDetector.classify(TEST_FILE.replace(".xml", "-empty.xml"), "model-devel", "predicted-devel-empty", fromStep=options.detectorStep)
    eventDetector.classify(getEmptyCorpus(TEST_FILE), options.develModel, "classification/devel-empty", fromStep=detectorStep["EMPTY"])
if not options.noTestSet:
    if selector.check("TEST"):
        print >> sys.stderr, "----------------------------------------------------"
        print >> sys.stderr, "------------- Test set classification --------------"
        print >> sys.stderr, "----------------------------------------------------"
        eventDetector.stWriteScores = False # the evaluation server doesn't like additional files
        eventDetector.classify(FINAL_TEST_FILE, options.testModel, "classification/test", fromStep=detectorStep["TEST"], saveChangedModelPath="model-test-classify-ids")
        #print os.listdir(os.getcwd())
        STFormat.Compare.compare("classification/test-events.tar.gz", "classification/devel-events.tar.gz", "a2")

