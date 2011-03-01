from TriggerEdgeClassify import *

if __name__=="__main__":
    from optparse import OptionParser
    optparser = OptionParser()
    optparser.add_option("-e", "--test", default=None, dest="testFile", help="Test file in interaction xml")
    #optparser.add_option("-r", "--train", default=Settings.TrainFile, dest="trainFile", help="Train file in interaction xml")
    optparser.add_option("-o", "--output", default="/home/jari/biotext/BioNLP2011/support-analysis", dest="output", help="output directory")
    optparser.add_option("-a", "--task", default="1", dest="task", help="task number")
    optparser.add_option("-p", "--parse", default="split-McClosky", dest="parse", help="Parse XML element name")
    optparser.add_option("-t", "--tokenization", default=None, dest="tokenization", help="Tokenization XML element name")
    #optparser.add_option("-m", "--mode", default="BOTH", dest="mode", help="MODELS (recalculate SVM models), GRID (parameter grid search) or BOTH")
    # Classifier
    optparser.add_option("-c", "--classifier", default="Cls", dest="classifier", help="")
    #optparser.add_option("--csc", default="", dest="csc", help="")
    # Example builders
    optparser.add_option("-f", "--triggerExampleBuilder", default="GeneralEntityTypeRecognizerGztr", dest="triggerExampleBuilder", help="")
    optparser.add_option("-g", "--edgeExampleBuilder", default="MultiEdgeExampleBuilder", dest="edgeExampleBuilder", help="")
    # Feature params
    optparser.add_option("--triggerStyle", default="typed", dest="triggerStyle", help="")
    optparser.add_option("--edgeStyle", default=None, dest="edgeStyle", help="")
    # Id sets
    optparser.add_option("-v", "--triggerIds", default=None, dest="triggerIds", help="Trigger detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
    optparser.add_option("-w", "--edgeIds", default=None, dest="edgeIds", help="Edge detector SVM example class and feature id file stem (files = STEM.class_names and STEM.feature_names)")
    optparser.add_option("-m", "--triggerModel", default=Settings.TrainTriggerModel, dest="triggerModel", help="SVM-multiclass trigger model")
    optparser.add_option("-n", "--edgeModel", default=Settings.TrainEdgeModel, dest="edgeModel", help="SVM-multiclass edge (event argument) model")
    # Parameters to optimize
    optparser.add_option("-y", "--recallAdjustParams", default="0.5,0.6,0.65,0.7,0.85,1.0,1.1,1.2", dest="recallAdjustParams", help="Recall adjuster parameter values")
    # Shared task evaluation
    #optparser.add_option("-s", "--sharedTask", default=True, action="store_false", dest="sharedTask", help="Do Shared Task evaluation")
    optparser.add_option("--clearAll", default=False, action="store_true", dest="clearAll", help="Delete all files")
    (options, args) = optparser.parse_args()
    
    dataPath = "/home/jari/biotext/BioNLP2011/"
    dp = dataPath 
    data = {}
    data["REL"] = {"test-edge-model":dp + "tests/entrel/TriggerEdgeTestRelFeatures101119-testset/edge-models/model-c_10000",
                   "test-trigger-model":dp + "tests/entrel/TriggerEdgeTestRelFeatures101119-testset/trigger-models/model-c_150000",
                   "test-id-dir":dp + "tests/entrel/TriggerEdgeTestRelFeatures101119-testset/",
                   "devel-edge-model":dp + "tests/entrel/TriggerEdgeTestRelFeatures101119-develempty/edge-models/model-c_10000",
                   "devel-trigger-model":dp + "tests/entrel/TriggerEdgeTestRelFeatures101119-develempty/trigger-models/model-c_150000",
                   "devel-id-dir":dp + "tests/entrel/TriggerEdgeTestRelFeatures101119-develempty/"
                   }
    data["CO"] = {"test-edge-model":dp + "tests/CO/TriggerEdgeTest101119-testset/edge-models/model-c_100000",
                  "test-trigger-model":dp + "tests/CO/TriggerEdgeTest101119-testset/trigger-models/model-c_200000",
                  "test-id-dir":dp + "tests/CO/TriggerEdgeTest101119-testset/",
                  "devel-edge-model":dp + "tests/CO/TriggerEdgeTest101119-develempty/edge-models/model-c_100000",
                  "devel-trigger-model":dp + "tests/CO/TriggerEdgeTest101119-develempty/trigger-models/model-c_200000",
                  "devel-id-dir":dp + "tests/CO/TriggerEdgeTest101119-develempty/"
                  }
    
    targets = {}
    targets["GE"] = {"train":dp + "data/main-tasks/GE/GE-train.xml",
                     "devel":dp + "data/main-tasks/GE/GE-devel.xml",
                     "test":dp + "data/main-tasks/GE/GE-test.xml"}
    targets["EPI"] = {"train":dp + "data/main-tasks/EPI/EPI-train.xml",
                     "devel":dp + "data/main-tasks/EPI/EPI-devel.xml",
                     "test":dp + "data/main-tasks/EPI/EPI-test.xml"}
    targets["ID"] = {"train":dp + "data/main-tasks/ID/ID-train.xml",
                     "devel":dp + "data/main-tasks/ID/ID-devel.xml",
                     "test":dp + "data/main-tasks/ID/ID-test.xml"}
    targets["BB"] = {"train":dp + "data/main-tasks/BB/BB-train.xml",
                     "devel":dp + "data/main-tasks/BB/BB-devel.xml",
                     "test":dp + "data/main-tasks/BB/BB-test.xml"}
    targets["BI"] = {"train":dp + "data/main-tasks/BI/BI-train.xml",
                     "devel":dp + "data/main-tasks/BI/BI-devel.xml",
                     "test":dp + "data/main-tasks/BI/BI-test.xml"}
    # sup-tasks
    targets["CO"] = {"train":dp + "data/supporting-tasks/CO/co-train.xml",
                     "devel":dp + "data/supporting-tasks/CO/co-devel.xml",
                     "test":dp + "data/supporting-tasks/CO/co-test.xml"}
    targets["REL"] = {"train":dp + "data/supporting-tasks/REL/rel-train.xml",
                     "devel":dp + "data/supporting-tasks/REL/rel-devel.xml",
                     "test":dp + "data/supporting-tasks/REL/rel-test.xml"}
    targets["REN"] = {"train":dp + "data/supporting-tasks/REN/ren-train.xml",
                     "devel":dp + "data/supporting-tasks/REN/ren-devel.xml"}
    
    mainOutdir = options.output
    for task in ["REL", "CO"]:
        options.task = task
        if task == "REL":
            options.recallAdjustParams = 1.1
            options.edgeStyle = "trigger_features,typed,directed,no_linear,entities,noMasking,maxFeatures,rel_limits,rel_features"
            options.triggerStyle = "typed,rel_features"
            options.triggerExampleBuilder = "GeneralEntityTypeRecognizerGztr"
        elif task == "CO":
            options.recallAdjustParams = 0.95
            options.edgeStyle = "trigger_features,typed,directed,no_linear,entities,noMasking,maxFeatures,co_limits"
            options.triggerStyle = "typed"
            options.triggerExampleBuilder = "PhraseTriggerExampleBuilder"
        for trainedFor in ["devel", "test"]:
            for target in ["ID", "BI", "CO", "REL", "REN"]: #["GE", "EPI", "ID", "BI", "BB", "CO", "REL", "REN"]: #["ID", "GE"]: #["CO","REL"]: #["GE"]: #["GE", "EPI", "BI", "CO", "REL", "REN"]:
                for targetSet in ["test", "devel", "train"]:
                    if not targetSet in targets[target]:
                        print "Set", targetSet, "not defined for target", target
                    options.testFile = targets[target][targetSet]
                    options.output = mainOutdir + "/" + task + "-" + trainedFor + "-for-" + target + "-" + targetSet
                    options.triggerModel = data[task][trainedFor+"-trigger-model"]
                    options.edgeModel = data[task][trainedFor+"-edge-model"]
                    options.triggerIds = data[task][trainedFor+"-id-dir"] + "trigger-ids"
                    options.edgeIds = data[task][trainedFor+"-id-dir"] + "edge-ids"
                    if target in ["GE", "EPI", "ID", "BB"]:
                        options.parse = "split-mccc-preparsed"
                        options.tokenization = "split-mccc-preparsed"
                    elif target == "BI":
                        options.parse = "gold"
                        options.tokenization = "gold"
                    else:
                        options.parse = "split-McClosky"
                        options.tokenization = "split-McClosky"
                    classify(options)
