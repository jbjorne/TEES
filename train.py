import sys, os
from Utils.InteractionXML.DeleteElements import getEmptyCorpus
import Utils.InteractionXML.Catenate as Catenate
import Utils.Stream as Stream
import Utils.Settings as Settings
import Utils.Parameters as Parameters
from Utils.Connection.Connection import getConnection
import Utils.STFormat.Compare
import shutil
import atexit
import types
from Core.Model import Model
from Detectors.StepSelector import StepSelector
from Detectors.Preprocessor import Preprocessor

def train(output, task=None, detector=None, inputFiles=None, models=None, parse=None,
          processUnmerging=None, processModifiers=None, isSingleStage=False, 
          bioNLPSTParams=None, preprocessorParams=None, exampleStyles=None, 
          classifierParams=None,  doFullGrid=False, deleteOutput=False, copyFrom=None, 
          log="log.txt", step=None, omitSteps=None, debug=False, connection=None):
    # Insert default arguments where needed
    inputFiles = Parameters.get(inputFiles, {"train":None, "devel":None, "test":None})
    models = Parameters.get(models, {"devel":None, "test":None})
    exampleStyles = Parameters.get(exampleStyles, {"examples":None, "trigger":None, "edge":None, "unmerging":None, "modifiers":None})
    classifierParams = Parameters.get(classifierParams, {"examples":None, "trigger":None, "recall":None, "edge":None, "unmerging":None, "modifiers":None})
    processUnmerging = getDefinedBool(processUnmerging)
    processModifiers = getDefinedBool(processModifiers)
    # Initialize working directory
    workdir(output, deleteOutput, copyFrom, log)
    # Get task specific parameters
    detector, processUnmerging, processModifiers, isSingleStage, bioNLPSTParams, preprocessorParams, exampleStyles, classifierParams, removeNamesFromEmpty = getTaskSettings(task, 
        detector, processUnmerging, processModifiers, isSingleStage, bioNLPSTParams, preprocessorParams, inputFiles, exampleStyles, classifierParams)   
    if task != None: task = task.replace("-MINI", "").replace("-FULL", "")
    # Define processing steps
    selector, detectorSteps, omitDetectorSteps = getSteps(step, omitSteps, ["TRAIN", "DEVEL", "EMPTY", "TEST"])
    
    # Initialize the detector
    detector, detectorName = getDetector(detector)
    detector = detector() # initialize object
    detector.debug = debug
    detector.bioNLPSTParams = detector.getBioNLPSharedTaskParams(bioNLPSTParams)
    #detector.useBioNLPSTFormat = useBioNLPSTFormat # classify-output and grid evaluation in ST-format
    #detector.stWriteScores = True # write confidence scores into additional st-format files
    connection = getConnection(connection)
    detector.setConnection(connection)
    connection.debug = debug
    if deleteOutput:
        connection.clearWorkDir()
    
    # Train
    if selector.check("TRAIN"):
        print >> sys.stderr, "----------------------------------------------------"
        print >> sys.stderr, "------------------ Train Detector ------------------"
        print >> sys.stderr, "----------------------------------------------------"
        if isSingleStage:
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
                if preprocessorParams != None:
                    preprocessor = Preprocessor()
                    model.addStr("preprocessorParams", Parameters.toString(preprocessor.getParameters(preprocessorParams)))
                model.save()
                model.close()
    if selector.check("DEVEL"):
        print >> sys.stderr, "----------------------------------------------------"
        print >> sys.stderr, "------------ Check devel classification ------------"
        print >> sys.stderr, "----------------------------------------------------"
        detector.classify(inputFiles["devel"], models["devel"], "classification-devel/devel-events", goldData=inputFiles["devel"], fromStep=detectorSteps["DEVEL"], workDir="classification-devel")
    if selector.check("EMPTY"):
        # By passing an emptied devel set through the prediction system, we can check that we get the same predictions
        # as in the DEVEL step, ensuring the model does not use leaked information.
        print >> sys.stderr, "----------------------------------------------------"
        print >> sys.stderr, "------------ Empty devel classification ------------"
        print >> sys.stderr, "----------------------------------------------------"
        detector.classify(getEmptyCorpus(inputFiles["devel"], removeNames=removeNamesFromEmpty), models["devel"], "classification-empty/devel-empty-events", fromStep=detectorSteps["EMPTY"], workDir="classification-empty")
    if selector.check("TEST"):
        print >> sys.stderr, "----------------------------------------------------"
        print >> sys.stderr, "------------- Test set classification --------------"
        print >> sys.stderr, "----------------------------------------------------"
        if inputFiles["test"] == None or not os.path.exists(inputFiles["test"]):
            print >> sys.stderr, "Skipping, test file", inputFiles["test"], "does not exist"
        else:
            detector.bioNLPSTParams["scores"] = False # the evaluation server doesn't like additional files
            detector.classify(inputFiles["test"], models["test"], "classification-test/test-events", fromStep=detectorSteps["TEST"], workDir="classification-test")
            if detector.bioNLPSTParams["convert"]:
                Utils.STFormat.Compare.compare("classification-test/test-events.tar.gz", "classification-devel/devel-events.tar.gz", "a2")

def getSteps(step, omitSteps, mainSteps):
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
        detector = model.getStr("detector")
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


def workdir(path, deleteIfExists=True, copyFrom=None, log="log.txt"):
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
    # Open log (if a relative path, it goes under workdir)
    if log != None:
        Stream.openLog(log)
    else:
        print >> sys.stderr, "No logging"
    return path

def getTaskSettings(task, detector, processUnmerging, processModifiers, isSingleStage,
                    bioNLPSTParams, preprocessorParams, 
                    inputFiles, exampleStyles, classifierParameters):
    if task != None:
        print >> sys.stderr, "Determining training settings for task", task
        assert task.replace("-MINI", "") in ["GE09", "GE09.1", "GE09.2", "GE", "GE.1", "GE.2", "EPI", "ID", "BB", "BI", "BI-FULL", "CO", "REL", "REN", "DDI", "DDI-FULL"], task
    
        fullTaskId = task
        subTask = 2
        if "." in task:
            task, subTask = task.split(".")
            subTask = int(subTask)
        #dataPath = os.path.expanduser("~/biotext/BioNLP2011/data/main-tasks/")
        dataPath = Settings.CORPUS_DIR
        # Optional overrides for input files
        #if inputFiles["devel"] == None: inputFiles["devel"] = dataPath + task + "/" + task + "-devel.xml"
        #if inputFiles["train"] == None: inputFiles["train"] = dataPath + task + "/" + task + "-train.xml"
        #if inputFiles["test"] == None: inputFiles["test"] = dataPath + task + "/" + task + "-test.xml"
        if inputFiles["devel"] == None and inputFiles["devel"] != "None": 
            inputFiles["devel"] = os.path.join(dataPath, task.replace("-FULL", "") + "-devel.xml")
        if inputFiles["train"] == None and inputFiles["train"] != "None":
            if task == "ID": # add GE-task data to the ID training set
                inputFiles["train"] = Catenate.catenate([os.path.join(dataPath, "ID-train.xml"),
                                                         os.path.join(dataPath, "GE-devel.xml"),
                                                         os.path.join(dataPath, "GE-train.xml")], 
                                                        "training/ID-train-and-GE-devel-and-train.xml.gz", fast=True)
            else:
                inputFiles["train"] = os.path.join(dataPath, task.replace("-FULL", "") + "-train.xml")
        if inputFiles["test"] == None and inputFiles["test"] != "None": 
            inputFiles["test"] = os.path.join(dataPath, task.replace("-FULL", "") + "-test.xml")
        
        task = task.replace("-MINI", "")
        # Example generation parameters
        if detector == None:
            detector = "Detectors.EventDetector"
            if task == "CO":
                detector = "Detectors.CODetector"
            elif task in ["REN", "BI", "DDI"]:
                detector = "Detectors.EdgeDetector"
                isSingleStage = True
            print >> sys.stderr, "Detector undefined, using default '" + detector + "' for task", fullTaskId
        if bioNLPSTParams == None and task not in ["DDI", "DDI-FULL"]:
            bioNLPSTParams = "convert:evaluate:scores"
        if preprocessorParams == None:
            preprocessorParams = ["intermediateFiles"]
            if task in ["BI", "BI-FULL", "BB", "DDI", "DDI-FULL"]:
                preprocessorParams += ["omitSteps=NER,DIVIDE-SETS"]
            else:
                preprocessorParams += ["omitSteps=DIVIDE-SETS"]
                preprocessorParams += ["PARSE.requireEntities"] # parse only sentences where BANNER found an entity
            preprocessorParams = ":".join(preprocessorParams)
            print >> sys.stderr, "Preprocessor parameters undefined, using default '" + preprocessorParams + "' for task", fullTaskId
        if processUnmerging == None and not isSingleStage:
            processUnmerging = True
            if task in ["CO", "REL", "BB", "BI-FULL", "DDI-FULL"]:
                processUnmerging = False
            print >> sys.stderr, "Unmerging undefined, using default", processUnmerging, "for task", fullTaskId
        if processModifiers == None:
            processModifiers = False
            if task in ["GE", "EPI", "ID"]: 
                processModifiers = True
            print >> sys.stderr, "Modifier prediction undefined, using default", processModifiers, " for task", fullTaskId
        if exampleStyles["examples"] == None and isSingleStage:
            if task == "REN":
                exampleStyles["examples"] = "trigger_features:typed:no_linear:entities:noMasking:maxFeatures:bacteria_renaming:maskTypeAsProtein=Gene"
            elif task == "BI":
                exampleStyles["examples"] = "trigger_features:typed:directed:no_linear:entities:noMasking:maxFeatures:bi_limits"
            elif task == "DDI":
                exampleStyles["examples"] = "trigger_features:typed:no_linear:entities:noMasking:maxFeatures:ddi_features:ddi_mtmx:filter_shortest_path=conj_and"
            print >> sys.stderr, "Single-stage examples style undefined, using default '" + exampleStyles["examples"] + "' for task", fullTaskId
        if exampleStyles["edge"] == None and not isSingleStage:
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
                exampleStyles["edge"]="trigger_features:typed:directed:no_linear:entities:noMasking:maxFeatures:rel_limits:rel_features"
            elif task == "CO":
                exampleStyles["edge"]="trigger_features:typed:directed:no_linear:entities:noMasking:maxFeatures:co_limits"
            elif task == "BI-FULL":
                exampleStyles["edge"] = "trigger_features:typed:directed:no_linear:entities:noMasking:maxFeatures:bi_limits"
            elif task == "DDI-FULL":
                exampleStyles["edge"] = "trigger_features:typed:no_linear:entities:noMasking:maxFeatures:ddi_features:filter_shortest_path=conj_and"
            else:
                exampleStyles["edge"]="trigger_features:typed:directed:no_linear:entities:noMasking:maxFeatures"
        if exampleStyles["trigger"] == None and not isSingleStage:
            print >> sys.stderr, "Trigger example style undefined, using default for task", fullTaskId
            if task in ["GE09", "GE"] and subTask == 1:
                exampleStyles["trigger"] = "genia_task1"
            elif task == "EPI":
                exampleStyles["trigger"] = "epi_merge_negated"
            elif task == "BB":
                exampleStyles["trigger"] = "bb_features:build_for_nameless:wordnet"
            elif task == "REL":
                exampleStyles["trigger"] = "rel_features"
            elif task == "CO":
                options.triggerExampleBuilder = "PhraseTriggerExampleBuilder"
            elif task in ["BI-FULL", "DDI-FULL"]:
                exampleStyles["trigger"] = "build_for_nameless:names"
        if exampleStyles["unmerging"] == None and not isSingleStage:
           exampleStyles["unmerging"] = "trigger_features:typed:directed:no_linear:entities:genia_limits:noMasking:maxFeatures"
           #if task == "ID": # Do not use catenated GE for unmerging examples
           #    exampleStyles["unmerging"] += ":sentenceLimit=id.ID"
        # Classifier parameters
        if classifierParameters["examples"] == None and isSingleStage:
            print >> sys.stderr, "Classifier parameters for single-stage examples undefined, using default for task", fullTaskId
            if task == "REN":
                classifierParameters["examples"] = "10,100,1000,2000,3000,4000,4500,5000,5500,6000,7500,10000,20000,25000,28000,50000,60000"
            elif task == "BI":
                classifierParameters["examples"] = "10,100,1000,2500,5000,7500,10000,20000,25000,28000,50000,60000,65000,80000,100000,150000"
            elif task == "DDI":
                classifierParameters["examples"] = "c=10,100,1000,2500,4000,5000,6000,7500,10000,20000,25000,50000:TEES.threshold"
        if classifierParameters["trigger"] == None and not isSingleStage:
            print >> sys.stderr, "Classifier parameters for trigger examples undefined, using default for task", fullTaskId
            classifierParameters["trigger"] = "1000,5000,10000,20000,50000,80000,100000,150000,180000,200000,250000,300000,350000,500000,1000000"
        if classifierParameters["recall"] == None and not isSingleStage:
            print >> sys.stderr, "Recall adjust parameter undefined, using default for task", fullTaskId
            classifierParameters["recall"] = "0.5,0.6,0.65,0.7,0.85,1.0,1.1,1.2"
            if task == "CO":
                classifierParameters["recall"] = "0.8,0.9,0.95,1.0"
        if classifierParameters["edge"] == None and not isSingleStage:
            print >> sys.stderr, "Classifier parameters for edge examples undefined, using default for task", fullTaskId
            classifierParameters["edge"] = "5000,7500,10000,20000,25000,27500,28000,29000,30000,35000,40000,50000,60000,65000"
            if task in ["REL", "CO"]:
                classifierParameters["edge"] = "10,100,1000,5000,7500,10000,20000,25000,28000,50000,60000,65000,100000,500000,1000000"
        if classifierParameters["unmerging"] == None and not isSingleStage:
            print >> sys.stderr, "Classifier parameters for unmerging examples undefined, using default for task", fullTaskId
            classifierParameters["unmerging"] = "1,10,100,500,1000,1500,2500,5000,10000,20000,50000,80000,100000"
        if classifierParameters["modifiers"] == None and not isSingleStage:
            print >> sys.stderr, "Classifier parameters for modifier examples undefined, using default for task", fullTaskId
            classifierParameters["modifiers"] = "5000,10000,20000,50000,100000"
    
    if isSingleStage and exampleStyles["examples"] != None and "names" in exampleStyles["examples"]:
        removeNamesFromEmpty = True
    elif (not isSingleStage) and exampleStyles["trigger"] != None and "names" in exampleStyles["trigger"]:
        removeNamesFromEmpty = True
    else:
        removeNamesFromEmpty = False
    return detector, processUnmerging, processModifiers, isSingleStage, bioNLPSTParams, preprocessorParams, exampleStyles, classifierParameters, removeNamesFromEmpty

def getDefinedBool(string):
    if string in (True, False): # already defined
        return string
    assert string in (None, "True", "False") # undefined or needs to be converted to bool
    if string == None:
        return None
    elif string == "True":
        return True
    else:
        return False

def getDefinedBoolOption(option, opt, value, parser):
    if value == None:
        setattr(parser.values, option.dest, True)
    else:
        setattr(parser.values, option.dest, getDefinedBool(value))

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
        
    from optparse import OptionParser, OptionGroup
    optparser = OptionParser()
    # main options
    group = OptionGroup(optparser, "Main Options", "")
    group.add_option("-t", "--task", default=None, dest="task", help="task number")
    group.add_option("-p", "--parse", default="McCC", dest="parse", help="Parse XML element name")
    group.add_option("-c", "--connection", default=None, dest="connection", help="")
    optparser.add_option_group(group)
    # input
    group = OptionGroup(optparser, "Input Files", "If these are undefined, a task (-t) specific corpus file will be used")
    group.add_option("--trainFile", default=None, dest="trainFile", help="")
    group.add_option("--develFile", default=None, dest="develFile", help="")
    group.add_option("--testFile", default=None, dest="testFile", help="")
    optparser.add_option_group(group)
    # output
    group = OptionGroup(optparser, "Output Files", "Files created from training the detector")
    group.add_option("-o", "--output", default=None, dest="output", help="Output directory for intermediate files")
    group.add_option("--develModel", default="model-devel", dest="develModel", help="Model trained on 'trainFile', with parameters optimized on 'develFile'")
    group.add_option("--testModel", default="model-test", dest="testModel", help="Model trained on 'trainFile'+'develFile', with parameters from 'develModel'")
    optparser.add_option_group(group)
    # Example builders
    group = OptionGroup(optparser, "Detector to train", "")
    group.add_option("--detector", default=None, dest="detector", help="the detector class to use")
    group.add_option("--singleStage", default=False, action="store_true", dest="singleStage", help="'detector' is a single stage detector")
    group.add_option("--noBioNLPSTFormat", default=False, action="store_true", dest="noBioNLPSTFormat", help="Do not output BioNLP Shared Task format version (a1, a2, txt)")
    group.add_option("--bioNLPSTParams", default=None, dest="bioNLPSTParams", help="")
    group.add_option("--preprocessorParams", default=None, dest="preprocessorParams", help="")
    optparser.add_option_group(group)
    # Example builder parameters
    event = OptionGroup(optparser, "Event Detector Options (used when not using '--singleStage')", "")
    single = OptionGroup(optparser, "Single Stage Detector Options (used when using '--singleStage')", "")
    single.add_option("--exampleStyle", default=None, dest="exampleStyle", help="Single-stage detector example style")
    event.add_option("-u", "--unmerging", default=None, action="callback", callback=getDefinedBoolOption, dest="unmerging", help="SVM unmerging")
    event.add_option("-m", "--modifiers", default=None, action="callback", callback=getDefinedBoolOption, dest="modifiers", help="Train model for modifier detection")
    event.add_option("--triggerStyle", default=None, dest="triggerStyle", help="Event detector trigger example style")
    event.add_option("--edgeStyle", default=None, dest="edgeStyle", help="Event detector edge example style")
    event.add_option("--unmergingStyle", default=None, dest="unmergingStyle", help="Event detector unmerging example style")
    event.add_option("--modifierStyle", default=None, dest="modifierStyle", help="Event detector modifier example style")
    # Classifier parameters
    single.add_option("-e", "--exampleParams", default=None, dest="exampleParams", help="Single-stage detector parameters")
    event.add_option("-r", "--triggerParams", default=None, dest="triggerParams", help="Trigger detector c-parameter values")
    event.add_option("-a", "--recallAdjustParams", default=None, dest="recallAdjustParams", help="Recall adjuster parameter values")
    event.add_option("-d", "--edgeParams", default=None, dest="edgeParams", help="Edge detector c-parameter values")
    event.add_option("-n", "--unmergingParams", default=None, dest="unmergingParams", help="Unmerging c-parameter values")
    event.add_option("-f", "--modifierParams", default=None, dest="modifierParams", help="Modifier c-parameter values")
    event.add_option("--fullGrid", default=False, action="store_true", dest="fullGrid", help="Full grid search for parameters")
    optparser.add_option_group(single)
    optparser.add_option_group(event)
    # Debugging and process control
    debug = OptionGroup(optparser, "Debug and Process Control Options", "")
    debug.add_option("--step", default=None, dest="step", help="Step to start processing from, with optional substep (STEP=SUBSTEP). Step values are TRAIN, DEVEL, EMPTY and TEST.")
    debug.add_option("--omitSteps", default=None, dest="omitSteps", help="")
    debug.add_option("--copyFrom", default=None, dest="copyFrom", help="Copy this directory as template")
    debug.add_option("--log", default="log.txt", dest="log", help="Log file name")
    debug.add_option("--noLog", default=False, action="store_true", dest="noLog", help="Do not keep a log file")
    debug.add_option("--clearAll", default=False, action="store_true", dest="clearAll", help="Delete all files")
    debug.add_option("--debug", default=False, action="store_true", dest="debug", help="More verbose output")
    optparser.add_option_group(debug)
    (options, args) = optparser.parse_args()
    
    assert options.output != None
    if options.noLog: options.log = None
    train(options.output, options.task, options.detector, 
          inputFiles={"devel":options.develFile, "train":options.trainFile, "test":options.testFile},
          models={"devel":options.develModel, "test":options.testModel}, parse=options.parse,
          processUnmerging=options.unmerging, processModifiers=options.modifiers, isSingleStage=options.singleStage, 
          bioNLPSTParams=options.bioNLPSTParams, preprocessorParams=options.preprocessorParams,
          exampleStyles={"examples":options.exampleStyle, "trigger":options.triggerStyle, "edge":options.edgeStyle, "unmerging":options.unmergingStyle, "modifiers":options.modifierStyle},
          classifierParams={"examples":options.exampleParams, "trigger":options.triggerParams, "recall":options.recallAdjustParams, "edge":options.edgeParams, "unmerging":options.unmergingParams, "modifiers":options.modifierParams}, 
          doFullGrid=options.fullGrid, deleteOutput=options.clearAll, copyFrom=options.copyFrom, 
          log=options.log, step=options.step, omitSteps=options.omitSteps, debug=options.debug, connection=options.connection)