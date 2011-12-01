import sys, os
import shutil
from Detector import Detector
from TriggerDetector import TriggerDetector
from EdgeDetector import EdgeDetector
from Core.OptimizeParameters import getParameterCombinations
from Core.OptimizeParameters import getCombinationString
from Core.RecallAdjust import RecallAdjust
import Utils.Parameters as Parameters
import InteractionXML
import Evaluators.EvaluateInteractionXML as EvaluateInteractionXML
import STFormat.ConvertXML
import STFormat.Compare

class EventDetector(Detector):
    def __init__(self):
        Detector.__init__(self)
        self.triggerDetector = TriggerDetector()
        self.edgeDetector = EdgeDetector()
        self.STATE_COMPONENT_TRAIN = "COMPONENT_TRAIN"
        self.tag = "event-"
    
    def setCSCConnection(self, options, cscworkdir):
        self.triggerDetector.setCSCConnection(options, os.path.join(cscworkdir, "trigger"))
        self.edgeDetector.setCSCConnection(options, os.path.join(cscworkdir, "edge"))
    
    def train(self, trainData=None, optData=None, 
              model=None, combinedModel=None,
              triggerExampleStyle=None, edgeExampleStyle=None,
              triggerClassifierParameters=None, edgeClassifierParameters=None,
              recallAdjustParameters=None, fullGrid=False,
              parse=None, tokenization=None,
              fromStep=None, toStep=None):
        # Initialize the training process ##############################
        self.initVariables(trainData=trainData, optData=optData, model=model, combinedModel=combinedModel,
                           triggerExampleStyle=triggerExampleStyle, edgeExampleStyle=edgeExampleStyle,
                           triggerClassifierParameters=triggerClassifierParameters, 
                           edgeClassifierParameters=edgeClassifierParameters, 
                           recallAdjustParameters=recallAdjustParameters, 
                           fullGrid=fullGrid, parse=parse, tokenization=tokenization)
        # Begin the training process ####################################
        self.enterState(self.STATE_TRAIN, ["EXAMPLES", "BEGIN-MODEL", "END-MODEL", "BEGIN-COMBINED-MODEL", "GRID", "BEGIN-COMBINED-MODEL-FULLGRID", "END-COMBINED-MODEL"], fromStep, toStep)
        self.triggerDetector.enterState(self.STATE_COMPONENT_TRAIN)
        self.edgeDetector.enterState(self.STATE_COMPONENT_TRAIN)
        if self.checkStep("EXAMPLES"):
            self.model = self.initModel(self.model, 
                                         [("triggerExampleStyle", self.triggerDetector.tag+"example-style"), 
                                          ("triggerClassifierParameters", self.triggerDetector.tag+"classifier-parameters"),
                                          ("edgeExampleStyle", self.edgeDetector.tag+"example-style"), 
                                          ("edgeClassifierParameters", self.edgeDetector.tag+"classifier-parameters")])
            self.saveStr("parse", parse, self.model)
            self.combinedModel = self.initModel(self.combinedModel)
            self.triggerDetector.buildExamples(self.model, [optData, trainData], [self.triggerDetector.tag+"opt-examples.gz", self.triggerDetector.tag+"train-examples.gz"], saveIdsToModel=True)
            self.edgeDetector.buildExamples(self.model, [optData, trainData], [self.edgeDetector.tag+"opt-examples.gz", self.edgeDetector.tag+"train-examples.gz"], saveIdsToModel=True)
        # (Re-)open models in case we start after "EXAMPLES" step
        self.model = self.openModel(model, "a")
        self.combinedModel = self.openModel(combinedModel, "a")
        if self.checkStep("BEGIN-MODEL"):
            self.triggerDetector.beginModel(None, self.model, [self.triggerDetector.tag+"train-examples.gz"], self.triggerDetector.tag+"opt-examples.gz")
            self.edgeDetector.beginModel(None, self.model, [self.edgeDetector.tag+"train-examples.gz"], self.edgeDetector.tag+"opt-examples.gz")
        if self.checkStep("END-MODEL"):
            self.triggerDetector.endModel(None, self.model, self.triggerDetector.tag+"opt-examples.gz")
            self.edgeDetector.endModel(None, self.model, self.edgeDetector.tag+"opt-examples.gz")
        if self.checkStep("BEGIN-COMBINED-MODEL"):
            if not self.fullGrid:
                print >> sys.stderr, "Training combined model before grid search"
                self.triggerDetector.beginModel(None, self.combinedModel, [self.triggerDetector.tag+"train-examples.gz", self.triggerDetector.tag+"opt-examples.gz"], self.triggerDetector.tag+"opt-examples.gz", self.model)
                self.edgeDetector.beginModel(None, self.combinedModel, [self.edgeDetector.tag+"train-examples.gz", self.edgeDetector.tag+"opt-examples.gz"], self.edgeDetector.tag+"opt-examples.gz", self.model)
            else:
                print >> sys.stderr, "Combined model will be trained after grid search"
        if self.checkStep("GRID"):
            self.doGrid()
        if self.checkStep("BEGIN-COMBINED-MODEL-FULLGRID"):
            if self.fullGrid:
                print >> sys.stderr, "Training combined model after grid search"
                self.triggerDetector.beginModel(None, self.combinedModel, [self.triggerDetector.tag+"train-examples.gz", self.triggerDetector.tag+"opt-examples.gz"], self.triggerDetector.tag+"opt-examples.gz", self.model)
                self.edgeDetector.beginModel(None, self.combinedModel, [self.edgeDetector.tag+"train-examples.gz", self.edgeDetector.tag+"opt-examples.gz"], self.edgeDetector.tag+"opt-examples.gz", self.model)
            else:
                print >> sys.stderr, "Combined model has been trained before grid search"
        if self.checkStep("END-COMBINED-MODEL"):
            self.triggerDetector.endModel(None, self.combinedModel, self.triggerDetector.tag+"opt-examples.gz")
            self.edgeDetector.endModel(None, self.combinedModel, self.edgeDetector.tag+"opt-examples.gz")
        # End the training process ####################################
        self.exitState()
        self.triggerDetector.exitState()
        self.edgeDetector.exitState()
    
    def doGrid(self):
        BINARY_RECALL_MODE = False # TODO: make a parameter
        print >> sys.stderr, "--------- Booster parameter search ---------"
        # Build trigger examples
        self.triggerDetector.buildExamples(self.model, [self.optData], ["test-trigger-examples.gz"])
        
        count = 0
        bestResults = None
        if self.fullGrid:
            # Parameters to optimize
            ALL_PARAMS={
                "trigger":[int(i) for i in Parameters.splitParameters(self.triggerClassifierParameters)["c"]], 
                "booster":[float(i) for i in self.recallAdjustParameters.split(",")], 
                "edge":[int(i) for i in Parameters.splitParameters(self.edgeClassifierParameters)["c"]] }
        else:
            ALL_PARAMS={"trigger":Parameters.splitParameters(self.model.get(self.triggerDetector.tag+"classifier-parameters"))["c"],
                        "booster":[float(i) for i in self.recallAdjustParameters.split(",")],
                        "edge":Parameters.splitParameters(self.model.get(self.edgeDetector.tag+"classifier-parameters"))["c"]}
        paramCombinations = getParameterCombinations(ALL_PARAMS)
        #for boost in boosterParams:
        prevTriggerParam = None
        EDGE_MODEL_STEM = os.path.join(self.edgeDetector.workDir, os.path.normpath(self.model.path)+"-edge-models/model-c_")
        TRIGGER_MODEL_STEM = os.path.join(self.triggerDetector.workDir, os.path.normpath(self.model.path)+"-trigger-models/model-c_")
        for params in paramCombinations:
            print >> sys.stderr, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            print >> sys.stderr, "Processing params", str(count+1) + "/" + str(len(paramCombinations)), params
            print >> sys.stderr, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            
            # Triggers
            if params["trigger"] != prevTriggerParam:
                print >> sys.stderr, "Classifying trigger examples for parameter", params["trigger"]
                self.triggerDetector.classifyToXML(self.optData, self.model, "test-trigger-examples.gz", "grid-", classifierModel=TRIGGER_MODEL_STEM+str(params["trigger"])+".gz", split=False)
            prevTriggerParam = params["trigger"]
            
            # Boost
            xml = RecallAdjust.run("grid-trigger-pred.xml", params["booster"], None, binary=BINARY_RECALL_MODE)
            xml = InteractionXML.splitMergedElements(xml, None)
            xml = InteractionXML.recalculateIds(xml, None, True)
            
            # Build edge examples
            self.edgeDetector.buildExamples(self.model, [xml], ["test-edge-examples.gz"], [self.optData])
            # Classify with pre-defined model
            edgeClassifierModel=EDGE_MODEL_STEM+str(params["edge"])+".gz"
            xml = self.edgeDetector.classifyToXML(xml, self.model, "test-edge-examples.gz", "grid-", classifierModel=edgeClassifierModel, split=True)
            if xml != None:                
                # EvaluateInteractionXML differs from the previous evaluations in that it can
                # be used to compare two separate Interaction XML files. One of these is the gold file,
                # against which the other is evaluated by heuristically matching triggers and
                # edges. Note that this evaluation will differ somewhat from the previous ones,
                # which evaluate on the level of examples.
                # TODO: Where should the EvaluateInteractionXML evaluator come from?
                EIXMLResult = EvaluateInteractionXML.run(self.edgeDetector.evaluator, xml, self.optData, self.parse)
                # Convert to ST-format
                if os.path.exists("flat-devel-geniaformat"):
                    shutil.rmtree("flat-devel-geniaformat")
                STFormat.ConvertXML.toSTFormat(xml, "flat-devel-geniaformat", "a2") #getA2FileTag(options.task, subTask))
                
#                if options.task in ["OLD", "GE", "EPI", "ID"]:
#                    assert options.unmerging
#                    if options.unmerging:
#                        if os.path.exists("unmerged-devel-geniaformat"):
#                            shutil.rmtree("unmerged-devel-geniaformat")
#                        print >> sys.stderr, "--------- ML Unmerging ---------"
#                        GOLD_TEST_FILE = TEST_FILE.replace("-nodup", "")
#                        UnmergingExampleBuilder.run("flat-devel.xml.gz", "unmerging-grid-examples", PARSE, TOK, UNMERGING_FEATURE_PARAMS, UNMERGING_IDS, GOLD_TEST_FILE)
#                        CLASSIFIER.test("unmerging-grid-examples", bestUnmergingModel, "unmerging-grid-classifications")
#                        unmergedXML = BioTextExampleWriter.write("unmerging-grid-examples", "unmerging-grid-classifications", "flat-devel.xml.gz", "unmerged-devel.xml.gz", UNMERGING_IDS+".class_names", PARSE, TOK)
#                        STFormat.ConvertXML.toSTFormat(unmergedXML, "unmerged-devel-geniaformat", getA2FileTag(options.task, subTask))
#                        if options.task == "OLD":
#                            results = evaluateSharedTask("unmerged-devel-geniaformat", subTask)
#                        elif options.task == "GE":
#                            results = evaluateBioNLP11Genia("unmerged-devel-geniaformat", subTask)
#                        elif options.task in ["EPI", "ID"]:
#                            results = evaluateEPIorID("unmerged-devel-geniaformat", options.task)
#                        else:
#                            assert False
#                        shutil.rmtree("unmerged-devel-geniaformat")
#                        if options.task in ["OLD", "GE"]:
#                            if bestResults == None or bestResults[1]["approximate"]["ALL-TOTAL"]["fscore"] < results["approximate"]["ALL-TOTAL"]["fscore"]:
#                                bestResults = (params, results)
#                        else:
#                            if bestResults == None or bestResults[1]["TOTAL"]["fscore"] < results["TOTAL"]["fscore"]:
#                                bestResults = (params, results)
#                    if options.task in ["OLD"]: # rule-based unmerging
#                        print >> sys.stderr, "--------- Rule based unmerging ---------"
#                        # Post-processing
#                        unmergedXML = unflatten(xml, PARSE, TOK)
#                        # Output will be stored to the geniaformat-subdirectory, where will also be a
#                        # tar.gz-file which can be sent to the Shared Task evaluation server.
#                        #gifxmlToGenia(unmergedXML, "rulebased-unmerging-geniaformat", subTask)
#                        if os.path.exists("rulebased-unmerging-geniaformat"):
#                            shutil.rmtree("rulebased-unmerging-geniaformat")
#                        STFormat.ConvertXML.toSTFormat(unmergedXML, "rulebased-unmerging-geniaformat", getA2FileTag(options.task, subTask))
#                        # Evaluation of the Shared Task format
#                        results = evaluateSharedTask("rulebased-unmerging-geniaformat", subTask)
#                        #if bestResults == None or bestResults[1]["approximate"]["ALL-TOTAL"]["fscore"] < results["approximate"]["ALL-TOTAL"]["fscore"]:
#                        #    bestResults = (boost, results)
#                elif options.task == "BB":
#                    results = evaluateBX("flat-devel-geniaformat", "BB")
#                    if bestResults == None or results["fscore"]  > bestResults[1]["fscore"]:
#                        bestResults = (params, results)
#                else:
                if bestResults == None or EIXMLResult.getData().fscore > bestResults[1].getData().fscore:
                    bestResults = (params, EIXMLResult)
                shutil.rmtree("flat-devel-geniaformat")
            else:
                print >> sys.stderr, "No predicted edges"
            count += 1
        print >> sys.stderr, "Booster search complete"
        print >> sys.stderr, "Tested", count, "out of", count, "combinations"
        print >> sys.stderr, "Best parameters:", bestResults[0]
        # Save grid model
        self.saveStr("recallAdjustParameter", str(bestResults[0]["booster"]), self.model)
        if self.combinedModel != None:
            self.saveStr("recallAdjustParameter", str(bestResults[0]["booster"]), self.combinedModel)
        if self.fullGrid: # define best models
            self.triggerDetector.addClassifierModel(self.model, TRIGGER_MODEL_STEM+str(bestResults[0]["trigger"])+".gz", bestResults[0]["trigger"])
            self.edgeDetector.addClassifierModel(self.model, EDGE_MODEL_STEM+str(bestResults[0]["edge"])+".gz", bestResults[0]["edge"])
        #if options.task in ["OLD", "GE"]:
        print >> sys.stderr, "Best result:", bestResults[1]
