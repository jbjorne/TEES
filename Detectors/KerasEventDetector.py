import sys, os
from Detectors.EventDetector import EventDetector
from Detectors.KerasEntityDetector import KerasEntityDetector
from Detectors.KerasEdgeDetector import KerasEdgeDetector
from Detectors.KerasUnmergingDetector import KerasUnmergingDetector

class KerasEventDetector(EventDetector):
    def __init__(self):
        EventDetector.__init__(self)
        #self.triggerDetector = KerasEntityDetector()
        #self.tag = "event-"
        self.kerasComponents = {"trigger":False, "edge":False, "unmerging":False, "modifier":False}
        
    def hasKerasStyle(self, style):
        if style != None and "keras" in style:
            return True
        return False
    
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
        self.initVariables(trainData=trainData, optData=optData, model=model, combinedModel=combinedModel,
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
        if self.hasKerasStyle(triggerExampleStyle):
            self.triggerDetector = KerasEntityDetector()
            self.kerasComponents["trigger"] = True
        if self.hasKerasStyle(edgeExampleStyle):
            self.edgeDetector = KerasEdgeDetector()
            self.kerasComponents["edge"] = True
        if self.hasKerasStyle(unmergingExampleStyle):
            self.unmergingDetector = KerasUnmergingDetector()
            self.kerasComponents["unmerging"] = True
        print >> sys.stderr, "Keras components:", self.kerasComponents
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
        
    def doGrid(self):
        # Save grid model
        self.saveStr("recallAdjustParameter", str(1.0), self.model)
        self.saveStr("recallAdjustParameter", str(1.0), self.combinedModel, False)