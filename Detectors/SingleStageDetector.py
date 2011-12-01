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
        Detector.__init__(self)
        self.deleteCombinedExamples = True
        
    def beginModel(self, step, model, trainExampleFiles, testExampleFile, importIdsFromModel=None):
        if self.checkStep(step, False):
            if model != None:
                if self.state != None and step != None:
                    print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":" + step
                # Create combined model
                model = self.openModel(model, "w")
                assert model.mode in ["a", "w"], (model.path, model.mode)
                if importIdsFromModel != None:
                    importModel = self.openModel(importIdsFromModel, "r")
                    model.importFrom(self.openModel(importModel, "r"), [self.tag+"ids.classes", self.tag+"ids.features", self.tag+"classifier-parameters", self.tag+"example-style", "parse"])
                # Catenate example files
                if type(trainExampleFiles) in types.StringTypes:
                    combinedTrainExamples = trainExampleFiles
                elif len(trainExampleFiles) == 1: 
                    combinedTrainExamples = trainExampleFiles[0]
                else:
                    combinedTrainExamples = os.path.normpath(model.path)+"-"+self.tag+"combined-examples.gz"
                    combinedTrainExamplesFile = gzip.open(combinedTrainExamples, 'wb')
                    for trainExampleFile in trainExampleFiles:
                        print >> sys.stderr, "Catenating", trainExampleFile, "to", combinedTrainExamples
                        shutil.copyfileobj(gzip.open(trainExampleFile, 'rb'), combinedTrainExamplesFile)
                    combinedTrainExamplesFile.close()
                # Upload training model
                classifierParameters = Parameters.splitParameters(model.get(self.tag+"classifier-parameters"))
                origCSCWorkDir = self.cscConnection.workSubDir
                classifierWorkDir = os.path.normpath(model.path)+"-"+self.tag+"models"
                self.cscConnection.setWorkSubDir(os.path.join(origCSCWorkDir,classifierWorkDir), deleteWorkDir=True)
                optimize(self.classifier, self.evaluator, combinedTrainExamples, testExampleFile,\
                         model.get(self.tag+"ids.classes"), classifierParameters, classifierWorkDir, None, self.cscConnection, False, "SUBMIT")
                self.cscConnection.setWorkSubDir(origCSCWorkDir)
                model.save()
    
    def endModel(self, step, model, testExampleFile):
        if self.checkStep(step, False):
            if model != None:
                if self.state != None and step != None:
                    print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":" + step
                # Download combined model
                model = self.openModel(model, "a")
                assert model.mode in ["a", "w"]
                classifierParameters = Parameters.splitParameters(model.get(self.tag+"classifier-parameters"))
                origCSCWorkDir = self.cscConnection.workSubDir
                classifierWorkDir = os.path.normpath(model.path)+"-"+self.tag+"models"
                self.cscConnection.setWorkSubDir(os.path.join(origCSCWorkDir,classifierWorkDir))
                bestResult = optimize(self.classifier, self.evaluator, None, testExampleFile,\
                                      model.get(self.tag+"ids.classes"), classifierParameters, classifierWorkDir, None, self.cscConnection, False, "RESULTS")
                self.cscConnection.setWorkSubDir(origCSCWorkDir)
                self.addClassifierModel(model, bestResult[1], bestResult[4])
                model.save()
                # Check for catenated example file
                if self.deleteCombinedExamples:
                    combinedTrainExamples = os.path.normpath(model.path)+"-"+self.tag+"combined-examples.gz"
                    if os.path.exists(combinedTrainExamples):
                        print >> sys.stderr, "Deleting catenated training example file", combinedTrainExamples
                        os.remove(combinedTrainExamples)
    
    def train(self, trainData=None, optData=None, model=None, combinedModel=None, exampleStyle=None, 
              classifierParameters=None, parse=None, tokenization=None, fromStep=None, toStep=None):
        self.initVariables(trainData=trainData, optData=optData, model=model, combinedModel=combinedModel, exampleStyle=exampleStyle, classifierParameters=classifierParameters, parse=parse, tokenization=tokenization)
        self.enterState(self.STATE_TRAIN, ["EXAMPLES", "BEGIN-MODEL", "END-MODEL", "BEGIN-COMBINED-MODEL", "END-COMBINED-MODEL"], fromStep, toStep)
        if self.checkStep("EXAMPLES"):
            self.model = self.initModel(self.model, [("exampleStyle", self.tag+"example-style"), ("classifierParameters", self.tag+"classifier-parameters")])
            self.saveStr("parse", parse, self.model)
            self.buildExamples(self.model, [optData, trainData], [self.tag+"opt-examples.gz", self.tag+"train-examples.gz"], saveIdsToModel=True)
        self.model = self.openModel(model, "a") # Devel model already exists, with ids etc
        self.beginModel("BEGIN-MODEL", self.model, [self.tag+"train-examples.gz"], self.tag+"opt-examples.gz")
        self.endModel("END-MODEL", self.model, self.tag+"opt-examples.gz")
        self.beginModel("BEGIN-COMBINED-MODEL", self.combinedModel, [self.tag+"train-examples.gz", self.tag+"opt-examples.gz"], self.tag+"opt-examples.gz", self.model)
        self.endModel("END-COMBINED-MODEL", self.combinedModel, self.tag+"opt-examples.gz")
        self.exitState()
        
    def classify(self, data, model, output, parse=None):
        self._enterState(self.STATE_CLASSIFY)
        model = self.openModel(model, "r")
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
        
    def classifyToXML(self, data, model, exampleFileName=None, tag="", classifierModel=None, split=False, goldData=None):
        model = self.openModel(model, "r")
        if exampleFileName == None:
            exampleFileName = tag+self.tag+"examples.gz"
            self.buildExamples(model, [data], [exampleFileName], [goldData])
        if classifierModel == None:
            classifierModel = model.get(self.tag+"classifier-model.gz")
        else:
            assert os.path.exists(classifierModel), classifierModel
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