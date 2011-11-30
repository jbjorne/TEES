import sys, os
import shutil
import itertools
import gzip
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Core.Model import Model
import STFormat.ConvertXML
import STFormat.Compare
from Murska.CSCConnection import CSCConnection
from Core.OptimizeParameters import optimize
from StepSelector import StepSelector
import Utils.Parameters as Parameters
import types
from Detector import Detector

from ExampleWriters.BioTextExampleWriter import BioTextExampleWriter
import Evaluators.EvaluateInteractionXML as EvaluateInteractionXML
import InteractionXML

class SingleStageDetector(Detector):
    def __init__(self):
        Detector .__init__(self)
        
#    def _beginOptModel(self):
#        if self.select == None or self.select.check("OPTIMIZE"):
#            print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":TRAIN"
#            self.cscConnection.setWorkSubDir(self.tag+"models")
#            optimize(self.classifier, self.evaluator, self.tag+"train-examples.gz", self.tag+"opt-examples.gz",\
#                     self.model.get(self.tag+"ids.classes"), self.classifierParameters, self.tag+"models", None, self.cscConnection, False, "SUBMIT")
#    
#    def _endOptModel(self):
#        # Download models
#        if self.checkStep("MODELS"):
#            self.cscConnection.setWorkSubDir(self.tag+"models")
#            bestResult = optimize(self.classifier, self.evaluator, self.tag+"train-examples.gz", self.tag+"opt-examples.gz",\
#                                  self.model.get(self.tag+"ids.classes"), self.classifierParameters, self.tag+"models", None, self.cscConnection, False, "RESULTS")
#            self.addClassifierModel(self.model, bestResult[1], bestResult[4])
#            self.model.save()
        
    def beginModel(self, step, model, trainExampleFiles, testExampleFile, importIdsFromModel=None):
        if self.checkStep(step, False):
            if model != None:
                print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":" + step
                # Create combined model
                model = self._openModel(model, "w")
                assert model.mode in ["a", "w"], (model.path, model.mode)
                if importIdsFromModel != None:
                    model.importFrom(self._openModel(importIdsFromModel, "r"), [self.tag+"ids.classes", self.tag+"ids.features", self.tag+"classifier-parameters"])
                # Catenate example files
                if len(trainExampleFiles) == 1:
                    combinedTrainExamples = trainExampleFiles[0]
                else:
                    combinedTrainExamples = os.path.normpath(self.model.path)+"-combined-examples.gz"
                    combinedTrainExamplesFile = gzip.open(combinedTrainExamples, 'wb')
                    for trainExampleFile in trainExampleFiles:
                        print >> sys.stderr, "Catenating", trainExampleFile, "to", combinedTrainExamplesFile
                        shutil.copyfileobj(gzip.open(trainExampleFile, 'rb'), combinedTrainExamplesFile)
                    combinedTrainExamplesFile.close()
                # Upload training model
                classifierParameters = Parameters.splitParameters(model.get(self.tag+"classifier-parameters"))
                classifierWorkDir = os.path.normpath(self.model.path)+"-"+self.tag+"models"
                self.cscConnection.setWorkSubDir(classifierWorkDir)
                optimize(self.classifier, self.evaluator, combinedTrainExamples, testExampleFile,\
                         model.get(self.tag+"ids.classes"), classifierParameters, classifierWorkDir, None, self.cscConnection, False, "SUBMIT")
                model.save()
    
    def endModel(self, step, model, testExampleFile):
        if self.checkStep(step, False):
            if model != None:
                print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":" + step
                # Download combined model
                model = self._openModel(model, "a")
                assert model.mode in ["a", "w"]
                classifierParameters = Parameters.splitParameters(model.get(self.tag+"classifier-parameters"))
                classifierWorkDir = os.path.normpath(self.model.path)+"-"+self.tag+"models"
                self.cscConnection.setWorkSubDir(classifierWorkDir)
                bestResult = optimize(self.classifier, self.evaluator, None, testExampleFile,\
                                      model.get(self.tag+"ids.classes"), classifierParameters, classifierWorkDir, None, self.cscConnection, False, "RESULTS")
                self.addClassifierModel(model, bestResult[1], bestResult[4])
                model.save()
    
    def train(self, trainData=None, optData=None, model=None, combinedModel=None, exampleStyle=None, 
              classifierParameters=None, parse=None, tokenization=None, fromStep=None, toStep=None):
        self._enterState(self.STATE_TRAIN, ["EXAMPLES", "BEGIN-MODEL", "END-MODEL", "BEGIN-COMBINED-MODEL", "END-COMBINED-MODEL"], fromStep, toStep)
        self._initVariables(trainData=trainData, optData=optData, model=model, combinedModel=combinedModel, exampleStyle=exampleStyle, classifierParameters=classifierParameters, parse=parse, tokenization=tokenization)
        if self.checkStep("EXAMPLES"):
            self.model = self._initModel(self.model, [("exampleStyle", self.tag+"example-style"), ("classifierParameters", self.tag+"classifier-parameters")])
            self.saveStr("parse", parse, self.model)
            self.buildExamples(self.model, [optData, trainData], [self.tag+"opt-examples.gz", self.tag+"train-examples.gz"], saveIdsToModel=True)
        self.model = self._openModel(model, "a")
        self.beginModel("BEGIN-MODEL", self.model, [self.tag+"train-examples.gz"], self.tag+"opt-examples.gz")
        self.endModel("END-MODEL", self.model, self.tag+"opt-examples.gz")
        self.beginModel("BEGIN-COMBINED-MODEL", self.combinedModel, [self.tag+"train-examples.gz", self.tag+"opt-examples.gz"], self.tag+"opt-examples.gz", self.model)
        self.endModel("END-COMBINED-MODEL", self.combinedModel, self.tag+"opt-examples.gz")
        self._exitState()
        
    def classify(self, data, model, output, parse=None):
        self._enterState(self.STATE_CLASSIFY)
        model = self._openModel(model, "r")
        if parse == None:
            parse = self.getStr("parse", model)
        self.buildExamples(model, [data], [output+".examples.gz"])
        self.classifier.test(output+".examples.gz", model.get(self.tag+"classifier-model.gz"), output + ".classifications")
        self.evaluator.evaluate(output+".examples.gz", output+".classifications", model.get(self.tag+"ids.classes"))
        xml = BioTextExampleWriter.write(output+".examples.gz", output+".classifications", data, None, model.get(self.tag+"ids.classes"), parse)
        xml = InteractionXML.splitMergedElements(xml, None)
        xml = InteractionXML.recalculateIds(xml, output+".xml.gz", True)
        EvaluateInteractionXML.run(self.evaluator, xml, data, parse)
        STFormat.ConvertXML.toSTFormat(xml, output+".tar.gz", outputTag="a2")
        if self.stEvaluator != None:
            self.stEvaluator.evaluate(output+".tar.gz")
        self._exitState()
        
    def classifyToXML(self, data, model, exampleFileName=None, tag="", classifierModel=None, split=False):
        model = self._openModel(model, "r")
        if exampleFileName == None:
            exampleFileName = tag+self.tag+"examples.gz"
            self.buildExamples(model, [data], [exampleFileName])
        if classifierModel == None:
            classifierModel = model.get(self.tag+"classifier-model.gz")
        self.classifier.test(exampleFileName, classifierModel, tag+self.tag+"classifications")
        evaluator = self.evaluator.evaluate(exampleFileName, tag+self.tag+"classifications", model.get(self.tag+"ids.classes"))
        if evaluator.getData().getTP() + evaluator.getData().getFP() > 0:
            outputFileName = tag+self.tag+"pred.xml"
            if split:
                xml = BioTextExampleWriter.write(exampleFileName, tag+self.tag+"classifications", data, None, model.get(self.tag+"ids.classes"), self.getStr("parse", model))
                xml = InteractionXML.splitMergedElements(xml, None)
                xml = InteractionXML.recalculateIds(xml, outputFileName, True)
            else:
                xml = BioTextExampleWriter.write(exampleFileName, tag+self.tag+"classifications", data, outputFileName, model.get(self.tag+"ids.classes"), self.getStr("parse", model))
            return xml
        else:
            print >> sys.stderr, "No positive predictions, XML file", tag+self.tag+"pred.xml", "not written"
            return None