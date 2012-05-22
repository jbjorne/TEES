import sys, os
import shutil
import itertools
import gzip
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Core.Model import Model
import STFormat.ConvertXML
import STFormat.Compare
from JariSandbox.ComplexPPI.Source.Murska.CSCConnection import CSCConnection
from Core.OptimizeParameters import optimize
from StepSelector import StepSelector
import Utils.Parameters as Parameters
import types
import time, datetime

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
        self.variablesToRemove = set()
    
    def __del__(self):
        self._closeModels()
    
    def _closeModels(self):
        for model in self.modelsToClose:
            model.close()
    
    def checkStep(self, step, verbose=True):
        if self.select == None or self.select.check(step):
            if verbose: print >> sys.stderr, "--------- ENTER STEP", self.__class__.__name__ + ":" + self.state + ":" + step, "---------"
            return True
        else:
            return False
    
    def getStepStatus(self, step):
        if self.select == None:
            return "NOT_EXIST"
        else:
            return self.select.getStepStatus(step)
    
    def setWorkDir(self, workDir=""):
        if workDir == None: # bypass assignment and keep currently defined workdir
            return
        elif workDir.strip() == "": # current system path
            self.workDir = ""
        elif not workDir.endswith("/"): # make sure workdir can be combined with other paths using '+'
            self.workDir = workDir + "/"
    
#    def getSharedStep(self, childDetector, step, direction=1):
#        childDetector.select.getSharedStep(step, self.select.steps, direction)
    
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
        return self.openModel(model)
    
    def saveStr(self, name, value, model=None, modelMustExist=True):
        if type(model) in types.StringTypes:
            modelObj = self.openModel(model, "a")
        else:
            if modelMustExist:
                assert model != None
            modelObj = model
        modelObj.addStr(name, value)
        modelObj.save()
    
    def saveStrings(self, dict, model=None, modelMustExist=True):
        if type(model) in types.StringTypes:
            modelObj = self.openModel(model, "a")
        else:
            if modelMustExist:
                assert model != None
            modelObj = model
        modelObj.addStrings(dict)
        modelObj.save()
    
    def getStr(self, name, model):
        if type(model) in types.StringTypes:
            modelObj = self.openModel(model, "r")
        else:
            modelObj = model
        value = modelObj.getStr(name)
        if model == None: modelObj.close()
        return value
    
    def addClassifierModel(self, model, classifierModelPath, classifierParameters):
        if type(classifierParameters) in types.StringTypes:
            classifierParameters = Parameters.splitParameters(classifierParameters)
        classifierModel = model.get(self.tag+"classifier-model.gz", True)
        shutil.copy2(classifierModelPath, classifierModel)
        model.addStr(self.tag+"classifier-parameter", Parameters.toString(classifierParameters))
        #model.addStr(self.tag+"classifier-parameters", classifierParameters)
        #Parameters.saveParameters(classifierParameters, model.get(self.tag+"classifier-parameters", True))
    
    def openModel(self, model, mode="r"):
        if type(model) in types.StringTypes:
            model = Model(model, mode)
            self.modelsToClose.append(model)
        return model
    
    def buildExamples(self, model, datas, outputs, golds=[], exampleStyle=None, saveIdsToModel=False, parse=None):
        if exampleStyle == None:
            exampleStyle = Parameters.splitParameters(model.getStr(self.tag+"example-style"))
        if parse == None:
            parse = self.getStr(self.tag+"parse", model)
        for data, output, gold in itertools.izip_longest(datas, outputs, golds, fillvalue=[]):
            print >> sys.stderr, "Example generation for", output
            if not isinstance(data, (list, tuple)): data = [data]
            if not isinstance(gold, (list, tuple)): gold = [gold]
            append = False
            for dataSet, goldSet in itertools.izip_longest(data, gold, fillvalue=None):
                if dataSet != None:
                    self.exampleBuilder.run(dataSet, output, parse, None, exampleStyle, model.get(self.tag+"ids.classes", True), model.get(self.tag+"ids.features", True), goldSet, append)
                append = True
        if saveIdsToModel:
            model.save()
    
    def enterState(self, state, steps=None, fromStep=None, toStep=None, omitSteps=None):      
        if self.state == None:
            assert self.select == None
            self.state = state
            if self.select == None or (self.select.currentStep == None and fromStep == steps[0]):
                print >> sys.stderr, "---------", self.__class__.__name__ + ":" + state + "(ENTER)", "---------"
                self.enterStateTime = time.time()
            if steps != None:
                self.select = StepSelector(steps, fromStep, toStep, omitSteps=omitSteps)
        else:
            assert self.state == state, (state, self.state)
            assert self.select.steps == steps, (steps, self.select.steps)
            self.select.setLimits(fromStep, toStep)
    
    def initVariables(self, **vars):
        if self.state == None:
            for name in sorted(vars.keys()):
                setattr(self, name, vars[name])
                self.variablesToRemove.add(name)

    def initModel(self, model, saveParams=[]):
        if model == None:
            return model
        elif type(model) in types.StringTypes:
            model = self.openModel(model, "w")
        else:
            assert model.mode in ["a", "w"]
        for param in saveParams:
            #Parameters.saveParameters(getattr(self, param[0]), model.get(param[1], True))
            model.addStr(param[1], Parameters.toString(getattr(self, param[0])))
        model.save()
        return model
    
    def exitState(self):
        if self.select == None or self.select.currentStep == self.select.steps[-1]:
            if self.select != None:
                self.select.printStepTime() # print last step time
            print >> sys.stderr, "---------", self.__class__.__name__ + ":" + self.state + "(EXIT)", str(datetime.timedelta(seconds=time.time()-self.enterStateTime)), "---------"
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
