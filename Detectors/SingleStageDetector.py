import sys, os
import shutil
import itertools
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Core.Model import Model
import STFormat.ConvertXML
import STFormat.Compare
from Murska.CSCConnection import CSCConnection
from Core.OptimizeParameters import optimize
from StepSelector import StepSelector
import Utils.Parameters as Parameters

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
        self.tag = "ssd-"
        self._model = None
        self.workDir = ""
        
        self.exampleStyle = None
        self.classifierParameters = None
        self.parse = "split-mccc-preparsed"
        self.tokenization = None
        
        self.state = None # None, TRAIN, CLASSIFY
        self.select = None
        self.STATE_TRAIN = "STATE_TRAIN"
        self.STATE_CLASSIFY = "STATE_CLASSIFY"
        
        self.cscConnection = None
    
    def importIds(self, filename):
        pass
    
    def setCSCConnection(self, options, cscworkdir):
        if "local" not in options:
            clear = False
            if "clear" in options: 
                clear = True
            if "louhi" in options:
                self.cscConnection = CSCConnection(cscworkdir+"/edge-models", "jakrbj@louhi.csc.fi", clear)
            else:
                self.cscConnection = CSCConnection(cscworkdir+"/edge-models", "jakrbj@murska.csc.fi", clear)
        else:
            self.cscConnection = None
    
    def _openModel(self, path, readOnly=True):
        if readOnly:
            print >> sys.stderr, "Opening model", path, "if it exists"
            assert self.state == self.STATE_CLASSIFY, self.state
            self._model = Model(self.modelPath, "r")
        elif self.select.check("BEGIN"): # Begin training and clear model
            print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ".train:BEGIN"
            assert self.state == self.STATE_TRAIN, self.state
            print >> sys.stderr, "Clearing model", path, "if it exists"
            self._model = Model(self.modelPath, "w")
        else:
            print >> sys.stderr, "Using previous model", path, "if it exists"
            assert self.state == self.STATE_TRAIN, self.state
            self._model = Model(self.modelPath, "a")
    
    def _buildExamples(self, datas, outputs, golds=[]):
        if self.select.check("EXAMPLES"):
            print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":EXAMPLES"
            for data, output, gold in itertools.izip_longest(datas, outputs, golds, fillvalue=[]):
                print >> sys.stderr, "Example generation for", output
                if not isinstance(data, (list, tuple)): data = [data]
                if not isinstance(gold, (list, tuple)): gold = [gold]
                append = False
                for dataSet, goldSet in itertools.izip_longest(data, gold, fillvalue=None):
                    if dataSet != None:
                        self.exampleBuilder.run(dataSet, output, self.parse, self.tokenization, self.exampleStyle, self._model.get(self.tag+"ids.classes"), self._model.get(self.tag+"ids.features"), goldSet, append)
                    append = True
            if self._model.mode != "r":
                Parameters.saveParameters(self.exampleStyle, self._model.get(self.tag+"example-style", True))
                self._model.save()
    
    def _beginTrain(self):
        if self.select.check("TRAIN"):
            print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":TRAIN"
            optimize(self.classifier, self.evaluator, self.tag+"train-examples.gz", self.tag+"opt-examples.gz",\
                     self._model.get(self.tag+"ids.classes"), self.classifierParameters, self.tag+"models", None, self.cscConnection, False, "SUBMIT")
    
    def _endTrain(self):
        # Download models
        if self.select.check("MODELS"):
            print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":MODELS"
            bestResult = optimize(self.classifier, self.evaluator, self.tag+"train-examples.gz", self.tag+"opt-examples.gz",\
                                  self._model.get(self.tag+"ids.classes"), self.classifierParameters, self.tag+"models", None, self.cscConnection, False, "RESULTS")
            classifierModel = self._model.get(self.tag+"classifier-model.gz", True)
            shutil.copy2(bestResult[1], classifierModel)
            self._model.save()
            print bestResult[4]
            Parameters.saveParameters(bestResult[4], self._model.get(self.tag+"classifier-parameters", True))
            self._model.save()
    
    def _beginProcess(self, state, steps=[], fromStep=None, toStep=None):      
        if self.state == None:
            assert self.select == None
            self.state = state
            self.select = StepSelector(steps, fromStep, toStep)
        else:
            assert self.state == state, (state, self.state)
            assert self.select.steps == steps, (steps, self.select.steps)
            self.select.setLimits(fromStep, toStep)
    
    def _endProcess(self):
        if self.select.check("END"):
            print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":END"
            if self._model != None:
                self._model.close()
            self._model = None
            self.state = None
            self.select = None
    
    def train(self, trainData=None, optData=None, fromStep=None, toStep=None):
        self._beginProcess(self.STATE_TRAIN, ["BEGIN", "EXAMPLES", "TRAIN", "MODELS", "END"], fromStep, toStep)
        self._openModel(self.modelPath, False)
        self._buildExamples([optData, trainData], [self.tag+"opt-examples.gz", self.tag+"train-examples.gz"])
        self._beginTrain()
        self._endTrain()
        self._endProcess()
        
    def classify(self, data, output):
        self._beginProcess(self.STATE_CLASSIFY, ["EXAMPLES", "END"])
        self._openModel(self.modelPath)
        self._buildExamples([data], [output+".examples.gz"])
        self.classifier.test(output+".examples.gz", self._model.get(self.tag+"classifier-model.gz"), output + ".classifications")
        self.evaluator.evaluate(output+".examples.gz", output+".classifications", self._model.get(self.tag+"ids.classes"))
        xml = BioTextExampleWriter.write(output+".examples.gz", output+".classifications", data, None, self._model.get(self.tag+"ids.classes"), self.parse, self.tokenization)
        xml = InteractionXML.splitMergedElements(xml, None)
        xml = InteractionXML.recalculateIds(xml, output+".xml", True)
        EvaluateInteractionXML.run(self.evaluator, xml, data, self.parse, self.tokenization)
        STFormat.ConvertXML.toSTFormat(xml, output+".tar.gz", outputTag="a2")
        if self.stEvaluator != None:
            self.stEvaluator.evaluate(output+".tar.gz")
        self._endProcess()
