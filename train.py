#!/usr/bin/env python

"""
Train a new model for event or relation detection.
"""
import sys, os
from Utils.InteractionXML.DeleteElements import getEmptyCorpus
import Utils.InteractionXML.Catenate as Catenate
import Utils.Stream as Stream
import Utils.Settings as Settings
import Utils.Parameters as Parameters
from Utils.Connection.Connection import getConnection
import Utils.STFormat.Compare
import Utils.InteractionXML.Subset
import shutil
import atexit
import types
import tempfile
from Core.Model import Model
from Detectors.StepSelector import StepSelector
from Detectors.Preprocessor import Preprocessor
from Detectors.StructureAnalyzer import StructureAnalyzer
from Detectors.SingleStageDetector import SingleStageDetector

def train(output, task=None, detector=None, inputFiles=None, models=None, parse=None,
          processUnmerging=None, processModifiers=None, 
          bioNLPSTParams=None, preprocessorParams=None, exampleStyles=None, 
          classifierParams=None,  doFullGrid=False, deleteOutput=False, copyFrom=None, 
          log="log.txt", step=None, omitSteps=None, debug=False, connection=None, subset=None, folds=None):
    """
    Train a new model for event or relation detection.
    
    @param output: A directory where output files will appear.
    @param task: If defined, overridable default settings are used for many of the training parameters. Must be one of the supported TEES tasks.
    @param detector: a Detector object, or a string defining one to be imported
    @param inputFiles: A dictionary of file names, with keys "train", "devel" and, "test"
    @param models: A dictionary of file names defining the place for the new models, with keys "devel" and, "test"
    @param parse: The parse element name in the training interaction XML
    @param processUnmerging: Use the unmerging step of EventDetector. True, False or None for task default.
    @param processModifiers: Use the modifier detection step of EventDetector. True, False or None for task default.
    @param bioNLPSTParams: Parameters controlling BioNLP ST format output.
    @param preprocessorParams: Parameters controlling the preprocessor. Not used for training, but saved to the model for use when classifying.
    @param exampleStyles: A parameter set for controlling example builders.
    @param classifierParams: A parameter set for controlling classifiers.
    @param doFullGrid: Whether all parameters, as opposed to just recall adjustment, are tested in the EventDetector grid search.
    @param deleteOutput: Remove an existing output directory
    @param copyFrom: Copy an existing output directory for use as a template
    @param log: An optional alternative name for the log file. None is for no logging.
    @param step: A step=substep pair, where the steps are "TRAIN", "DEVEL", "EMPTY" and "TEST"
    @param omitSteps: step=substep parameters, where multiple substeps can be defined.
    @param debug: In debug mode, more output is shown, and some temporary intermediate files are saved
    @param connection: A parameter set defining a local or remote connection for training the classifier
    @param subset: A parameter set for making subsets of input files
    """
    # Insert default arguments where needed
    inputFiles = setDictDefaults(inputFiles, {"train":None, "devel":None, "test":None})
    models = setDictDefaults(models, {"devel":None, "test":None})
    exampleStyles = setDictDefaults(exampleStyles, {"examples":None, "trigger":None, "edge":None, "unmerging":None, "modifiers":None})
    classifierParams = setDictDefaults(classifierParams, {"examples":None, "trigger":None, "recall":None, "edge":None, "unmerging":None, "modifiers":None})
    subset = setDictDefaults(Parameters.get(subset), {"train":None, "devel":None, "test":None, "seed":0, "all":None})
    folds = setDictDefaults(folds, {"train":None, "devel":None, "test":None})
    processUnmerging = getDefinedBool(processUnmerging)
    processModifiers = getDefinedBool(processModifiers)
    # Initialize working directory
    workdir(output, deleteOutput, copyFrom, log)
    # Get task specific parameters
    detector, bioNLPSTParams, preprocessorParams = getTaskSettings(task, detector, 
        bioNLPSTParams, preprocessorParams, inputFiles, exampleStyles, classifierParams)
    # Learn training settings from input files
    detector = learnSettings(inputFiles, detector, classifierParams)   
    # Get corpus subsets   
    getFolds(inputFiles, folds)
    getSubsets(inputFiles, subset)
    if task != None: 
        task = task.replace("-FULL", "")
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
        if isinstance(detector, SingleStageDetector):
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
            if model != None and os.path.exists(model):
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
        #detector.bioNLPSTParams["scores"] = False # the evaluation server doesn't like additional files
        detector.classify(inputFiles["devel"], models["devel"], "classification-devel/devel", goldData=inputFiles["devel"], fromStep=detectorSteps["DEVEL"], workDir="classification-devel")
    if selector.check("EMPTY"):
        # By passing an emptied devel set through the prediction system, we can check that we get the same predictions
        # as in the DEVEL step, ensuring the model does not use leaked information.
        print >> sys.stderr, "----------------------------------------------------"
        print >> sys.stderr, "------------ Empty devel classification ------------"
        print >> sys.stderr, "----------------------------------------------------"
        #detector.bioNLPSTParams["scores"] = False # the evaluation server doesn't like additional files
        detector.classify(getEmptyCorpus(inputFiles["devel"], removeNames=("names" in str(exampleStyles["examples"]) or "names" in str(exampleStyles["trigger"])) ), models["devel"], "classification-empty/devel-empty", fromStep=detectorSteps["EMPTY"], workDir="classification-empty")
    if selector.check("TEST"):
        print >> sys.stderr, "----------------------------------------------------"
        print >> sys.stderr, "------------- Test set classification --------------"
        print >> sys.stderr, "----------------------------------------------------"
        if inputFiles["test"] == None or not os.path.exists(inputFiles["test"]):
            print >> sys.stderr, "Skipping, test file", inputFiles["test"], "does not exist"
        else:
            #detector.bioNLPSTParams["scores"] = False # the evaluation server doesn't like additional files
            detector.classify(inputFiles["test"], models["test"], "classification-test/test", fromStep=detectorSteps["TEST"], workDir="classification-test")
            if detector.bioNLPSTParams["convert"]:
                Utils.STFormat.Compare.compare("classification-test/test-events.tar.gz", "classification-devel/devel-events.tar.gz", "a2")

def setDictDefaults(dictionary, defaults):
    if dictionary == None:
        return defaults.copy()
    for key in defaults:
        if key not in dictionary:
            dictionary[key] = defaults[key]
    return dictionary

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

def getSubsets(inputFiles, subset, outdir="training"):
    for dataset in ("devel", "train", "test"):
        if inputFiles[dataset] not in [None, "None"] and (subset[dataset] != None or subset["all"] != None):
            fraction = subset[dataset]
            if fraction == None:
                fraction = subset["all"]
            if outdir == None:
                outdir = tempfile.mkdtemp()
            outFileName = os.path.join(outdir, "subset_" + str(fraction) + "_" + str(subset["seed"]) + "_" + os.path.basename(inputFiles[dataset]))
            if not os.path.exists(outFileName):
                Utils.InteractionXML.Subset.getSubset(inputFiles[dataset], outFileName, float(fraction), subset["seed"])
            inputFiles[dataset] = outFileName

def getFolds(inputFiles, folds, outdir="training"):
    if folds["train"] == None or folds["devel"] == None:
        return
    #assert inputFiles["devel"] in [None, "None"]
    #assert inputFiles["test"] in [None, "None"]
    origTrainFile = inputFiles["train"]
    for dataset in ("devel", "train", "test"):
        currentFold = folds[dataset]
        if currentFold == "None":
            inputFiles[dataset] = None
            continue
        elif currentFold == None:
            continue
        if type(currentFold) in types.StringTypes:
            currentFold = [currentFold]
        idString = "_".join(currentFold)
        idString = idString.replace("train", "t")
        if outdir == None:
            outdir = tempfile.mkdtemp()
        outFileName = os.path.join(outdir, dataset + "-" + idString + ".xml")
        if not os.path.exists(outFileName):
            Utils.InteractionXML.Subset.getSubset(origTrainFile, outFileName, attributes={"set":currentFold})
        inputFiles[dataset] = outFileName

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

def learnSettings(inputFiles, detector, classifierParameters):
    if detector == None:
        print >> sys.stderr, "*** Analyzing input files to determine training settings ***"
        structureAnalyzer = StructureAnalyzer()
        if not os.path.exists("training/structure.txt"): 
            datasets = sorted(filter(None, [inputFiles["train"], inputFiles["devel"]]))
            print >> sys.stderr, "input files:", datasets
            structureAnalyzer.analyze(datasets)
            print >> sys.stderr, structureAnalyzer.toString()
            structureAnalyzer.save(None, "training/structure.txt")
        else:
            print >> sys.stderr, "Using existing analysis from training/structure.txt"
            structureAnalyzer.load(None, "training/structure.txt")
    
    # Choose detector
    if detector == None:
        if "ENTITY" in structureAnalyzer.targets and "INTERACTION" in structureAnalyzer.targets:
            detector = "Detectors.EventDetector"
        elif "ENTITY" in structureAnalyzer.targets:
            detector = "Detectors.EntityDetector"
        elif "INTERACTION" in structureAnalyzer.targets:
            detector = "Detectors.EdgeDetector"
        else:
            assert False, structureAnalyzer.targets
    print >> sys.stderr, "Using detector '" + str(detector) + "'"
    
    # Set default parameters
    if detector == "Detectors.EventDetector":
        classifierParameters["unmerging"] = Parameters.cat("c=1,10,100,500,1000,1500,2500,5000,10000,20000,50000,80000,100000", classifierParameters["unmerging"], "Classifier parameters for unmerging")        
        classifierParameters["modifiers"] = Parameters.cat("c=5000,10000,20000,50000,100000", classifierParameters["modifiers"], "Classifier parameters for modifiers")
        classifierParameters["edge"] = Parameters.cat("c=1000,4500,5000,7500,10000,20000,25000,27500,28000,29000,30000,35000,40000,50000,60000,65000", classifierParameters["edge"], "Classifier parameters for edges")
        classifierParameters["trigger"] = Parameters.cat("c=1000,5000,10000,20000,50000,80000,100000,150000,180000,200000,250000,300000,350000,500000,1000000", classifierParameters["trigger"], "Classifier parameters for triggers")
        classifierParameters["recall"] = Parameters.cat("0.5,0.6,0.65,0.7,0.85,1.0,1.1,1.2", classifierParameters["recall"], "Recall adjustment parameters")
    elif detector == "Detectors.EntityDetector":
        classifierParameters["examples"] = Parameters.cat("c=1000,5000,10000,20000,50000,80000,100000,150000,180000,200000,250000,300000,350000,500000,1000000", classifierParameters["examples"], "Classifier parameters for entities")
    elif detector == "Detectors.EdgeDetector":
        classifierParameters["examples"] = Parameters.cat("c=1000,4500,5000,7500,10000,20000,25000,27500,28000,29000,30000,35000,40000,50000,60000,65000", classifierParameters["examples"], "Classifier parameters for edges")

    return detector

def getTaskSettings(task, detector, bioNLPSTParams, preprocessorParams, 
                    inputFiles, exampleStyles, classifierParameters):
    if task != None:
        print >> sys.stderr, "*** Defining training settings for task", task, "***"
        fullTaskId = task
        subTask = 2
        if "." in task:
            task, subTask = task.split(".")
            subTask = int(subTask)
        dataPath = Settings.CORPUS_DIR
        for dataset in ["devel", "train", "test"]:
            if inputFiles[dataset] == None and inputFiles[dataset] != "None":
                inputFiles[dataset] = os.path.join(dataPath, task.replace("-FULL", "") + "-"+dataset+".xml")
            if task == "ID11" and dataset == "train":
                inputFiles[dataset] = Catenate.catenate([os.path.join(dataPath, "ID11-train.xml"), os.path.join(dataPath, "GE11-devel.xml"),
                                                         os.path.join(dataPath, "GE11-train.xml")], "training/ID11-train-and-GE11-devel-and-train.xml.gz", fast=True)
            if inputFiles[dataset] == "None":
                inputFiles[dataset] = None
            if inputFiles[dataset] != None and not os.path.exists(inputFiles[dataset]):
                inputFiles[dataset] = None
                print >> sys.stderr, "Input file", inputFiles[dataset], "for set '" + dataset + "' does not exist, skipping."
        assert inputFiles["train"] != None # at least training set must exist
        # Example generation parameters
        if task == "CO11":
            detector = "Detectors.CODetector"
        elif task in ["BI11-FULL", "DDI11-FULL"]:
            detector = "Detectors.EventDetector"
        
        # BioNLP Shared Task and preprocessing parameters
        if task == "BI11-FULL":
            bioNLPSTParams = Parameters.cat(bioNLPSTParams, "convert:scores", "BioNLP Shared Task / " + fullTaskId, ["default"]) # the shared task evaluator is not designed for predicted entities
        elif task == "REL11":
            bioNLPSTParams = Parameters.cat(bioNLPSTParams, "convert:evaluate:scores:a2Tag=rel", "BioNLP Shared Task / " + fullTaskId, ["default"])
        elif task not in ["DDI11", "DDI11-FULL", "DDI13"]:
            bioNLPSTParams = Parameters.cat(bioNLPSTParams, "convert:evaluate:scores", "BioNLP Shared Task / " + fullTaskId, ["default"])
        
        # Preprocessing parameters
        if task in ["BI11", "BI11-FULL", "BB11", "DDI11", "DDI11-FULL"]:
            Parameters.cat("intermediateFiles:omitSteps=NER,DIVIDE-SETS", preprocessorParams, "Preprocessor /" + fullTaskId, ["default"])
        else: # parse only sentences where BANNER found an entity
            Parameters.cat("intermediateFiles:omitSteps=DIVIDE-SETS:PARSE.requireEntities", preprocessorParams, "Preprocessor /" + fullTaskId, ["default"])
        
        # Example style parameters for single-stage tasks
        if task == "REN11":
            exampleStyles["examples"] = Parameters.cat("undirected:bacteria_renaming:maskTypeAsProtein=Gene", exampleStyles["examples"], "Single-stage example style / " + fullTaskId)
        elif task == "DDI11":
            exampleStyles["examples"] = Parameters.cat("drugbank_features:ddi_mtmx:filter_shortest_path=conj_and", exampleStyles["examples"], "Single-stage example style / " + fullTaskId)
        elif task == "DDI13":
            exampleStyles["examples"] = Parameters.cat("keep_neg:drugbank_features:filter_shortest_path=conj_and", exampleStyles["examples"], "Single-stage example style / " + fullTaskId)
        elif task == "BI11":
            exampleStyles["edge"] = Parameters.cat("bi_features", exampleStyles["edge"], "Edge example style / " + fullTaskId)
        # Edge style
        if task in ["GE09", "GE11", "GE13"] and subTask == 1:
            exampleStyles["edge"] = Parameters.cat("genia_features:genia_task1", exampleStyles["edge"])
        elif task in ["GE09", "GE11", "GE13"]:
            exampleStyles["edge"] = Parameters.cat("genia_features", exampleStyles["edge"])
        elif task == "REL11":
            exampleStyles["edge"] = Parameters.cat("rel_features", exampleStyles["edge"], "Edge example style / " + fullTaskId)
        elif task == "DDI11-FULL":
            exampleStyles["edge"] = Parameters.cat("drugbank_features:filter_shortest_path=conj_and", exampleStyles["edge"], "Edge example style / " + fullTaskId)
        elif task == "CO11":
            exampleStyles["edge"] = Parameters.cat("co_features", exampleStyles["edge"], "Edge example style / " + fullTaskId)
        elif task == "BI11-FULL":
            exampleStyles["edge"] = Parameters.cat("bi_features", exampleStyles["edge"], "Edge example style / " + fullTaskId)
        # Trigger style
        if task in ["GE09", "GE11", "GE13"] and subTask == 1:
            exampleStyles["trigger"] = Parameters.cat("genia_task1", exampleStyles["trigger"], "Trigger example style / " + fullTaskId)
        elif task in ["EPI11", "PC13"]:
            exampleStyles["trigger"] = Parameters.cat("epi_merge_negated", exampleStyles["trigger"], "Trigger example style / " + fullTaskId)
        elif task == "BB11": # "bb_features:build_for_nameless:wordnet"
            exampleStyles["trigger"] = Parameters.cat("bb_features:build_for_nameless", exampleStyles["trigger"], "Trigger example style / " + fullTaskId)
        elif task == "BB13T3": # "bb_features:build_for_nameless:wordnet"
            exampleStyles["trigger"] = Parameters.cat("bb_features:build_for_nameless", exampleStyles["trigger"], "Trigger example style / " + fullTaskId)
        elif task == "REL11":
            exampleStyles["trigger"] = Parameters.cat("rel_features", exampleStyles["trigger"], "Trigger example style / " + fullTaskId)
        elif task in ["BI11-FULL", "DDI11-FULL"]:
            exampleStyles["trigger"] = "build_for_nameless:names"        
        # Classifier parameters
        if task == "DDI11":
            classifierParameters["examples"] = Parameters.cat("c=10,100,1000,2500,4000,5000,6000,7500,10000,20000,25000,50000:TEES.threshold", classifierParameters["examples"], "Classifier parameters for single-stage examples" + fullTaskId)
        #elif task == "DDI13":
        #    classifierParameters["examples"] = Parameters.cat("c=10,100,1000,2500,4000,5000,6000,7500,10000,20000,25000,50000:TEES.threshold", classifierParameters["examples"], "Classifier parameters for single-stage examples" + fullTaskId)
        elif task == "CO11":
            classifierParameters["edge"] = Parameters.cat("c=1000,4500,5000,7500,10000,20000,25000,27500,28000,29000,30000,35000,40000,50000,60000,65000", classifierParameters["examples"], "Classifier parameters for edges / " + fullTaskId)
            classifierParameters["trigger"] = Parameters.cat("c=1000,5000,10000,20000,50000,80000,100000,150000,180000,200000,250000,300000,350000,500000,1000000", classifierParameters["examples"], "Classifier parameters for triggers / " + fullTaskId)
            classifierParameters["recall"] = Parameters.cat("0.8,0.9,0.95,1.0", classifierParameters["recall"], "Recall adjust / " + fullTaskId)
    
    return detector, bioNLPSTParams, preprocessorParams

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
    optparser = OptionParser(description="Train a new event/relation extraction model")
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
    #group.add_option("--singleStage", default=False, action="store_true", dest="singleStage", help="'detector' is a single stage detector")
    #group.add_option("--noBioNLPSTFormat", default=False, action="store_true", dest="noBioNLPSTFormat", help="Do not output BioNLP Shared Task format version (a1, a2, txt)")
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
    event.add_option("--subset", default=None, dest="subset", help="")
    event.add_option("--folds", default=None, dest="folds", help="")
    optparser.add_option_group(debug)
    (options, args) = optparser.parse_args()
    
    if options.testModel == "None":
        options.testModel = None
    
    assert options.output != None
    if options.noLog: options.log = None
    train(options.output, options.task, options.detector, 
          inputFiles={"devel":options.develFile, "train":options.trainFile, "test":options.testFile},
          models={"devel":options.develModel, "test":options.testModel}, parse=options.parse,
          processUnmerging=options.unmerging, processModifiers=options.modifiers, 
          bioNLPSTParams=options.bioNLPSTParams, preprocessorParams=options.preprocessorParams,
          exampleStyles={"examples":options.exampleStyle, "trigger":options.triggerStyle, "edge":options.edgeStyle, "unmerging":options.unmergingStyle, "modifiers":options.modifierStyle},
          classifierParams={"examples":options.exampleParams, "trigger":options.triggerParams, "recall":options.recallAdjustParams, "edge":options.edgeParams, "unmerging":options.unmergingParams, "modifiers":options.modifierParams}, 
          doFullGrid=options.fullGrid, deleteOutput=options.clearAll, copyFrom=options.copyFrom, 
          log=options.log, step=options.step, omitSteps=options.omitSteps, debug=options.debug, 
          connection=options.connection, subset=options.subset, folds=options.folds)
