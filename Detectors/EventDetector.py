import sys, os
import shutil
from Detector import Detector
from TriggerDetector import TriggerDetector
from EdgeDetector import EdgeDetector
from UnmergingDetector import UnmergingDetector
from Core.OptimizeParameters import getParameterCombinations
from Core.OptimizeParameters import getCombinationString
from Core.RecallAdjust import RecallAdjust
import Utils.Parameters as Parameters
import InteractionXML
import Evaluators.EvaluateInteractionXML as EvaluateInteractionXML
import STFormat.ConvertXML
import STFormat.Compare
import Evaluators.BioNLP11GeniaTools.evaluate

class EventDetector(Detector):
    def __init__(self):
        Detector.__init__(self)
        self.triggerDetector = TriggerDetector()
        self.edgeDetector = EdgeDetector()
        self.unmergingDetector = UnmergingDetector()
        self.STATE_COMPONENT_TRAIN = "COMPONENT_TRAIN"
        self.tag = "event-"
    
    def setCSCConnection(self, options, cscworkdir):
        self.triggerDetector.setCSCConnection(options, os.path.join(cscworkdir, "trigger"))
        self.edgeDetector.setCSCConnection(options, os.path.join(cscworkdir, "edge"))
        self.unmergingDetector.setCSCConnection(options, os.path.join(cscworkdir, "unmerging"))
    
    def train(self, trainData=None, optData=None, 
              model=None, combinedModel=None,
              triggerExampleStyle=None, edgeExampleStyle=None, unmergingExampleStyle=None,
              triggerClassifierParameters=None, edgeClassifierParameters=None, unmergingClassifierParameters=None,
              recallAdjustParameters=None, unmerging=False, fullGrid=False,
              parse=None, tokenization=None,
              fromStep=None, toStep=None):
        # Initialize the training process ##############################
        self.initVariables(trainData=trainData, optData=optData, model=model, combinedModel=combinedModel,
                           triggerExampleStyle=triggerExampleStyle, edgeExampleStyle=edgeExampleStyle, unmergingExampleStyle=unmergingExampleStyle,
                           triggerClassifierParameters=triggerClassifierParameters, 
                           edgeClassifierParameters=edgeClassifierParameters,
                           unmergingClassifierParameters=unmergingClassifierParameters, 
                           recallAdjustParameters=recallAdjustParameters, unmerging=unmerging, 
                           fullGrid=fullGrid, parse=parse, tokenization=tokenization)
        # Begin the training process ####################################
        self.enterState(self.STATE_TRAIN, ["EXAMPLES", "BEGIN-MODEL", "END-MODEL", "BEGIN-COMBINED-MODEL", 
                                           "SELF-TRAIN-EXAMPLES-FOR-UNMERGING", "UNMERGING-EXAMPLES", "BEGIN-UNMERGING-MODEL", "END-UNMERGING-MODEL", 
                                           "GRID", "BEGIN-COMBINED-MODEL-FULLGRID", "END-COMBINED-MODEL"], fromStep, toStep)
        self.triggerDetector.enterState(self.STATE_COMPONENT_TRAIN)
        self.edgeDetector.enterState(self.STATE_COMPONENT_TRAIN)
        self.unmergingDetector.enterState(self.STATE_COMPONENT_TRAIN)
        if self.checkStep("EXAMPLES"):
            self.model = self.initModel(self.model, 
                                         [("triggerExampleStyle", self.triggerDetector.tag+"example-style"), 
                                          ("triggerClassifierParameters", self.triggerDetector.tag+"classifier-parameters"),
                                          ("edgeExampleStyle", self.edgeDetector.tag+"example-style"), 
                                          ("edgeClassifierParameters", self.edgeDetector.tag+"classifier-parameters"),
                                          ("unmergingExampleStyle", self.unmergingDetector.tag+"example-style"), 
                                          ("unmergingClassifierParameters", self.unmergingDetector.tag+"classifier-parameters")])
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
        self.trainUnmergingDetector()
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
        self.unmergingDetector.exitState()
    
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
                STFormat.ConvertXML.toSTFormat(xml, "flat-devel-geniaformat", "a2") #getA2FileTag(options.task, subTask))
                stFormatDir = "flat-devel-geniaformat"
                
#                if options.task in ["OLD", "GE", "EPI", "ID"]:
                if self.unmerging:
                    print >> sys.stderr, "--------- ML Unmerging ---------"
                    xml = self.unmergingDetector.classifyToXML(xml, self.model, None, "grid-unmerging-", split=False, goldData=self.optData.replace("-nodup", ""))
                    STFormat.ConvertXML.toSTFormat(xml, "grid-unmerged-geniaformat", "a2")
                    stFormatDir = "grid-unmerging-geniaformat"
#                    if options.task == "OLD":
#                        results = evaluateSharedTask("unmerged-devel-geniaformat", subTask)
#                    elif options.task == "GE":
#                        results = evaluateBioNLP11Genia("unmerged-devel-geniaformat", subTask)
#                    elif options.task in ["EPI", "ID"]:
#                        results = evaluateEPIorID("unmerged-devel-geniaformat", options.task)
#                    else:
#                        assert False
#                    shutil.rmtree("unmerged-devel-geniaformat")
#                    if options.task in ["OLD", "GE"]:
#                        if bestResults == None or bestResults[1]["approximate"]["ALL-TOTAL"]["fscore"] < results["approximate"]["ALL-TOTAL"]["fscore"]:
#                            bestResults = (params, results)
#                    else:
#                        if bestResults == None or bestResults[1]["TOTAL"]["fscore"] < results["TOTAL"]["fscore"]:
#                            bestResults = (params, results)

#                elif options.task == "BB":
#                    results = evaluateBX("flat-devel-geniaformat", "BB")
#                    if bestResults == None or results["fscore"]  > bestResults[1]["fscore"]:
#                        bestResults = (params, results)
#                else:
                stEvaluation = Evaluators.BioNLP11GeniaTools.evaluate(stFormatDir, self.task)
                if stEvaluation != None:
                    if bestResults == None or stEvaluation[0] > bestResults[1][0]:
                        bestResults = (params, stEvaluation)
                else:
                    if bestResults == None or EIXMLResult.getData().fscore > bestResults[1].getData().fscore:
                        bestResults = (params, EIXMLResult)
                shutil.rmtree("flat-devel-geniaformat")
                if os.path.exists("grid-unmerging-geniaformat"):
                    shutil.rmtree("grid-unmerging-geniaformat")
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

    def trainUnmergingDetector(self):
        xml = None
        if not self.unmerging:
            print >> sys.stderr, "No unmerging"
        if self.checkStep("SELF-TRAIN-EXAMPLES-FOR-UNMERGING", self.unmerging) and self.unmerging:
            # Self-classified train data for unmerging
            xml = self.triggerDetector.classifyToXML(self.trainData, self.model, None, "unmerging-extra-", split=True)
            xml = self.edgeDetector.classifyToXML(xml, self.model, None, "unmerging-extra-", split=True)
            assert xml != None
            EvaluateInteractionXML.run(self.edgeDetector.evaluator, xml, self.trainData, self.parse)
        if self.checkStep("UNMERGING-EXAMPLES", self.unmerging) and self.unmerging:
            # Unmerging example generation
            GOLD_TEST_FILE = self.optData.replace("-nodup", "")
            GOLD_TRAIN_FILE = self.trainData.replace("-nodup", "")
            if xml == None: 
                xml = "unmerging-extra-edge-pred.xml"
            self.unmergingDetector.buildExamples(self.model, [self.optData, [self.trainData, xml]], 
                                                 ["unmerging-opt-examples.gz", "unmerging-train-examples.gz"], 
                                                 [GOLD_TEST_FILE, [GOLD_TRAIN_FILE, GOLD_TRAIN_FILE]], 
                                                 exampleStyle=self.unmergingExampleStyle, saveIdsToModel=True)
            xml = None
            #UnmergingExampleBuilder.run("/home/jari/biotext/EventExtension/TrainSelfClassify/test-predicted-edges.xml", GOLD_TRAIN_FILE, UNMERGING_TRAIN_EXAMPLE_FILE, PARSE, TOK, UNMERGING_FEATURE_PARAMS, UNMERGING_IDS, append=True)
        if self.checkStep("BEGIN-UNMERGING-MODEL", self.unmerging) and self.unmerging:
            self.unmergingDetector.beginModel(None, self.model, "unmerging-train-examples.gz", "unmerging-opt-examples.gz")
        if self.checkStep("END-UNMERGING-MODEL", self.unmerging) and self.unmerging:
            self.unmergingDetector.endModel(None, self.model, "unmerging-opt-examples.gz")
