import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../CommonUtils") # new CommonUtils
from InteractionXML.DeleteElements import getEmptyCorpus
import Utils.Stream as Stream
from Utils.Connection.Unix import getConnection
import STFormat.ConvertXML
import STFormat.Compare
import shutil
import atexit
from Detectors.StepSelector import StepSelector

def train():
    pass

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

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
        
    from optparse import OptionParser
    optparser = OptionParser()
    # input
    optparser.add_option("--trainFile", default=None, dest="trainFile", help="")
    optparser.add_option("--develFile", default=None, dest="develFile", help="")
    optparser.add_option("--testFile", default=None, dest="testFile", help="")
    # output
    optparser.add_option("-o", "--output", default=None, dest="output", help="output directory")
    optparser.add_option("--develModel", default="model-devel", dest="develModel", help="")
    optparser.add_option("--testModel", default="model-test", dest="testModel", help="")
    # extras
    optparser.add_option("-a", "--task", default=None, dest="task", help="task number")
    optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
    # Classifier
    optparser.add_option("-c", "--connection", default=None, dest="connection", help="")
    # Example builders
    optparser.add_option("--detector", default="Detectors.EventDetector", dest="detector", help="")
    optparser.add_option("--singleStage", default=False, action="store_true", dest="singleStage", help="Use a single stage detector")
    # Example builder parameters
    optparser.add_option("--exampleStyle", default=None, dest="exampleStyle", help="Single-stage detector example style")
    optparser.add_option("--triggerStyle", default=None, dest="triggerStyle", help="Event detector trigger example style")
    optparser.add_option("--edgeStyle", default=None, dest="edgeStyle", help="Event detector edge example style")
    optparser.add_option("--modifierStyle", default=None, dest="modifierStyle", help="Event detector modifier example style")
    # Classifier parameters
    optparser.add_option("--exampleParams", default=None, dest="exampleParams", help="Single-stage detector parameters")
    optparser.add_option("-x", "--triggerParams", default="1000,5000,10000,20000,50000,80000,100000,150000,180000,200000,250000,300000,350000,500000,1000000", dest="triggerParams", help="Trigger detector c-parameter values")
    optparser.add_option("-y", "--recallAdjustParams", default="0.5,0.6,0.65,0.7,0.85,1.0,1.1,1.2", dest="recallAdjustParams", help="Recall adjuster parameter values")
    optparser.add_option("-z", "--edgeParams", default="5000,7500,10000,20000,25000,27500,28000,29000,30000,35000,40000,50000,60000,65000", dest="edgeParams", help="Edge detector c-parameter values")
    optparser.add_option("--uParams", default="1,10,100,500,1000,1500,2500,5000,10000,20000,50000,80000,100000", dest="uParams", help="Unmerging c-parameter values")
    optparser.add_option("--modifierParams", default="5000,10000,20000,50000,100000", dest="modifierParams", help="Modifier c-parameter values")
    optparser.add_option("-u", "--unmerging", default=False, action="store_true", dest="unmerging", help="SVM unmerging")
    optparser.add_option("-m", "--modifiers", default=False, action="store_true", dest="modifiers", help="Train model for modifier detection")
    optparser.add_option("--fullGrid", default=False, action="store_true", dest="fullGrid", help="Full grid search for parameters")
    # Debugging and process control
    optparser.add_option("--step", default=None, dest="step", help="")
    optparser.add_option("--copyFrom", default=None, dest="copyFrom", help="Copy this directory as template")
    optparser.add_option("--noLog", default=False, action="store_true", dest="noLog", help="")
    optparser.add_option("--noTestSet", default=False, action="store_true", dest="noTestSet", help="")
    optparser.add_option("--clearAll", default=False, action="store_true", dest="clearAll", help="Delete all files")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="More verbose output")
    (options, args) = optparser.parse_args()
    
    # Validate options
    assert options.output != None
    assert options.task in ["GE00", "GE09.1", "GE09.2", "GE", "GE.1", "GE.2", "EPI", "ID", "BB", "BI", "CO", "REL", "REN"]
    
    step = options.step
    detectorStep = {"TRAIN":None, "DEVEL":None, "EMPTY":None, "TEST":None} # TRAIN substep
    if options.step != None and "." in options.step:
        step = options.step.split(".")[0]
        detectorStep[step] = options.step.split(".")[1]
    selector = StepSelector(["TRAIN", "DEVEL", "EMPTY", "TEST"], fromStep=step)

    fullTaskId = options.task
    subTask = 2
    if "." in options.task:
        options.task, subTask = options.task.split(".")
        subTask = int(subTask)
    if options.task != None:
        dataPath = os.path.expanduser("~/biotext/BioNLP2011/data/main-tasks/")
        trainFile = dataPath + options.task + "/" + options.task + "-train" + options.extraTag + ".xml"
        develFile = dataPath + options.task + "/" + options.task + "-devel" + options.extraTag + ".xml"
        testFile = dataPath + options.task + "/" + options.task + "-test" + options.extraTag + ".xml" # test set never uses extratag
    # Optional overrides for input files
    if options.trainFile != None: trainFile = options.trainFile
    if options.develFile != None: develFile = options.develFile
    if options.testFile != None: testFile = options.testFile
    
    # Example generation parameters
    if options.edgeStyle != None:
        EDGE_FEATURE_PARAMS=options.edgeStyle
    else:
        if options.task in ["GE09", "GE"]:
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
        if options.task in ["GE09", "GE"] and subTask == 1:
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
    if options.copyFrom != None:
        if os.path.exists(WORKDIR):
            shutil.rmtree(WORKDIR)
        print >> sys.stderr, "Copying template from", options.copyFrom
        shutil.copytree(options.copyFrom, WORKDIR)
        workdir(WORKDIR, False)
    else:
        workdir(WORKDIR, options.clearAll) # Select a working directory, optionally remove existing files
    if not options.noLog:
        Stream.openLog("log.txt")
        #log() # Start logging into a file in working directory
    
    print >> sys.stderr, "Importing detector", options.detector
    Detector = eval("from " + options.detector + " import " + options.detector.split(".")[-1])
    detector = Detector()
    detector.debug = options.debug
    detector.stWriteScores = True # write confidence scores into additional st-format files
    detector.setConnection(getConnection(options.connection)).debug = options.debug
    # Pre-calculate all the required SVM models
    if selector.check("TRAIN"):
        print >> sys.stderr, "----------------------------------------------------"
        print >> sys.stderr, "------------------ Train Detector ------------------"
        print >> sys.stderr, "----------------------------------------------------"
        if options.singleStage:
            detector.train(trainFile, develFile, options.develModel, options.testModel,
                           options.exampleStyle, options.exampleParams, options.parse, None, fullTaskId,
                           fromStep=detectorStep["TRAIN"], workDir="training")
        else:
            detector.train(trainFile, develFile, options.develModel, options.testModel,
                           TRIGGER_FEATURE_PARAMS, EDGE_FEATURE_PARAMS, "", options.modifierStyle,
                           options.triggerParams, options.edgeParams, options.uParams, options.modifierParams,
                           options.recallAdjustParams, options.unmerging, options.modifiers, 
                           options.fullGrid, fullTaskId, options.parse, None,
                           fromStep=detectorStep["TRAIN"], workDir="training")
    if selector.check("DEVEL"):
        print >> sys.stderr, "----------------------------------------------------"
        print >> sys.stderr, "------------ Check devel classification ------------"
        print >> sys.stderr, "----------------------------------------------------"
        detector.classify(develFile, options.develModel, "classification/devel", fromStep=detectorStep["DEVEL"])
    if selector.check("EMPTY"):
        # By passing an emptied devel set through the prediction system, we can check that we get the same predictions
        # as in the DEVEL step, ensuring the model does not use leaked information.
        print >> sys.stderr, "----------------------------------------------------"
        print >> sys.stderr, "------------ Empty devel classification ------------"
        print >> sys.stderr, "----------------------------------------------------"
        detector.classify(getEmptyCorpus(develFile), options.develModel, "classification/devel-empty", fromStep=detectorStep["EMPTY"])
    if (not options.noTestSet) and selector.check("TEST"):
        print >> sys.stderr, "----------------------------------------------------"
        print >> sys.stderr, "------------- Test set classification --------------"
        print >> sys.stderr, "----------------------------------------------------"
        detector.stWriteScores = False # the evaluation server doesn't like additional files
        detector.classify(testFile, options.testModel, "classification/test", fromStep=detectorStep["TEST"])
        STFormat.Compare.compare("classification/test-events.tar.gz", "classification/devel-events.tar.gz", "a2")