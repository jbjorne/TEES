# Optimize parameters for event detection and produce event and edge model files

# most imports are defined in Pipeline
from Pipeline import *
import sys, os
import STFormat.ConvertXML
import STFormat.Compare
from Detectors.SingleStageDetector import SingleStageDetector
from Detectors.StepSelector import StepSelector
from InteractionXML.MakeSubset import makeSubset

from optparse import OptionParser
optparser = OptionParser()
optparser.add_option("-e", "--test", default=Settings.DevelFile, dest="testFile", help="Test file in interaction xml")
optparser.add_option("-r", "--train", default=Settings.TrainFile, dest="trainFile", help="Train file in interaction xml")
optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
optparser.add_option("-a", "--task", default="BI", dest="task", help="task number")
optparser.add_option("-p", "--parse", default="gold", dest="parse", help="Parse XML element name")
optparser.add_option("-t", "--tokenization", default="gold", dest="tokenization", help="Tokenization XML element name")
# Classifier
optparser.add_option("-c", "--classifier", default="Cls", dest="classifier", help="")
optparser.add_option("--csc", default="murska", dest="csc", help="")
# Example builders
optparser.add_option("--downSampleTrain", default=1.0, type="float", dest="downSampleTrain", help="")
optparser.add_option("--downSampleSeed", default=1, type="int", dest="downSampleSeed", help="")
optparser.add_option("--noTestSet", default=False, action="store_true", dest="noTestSet", help="")
optparser.add_option("-f", "--edgeExampleBuilder", default="MultiEdgeExampleBuilder", dest="edgeExampleBuilder", help="")
optparser.add_option("-s", "--styles", default=None, dest="edgeStyles", help="")
optparser.add_option("--step", default=None, dest="step", help="")
optparser.add_option("--detectorStep", default=None, dest="detectorStep", help="")
#optparser.add_option("-g", "--gazetteer", default="none", dest="gazetteer", help="gazetteer options: none, stem, full")
# Id sets
optparser.add_option("-v", "--edgeIds", default=None, dest="edgeIds", help="Trigger detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
# Parameters to optimize
optparser.add_option("-x", "--edgeParams", default="2500,5000,7500", dest="edgeParams", help="Trigger detector c-parameter values")
optparser.add_option("--clearAll", default=False, action="store_true", dest="clearAll", help="Delete all files")
(options, args) = optparser.parse_args()

selector = StepSelector(["TRAIN", "DEVEL", "EMPTY", "TEST"], fromStep=options.step)

# Check options
assert options.output != None
assert options.task in ["BI", "REN"]
if options.task == "BI":
    dataPath = os.path.expanduser("~/biotext/BioNLP2011/data/main-tasks/")
    TRAIN_FILE = dataPath + options.task + "/" + options.task + "-train-nodup.xml"
    TEST_FILE = dataPath + options.task + "/" + options.task + "-devel-nodup.xml"
    FINAL_TEST_FILE = dataPath + options.task + "/" + options.task + "-test.xml"
    BXEv.setOptions("genia-BXEv", "BI", TEST_FILE, options.parse, options.tokenization, "edge-ids")
    EVALUATOR = BXEv
else:
    dataPath = os.path.expanduser("~/biotext/BioNLP2011/data/supporting-tasks/REN/")
    TRAIN_FILE = dataPath + "ren-train.xml"
    TEST_FILE = dataPath + "ren-devel.xml"
    FINAL_TEST_FILE = dataPath + "ren-test.xml"
    EVALUATOR = Ev
exec "CLASSIFIER = " + options.classifier

if options.clearAll and "clear" not in options.csc:
    options.csc += (",clear")

# Main settings
develDetector = SingleStageDetector()
develDetector.classifier = CLASSIFIER
develDetector.evaluator = EVALUATOR
develDetector.exampleBuilder = eval(options.edgeExampleBuilder)
develDetector.tag = "edge-"

# These commands will be in the beginning of most pipelines
WORKDIR=options.output
CSC_WORKDIR = os.path.join("CSCConnection",WORKDIR.lstrip("/"))

workdir(WORKDIR, options.clearAll) # Select a working directory, don't remove existing files
log() # Start logging into a file in working directory

# Make downsampling for learning curve
if options.downSampleTrain != 1.0:
    downSampleTag = "-r" + str(options.downSampleTrain) + "_s" + str(options.downSampleSeed)
    if not os.path.exists(options.task + "-train-nodup" + downSampleTag + ".xml"):
        newTrainFile = makeSubset(TRAIN_FILE, options.task + "-train-nodup" + downSampleTag + ".xml", options.downSampleTrain, options.downSampleSeed)
    if not os.path.exists(options.task + "-train" + downSampleTag + ".xml"):
        makeSubset(TRAIN_FILE.replace("-nodup", ""), options.task + "-train" + downSampleTag + ".xml", options.downSampleTrain, options.downSampleSeed)
    TRAIN_FILE = options.task + "-train-nodup" + downSampleTag + ".xml"

# Example generation parameters
if options.edgeStyles != None:
    options.styles = "style:"+options.edgeStyles
elif options.task == "BI":
    options.styles="style:trigger_features,typed,directed,no_linear,entities,noMasking,maxFeatures,bi_limits"
elif options.task == "REN":
    options.styles="style:trigger_features,typed,no_linear,entities,noMasking,maxFeatures,bacteria_renaming"
    options.edgeParams = "10,100,1000,2000,3000,4000,4500,5000,5500,6000,7500,10000,20000,25000,28000,50000,60000"
options.edgeParams="c:" + options.edgeParams
develDetector.setCSCConnection(options.csc, CSC_WORKDIR)
    
###############################################################################
# Edge example generation and model upload
###############################################################################
if selector.check("TRAIN"):
    print >> sys.stderr, "------------ Train Edge Detector ------------"
    develDetector.train(TRAIN_FILE, TEST_FILE, "model-devel", "model-test", 
                        options.styles, options.edgeParams, options.parse, options.tokenization,
                        fromStep=options.detectorStep)
if selector.check("DEVEL"):
    print >> sys.stderr, "------------ Check devel classification ------------"
    develDetector.classify(TEST_FILE, "model-devel", "predicted-devel")
if selector.check("EMPTY"):    
    print >> sys.stderr, "------------ Empty devel classification ------------"
    develDetector.classify(TEST_FILE.replace(".xml", "-empty.xml"), "model-devel", "predicted-devel-empty")
if not options.noTestSet:
    if selector.check("TEST"):    
        print >> sys.stderr, "------------ Test set classification ------------"
        develDetector.classify(FINAL_TEST_FILE, "model-test", "predicted-test")
        STFormat.Compare.compare("predicted-test.tar.gz", "predicted-devel.tar.gz", "a2")
