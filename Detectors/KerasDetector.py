import sys
from Detector import Detector

class EventDetector(Detector):

    def __init__(self):
        Detector.__init__(self)
        self.STATE_COMPONENT_TRAIN = "COMPONENT_TRAIN"
        self.tag = "keras-"
    
    def buildExamples(self, model, datas, outputs, golds=[], exampleStyle=None, saveIdsToModel=False, parse=None):
        if exampleStyle == None:
            exampleStyle = model.getStr(self.tag+"example-style")
        if parse == None:
            parse = self.getStr(self.tag+"parse", model)
        self.structureAnalyzer.load(model)
        self.exampleBuilder.structureAnalyzer = self.structureAnalyzer
        for data, output, gold in itertools.izip_longest(datas, outputs, golds, fillvalue=[]):
            print >> sys.stderr, "Example generation for", output
            if not isinstance(data, (list, tuple)): data = [data]
            if not isinstance(gold, (list, tuple)): gold = [gold]
            append = False
            for dataSet, goldSet in itertools.izip_longest(data, gold, fillvalue=None):
                if dataSet != None:
                    self.exampleBuilder.run(dataSet, output, parse, None, exampleStyle, model.get(self.tag+"ids.classes", 
                        True), model.get(self.tag+"ids.features", True), goldSet, append, saveIdsToModel,
                        structureAnalyzer=self.structureAnalyzer)
                append = True
        if hasattr(self.structureAnalyzer, "typeMap") and model.mode != "r":
            print >> sys.stderr, "Saving StructureAnalyzer.typeMap"
            self.structureAnalyzer.save(model)
            model.save()
        if saveIdsToModel:
            model.save()
    
    def train(self, trainData=None, optData=None, model=None, combinedModel=None, exampleStyle=None, 
              classifierParameters=None, parse=None, tokenization=None, task=None, fromStep=None, toStep=None,
              workDir=None):
        self.initVariables(trainData=trainData, optData=optData, model=model, combinedModel=combinedModel, exampleStyle=exampleStyle, classifierParameters=classifierParameters, parse=parse, tokenization=tokenization)
        self.setWorkDir(workDir)
        self.enterState(self.STATE_TRAIN, ["ANALYZE", "EXAMPLES", "MODEL"], fromStep, toStep)
        if self.checkStep("ANALYZE"):
            # General training initialization done at the beginning of the first state
            self.model = self.initModel(self.model, [("exampleStyle", self.tag+"example-style"), ("classifierParameters", self.tag+"classifier-parameters-train")])
            self.saveStr(self.tag+"parse", parse, self.model)
            if task != None:
                self.saveStr(self.tag+"task", task, self.model)
            # Perform structure analysis
            self.structureAnalyzer.analyze([optData, trainData], self.model)
            print >> sys.stderr, self.structureAnalyzer.toString()
        self.model = self.openModel(model, "a") # Devel model already exists, with ids etc
        if self.checkStep("EXAMPLES"):
            self.buildExamples(self.model, [optData, trainData], [self.workDir+self.tag+"opt-examples.gz", self.workDir+self.tag+"train-examples.gz"], saveIdsToModel=True)
        self.beginModel("BEGIN-MODEL", self.model, [self.workDir+self.tag+"train-examples.gz"], self.workDir+self.tag+"opt-examples.gz")
        self.endModel("END-MODEL", self.model, self.workDir+self.tag+"opt-examples.gz")
        self.beginModel("BEGIN-COMBINED-MODEL", self.combinedModel, [self.workDir+self.tag+"train-examples.gz", self.workDir+self.tag+"opt-examples.gz"], self.workDir+self.tag+"opt-examples.gz", self.model)
        self.endModel("END-COMBINED-MODEL", self.combinedModel, self.workDir+self.tag+"opt-examples.gz")
        if workDir != None:
            self.setWorkDir("")
        self.exitState()