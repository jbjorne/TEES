import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/CommonUtils") # new CommonUtils
from InteractionXML.DeleteElements import getEmptyCorpus
import Utils.Stream as Stream
import Utils.Settings as Settings
import Utils.Parameters as Parameters
from Utils.Connection.Unix import getConnection
import STFormat.ConvertXML
import STFormat.Compare
import shutil
import atexit
import types
from Core.Model import Model
from Detectors.StepSelector import StepSelector

def train(output, task=None, detector=None, 
          inputFiles={"train":None, "devel":None, "test":None}, 
          models={"devel":None, "test":None}, parse=None,
          processUnmerging=True, processModifiers=True, isSingleStage=False,
          exampleStyles={"examples":None, "trigger":None, "edge":None, "unmerging":None, "modifiers":None},
          classifierParams={"examples":None, "trigger":None, "recall":None, "edge":None, "unmerging":None, "modifiers":None}, 
          doFullGrid=False, deleteOutput=False, copyFrom=None, log=True, step=None, omitSteps=None, debug=False, connection=None):
    # Get task specific parameters
    detector, processUnmerging, processModifiers, isSingleStage, exampleStyles, classifierParams = getTaskSettings(task, 
        detector, processUnmerging, processModifiers, isSingleStage, inputFiles, exampleStyles, classifierParams)   
    # Define processing steps
    selector, detectorSteps, omitDetectorSteps = getSteps(step, omitSteps, ["TRAIN", "DEVEL", "EMPTY", "TEST"])
    # Initialize working directory
    workdir(output, deleteOutput, copyFrom, log)
    
    # Initialize the detector
    detector, detectorName = getDetector(detector)
    detector = detector() # initialize object
    detector.debug = debug
    detector.stWriteScores = True # write confidence scores into additional st-format files
    detector.setConnection(getConnection(connection)).debug = debug
    
    # Train
    if selector.check("TRAIN"):
        print >> sys.stderr, "----------------------------------------------------"
        print >> sys.stderr, "------------------ Train Detector ------------------"
        print >> sys.stderr, "----------------------------------------------------"
        if options.singleStage:
            detector.train(inputFiles["train"], inputFiles["devel"], models["devel"], models["test"],
                           exampleStyles["examples"], classifierParams["examples"], parse, None, task,
                           fromStep=detectorSteps["TRAIN"], workDir="training")
        else:
            detector.train(inputFiles["train"], inputFiles["devel"], models["devel"], models["test"],
                           exampleStyles["trigger"], exampleStyles["edge"], exampleStyles["unmerging"], exampleStyles["modifiers"],
                           classifierParams["trigger"], classifierParams["edge"], classifierParams["unmerging"], classifierParams["modifiers"],
                           classifierParams["recall"], processUnmerging, processModifiers, 
                           doFullGrid, task, parse, None,
                           fromStep=detectorSteps["TRAIN"], workDir="training")
        # Save the detector type
        for model in [models["devel"], models["test"]]:
            if os.path.exists(model):
                model = Model(model, "a")
                model.addStr("detector", detectorName)
                model.save()
                model.close()
    if selector.check("DEVEL"):
        print >> sys.stderr, "----------------------------------------------------"
        print >> sys.stderr, "------------ Check devel classification ------------"
        print >> sys.stderr, "----------------------------------------------------"
        detector.classify(inputFiles["devel"], models["devel"], "classification/devel", fromStep=detectorSteps["DEVEL"])
    if selector.check("EMPTY"):
        # By passing an emptied devel set through the prediction system, we can check that we get the same predictions
        # as in the DEVEL step, ensuring the model does not use leaked information.
        print >> sys.stderr, "----------------------------------------------------"
        print >> sys.stderr, "------------ Empty devel classification ------------"
        print >> sys.stderr, "----------------------------------------------------"
        detector.classify(getEmptyCorpus(inputFiles["devel"]), models["devel"], "classification/devel-empty", fromStep=detectorSteps["EMPTY"])
    if selector.check("TEST"):
        print >> sys.stderr, "----------------------------------------------------"
        print >> sys.stderr, "------------- Test set classification --------------"
        print >> sys.stderr, "----------------------------------------------------"
        if inputFiles["test"] == None or not os.path.exists(inputFiles["test"]):
            print >> sys.stderr, "Skipping, test file", inputFiles["test"], "does not exist"
        else:
            detector.stWriteScores = False # the evaluation server doesn't like additional files
            detector.classify(inputFiles["test"], models["test"], "classification/test", fromStep=detectorSteps["TEST"])
            STFormat.Compare.compare("classification/test-events.tar.gz", "classification/devel-events.tar.gz", "a2")

def getSteps(step, omitSteps, mainSteps=["TRAIN", "DEVEL", "EMPTY", "TEST"]):
    # Determine substep to start from, for the main step from which processing starts
    step = Parameters.get(step, mainSteps)
    fromMainStep = None
    fromSubStep = {} # The substep to start from, for the main step to start from
    for mainStep in step.keys():
        fromSubStep[mainStep] = step[mainStep] # the sub step to start from
        if step[mainStep] != None:
            assert fromMainStep == None # processing can start from one place only
            fromMainStep = mainStep
            if step[mainStep] == True:
                fromSubStep[mainStep] = None
            else:
                assert type(step[mainStep]) in types.StringTypes # no list allowed, processing can start from one place only
    # Determine steps to omit
    omitSubSteps = {} # Skip these substeps. If the value is True, skip the entire main step.
    omitMainSteps = []
    omitSteps = Parameters.get(omitSteps, mainSteps)
    for mainStep in omitSteps.keys():
        omitSubSteps[mainStep] = omitSteps[mainStep]
        if omitSteps[mainStep] == True:
            omitMainSteps.append(mainStep)
            omitSubSteps[mainStep] = None
    # Initialize main step selector
    if fromMainStep != None:
        if fromSubStep[fromMainStep] != None:
            print >> sys.stderr, "Starting process from step", fromMainStep + ", substep", fromSubStep[fromMainStep]
        else:
            print >> sys.stderr, "Starting process from step", fromMainStep
    selector = StepSelector(mainSteps, fromStep=fromMainStep, omitSteps=omitMainSteps)
    return selector, fromSubStep, omitSubSteps

def getDetector(detector, model=None):
    # Get the detector
    if detector == None:
        assert model != None
        model = Model(model, "r")
        model.getStr("detector")
        model.close()
    if type(detector) in types.StringTypes:
        print >> sys.stderr, "Importing detector", detector
        detectorName = detector
        if detector.startswith("from"):
            exec detector
            detector = eval(detector.split(".")[-1])
        else:
            exec "from " + detector + " import " + detector.split(".")[-1]
            detector = eval(detector.split(".")[-1])
    else: # assume it is a class
        detectorName = detector.__name__
        print >> sys.stderr, "Using detector", detectorName
        detector = detector
    return detector, detectorName


def workdir(path, deleteIfExists=True, copyFrom=None, log=True):
    # When using a template, always remove existing work directory
    if copyFrom != None:
        deleteIfExists = True
    # Remove existing work directory, if requested to do so
    if os.path.exists(path) and deleteIfExists:
        print >> sys.stderr, "Output directory exists, removing", path
        shutil.rmtree(path)
    # Create work directory if needed
    if not os.path.exists(path):
        if copyFrom == None:
            print >> sys.stderr, "Making output directory", path
            os.makedirs(path)
        else:
            print >> sys.stderr, "Copying template from", options.copyFrom, "to", path
            shutil.copytree(options.copyFrom, path)
    else:
        print >> sys.stderr, "Using existing output directory", path
    # Remember current directory and switch to workdir
    atexit.register(os.chdir, os.getcwd())
    os.chdir(path)
    # Open log at workdir
    if log:
        Stream.openLog("log.txt")
    return path

def getTaskSettings(task, detector, processUnmerging, processModifiers, isSingleStage,
                    inputFiles, exampleStyles, classifierParameters):
    if task != None:
        print >> sys.stderr, "Determining training settings for task", task
        assert task in ["GE00", "GE09.1", "GE09.2", "GE", "GE.1", "GE.2", "EPI", "ID", "BB", "BI", "CO", "REL", "REN", "DDI"]
    
        fullTaskId = task
        subTask = 2
        if "." in task:
            task, subTask = task.split(".")
            subTask = int(subTask)
        dataPath = os.path.expanduser("~/biotext/BioNLP2011/data/main-tasks/")
        #dataPath = Settings.CORPUS_DIR
        # Optional overrides for input files
        if inputFiles["devel"] == None: inputFiles["devel"] = dataPath + task + "/" + task + "-devel.xml"
        if inputFiles["train"] == None: inputFiles["train"] = dataPath + task + "/" + task + "-train.xml"
        if inputFiles["test"] == None: inputFiles["test"] = dataPath + task + "/" + task + "-test.xml"
        
        # Example generation parameters
        if exampleStyles["edge"] == None:
            print >> sys.stderr, "Edge example style undefined, using default for task", fullTaskId
            if task in ["GE09", "GE"]:
                exampleStyles["edge"]="trigger_features:typed:directed:no_linear:entities:genia_limits:noMasking:maxFeatures" #,multipath"
                if subTask == 1:
                    exampleStyles["edge"] += ":genia_task1"
            elif task in ["BB"]:
                exampleStyles["edge"]="trigger_features:typed:directed:no_linear:entities:bb_limits:noMasking:maxFeatures"
            elif task == "EPI":
                exampleStyles["edge"]="trigger_features:typed:directed:no_linear:entities:epi_limits:noMasking:maxFeatures"
            elif task == "ID":
                exampleStyles["edge"]="trigger_features:typed:directed:no_linear:entities:id_limits:noMasking:maxFeatures"
            elif task == "REL":
                exampleStyles["edge"]="trigger_features:typed,directed:no_linear:entities:noMasking:maxFeatures:rel_limits:rel_features"
            elif task == "CO":
                exampleStyles["edge"]="trigger_features:typed:directed:no_linear:entities:noMasking:maxFeatures:co_limits"
            else:
                exampleStyles["edge"]="trigger_features:typed:directed:no_linear:entities:noMasking:maxFeatures"
        if exampleStyles["trigger"] == None:
            print >> sys.stderr, "Trigger example style undefined, using default for task", fullTaskId
            if task in ["GE09", "GE"] and subTask == 1:
                exampleStyles["trigger"] = "genia_task1"
            elif task in ["BB"]:
                exampleStyles["trigger"] = "bb_features:build_for_nameless:wordnet"
            elif task == "REL":
                exampleStyles["trigger"] = "rel_features"
            elif task == "CO":
                options.triggerExampleBuilder = "PhraseTriggerExampleBuilder"
        # Classifier parameters
        if classifierParameters["edge"] == None:
            print >> sys.stderr, "Classifier parameters for edge examples undefined, using default for task", fullTaskId
            classifierParameters["edge"] = "5000,7500,10000,20000,25000,27500,28000,29000,30000,35000,40000,50000,60000,65000"
            if task == "REL":
                classifierParameters["edge"] = "10,100,1000,5000,7500,10000,20000,25000,28000,50000,60000,65000,100000,500000,1000000"
            elif task == "CO":
                classifierParameters["edge"] = "10,100,1000,5000,7500,10000,20000,25000,28000,50000,60000,65000,100000,500000,1000000"
        if classifierParameters["recall"] == None:
            print >> sys.stderr, "Recall adjust parameter undefined, using default for task", fullTaskId
            classifierParameters["recall"] = "0.5,0.6,0.65,0.7,0.85,1.0,1.1,1.2"
            if task == "CO":
                classifierParameters["recall"] = "0.8,0.9,0.95,1.0"
        if classifierParameters["trigger"] == None:
            print >> sys.stderr, "Classifier parameters for trigger examples undefined, using default for task", fullTaskId
            classifierParameters["trigger"] = "1000,5000,10000,20000,50000,80000,100000,150000,180000,200000,250000,300000,350000,500000,1000000"
    
    return detector, processUnmerging, processModifiers, isSingleStage, exampleStyles, classifierParameters

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
    optparser.add_option("-t", "--task", default=None, dest="task", help="task number")
    optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
    optparser.add_option("-u", "--unmerging", default=False, action="store_true", dest="unmerging", help="SVM unmerging")
    optparser.add_option("-m", "--modifiers", default=False, action="store_true", dest="modifiers", help="Train model for modifier detection")
    # Classifier
    optparser.add_option("-c", "--connection", default=None, dest="connection", help="")
    # Example builders
    optparser.add_option("--detector", default="Detectors.EventDetector", dest="detector", help="")
    optparser.add_option("--singleStage", default=False, action="store_true", dest="singleStage", help="Use a single stage detector")
    # Example builder parameters
    optparser.add_option("--exampleStyle", default=None, dest="exampleStyle", help="Single-stage detector example style")
    optparser.add_option("--triggerStyle", default=None, dest="triggerStyle", help="Event detector trigger example style")
    optparser.add_option("--edgeStyle", default=None, dest="edgeStyle", help="Event detector edge example style")
    optparser.add_option("--unmergingStyle", default=None, dest="unmergingStyle", help="Event detector unmerging example style")
    optparser.add_option("--modifierStyle", default=None, dest="modifierStyle", help="Event detector modifier example style")
    # Classifier parameters
    optparser.add_option("-e", "--exampleParams", default=None, dest="exampleParams", help="Single-stage detector parameters")
    optparser.add_option("-r", "--triggerParams", default="1000,5000,10000,20000,50000,80000,100000,150000,180000,200000,250000,300000,350000,500000,1000000", dest="triggerParams", help="Trigger detector c-parameter values")
    optparser.add_option("-a", "--recallAdjustParams", default="0.5,0.6,0.65,0.7,0.85,1.0,1.1,1.2", dest="recallAdjustParams", help="Recall adjuster parameter values")
    optparser.add_option("-d", "--edgeParams", default="5000,7500,10000,20000,25000,27500,28000,29000,30000,35000,40000,50000,60000,65000", dest="edgeParams", help="Edge detector c-parameter values")
    optparser.add_option("-n", "--unmergingParams", default="1,10,100,500,1000,1500,2500,5000,10000,20000,50000,80000,100000", dest="unmergingParams", help="Unmerging c-parameter values")
    optparser.add_option("-f", "--modifierParams", default="5000,10000,20000,50000,100000", dest="modifierParams", help="Modifier c-parameter values")
    optparser.add_option("--fullGrid", default=False, action="store_true", dest="fullGrid", help="Full grid search for parameters")
    # Debugging and process control
    optparser.add_option("--step", default=None, dest="step", help="")
    optparser.add_option("--omitSteps", default=None, dest="omitSteps", help="")
    optparser.add_option("--copyFrom", default=None, dest="copyFrom", help="Copy this directory as template")
    optparser.add_option("--noLog", default=False, action="store_true", dest="noLog", help="")
    optparser.add_option("--clearAll", default=False, action="store_true", dest="clearAll", help="Delete all files")
    optparser.add_option("--debug", default=False, action="store_true", dest="debug", help="More verbose output")
    (options, args) = optparser.parse_args()
    
    assert options.output != None
    train(options.output, options.task, options.detector, 
          inputFiles={"devel":options.develFile, "train":options.trainFile, "test":options.testFile},
          models={"devel":options.develModel, "test":options.testModel}, parse=options.parse,
          processUnmerging=options.unmerging, processModifiers=options.modifiers, isSingleStage=options.singleStage,
          exampleStyles={"examples":options.exampleStyle, "trigger":options.triggerStyle, "edge":options.edgeStyle, "unmerging":options.unmergingStyle, "modifiers":options.modifierStyle},
          classifierParams={"examples":options.exampleParams, "trigger":options.triggerParams, "recall":options.recallAdjustParams, "edge":options.edgeParams, "unmerging":options.unmergingParams, "modifiers":options.modifierParams}, 
          doFullGrid=options.fullGrid, deleteOutput=options.clearAll, copyFrom=options.copyFrom, 
          log=not options.noLog, step=options.step, omitSteps=options.omitSteps, debug=options.debug, connection=options.connection)