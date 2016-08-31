import sys, os
import shutil
from Detectors.EdgeDetector import EdgeDetector
from Classifiers.AllCorrectClassifier import AllCorrectClassifier
import Utils.ElementTreeUtils as ETUtils
import Evaluators.EvaluateInteractionXML as EvaluateInteractionXML
import Utils.STFormat.ConvertXML
import Utils.Parameters as Parameters
from Detectors.SingleStageDetector import SingleStageDetector

class PairBuilder(EdgeDetector):
    def __init__(self):
        EdgeDetector.__init__(self)
        self.Classifier = AllCorrectClassifier
    
    def train(self, trainData=None, optData=None, model=None, combinedModel=None, exampleStyle=None, 
        classifierParameters=None, parse=None, tokenization=None, task=None, fromStep=None, toStep=None, 
        workDir=None):
        
        exampleStyle = Parameters.cat(exampleStyle, "keep_neg:no_features")
        SingleStageDetector.train(self, trainData, optData, model, combinedModel, exampleStyle, classifierParameters, parse, tokenization, fromStep, toStep)
        self.classify(trainData, model, "classification-train/train", goldData=trainData, workDir="classification-train")
        
#         self.initVariables(trainData=trainData, optData=optData, model=model, combinedModel=combinedModel, exampleStyle=exampleStyle, classifierParameters=classifierParameters, parse=parse, tokenization=tokenization)
#         self.setWorkDir(workDir)
#         self.enterState(self.STATE_TRAIN, ["ANALYZE", "EXAMPLES"], fromStep, toStep)
#         if self.checkStep("ANALYZE"):
#             # General training initialization done at the beginning of the first state
#             self.model = self.initModel(self.model, [("exampleStyle", self.tag+"example-style"), ("classifierParameters", self.tag+"classifier-parameters-train")])
#             self.saveStr(self.tag+"parse", parse, self.model)
#             if task != None:
#                 self.saveStr(self.tag+"task", task, self.model)
#             # Perform structure analysis
#             self.structureAnalyzer.analyze([optData, trainData], self.model)
#             print >> sys.stderr, self.structureAnalyzer.toString()
#         self.model = self.openModel(model, "a") # Devel model already exists, with ids etc
#         if self.checkStep("EXAMPLES"):
#             self.buildExamples(self.model, [optData, trainData], [self.workDir+self.tag+"opt-examples.gz", self.workDir+self.tag+"train-examples.gz"], saveIdsToModel=True)
#         if workDir != None:
#             self.setWorkDir("")
#         self.exitState()
#         # Classify the training set
#         self.classify(trainData, model, "classification-train/train", goldData=trainData, workDir="classification-train")
    
    def classify(self, data, model, output, parse=None, task=None, goldData=None, workDir=None, fromStep=None, omitSteps=None, validate=False):
        model = self.openModel(model, "r")
        self.enterState(self.STATE_CLASSIFY)
        self.setWorkDir(workDir)
        if workDir == None:
            self.setTempWorkDir()
        model = self.openModel(model, "r")
        if parse == None: parse = self.getStr(self.tag+"parse", model)
        workOutputTag = os.path.join(self.workDir, os.path.basename(output) + "-")
        self.classifyToXML(data, model, None, workOutputTag, model.get(self.tag+"classifier-model", defaultIfNotExist=None), goldData, parse)
        self.deleteTempWorkDir()
        self.exitState()