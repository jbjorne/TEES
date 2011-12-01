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

class Detector():
    def __init__(self):
        self.exampleBuilder = None
        self.classifier = None
        self.evaluator = None
        self.stEvaluator = None
        self.modelPath = None
        self.combinedModelPath = None
        self.tag = "UNKNOWN-"
        self.model = None
        self.combinedModel = None
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
        self.modelsToClose = []
        self.variablesToRemove = []
    
    def __del__(self):
        self._closeModels()
    
    def _closeModels(self):
        for model in self.modelsToClose:
            model.close()
    
    def checkStep(self, step, verbose=True):
        if self.select == None or self.select.check(step):
            if verbose: print >> sys.stderr, self.__class__.__name__ + ":" + self.state + ":" + step
            return True
        else:
            return False
    
    def getSharedStep(self, childDetector, step, direction=1):
        childDetector.select.getSharedStep(step, self.select.steps, direction)
    
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
    
    def getModel(self):
        return self._openModel(model)
    
    def saveStr(self, name, value, model=None):
        if type(model) in types.StringTypes:
            modelObj = self._openModel(model, "a")
        else:
            modelObj = model
        modelObj.addStr(name, value)
        modelObj.save()
    
    def getStr(self, name, model=None):
        if model == None:
            modelObj = self._openModel(model, "r")
        else:
            modelObj = model
        value = modelObj.getStr(name)
        if model == None: modelObj.close()
        return value
    
    def addClassifierModel(self, model, classifierModelPath, classifierParameters):
        classifierModel = model.get(self.tag+"classifier-model.gz", True)
        shutil.copy2(classifierModelPath, classifierModel)
        Parameters.saveParameters(classifierParameters, model.get(self.tag+"classifier-parameters", True))
    
    def _openModel(self, model, mode="r"):
        if type(model) in types.StringTypes:
            model = Model(model, mode)
            self.modelsToClose.append(model)
        return model
    
    def buildExamples(self, model, datas, outputs, golds=[], exampleStyle=None, saveIdsToModel=False):
        if exampleStyle == None:
            exampleStyle = Parameters.splitParameters(model.get(self.tag+"example-style"))
        for data, output, gold in itertools.izip_longest(datas, outputs, golds, fillvalue=[]):
            print >> sys.stderr, "Example generation for", output
            if not isinstance(data, (list, tuple)): data = [data]
            if not isinstance(gold, (list, tuple)): gold = [gold]
            append = False
            for dataSet, goldSet in itertools.izip_longest(data, gold, fillvalue=None):
                if dataSet != None:
                    self.exampleBuilder.run(dataSet, output, self.parse, self.tokenization, exampleStyle, model.get(self.tag+"ids.classes"), model.get(self.tag+"ids.features"), goldSet, append)
                append = True
        if saveIdsToModel:
            model.save()
    
    def _enterState(self, state, steps=None, fromStep=None, toStep=None):      
        if self.state == None:
            assert self.select == None
            self.state = state
            if steps != None:
                self.select = StepSelector(steps, fromStep, toStep)
            if self.select == None or (self.select.currentStep == None and fromStep == steps[0]):
                print >> sys.stderr, self.__class__.__name__ + ":" + state + "(ENTER)"
        else:
            assert self.state == state, (state, self.state)
            assert self.select.steps == steps, (steps, self.select.steps)
            self.select.setLimits(fromStep, toStep)
    
    def _initVariables(self, **vars):
        if self.select == None or self.select.currentStep == None:
            for name in sorted(vars.keys()):
                setattr(self, name, vars[name])
                self.variablesToRemove.append(name)

    def _initModel(self, model, saveParams=[]):
        if type(model) in types.StringTypes:
            model = self._openModel(model, "w")
        else:
            assert model.mode in ["a", "w"]
        for param in saveParams:
            Parameters.saveParameters(getattr(self, param[0]), model.get(param[1], True))
        model.save()
        return model
    
    def _exitState(self):
        if self.select == None or self.select.currentStep == self.select.steps[-1]:
            print >> sys.stderr, self.__class__.__name__ + ":" + self.state + "(EXIT)"
            self.state = None
            self.select = None
            for name in self.variablesToRemove:
                if hasattr(self, name):
                    delattr(self, name)
            self._closeModels()
        
    def train(self, trainData=None, optData=None, 
              model=None, combinedModel=None,
              exampleStyle=None, classifierParameters=None,
              parse=None, tokenization=None,
              fromStep=None, toStep=None):
        pass
        
    def classify(self, data, model, output):
        pass
