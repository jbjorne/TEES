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

selector = StepSelector(["TRAIN", "DEVEL", "EMPTY"], fromStep=options.step)

# Check options
assert options.output != None
assert options.task in ["BI", "REN"]
if options.task == "BI":
    dataPath = os.path.expanduser("~/biotext/BioNLP2011/data/main-tasks/")
    TRAIN_FILE = dataPath + options.task + "/" + options.task + "-train-nodup.xml"
    TEST_FILE = dataPath + options.task + "/" + options.task + "-devel-nodup.xml"
    if not options.noTestSet:
        EVERYTHING_FILE = dataPath + options.task + "/" + options.task + "-devel-and-train.xml"
        FINAL_TEST_FILE = dataPath + options.task + "/" + options.task + "-test.xml"
    BXEv.setOptions("genia-BXEv", "BI", TEST_FILE, options.parse, options.tokenization, "edge-ids")
    EVALUATOR = BXEv
else:
    dataPath = os.path.expanduser("~/biotext/BioNLP2011/data/supporting-tasks/REN/")
    TRAIN_FILE = dataPath + "ren-train.xml"
    TEST_FILE = dataPath + "ren-devel.xml"
    if not options.noTestSet:
        EVERYTHING_FILE = dataPath + "ren-devel-and-train.xml"
        FINAL_TEST_FILE = dataPath + "ren-test.xml"
    EVALUATOR = Ev
exec "CLASSIFIER = " + options.classifier

if options.clearAll and "clear" not in options.csc:
    options.csc += (",clear")

# Main settings
develDetector = SingleStageDetector()
develDetector.classifier = CLASSIFIER
develDetector.evaluator = EVALUATOR
develDetector.parse = options.parse
develDetector.tokenization = options.tokenization
develDetector.exampleBuilder = eval(options.edgeExampleBuilder)
develDetector.modelPath = "devel-model"

#testDetector = SingleStageDetector()
#testDetector.classifier = CLASSIFIER
#testDetector.evaluator = EVALUATOR
#testDetector.parse = options.parse
#testDetector.tokenization = options.tokenization
#testDetector.exampleBuilder = eval(options.edgeExampleBuilder)
#testDetector.modelPath = "test-model"

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
    develDetector.exampleStyle = "style:"+options.edgeStyles
elif options.task == "BI":
    develDetector.exampleStyle="style:trigger_features,typed,directed,no_linear,entities,noMasking,maxFeatures,bi_limits"
elif options.task == "REN":
    develDetector.exampleStyle="style:trigger_features,typed,no_linear,entities,noMasking,maxFeatures,bacteria_renaming"
    develDetector.classifierParameters = "10,100,1000,2000,3000,4000,4500,5000,5500,6000,7500,10000,20000,25000,28000,50000,60000"
develDetector.classifierParameters="c:" + options.edgeParams
develDetector.setCSCConnection(options.csc, CSC_WORKDIR)

#if not options.noTestSet:
#    EDGE_EVERYTHING_EXAMPLE_FILE = "edge-everything-examples-"+PARSE_TAG
#    EDGE_FINAL_TEST_EXAMPLE_FILE = "edge-final-examples-"+PARSE_TAG
#    EDGE_IDS = "edge-ids"
#if not "eval" in options.csc:
    
###############################################################################
# Edge example generation and model upload
###############################################################################
if selector.check("TRAIN"):
    develDetector.train(TRAIN_FILE, TEST_FILE, fromStep=options.detectorStep, toStep="EXAMPLES")
    #testDetector.train(EVERYTHING_FILE, FINAL_TEST_FILE, fromStep=options.step, toStep="EXAMPLES")
    develDetector.train(fromStep=options.detectorStep, toStep="TRAIN") # Upload models 
    develDetector.train(fromStep=options.detectorStep) # Model download
    #testDetector.train(fromStep=options.step) # Train final models

if selector.check("DEVEL"):
    print >> sys.stderr, "------------ Check devel classification ------------"
    develDetector.classify(TEST_FILE, "devel-predicted")
if selector.check("EMPTY"):    
    print >> sys.stderr, "------------ Empty devel classification ------------"
    develDetector.classify(TEST_FILE.replace(".xml", "-empty.xml"), "devel-predicted")

#if not options.noTestSet:
#    print >> sys.stderr, "------------ Test set classification ------------"
#    if "local" not in options.csc:
#        clear = False
#        if "clear" in options.csc: clear = True
#        if "louhi" in options.csc:
#            c = CSCConnection(CSC_WORKDIR+"/edge-everything-models", "jakrbj@louhi.csc.fi", clear)
#        else:
#            c = CSCConnection(CSC_WORKDIR+"/edge-everything-models", "jakrbj@murska.csc.fi", clear)
#    else:
#        c = None
#    finalEdgeModel = optimize(CLASSIFIER, Ev, EDGE_EVERYTHING_EXAMPLE_FILE, EDGE_TEST_EXAMPLE_FILE,\
#    EDGE_IDS+".class_names", "c:"+bestEdgeModel[2].split("_")[-1], "edge-everything-models", None, c, False)[1]
#    Cls.test(EDGE_FINAL_TEST_EXAMPLE_FILE, finalEdgeModel, "final-edge-test-classifications")
#    xml = BioTextExampleWriter.write(EDGE_FINAL_TEST_EXAMPLE_FILE, "final-edge-test-classifications", FINAL_TEST_FILE, None, EDGE_IDS+".class_names", PARSE, TOK)
#    xml = ix.splitMergedElements(xml, None)
#    xml = ix.recalculateIds(xml, "final-predicted-edges.xml", True)
#    EvaluateInteractionXML.run(Ev, xml, FINAL_TEST_FILE, PARSE, TOK)
#    STFormat.ConvertXML.toSTFormat(xml, "final-geniaformat", outputTag="a2")
#    # Sanity Check
#    STFormat.Compare.compare("final-geniaformat", "empty-devel-geniaformat", "a2")
