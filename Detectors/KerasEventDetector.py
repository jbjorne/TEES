import sys, os
import copy
from Detectors.EventDetector import EventDetector
from Detectors.KerasEntityDetector import KerasEntityDetector
from Detectors.KerasEdgeDetector import KerasEdgeDetector
from Detectors.KerasUnmergingDetector import KerasUnmergingDetector
from Detectors.KerasModifierDetector import KerasModifierDetector
import Evaluators.EvaluateInteractionXML as EvaluateInteractionXML
import Utils.Parameters as Parameters
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator

class KerasEventDetector(EventDetector):
    def __init__(self):
        EventDetector.__init__(self)
        #self.triggerDetector = KerasEntityDetector()
        #self.tag = "event-"
        self.kerasComponents = {"trigger":False, "edge":False, "unmerging":False, "modifier":False}
        self.evaluator = AveragingMultiClassEvaluator
        
    def hasKerasStyle(self, style):
        if style != None and "keras" in style:
            return True
        return False
    
    def initKerasComponents(self):
        if self.kerasComponents["trigger"]:
            self.triggerDetector = KerasEntityDetector()
        if self.kerasComponents["edge"]:
            self.edgeDetector = KerasEdgeDetector()
        if self.kerasComponents["unmerging"]:
            self.unmergingDetector = KerasUnmergingDetector()
        if self.kerasComponents["modifier"]:
            self.modifierDetector = KerasModifierDetector()
        print >> sys.stderr, "Keras components:", self.kerasComponents
    
    def train(self, trainData=None, optData=None, 
              model=None, combinedModel=None,
              triggerExampleStyle=None, edgeExampleStyle=None, unmergingExampleStyle=None, modifierExampleStyle=None,
              triggerClassifierParameters=None, edgeClassifierParameters=None, 
              unmergingClassifierParameters=None, modifierClassifierParameters=None, 
              recallAdjustParameters=None, unmerging=None, trainModifiers=None, 
              fullGrid=False, task=None,
              parse=None, tokenization=None,
              fromStep=None, toStep=None,
              workDir=None, testData=None):
        # Initialize the training process ##############################
        self.initVariables(trainData=trainData, optData=optData, testData=testData, model=model, combinedModel=combinedModel,
                           triggerExampleStyle=triggerExampleStyle, edgeExampleStyle=edgeExampleStyle, 
                           unmergingExampleStyle=unmergingExampleStyle, modifierExampleStyle=modifierExampleStyle,
                           triggerClassifierParameters=triggerClassifierParameters, 
                           edgeClassifierParameters=edgeClassifierParameters,
                           unmergingClassifierParameters=unmergingClassifierParameters,
                           modifierClassifierParameters=modifierClassifierParameters, 
                           recallAdjustParameters=recallAdjustParameters, unmerging=unmerging, trainModifiers=trainModifiers, 
                           fullGrid=fullGrid, task=task, parse=parse, tokenization=tokenization)
        self.setWorkDir(workDir)
        # Begin the training process ####################################
        self.enterState(self.STATE_TRAIN, ["ANALYZE", "EXAMPLES", "BEGIN-MODEL", "END-MODEL", "BEGIN-COMBINED-MODEL", 
                                           "SELF-TRAIN-EXAMPLES-FOR-UNMERGING", "UNMERGING-EXAMPLES", "BEGIN-UNMERGING-MODEL", "END-UNMERGING-MODEL", 
                                           "GRID", "BEGIN-COMBINED-MODEL-FULLGRID", "END-COMBINED-MODEL"], fromStep, toStep)
        self.kerasComponents["trigger"] = self.hasKerasStyle(triggerExampleStyle)
        self.kerasComponents["edge"] = self.hasKerasStyle(edgeExampleStyle)
        self.kerasComponents["unmerging"] = self.hasKerasStyle(unmergingExampleStyle)
        self.kerasComponents["modifier"] = self.hasKerasStyle(modifierExampleStyle)
        self.initKerasComponents()
        #if self.hasKerasStyle(modifierExampleStyle):
        #    self.edgeDetector = KerasEdgeDetector()
        self.triggerDetector.enterState(self.STATE_COMPONENT_TRAIN)
        self.edgeDetector.enterState(self.STATE_COMPONENT_TRAIN)
        self.unmergingDetector.enterState(self.STATE_COMPONENT_TRAIN)
        self.modifierDetector.enterState(self.STATE_COMPONENT_TRAIN)
        if self.checkStep("ANALYZE"):
            # General training initialization done at the beginning of the first state
            self.model = self.initModel(self.model, 
                                         [("triggerExampleStyle", self.triggerDetector.tag+"example-style"), 
                                          ("triggerClassifierParameters", self.triggerDetector.tag+"classifier-parameters-train"),
                                          ("edgeExampleStyle", self.edgeDetector.tag+"example-style"), 
                                          ("edgeClassifierParameters", self.edgeDetector.tag+"classifier-parameters-train"),
                                          ("unmergingExampleStyle", self.unmergingDetector.tag+"example-style"), 
                                          ("unmergingClassifierParameters", self.unmergingDetector.tag+"classifier-parameters-train"),
                                          ("modifierExampleStyle", self.modifierDetector.tag+"example-style"), 
                                          ("modifierClassifierParameters", self.modifierDetector.tag+"classifier-parameters-train")])
            self.combinedModel = self.initModel(self.combinedModel)
            self.model.debug = self.debug
            if self.combinedModel:
                self.combinedModel.debug = self.debug
            tags = [self.triggerDetector.tag, self.edgeDetector.tag, self.unmergingDetector.tag, self.modifierDetector.tag]
            stringDict = {}
            for tag in tags:
                stringDict[tag+"parse"] = parse
                stringDict[tag+"task"] = task
            self.saveStrings(stringDict, self.model)
            if self.combinedModel:
                self.saveStrings(stringDict, self.combinedModel, False)
            # Perform structure analysis
            self.structureAnalyzer.analyze([optData, trainData], self.model)
            print >> sys.stderr, self.structureAnalyzer.toString()
        # (Re-)open models in case we start after the first ("ANALYZE") step
        self.model = self.openModel(model, "a")
        if self.combinedModel:
            self.combinedModel = self.openModel(combinedModel, "a")
        # Use structure analysis to define automatic parameters
        if self.unmerging == None:
            if not self.structureAnalyzer.isInitialized():
                self.structureAnalyzer.load(self.model)
            self.unmerging = self.structureAnalyzer.hasEvents()
        if self.trainModifiers == None:
            if not self.structureAnalyzer.isInitialized():
                self.structureAnalyzer.load(self.model)
            self.trainModifiers = self.structureAnalyzer.hasModifiers()
        if self.checkStep("EXAMPLES"):
            if not self.kerasComponents["trigger"]:
                self.triggerDetector.buildExamples(self.model, [optData.replace("-nodup", ""), trainData.replace("-nodup", "")], [self.workDir+self.triggerDetector.tag+"opt-examples.gz", self.workDir+self.triggerDetector.tag+"train-examples.gz"], saveIdsToModel=True)
            if not self.kerasComponents["edge"]:
                self.edgeDetector.buildExamples(self.model, [optData.replace("-nodup", ""), trainData.replace("-nodup", "")], [self.workDir+self.edgeDetector.tag+"opt-examples.gz", self.workDir+self.edgeDetector.tag+"train-examples.gz"], saveIdsToModel=True)
            if self.trainModifiers and not self.kerasComponents["modifier"]:
                self.modifierDetector.buildExamples(self.model, [optData, trainData], [self.workDir+self.modifierDetector.tag+"opt-examples.gz", self.workDir+self.modifierDetector.tag+"train-examples.gz"], saveIdsToModel=True)             
        if self.checkStep("BEGIN-MODEL"):
            #for model in [self.model, self.combinedModel]:
            #    if model != None:
            #        model.addStr("BioNLPSTParams", Parameters.toString(self.bioNLPSTParams))
            self.triggerDetector.bioNLPSTParams = self.bioNLPSTParams
            if self.kerasComponents["trigger"]:
                self.triggerDetector.train(trainData, optData, self.model, self.combinedModel, triggerExampleStyle, None, parse, tokenization, task, testData=testData)
            else:
                self.triggerDetector.beginModel(None, self.model, [self.workDir+self.triggerDetector.tag+"train-examples.gz"], self.workDir+self.triggerDetector.tag+"opt-examples.gz")
            if self.kerasComponents["edge"]:
                self.edgeDetector.train(trainData, optData, self.model, self.combinedModel, edgeExampleStyle, None, parse, tokenization, task, testData=testData)
            else:
                self.edgeDetector.beginModel(None, self.model, [self.workDir+self.edgeDetector.tag+"train-examples.gz"], self.workDir+self.edgeDetector.tag+"opt-examples.gz")
            if self.trainModifiers:
                if self.kerasComponents["modifier"]:
                    self.modifierDetector.train(trainData, optData, self.model, self.combinedModel, modifierExampleStyle, None, parse, tokenization, task, testData=testData)
                else:
                    self.modifierDetector.beginModel(None, self.model, [self.workDir+self.modifierDetector.tag+"train-examples.gz"], self.workDir+self.modifierDetector.tag+"opt-examples.gz")
        if self.checkStep("END-MODEL"):
            if not self.kerasComponents["trigger"]:
                self.triggerDetector.endModel(None, self.model, self.workDir+self.triggerDetector.tag+"opt-examples.gz")
            if not self.kerasComponents["edge"]:
                self.edgeDetector.endModel(None, self.model, self.workDir+self.edgeDetector.tag+"opt-examples.gz")
            if self.trainModifiers and not self.kerasComponents["modifier"]:
                self.modifierDetector.endModel(None, self.model, self.workDir+self.modifierDetector.tag+"opt-examples.gz")
        if self.checkStep("BEGIN-COMBINED-MODEL"):
            if not self.fullGrid:
                if not self.kerasComponents["trigger"]:
                    print >> sys.stderr, "Training combined trigger model before grid search"
                    self.triggerDetector.beginModel(None, self.combinedModel, [self.workDir+self.triggerDetector.tag+"train-examples.gz", self.workDir+self.triggerDetector.tag+"opt-examples.gz"], self.workDir+self.triggerDetector.tag+"opt-examples.gz", self.model)
                if not self.kerasComponents["edge"]:
                    print >> sys.stderr, "Training combined edge model before grid search"
                    self.edgeDetector.beginModel(None, self.combinedModel, [self.workDir+self.edgeDetector.tag+"train-examples.gz", self.workDir+self.edgeDetector.tag+"opt-examples.gz"], self.workDir+self.edgeDetector.tag+"opt-examples.gz", self.model)
            else:
                print >> sys.stderr, "Combined model will be trained after grid search"
            if self.trainModifiers:
                if not self.kerasComponents["modifier"]:
                    print >> sys.stderr, "Training combined model for modifier detection"
                    self.modifierDetector.beginModel(None, self.combinedModel, [self.workDir+self.modifierDetector.tag+"train-examples.gz", self.workDir+self.modifierDetector.tag+"opt-examples.gz"], self.workDir+self.modifierDetector.tag+"opt-examples.gz", self.model)
        self.trainUnmergingDetector()
        if self.checkStep("GRID"):
            self.doGrid()
        if self.checkStep("BEGIN-COMBINED-MODEL-FULLGRID"):
            if self.fullGrid:
                if not self.kerasComponents["trigger"]:
                    print >> sys.stderr, "Training combined trigger model after grid search"
                    self.triggerDetector.beginModel(None, self.combinedModel, [self.workDir+self.triggerDetector.tag+"train-examples.gz", self.workDir+self.triggerDetector.tag+"opt-examples.gz"], self.workDir+self.triggerDetector.tag+"opt-examples.gz", self.model)
                if not self.kerasComponents["edge"]:
                    print >> sys.stderr, "Training combined edge model after grid search"
                    self.edgeDetector.beginModel(None, self.combinedModel, [self.workDir+self.edgeDetector.tag+"train-examples.gz", self.workDir+self.edgeDetector.tag+"opt-examples.gz"], self.workDir+self.edgeDetector.tag+"opt-examples.gz", self.model)
                if self.trainModifiers and not self.kerasComponents["modifier"]:
                    print >> sys.stderr, "Training combined model for modifier detection"
                    self.modifierDetector.beginModel(None, self.combinedModel, [self.workDir+self.modifierDetector.tag+"train-examples.gz", self.workDir+self.modifierDetector.tag+"opt-examples.gz"], self.workDir+self.modifierDetector.tag+"opt-examples.gz", self.model)
            else:
                print >> sys.stderr, "Combined model has been trained before grid search"
        if self.checkStep("END-COMBINED-MODEL"):
            if not self.kerasComponents["trigger"]:
                self.triggerDetector.endModel(None, self.combinedModel, self.workDir+self.triggerDetector.tag+"opt-examples.gz")
            if not self.kerasComponents["edge"]:
                self.edgeDetector.endModel(None, self.combinedModel, self.workDir+self.edgeDetector.tag+"opt-examples.gz")
            if self.trainModifiers and not self.kerasComponents["modifier"]:
                self.modifierDetector.endModel(None, self.combinedModel, self.workDir+self.modifierDetector.tag+"opt-examples.gz")
        # End the training process ####################################
        if workDir != None:
            self.setWorkDir("")
        self.exitState()
        #self.triggerDetector.exitState()
        self.edgeDetector.exitState()
        self.unmergingDetector.exitState()
        self.modifierDetector.exitState()
    
    def trainUnmergingDetector(self):
        xml = None
        if not self.unmerging:
            print >> sys.stderr, "No unmerging"
        if self.checkStep("SELF-TRAIN-EXAMPLES-FOR-UNMERGING", self.unmerging) and self.unmerging:
            # Self-classified train data for unmerging
            if self.doUnmergingSelfTraining:
                # This allows limiting to a subcorpus
                triggerStyle = copy.copy(Parameters.get(self.triggerExampleStyle))
                edgeStyle = copy.copy(Parameters.get(self.edgeExampleStyle))
                unmergingStyle = Parameters.get(self.unmergingExampleStyle)
                if "sentenceLimit" in unmergingStyle and unmergingStyle["sentenceLimit"]:
                    triggerStyle["sentenceLimit"] = unmergingStyle["sentenceLimit"]
                    edgeStyle["sentenceLimit"] = unmergingStyle["sentenceLimit"]
                # Build the examples
                xml = self.triggerDetector.classifyToXML(self.trainData, self.model, None, self.workDir+"unmerging-extra-", exampleStyle=triggerStyle)#, recallAdjust=0.5)
                xml = self.edgeDetector.classifyToXML(xml, self.model, None, self.workDir+"unmerging-extra-", exampleStyle=edgeStyle, goldData=self.trainData)#, recallAdjust=0.5)
                assert xml != None
                EvaluateInteractionXML.run(self.edgeDetector.evaluator, xml, self.trainData, self.parse)
            else:
                print >> sys.stderr, "No self-training for unmerging"
        if self.checkStep("UNMERGING-EXAMPLES", self.unmerging) and self.unmerging:
            GOLD_OPT_FILE = self.optData.replace("-nodup", "")
            GOLD_TRAIN_FILE = self.trainData.replace("-nodup", "")
            if self.kerasComponents["unmerging"]:
                extraData = None
                goldData=[GOLD_OPT_FILE, GOLD_TRAIN_FILE]
                if self.doUnmergingSelfTraining:
                    extraData = [None, xml]
                    goldData=[GOLD_OPT_FILE, [GOLD_TRAIN_FILE, GOLD_TRAIN_FILE]]
                self.unmergingDetector.train(self.trainData.replace("-nodup", ""), self.optData.replace("-nodup", ""), self.model, self.combinedModel, self.unmergingExampleStyle, None, self.parse, self.tokenization, self.task, testData=self.testData, goldData=goldData, extraData=extraData)
            else:
                # Unmerging example generation
                if self.doUnmergingSelfTraining:
                    if xml == None: 
                        xml = self.workDir+"unmerging-extra-edge-pred.xml.gz"
                    self.unmergingDetector.buildExamples(self.model, [self.optData.replace("-nodup", ""), [self.trainData.replace("-nodup", ""), xml]], 
                                                         [self.workDir+"unmerging-opt-examples.gz", self.workDir+"unmerging-train-examples.gz"], 
                                                         [GOLD_OPT_FILE, [GOLD_TRAIN_FILE, GOLD_TRAIN_FILE]], 
                                                         exampleStyle=self.unmergingExampleStyle, saveIdsToModel=True)
                    xml = None
                else:
                    self.unmergingDetector.buildExamples(self.model, [self.optData.replace("-nodup", ""), self.trainData.replace("-nodup", "")], 
                                                         [self.workDir+"unmerging-opt-examples.gz", self.workDir+"unmerging-train-examples.gz"], 
                                                         [GOLD_OPT_FILE, GOLD_TRAIN_FILE], 
                                                         exampleStyle=self.unmergingExampleStyle, saveIdsToModel=True)
                    xml = None
                #UnmergingExampleBuilder.run("/home/jari/biotext/EventExtension/TrainSelfClassify/test-predicted-edges.xml", GOLD_TRAIN_FILE, UNMERGING_TRAIN_EXAMPLE_FILE, PARSE, TOK, UNMERGING_FEATURE_PARAMS, UNMERGING_IDS, append=True)
        if self.checkStep("BEGIN-UNMERGING-MODEL", self.unmerging) and self.unmerging:
            if not self.kerasComponents["unmerging"]:
                self.unmergingDetector.beginModel(None, self.model, self.workDir+"unmerging-train-examples.gz", self.workDir+"unmerging-opt-examples.gz")
        if self.checkStep("END-UNMERGING-MODEL", self.unmerging) and self.unmerging:
            if not self.kerasComponents["unmerging"]:
                self.unmergingDetector.endModel(None, self.model, self.workDir+"unmerging-opt-examples.gz")
                print >> sys.stderr, "Adding unmerging classifier model to test-set event model"
                if self.combinedModel != None:
                    self.combinedModel.addStr("unmerging-example-style", self.model.getStr("unmerging-example-style"))
                    self.combinedModel.insert(self.model.get("unmerging-ids.classes"), "unmerging-ids.classes")
                    self.combinedModel.insert(self.model.get("unmerging-ids.features"), "unmerging-ids.features")
                    self.unmergingDetector.addClassifierModel(self.combinedModel, self.model.get("unmerging-classifier-model", True), 
                                                              self.model.getStr("unmerging-classifier-parameter"))
                    self.combinedModel.save()
        
    def doGrid(self):
        # Save grid model
        self.saveStr("recallAdjustParameter", str(1.0), self.model)
        self.saveStr("recallAdjustParameter", str(1.0), self.combinedModel, False)
        
    def classify(self, data, model, output, parse=None, task=None, goldData=None, fromStep=None, toStep=None, omitSteps=None, workDir=None):
        modelObj = self.openModel(model, "r")
        for component in sorted(self.kerasComponents.keys()):
            if component == "trigger" and modelObj.getStr(component + "-example-style", None) == None:
                style = modelObj.getStr("entity-example-style")
            else:
                style = modelObj.getStr(component + "-example-style")
            self.kerasComponents[component] = self.hasKerasStyle(style)
        modelObj.close()
        self.initKerasComponents()
        EventDetector.classify(self, data, model, output, parse=parse, task=task, goldData=goldData, fromStep=fromStep, toStep=toStep, omitSteps=omitSteps, workDir=workDir)