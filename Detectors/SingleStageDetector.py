import sys, os
import shutil
import itertools
import gzip
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../CommonUtils")
import cElementTreeUtils as ETUtils
from Core.Model import Model
import Core.ExampleUtils as ExampleUtils
import STFormat.ConvertXML
import STFormat.Compare
#from Murska.CSCConnection import CSCConnection
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
                # Information can be imported from an existing model. In this case, model is trained
                # with the parameter already defined in the import source. This is used when training
                # the combined model.
                if importIdsFromModel != None:
                    #importModel = self.openModel(importIdsFromModel, "r")
                    #model.importFrom(self.openModel(importModel, "r"), [self.tag+"ids.classes", self.tag+"ids.features", self.tag+"classifier-parameters", self.tag+"example-style", self.tag+"parse"])
                    model.importFrom(self.openModel(importIdsFromModel, "r"), [self.tag+"ids.classes", self.tag+"ids.features"],
                                     [self.tag+"classifier-parameter", self.tag+"example-style", self.tag+"parse"])
                    # Train the model with the parameters defined in the import source
                    model.addStr(self.tag+"classifier-parameters-train", model.getStr(self.tag+"classifier-parameter"))
                # Catenate example files
                if type(trainExampleFiles) in types.StringTypes:
                    combinedTrainExamples = trainExampleFiles
                elif len(trainExampleFiles) == 1: 
                    combinedTrainExamples = trainExampleFiles[0]
                else:
                    combinedTrainExamples = self.workDir + os.path.normpath(model.path)+"-"+self.tag+"combined-examples.gz"
                    combinedTrainExamplesFile = gzip.open(combinedTrainExamples, 'wb')
                    for trainExampleFile in trainExampleFiles:
                        print >> sys.stderr, "Catenating", trainExampleFile, "to", combinedTrainExamples
                        shutil.copyfileobj(gzip.open(trainExampleFile, 'rb'), combinedTrainExamplesFile)
                    combinedTrainExamplesFile.close()
                # Upload training model
                # The parameter grid is stored in the model as "*classifier-parameters-train" so that endModel can 
                # use it, and also as annotation for the trained model. The final selected parameter will
                # be stored as "*classifier-parameter" 
                classifierParameters = Parameters.splitParameters(model.getStr(self.tag+"classifier-parameters-train"))
                #origCSCWorkDir = self.cscConnection.workSubDir
                classifierWorkDir = self.workDir + os.path.normpath(model.path) + "-" + self.tag + "models"
                #self.cscConnection.setWorkSubDir(os.path.join(origCSCWorkDir,classifierWorkDir), deleteWorkDir=True)
                classifier = self.Classifier(self.connection)
                classifier.optimize(combinedTrainExamples, classifierWorkDir, classifierParameters, testExampleFile, model.get(self.tag+"ids.classes"), step="SUBMIT", evaluator=self.evaluator)
                #optimize(self.classifier, self.evaluator, combinedTrainExamples, testExampleFile,\
                #         model.get(self.tag+"ids.classes"), classifierParameters, classifierWorkDir, None, self.cscConnection, False, "SUBMIT")
                #self.cscConnection.setWorkSubDir(origCSCWorkDir)
                model.save()
    
    def endModel(self, step, model, testExampleFile):
        if self.checkStep(step, False):
            if model != None:
                if self.state != None and step != None:
                    print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":" + step
                # Download combined model
                model = self.openModel(model, "a")
                assert model.mode in ["a", "w"]
                classifierParameters = Parameters.splitParameters(model.getStr(self.tag+"classifier-parameters-train"))
                classifierWorkDir = self.workDir + os.path.normpath(model.path) + "-" + self.tag+ "models"
                #if self.cscConnection != None:
                #    origCSCWorkDir = self.cscConnection.workSubDir
                #    self.cscConnection.setWorkSubDir(os.path.join(origCSCWorkDir, classifierWorkDir))
                classifier = self.Classifier(self.connection)
                optimized = classifier.optimize("DUMMY", classifierWorkDir, classifierParameters, testExampleFile, model.get(self.tag+"ids.classes"), step="RESULTS", evaluator=self.evaluator)
                #bestResult = optimize(self.classifier, self.evaluator, None, testExampleFile,\
                #                      model.get(self.tag+"ids.classes"), classifierParameters, classifierWorkDir, None, self.cscConnection, False, "RESULTS")
                #if self.cscConnection != None:
                #    self.cscConnection.setWorkSubDir(origCSCWorkDir)
                self.addClassifierModel(model, optimized.model, optimized.parameters)
                #self.addClassifierModel(model, bestResult[1], bestResult[4])
                model.save()
                # Check for catenated example file
                if self.deleteCombinedExamples:
                    combinedTrainExamples = os.path.normpath(model.path)+"-"+self.tag+"combined-examples.gz"
                    if os.path.exists(combinedTrainExamples):
                        print >> sys.stderr, "Deleting catenated training example file", combinedTrainExamples
                        os.remove(combinedTrainExamples)
    
    def train(self, trainData=None, optData=None, model=None, combinedModel=None, exampleStyle=None, 
              classifierParameters=None, parse=None, tokenization=None, task=None, fromStep=None, toStep=None):
        self.initVariables(trainData=trainData, optData=optData, model=model, combinedModel=combinedModel, exampleStyle=exampleStyle, classifierParameters=classifierParameters, parse=parse, tokenization=tokenization)
        self.enterState(self.STATE_TRAIN, ["EXAMPLES", "BEGIN-MODEL", "END-MODEL", "BEGIN-COMBINED-MODEL", "END-COMBINED-MODEL"], fromStep, toStep)
        if self.checkStep("EXAMPLES"):
            self.model = self.initModel(self.model, [("exampleStyle", self.tag+"example-style"), ("classifierParameters", self.tag+"classifier-parameters")])
            self.saveStr(self.tag+"parse", parse, self.model)
            self.saveStr(self.tag+"task", task, self.model)
            self.buildExamples(self.model, [optData, trainData], [self.tag+"opt-examples.gz", self.tag+"train-examples.gz"], saveIdsToModel=True)
        self.model = self.openModel(model, "a") # Devel model already exists, with ids etc
        self.beginModel("BEGIN-MODEL", self.model, [self.tag+"train-examples.gz"], self.tag+"opt-examples.gz")
        self.endModel("END-MODEL", self.model, self.tag+"opt-examples.gz")
        self.beginModel("BEGIN-COMBINED-MODEL", self.combinedModel, [self.tag+"train-examples.gz", self.tag+"opt-examples.gz"], self.tag+"opt-examples.gz", self.model)
        self.endModel("END-COMBINED-MODEL", self.combinedModel, self.tag+"opt-examples.gz")
        self.exitState()
        
    def classify(self, data, model, output, parse=None, task=None):
        self.enterState(self.STATE_CLASSIFY)
        model = self.openModel(model, "r")
        if parse == None:
            parse = self.getStr(self.tag+"parse", model)
        if task == None:
            task = self.getStr(self.tag+"task", model)
        self.buildExamples(model, [data], [output+".examples.gz"])
        self.classifier.test(output+".examples.gz", model.get(self.tag+"classifier-model.gz"), output + ".classifications")
        self.evaluator.evaluate(output+".examples.gz", output+".classifications", model.get(self.tag+"ids.classes"))
        xml = BioTextExampleWriter.write(output+".examples.gz", output+".classifications", data, None, model.get(self.tag+"ids.classes"), parse)
        #xml = InteractionXML.splitMergedElements(xml, None)
        #xml = InteractionXML.recalculateIds(xml, output+".xml.gz", True)
        EvaluateInteractionXML.run(self.evaluator, xml, data, parse)
        STFormat.ConvertXML.toSTFormat(xml, output+".tar.gz", outputTag="a2")
        if self.stEvaluator != None:
            self.stEvaluator.evaluate(output+".tar.gz", task)
        self.exitState()
        
    def classifyToXML(self, data, model, exampleFileName=None, tag="", classifierModel=None, split=False, goldData=None, parse=None, recallAdjust=None, compressExamples=True):
        model = self.openModel(model, "r")
        if parse == None:
            parse = self.getStr(self.tag+"parse", model)
        if exampleFileName == None:
            exampleFileName = tag+self.tag+"examples"
            if compressExamples:
                exampleFileName += ".gz"
            self.buildExamples(model, [data], [exampleFileName], [goldData], parse=parse)
        if classifierModel == None:
            classifierModel = model.get(self.tag+"classifier-model")
        else:
            assert os.path.exists(classifierModel), classifierModel
        classifier = self.Classifier(self.connection)
        classifier.classify(exampleFileName, tag+self.tag+"classifications", classifierModel, finishBeforeReturn=True)
        #self.classifier.test(exampleFileName, classifierModel, tag+self.tag+"classifications")
        if recallAdjust == None:
            predictions = tag+self.tag+"classifications"
        else:
            predictions = ExampleUtils.loadPredictionsAdjust(tag+self.tag+"classifications", recallAdjust)
        evaluator = self.evaluator.evaluate(exampleFileName, predictions, model.get(self.tag+"ids.classes"))
        outputFileName = tag+self.tag+"pred.xml.gz"
        if evaluator.getData().getTP() + evaluator.getData().getFP() > 0:
            #if split:
            #    xml = BioTextExampleWriter.write(exampleFileName, predictions, data, None, model.get(self.tag+"ids.classes"), parse)
            #    xml = InteractionXML.splitMergedElements(xml, None)
            #    xml = InteractionXML.recalculateIds(xml, outputFileName, True)
            #else:
            #    xml = BioTextExampleWriter.write(exampleFileName, predictions, data, outputFileName, model.get(self.tag+"ids.classes"), parse)
            #return xml
            return BioTextExampleWriter.write(exampleFileName, predictions, data, outputFileName, model.get(self.tag+"ids.classes"), parse)
        else:
            # TODO: e.g. interactions must be removed if task does unmerging
            print >> sys.stderr, "No positive", self.tag + "predictions, XML file", tag+self.tag+"pred.xml", "unchanged from input"
            if type(data) in types.StringTypes: # assume its a file
                shutil.copy(data, outputFileName)
            else: # assume its an elementtree
                ETUtils.write(data, outputFileName)
            #print >> sys.stderr, "No positive predictions, XML file", tag+self.tag+"pred.xml", "not written"
            return data #None