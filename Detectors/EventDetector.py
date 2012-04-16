import sys, os
import shutil
import types
from Detector import Detector
from TriggerDetector import TriggerDetector
from EdgeDetector import EdgeDetector
from UnmergingDetector import UnmergingDetector
from ModifierDetector import ModifierDetector
from Core.OptimizeParameters import getParameterCombinations
from Core.OptimizeParameters import getCombinationString
from Core.RecallAdjust import RecallAdjust
import Utils.Parameters as Parameters
import InteractionXML
import Evaluators.EvaluateInteractionXML as EvaluateInteractionXML
import STFormat.ConvertXML
import STFormat.Compare
import Evaluators.BioNLP11GeniaTools

class EventDetector(Detector):
    def __init__(self):
        Detector.__init__(self)
        self.triggerDetector = TriggerDetector()
        self.edgeDetector = EdgeDetector()
        self.unmergingDetector = UnmergingDetector()
        self.doUnmergingSelfTraining = False
        self.modifierDetector = ModifierDetector()
        self.stEvaluator = Evaluators.BioNLP11GeniaTools
        self.stWriteScores = False
        self.STATE_COMPONENT_TRAIN = "COMPONENT_TRAIN"
        self.tag = "event-"
        
    
    def setCSCConnection(self, options, cscworkdir):
        self.triggerDetector.setCSCConnection(options, os.path.join(cscworkdir, "trigger"))
        self.edgeDetector.setCSCConnection(options, os.path.join(cscworkdir, "edge"))
        self.unmergingDetector.setCSCConnection(options, os.path.join(cscworkdir, "unmerging"))
        self.modifierDetector.setCSCConnection(options, os.path.join(cscworkdir, "modifier"))
    
    def train(self, trainData=None, optData=None, 
              model=None, combinedModel=None,
              triggerExampleStyle=None, edgeExampleStyle=None, unmergingExampleStyle=None, modifierExampleStyle=None,
              triggerClassifierParameters=None, edgeClassifierParameters=None, 
              unmergingClassifierParameters=None, modifierClassifierParameters=None, 
              recallAdjustParameters=None, unmerging=False, trainModifiers=False, 
              fullGrid=False, task=None,
              parse=None, tokenization=None,
              fromStep=None, toStep=None):
        # Initialize the training process ##############################
        self.initVariables(trainData=trainData, optData=optData, model=model, combinedModel=combinedModel,
                           triggerExampleStyle=triggerExampleStyle, edgeExampleStyle=edgeExampleStyle, 
                           unmergingExampleStyle=unmergingExampleStyle, modifierExampleStyle=modifierExampleStyle,
                           triggerClassifierParameters=triggerClassifierParameters, 
                           edgeClassifierParameters=edgeClassifierParameters,
                           unmergingClassifierParameters=unmergingClassifierParameters,
                           modifierClassifierParameters=modifierClassifierParameters, 
                           recallAdjustParameters=recallAdjustParameters, unmerging=unmerging, trainModifiers=trainModifiers, 
                           fullGrid=fullGrid, task=task, parse=parse, tokenization=tokenization)
        # Begin the training process ####################################
        self.enterState(self.STATE_TRAIN, ["EXAMPLES", "BEGIN-MODEL", "END-MODEL", "BEGIN-COMBINED-MODEL", 
                                           "SELF-TRAIN-EXAMPLES-FOR-UNMERGING", "UNMERGING-EXAMPLES", "BEGIN-UNMERGING-MODEL", "END-UNMERGING-MODEL", 
                                           "GRID", "BEGIN-COMBINED-MODEL-FULLGRID", "END-COMBINED-MODEL"], fromStep, toStep)
        self.triggerDetector.enterState(self.STATE_COMPONENT_TRAIN)
        self.edgeDetector.enterState(self.STATE_COMPONENT_TRAIN)
        self.unmergingDetector.enterState(self.STATE_COMPONENT_TRAIN)
        self.modifierDetector.enterState(self.STATE_COMPONENT_TRAIN)
        if self.checkStep("EXAMPLES"):
            self.model = self.initModel(self.model, 
                                         [("triggerExampleStyle", self.triggerDetector.tag+"example-style"), 
                                          ("triggerClassifierParameters", self.triggerDetector.tag+"classifier-parameters"),
                                          ("edgeExampleStyle", self.edgeDetector.tag+"example-style"), 
                                          ("edgeClassifierParameters", self.edgeDetector.tag+"classifier-parameters"),
                                          ("unmergingExampleStyle", self.unmergingDetector.tag+"example-style"), 
                                          ("unmergingClassifierParameters", self.unmergingDetector.tag+"classifier-parameters"),
                                          ("modifierExampleStyle", self.modifierDetector.tag+"example-style"), 
                                          ("modifierClassifierParameters", self.modifierDetector.tag+"classifier-parameters")])
            tags = [self.triggerDetector.tag, self.edgeDetector.tag, self.unmergingDetector.tag]
            if trainModifiers: tags += [self.modifierDetector.tag]
            for tag in tags:
                self.saveStr(tag+"parse", parse, self.model)
                self.saveStr(tag+"task", task, self.model)
            self.combinedModel = self.initModel(self.combinedModel)
            if self.combinedModel != None:
                for tag in [self.triggerDetector.tag, self.edgeDetector.tag, self.unmergingDetector.tag]:
                    self.saveStr(tag+"parse", parse, self.combinedModel)
                    self.saveStr(tag+"task", task, self.combinedModel)
            self.triggerDetector.buildExamples(self.model, [optData, trainData], [self.triggerDetector.tag+"opt-examples.gz", self.triggerDetector.tag+"train-examples.gz"], saveIdsToModel=True)
            self.edgeDetector.buildExamples(self.model, [optData, trainData], [self.edgeDetector.tag+"opt-examples.gz", self.edgeDetector.tag+"train-examples.gz"], saveIdsToModel=True)
            if trainModifiers:
                self.modifierDetector.buildExamples(self.model, [optData, trainData], [self.modifierDetector.tag+"opt-examples.gz", self.modifierDetector.tag+"train-examples.gz"], saveIdsToModel=True)             
        # (Re-)open models in case we start after the "EXAMPLES" step
        self.model = self.openModel(model, "a")
        self.combinedModel = self.openModel(combinedModel, "a")
        if self.checkStep("BEGIN-MODEL"):
            self.triggerDetector.beginModel(None, self.model, [self.triggerDetector.tag+"train-examples.gz"], self.triggerDetector.tag+"opt-examples.gz")
            self.edgeDetector.beginModel(None, self.model, [self.edgeDetector.tag+"train-examples.gz"], self.edgeDetector.tag+"opt-examples.gz")
            if trainModifiers:
                self.modifierDetector.beginModel(None, self.model, [self.modifierDetector.tag+"train-examples.gz"], self.modifierDetector.tag+"opt-examples.gz")
        if self.checkStep("END-MODEL"):
            self.triggerDetector.endModel(None, self.model, self.triggerDetector.tag+"opt-examples.gz")
            self.edgeDetector.endModel(None, self.model, self.edgeDetector.tag+"opt-examples.gz")
            if trainModifiers:
                self.modifierDetector.endModel(None, self.model, self.modifierDetector.tag+"opt-examples.gz")
        if self.checkStep("BEGIN-COMBINED-MODEL"):
            if not self.fullGrid:
                print >> sys.stderr, "Training combined model before grid search"
                self.triggerDetector.beginModel(None, self.combinedModel, [self.triggerDetector.tag+"train-examples.gz", self.triggerDetector.tag+"opt-examples.gz"], self.triggerDetector.tag+"opt-examples.gz", self.model)
                self.edgeDetector.beginModel(None, self.combinedModel, [self.edgeDetector.tag+"train-examples.gz", self.edgeDetector.tag+"opt-examples.gz"], self.edgeDetector.tag+"opt-examples.gz", self.model)
            else:
                print >> sys.stderr, "Combined model will be trained after grid search"
            if trainModifiers:
                print >> sys.stderr, "Training combined model for modifier detection"
                self.modifierDetector.beginModel(None, self.combinedModel, [self.modifierDetector.tag+"train-examples.gz", self.modifierDetector.tag+"opt-examples.gz"], self.modifierDetector.tag+"opt-examples.gz", self.model)
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
            if trainModifiers:
                self.modifierDetector.endModel(None, self.combinedModel, self.modifierDetector.tag+"opt-examples.gz")
        # End the training process ####################################
        self.exitState()
        self.triggerDetector.exitState()
        self.edgeDetector.exitState()
        self.unmergingDetector.exitState()
        self.modifierDetector.exitState()
    
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
            xml = RecallAdjust.run("grid-trigger-pred.xml.gz", params["booster"], None, binary=BINARY_RECALL_MODE)
            xml = InteractionXML.splitMergedElements(xml, None)
            xml = InteractionXML.recalculateIds(xml, None, True)
            
            # Build edge examples
            self.edgeDetector.buildExamples(self.model, [xml], ["test-edge-examples.gz"], [self.optData])
            # Classify with pre-defined model
            edgeClassifierModel=EDGE_MODEL_STEM+str(params["edge"])+".gz"
            xml = self.edgeDetector.classifyToXML(xml, self.model, "test-edge-examples.gz", "grid-", classifierModel=edgeClassifierModel, split=True)
            if xml != None:                
                # TODO: Where should the EvaluateInteractionXML evaluator come from?
                EIXMLResult = EvaluateInteractionXML.run(self.edgeDetector.evaluator, xml, self.optData, self.parse)
                # Convert to ST-format
                STFormat.ConvertXML.toSTFormat(xml, "flat-devel-geniaformat", "a2") #getA2FileTag(options.task, subTask))
                stFormatDir = "flat-devel-geniaformat"
                
                if self.unmerging:
                    xml = self.unmergingDetector.classifyToXML(xml, self.model, None, "grid-unmerging-", split=False, goldData=self.optData.replace("-nodup", ""))
                    STFormat.ConvertXML.toSTFormat(xml, "grid-unmerging-geniaformat", "a2")
                    stFormatDir = "grid-unmerging-geniaformat"
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
            if self.doUnmergingSelfTraining:
                xml = self.triggerDetector.classifyToXML(self.trainData, self.model, None, "unmerging-extra-", split=True)
                xml = self.edgeDetector.classifyToXML(xml, self.model, None, "unmerging-extra-", split=True)
                assert xml != None
                EvaluateInteractionXML.run(self.edgeDetector.evaluator, xml, self.trainData, self.parse)
        if self.checkStep("UNMERGING-EXAMPLES", self.unmerging) and self.unmerging:
            # Unmerging example generation
            GOLD_TEST_FILE = self.optData.replace("-nodup", "")
            GOLD_TRAIN_FILE = self.trainData.replace("-nodup", "")
            if self.doUnmergingSelfTraining:
                if xml == None: 
                    xml = "unmerging-extra-edge-pred.xml"
                self.unmergingDetector.buildExamples(self.model, [self.optData, [self.trainData, xml]], 
                                                     ["unmerging-opt-examples.gz", "unmerging-train-examples.gz"], 
                                                     [GOLD_TEST_FILE, [GOLD_TRAIN_FILE, GOLD_TRAIN_FILE]], 
                                                     exampleStyle=self.unmergingExampleStyle, saveIdsToModel=True)
                xml = None
            else:
                self.unmergingDetector.buildExamples(self.model, [self.optData, self.trainData], 
                                                     ["unmerging-opt-examples.gz", "unmerging-train-examples.gz"], 
                                                     [GOLD_TEST_FILE, GOLD_TRAIN_FILE], 
                                                     exampleStyle=self.unmergingExampleStyle, saveIdsToModel=True)
                xml = None
            #UnmergingExampleBuilder.run("/home/jari/biotext/EventExtension/TrainSelfClassify/test-predicted-edges.xml", GOLD_TRAIN_FILE, UNMERGING_TRAIN_EXAMPLE_FILE, PARSE, TOK, UNMERGING_FEATURE_PARAMS, UNMERGING_IDS, append=True)
        if self.checkStep("BEGIN-UNMERGING-MODEL", self.unmerging) and self.unmerging:
            self.unmergingDetector.beginModel(None, self.model, "unmerging-train-examples.gz", "unmerging-opt-examples.gz")
        if self.checkStep("END-UNMERGING-MODEL", self.unmerging) and self.unmerging:
            self.unmergingDetector.endModel(None, self.model, "unmerging-opt-examples.gz")
            print >> sys.stderr, "Adding unmerging classifier model to test-set event model"
            if self.combinedModel != None:
                self.combinedModel.insert(self.model.get("unmerging-example-style"), "unmerging-example-style")
                self.combinedModel.insert(self.model.get("unmerging-ids.classes"), "unmerging-ids.classes")
                self.combinedModel.insert(self.model.get("unmerging-ids.features"), "unmerging-ids.features")
                self.unmergingDetector.addClassifierModel(self.combinedModel, self.model.get("unmerging-classifier-model.gz"), 
                                                          Parameters.splitParameters(self.model.get("unmerging-classifier-parameters")))
                self.combinedModel.save()

    def classify(self, data, model, output, parse=None, task=None, fromStep=None, toStep=None, saveChangedModelPath=None):
        BINARY_RECALL_MODE = False # TODO: make a parameter
        xml = None
        self.initVariables(classifyData=data, model=model, xml=None, task=task, parse=parse)
        self.enterState(self.STATE_CLASSIFY, ["TRIGGERS", "RECALL-ADJUST", "EDGES", "UNMERGING", "MODIFIERS", "ST-CONVERT"], fromStep, toStep)
        self.model = self.openModel(self.model, "r")
        if self.checkStep("TRIGGERS"):
            xml = self.triggerDetector.classifyToXML(self.classifyData, self.model, None, output + "-", split=False, parse=self.parse)
        if self.checkStep("RECALL-ADJUST"):
            xml = self.getWorkFile(xml, output + "-trigger-pred.xml.gz")
            xml = RecallAdjust.run(xml, float(self.getStr("recallAdjustParameter", self.model)), None, binary=BINARY_RECALL_MODE)
            xml = InteractionXML.splitMergedElements(xml, None)
            xml = InteractionXML.recalculateIds(xml, output+"-recall-adjusted.xml.gz", True)
        if self.checkStep("EDGES"):
            xml = self.getWorkFile(xml, output + "-recall-adjusted.xml.gz")
            xml = self.edgeDetector.classifyToXML(xml, self.model, None, output + "-", split=True, parse=self.parse)
            assert xml != None
            if self.parse == None:
                edgeParse = self.getStr(self.edgeDetector.tag+"parse", self.model)
            else:
                edgeParse = self.parse
            #EvaluateInteractionXML.run(self.edgeDetector.evaluator, xml, self.classifyData, edgeParse)
            EvaluateInteractionXML.run(self.edgeDetector.evaluator, xml, None, edgeParse)
        if self.checkStep("UNMERGING"):
            if self.model.hasMember("unmerging-classifier-model.gz"):
                #xml = self.getWorkFile(xml, output + "-edge-pred.xml.gz")
                # To avoid running out of memory, always use file on disk
                xml = self.getWorkFile(None, output + "-edge-pred.xml.gz")
                goldData = None
                if type(self.classifyData) in types.StringTypes:
                    if os.path.exists(self.classifyData.replace("-nodup", "")):
                        goldData = self.classifyData.replace("-nodup", "")
                xml = self.unmergingDetector.classifyToXML(xml, self.model, None, output + "-", split=False, goldData=goldData, parse=self.parse)
            else:
                print >> sys.stderr, "No unmerging"
        if self.checkStep("MODIFIERS"):
            if self.model.hasMember("modifier-classifier-model.gz"):
                xml = self.getWorkFile(xml, [output + "-unmerging-pred.xml.gz", output + "-edge-pred.xml.gz"])
                xml = self.modifierDetector.classifyToXML(xml, self.model, None, output + "-", split=False, parse=self.parse)
            else:
                print >> sys.stderr, "No model for modifier detection"
        if self.checkStep("ST-CONVERT"):
            xml = self.getWorkFile(xml, [output + "-modifier-pred.xml.gz", output + "-unmerging-pred.xml.gz", output + "-edge-pred.xml.gz"])
            STFormat.ConvertXML.toSTFormat(xml, output+"-events.tar.gz", outputTag="a2", writeScores=self.stWriteScores)
            if self.stEvaluator != None:
                task = self.task
                if task == None:
                    task = self.getStr(self.edgeDetector.tag+"task", self.model)
                self.stEvaluator.evaluate(output + "-events.tar.gz", task)
            if saveChangedModelPath != None:
                self.model.saveAs(saveChangedModelPath)
        self.exitState()
    
    def getWorkFile(self, fileObject, serializedPath=None):
        """
        Returns fileObject if it is not None, otherwise tries all paths in serializedPath
        and returns the first one that exists. Use this to get an intermediate file in a
        stepwise process.
        """
        if fileObject != None:
            return fileObject
        elif type(serializedPath) not in types.StringTypes: # multiple files to try
            for sPath in serializedPath:
                if os.path.exists(sPath):
                    return sPath
            assert False
        else:
            assert os.path.exists(serializedPath)
            return serializedPath
