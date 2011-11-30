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
        super(SingleStageDetector, self).__init__()
        
    def _beginOptModel(self):
        if self.select == None or self.select.check("OPTIMIZE"):
            print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":TRAIN"
            self.cscConnection.setWorkSubDir(self.tag+"models")
            optimize(self.classifier, self.evaluator, self.tag+"train-examples.gz", self.tag+"opt-examples.gz",\
                     self.model.get(self.tag+"ids.classes"), self.classifierParameters, self.tag+"models", None, self.cscConnection, False, "SUBMIT")
    
    def _endOptModel(self):
        # Download models
        if self.checkStep("MODELS"):
            self.cscConnection.setWorkSubDir(self.tag+"models")
            bestResult = optimize(self.classifier, self.evaluator, self.tag+"train-examples.gz", self.tag+"opt-examples.gz",\
                                  self.model.get(self.tag+"ids.classes"), self.classifierParameters, self.tag+"models", None, self.cscConnection, False, "RESULTS")
            self.addClassifierModel(self.model, bestResult[1], bestResult[4])
            self.model.save()
        
    def _beginCombinedModel(self):
        if self.checkStep("TRAIN-COMBINED", False):
            if self.combinedModel != None:
                print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":TRAIN-COMBINED"
                # Create combined model
                self.combinedModel = self._openModel(self.combinedModel, "w")
                self.combinedModel.importFrom(self.model, [self.tag+"ids.classes", self.tag+"ids.features", self.tag+"classifier-parameters"])
                # Catenate example files
                combinedExamples = gzip.open(self.tag+"train-and-opt-examples.gz", 'wb')
                shutil.copyfileobj(gzip.open(self.tag+"opt-examples.gz", 'rb'), combinedExamples)
                shutil.copyfileobj(gzip.open(self.tag+"train-examples.gz", 'rb'), combinedExamples)
                combinedExamples.close()
                # Upload training model
                classifierParameters = Parameters.splitParameters(self.model.get(self.tag+"classifier-parameters"))
                print classifierParameters
                self.cscConnection.setWorkSubDir(self.tag+"combined-model")
                optimize(self.classifier, self.evaluator, self.tag+"train-and-opt-examples.gz", self.tag+"opt-examples.gz",\
                         self.combinedModel.get(self.tag+"ids.classes"), classifierParameters, self.tag+"models-train-and-opt", None, self.cscConnection, False, "SUBMIT")
                self.combinedModel.save()
                self.combinedModel.close()
                self.combinedModel = None
    
    def _endCombinedModel(self):
        if self.checkStep("MODEL-COMBINED"):
            if self.combinedModel != None:
                print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":MODEL-COMBINED"
                # Download combined model
                self.combinedModel = self._openModel(self.combinedModel, "a")
                classifierParameters = Parameters.splitParameters(self.combinedModel.get(self.tag+"classifier-parameters"))
                self.cscConnection.setWorkSubDir(self.tag+"combined-model")
                bestResult = optimize(self.classifier, self.evaluator, self.tag+"train-and-opt-examples.gz", self.tag+"opt-examples.gz",\
                                      self.combinedModel.get(self.tag+"ids.classes"), classifierParameters, self.tag+"models-train-and-opt", None, self.cscConnection, False, "RESULTS")
                self.addClassifierModel(self.combinedModel, bestResult[1], bestResult[4])
                self.combinedModel.save()
                self.combinedModel.close()
                self.combinedModel = None
    
    def train(self, trainData=None, optData=None, 
              model=None, combinedModel=None,
              exampleStyle=None, classifierParameters=None,
              parse=None, tokenization=None,
              fromStep=None, toStep=None):
        self._enterState(self.STATE_TRAIN, ["EXAMPLES", "OPTIMIZE", "MODELS", "TRAIN-COMBINED", "MODEL-COMBINED"], fromStep, toStep)
        self._initTrainVariables(trainData, optData, model, combinedModel, exampleStyle, classifierParameters, parse, tokenization)
        self._initModel(self.model, False)
        if self.select == None or self.select.check("EXAMPLES"):
            if self.select != None: print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":EXAMPLES"
            self.buildExamples([optData, trainData], [self.tag+"opt-examples.gz", self.tag+"train-examples.gz"])
        self._beginOptModel()
        self._endOptModel()
        self._beginCombinedModel()
        self._endCombinedModel()
        self._exitState()
        
    def classify(self, data, model, output):
        self._enterState(self.STATE_CLASSIFY)
        self.model = self._openModel(model, "r")
        self.buildExamples([data], [output+".examples.gz"])
        self.classifier.test(output+".examples.gz", self.model.get(self.tag+"classifier-model.gz"), output + ".classifications")
        self.evaluator.evaluate(output+".examples.gz", output+".classifications", self.model.get(self.tag+"ids.classes"))
        xml = BioTextExampleWriter.write(output+".examples.gz", output+".classifications", data, None, self.model.get(self.tag+"ids.classes"), self.parse, self.tokenization)
        xml = InteractionXML.splitMergedElements(xml, None)
        xml = InteractionXML.recalculateIds(xml, output+".xml.gz", True)
        EvaluateInteractionXML.run(self.evaluator, xml, data, self.parse, self.tokenization)
        STFormat.ConvertXML.toSTFormat(xml, output+".tar.gz", outputTag="a2")
        if self.stEvaluator != None:
            self.stEvaluator.evaluate(output+".tar.gz")
        self.model.close()
        self.model = None
        self._exitState()
