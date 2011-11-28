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

from ExampleWriters.BioTextExampleWriter import BioTextExampleWriter
import Evaluators.EvaluateInteractionXML as EvaluateInteractionXML
import InteractionXML

class SingleStageDetector():
    def __init__(self):
        self.exampleBuilder = None
        self.classifier = None
        self.evaluator = None
        self.stEvaluator = None
        self.modelPath = None
        self.combinedModelPath = None
        self.tag = "ssd-"
        self._model = None
        self._combinedModel = None
        self.workDir = ""
        
        self.exampleStyle = None
        self.classifierParameters = None
        self.parse = "split-mccc-preparsed"
        self.tokenization = None
        
        self.state = None # None, TRAIN, CLASSIFY
        self.select = None
        self.STATE_TRAIN = "TRAIN"
        self.STATE_CLASSIFY = "CLASSIFY"
        
        self.cscConnection = None
    
    def setCSCConnection(self, options, cscworkdir):
        if "local" not in options:
            clear = False
            if "clear" in options: 
                clear = True
            if "louhi" in options:
                self.cscConnection = CSCConnection(cscworkdir, "jakrbj@louhi.csc.fi", clear)
            else:
                self.cscConnection = CSCConnection(cscworkdir, "jakrbj@murska.csc.fi", clear)
        else:
            self.cscConnection = None
    
    def _openModel(self, model, mode="r"):
        if type(model) == types.StringTypes:
            return Model(self.modelPath, mode)
        else:
            return model
    
    def _buildExamples(self, datas, outputs, golds=[]):
        if self.select == None or self.select.check("EXAMPLES"):
            if self.select != None: print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":EXAMPLES"
            exampleStyle = Parameters.splitParameters(self._model.get(self.tag+"example-style"))
            for data, output, gold in itertools.izip_longest(datas, outputs, golds, fillvalue=[]):
                print >> sys.stderr, "Example generation for", output
                if not isinstance(data, (list, tuple)): data = [data]
                if not isinstance(gold, (list, tuple)): gold = [gold]
                append = False
                for dataSet, goldSet in itertools.izip_longest(data, gold, fillvalue=None):
                    if dataSet != None:
                        self.exampleBuilder.run(dataSet, output, self.parse, self.tokenization, exampleStyle, self._model.get(self.tag+"ids.classes"), self._model.get(self.tag+"ids.features"), goldSet, append)
                    append = True
    
    def _beginOptModel(self):
        if self.select == None or self.select.check("OPTIMIZE"):
            print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":TRAIN"
            self.cscConnection.setWorkSubDir(self.tag+"models")
            optimize(self.classifier, self.evaluator, self.tag+"train-examples.gz", self.tag+"opt-examples.gz",\
                     self._model.get(self.tag+"ids.classes"), self.classifierParameters, self.tag+"models", None, self.cscConnection, False, "SUBMIT")
    
    def _endOptModel(self):
        # Download models
        if self.select.check("MODELS"):
            print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":MODELS"
            self.cscConnection.setWorkSubDir(self.tag+"models")
            bestResult = optimize(self.classifier, self.evaluator, self.tag+"train-examples.gz", self.tag+"opt-examples.gz",\
                                  self._model.get(self.tag+"ids.classes"), self.classifierParameters, self.tag+"models", None, self.cscConnection, False, "RESULTS")
            classifierModel = self._model.get(self.tag+"classifier-model.gz", True)
            shutil.copy2(bestResult[1], classifierModel)
            self._model.save()
            print bestResult[4]
            Parameters.saveParameters(bestResult[4], self._model.get(self.tag+"classifier-parameters", True))
            self._model.save()
    
    def _enterState(self, state, steps=None, fromStep=None, toStep=None):      
        if self.state == None:
            assert self.select == None
            self.state = state
            if steps != None:
                self.select = StepSelector(steps, fromStep, toStep)
            else:
                self.select = None
        else:
            assert self.state == state, (state, self.state)
            assert self.select.steps == steps, (steps, self.select.steps)
            self.select.setLimits(fromStep, toStep)

    def _initTrainVariables(self, model, parse=None, tokenization=None):
        if self.select == None or self.select.currentStep == None:
            self._model = self._openModel(model, "w")
            Parameters.saveParameters(self.exampleStyle, self._model.get(self.tag+"example-style", True))
            self._model.save()
        else:
            self._model = Model(self.modelPath, "a")
    
    def _exitState(self):
        if self.select == None or self.select.currentStep == self.select.steps[-1]:
            print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":END"
            if self._model != None:
                self._model.close()
            self._model = None
            self.state = None
            self.select = None
    
    def _beginCombinedModel(self):
        if self.select == None or self.select.check("TRAIN-COMBINED"):
            if self.combinedModelPath != None:
                print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":TRAIN-COMBINED"
                # Create combined model
                self._combinedModel = Model(self.combinedModelPath, "w")
                self._combinedModel.importFrom(self._model, [self.tag+"ids.classes", self.tag+"ids.features", self.tag+"classifier-parameters"])
                # Catenate example files
                combinedExamples = gzip.open(self.tag+"train-and-opt-examples.gz", 'wb')
                shutil.copyfileobj(gzip.open(self.tag+"opt-examples.gz", 'rb'), combinedExamples)
                shutil.copyfileobj(gzip.open(self.tag+"train-examples.gz", 'rb'), combinedExamples)
                combinedExamples.close()
                # Upload training model
                classifierParameters = Parameters.splitParameters(self._model.get(self.tag+"classifier-parameters"))
                print classifierParameters
                self.cscConnection.setWorkSubDir(self.tag+"combined-model")
                optimize(self.classifier, self.evaluator, self.tag+"train-and-opt-examples.gz", self.tag+"opt-examples.gz",\
                         self._combinedModel.get(self.tag+"ids.classes"), classifierParameters, self.tag+"models-train-and-opt", None, self.cscConnection, False, "SUBMIT")
                self._combinedModel.save()
                self._combinedModel.close()
                self._combinedModel = None
    
    def _endCombinedModel(self):
        if self.select == None or self.select.check("MODEL-COMBINED"):
            if self.combinedModelPath != None:
                print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":MODEL-COMBINED"
                # Download combined model
                self._combinedModel = Model(self.combinedModelPath, "a")
                classifierParameters = Parameters.splitParameters(self._combinedModel.get(self.tag+"classifier-parameters"))
                self.cscConnection.setWorkSubDir(self.tag+"combined-model")
                bestResult = optimize(self.classifier, self.evaluator, self.tag+"train-and-opt-examples.gz", self.tag+"opt-examples.gz",\
                                      self._combinedModel.get(self.tag+"ids.classes"), classifierParameters, self.tag+"models-train-and-opt", None, self.cscConnection, False, "RESULTS")
                classifierModel = self._combinedModel.get(self.tag+"classifier-model.gz", True)
                shutil.copy2(bestResult[1], classifierModel)
                self._combinedModel.save()
                print bestResult[4]
                self._combinedModel.close()
                self._combinedModel = None
    
    def train(self, trainData=None, optData=None, 
              model=None, combinedModel=None,
              exampleStyle=None, classifierParameters=None,
              parse=None, tokenization=None,
              fromStep=None, toStep=None):
        self._enterState(self.STATE_TRAIN, ["EXAMPLES", "OPTIMIZE", "MODELS", "TRAIN-COMBINED", "MODEL-COMBINED"], fromStep, toStep)
        self._initTrainVariables(trainData, optData, model, combinedModel, exampleStyle, classifierParameters, parse, tokenization)
        self._openModel(self.modelPath, False)
        self._buildExamples([optData, trainData], [self.tag+"opt-examples.gz", self.tag+"train-examples.gz"])
        self._beginOptModel()
        self._endOptModel()
        self._beginCombinedModel()
        self._endCombinedModel()
        self._exitState()
        
    def classify(self, data, model, output):
        self._enterState(self.STATE_CLASSIFY)
        self._model = self._openModel(model, "r")
        self._buildExamples([data], [output+".examples.gz"])
        self.classifier.test(output+".examples.gz", self._model.get(self.tag+"classifier-model.gz"), output + ".classifications")
        self.evaluator.evaluate(output+".examples.gz", output+".classifications", self._model.get(self.tag+"ids.classes"))
        xml = BioTextExampleWriter.write(output+".examples.gz", output+".classifications", data, None, self._model.get(self.tag+"ids.classes"), self.parse, self.tokenization)
        xml = InteractionXML.splitMergedElements(xml, None)
        xml = InteractionXML.recalculateIds(xml, output+".xml.gz", True)
        EvaluateInteractionXML.run(self.evaluator, xml, data, self.parse, self.tokenization)
        STFormat.ConvertXML.toSTFormat(xml, output+".tar.gz", outputTag="a2")
        if self.stEvaluator != None:
            self.stEvaluator.evaluate(output+".tar.gz")
        self._model.close()
        self._model = None
        self._exitState()
