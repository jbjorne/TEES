import sys, os
from Detectors.EventDetector import EventDetector
from Detectors.EntityDetector import EntityDetector
from Detectors.KerasEntityDetector import KerasEntityDetector

class KerasEventDetector(EventDetector):
    def __init__(self):
        EventDetector.__init__(self)
        self.triggerDetector = KerasEntityDetector()
        self.tag = "event-"
    
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
            self.model.debug = self.combinedModel.debug = self.debug
            tags = [self.triggerDetector.tag, self.edgeDetector.tag, self.unmergingDetector.tag, self.modifierDetector.tag]
            stringDict = {}
            for tag in tags:
                stringDict[tag+"parse"] = parse
                stringDict[tag+"task"] = task
            self.saveStrings(stringDict, self.model)
            self.saveStrings(stringDict, self.combinedModel, False)
            # Perform structure analysis
            self.structureAnalyzer.analyze([optData, trainData], self.model)
            print >> sys.stderr, self.structureAnalyzer.toString()
        # (Re-)open models in case we start after the first ("ANALYZE") step
        self.model = self.openModel(model, "a")
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
            #self.triggerDetector.buildExamples(self.model, [optData.replace("-nodup", ""), trainData.replace("-nodup", "")], [self.workDir+self.triggerDetector.tag+"opt-examples.gz", self.workDir+self.triggerDetector.tag+"train-examples.gz"], saveIdsToModel=True)
            self.edgeDetector.buildExamples(self.model, [optData.replace("-nodup", ""), trainData.replace("-nodup", "")], [self.workDir+self.edgeDetector.tag+"opt-examples.gz", self.workDir+self.edgeDetector.tag+"train-examples.gz"], saveIdsToModel=True)
            if self.trainModifiers:
                self.modifierDetector.buildExamples(self.model, [optData, trainData], [self.workDir+self.modifierDetector.tag+"opt-examples.gz", self.workDir+self.modifierDetector.tag+"train-examples.gz"], saveIdsToModel=True)             
        if self.checkStep("BEGIN-MODEL"):
            #for model in [self.model, self.combinedModel]:
            #    if model != None:
            #        model.addStr("BioNLPSTParams", Parameters.toString(self.bioNLPSTParams))
            self.triggerDetector.bioNLPSTParams = self.bioNLPSTParams
            self.triggerDetector.train(trainData, optData, self.model, self.combinedModel, triggerExampleStyle, None, parse, tokenization, task, testData=testData)
            #self.triggerDetector.beginModel(None, self.model, [self.workDir+self.triggerDetector.tag+"train-examples.gz"], self.workDir+self.triggerDetector.tag+"opt-examples.gz")
            self.edgeDetector.beginModel(None, self.model, [self.workDir+self.edgeDetector.tag+"train-examples.gz"], self.workDir+self.edgeDetector.tag+"opt-examples.gz")
            if self.trainModifiers:
                self.modifierDetector.beginModel(None, self.model, [self.workDir+self.modifierDetector.tag+"train-examples.gz"], self.workDir+self.modifierDetector.tag+"opt-examples.gz")
        if self.checkStep("END-MODEL"):
            #self.triggerDetector.endModel(None, self.model, self.workDir+self.triggerDetector.tag+"opt-examples.gz")
            self.edgeDetector.endModel(None, self.model, self.workDir+self.edgeDetector.tag+"opt-examples.gz")
            if self.trainModifiers:
                self.modifierDetector.endModel(None, self.model, self.workDir+self.modifierDetector.tag+"opt-examples.gz")
        if self.checkStep("BEGIN-COMBINED-MODEL"):
            if not self.fullGrid:
                print >> sys.stderr, "Training combined model before grid search"
                #self.triggerDetector.beginModel(None, self.combinedModel, [self.workDir+self.triggerDetector.tag+"train-examples.gz", self.workDir+self.triggerDetector.tag+"opt-examples.gz"], self.workDir+self.triggerDetector.tag+"opt-examples.gz", self.model)
                self.edgeDetector.beginModel(None, self.combinedModel, [self.workDir+self.edgeDetector.tag+"train-examples.gz", self.workDir+self.edgeDetector.tag+"opt-examples.gz"], self.workDir+self.edgeDetector.tag+"opt-examples.gz", self.model)
            else:
                print >> sys.stderr, "Combined model will be trained after grid search"
            if self.trainModifiers:
                print >> sys.stderr, "Training combined model for modifier detection"
                self.modifierDetector.beginModel(None, self.combinedModel, [self.workDir+self.modifierDetector.tag+"train-examples.gz", self.workDir+self.modifierDetector.tag+"opt-examples.gz"], self.workDir+self.modifierDetector.tag+"opt-examples.gz", self.model)
        self.trainUnmergingDetector()
        if self.checkStep("GRID"):
            self.doGrid()
        if self.checkStep("BEGIN-COMBINED-MODEL-FULLGRID"):
            if self.fullGrid:
                print >> sys.stderr, "Training combined model after grid search"
                #self.triggerDetector.beginModel(None, self.combinedModel, [self.workDir+self.triggerDetector.tag+"train-examples.gz", self.workDir+self.triggerDetector.tag+"opt-examples.gz"], self.workDir+self.triggerDetector.tag+"opt-examples.gz", self.model)
                self.edgeDetector.beginModel(None, self.combinedModel, [self.workDir+self.edgeDetector.tag+"train-examples.gz", self.workDir+self.edgeDetector.tag+"opt-examples.gz"], self.workDir+self.edgeDetector.tag+"opt-examples.gz", self.model)
                if self.trainModifiers:
                    print >> sys.stderr, "Training combined model for modifier detection"
                    self.modifierDetector.beginModel(None, self.combinedModel, [self.workDir+self.modifierDetector.tag+"train-examples.gz", self.workDir+self.modifierDetector.tag+"opt-examples.gz"], self.workDir+self.modifierDetector.tag+"opt-examples.gz", self.model)
            else:
                print >> sys.stderr, "Combined model has been trained before grid search"
        if self.checkStep("END-COMBINED-MODEL"):
            #self.triggerDetector.endModel(None, self.combinedModel, self.workDir+self.triggerDetector.tag+"opt-examples.gz")
            self.edgeDetector.endModel(None, self.combinedModel, self.workDir+self.edgeDetector.tag+"opt-examples.gz")
            if self.trainModifiers:
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