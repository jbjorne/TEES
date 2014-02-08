"""
The base class for the object oriented interface.
"""
import sys, os
import shutil
import itertools
import tempfile
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Core.Model import Model
from StepSelector import StepSelector
from StructureAnalyzer import StructureAnalyzer
import Utils.Parameters as Parameters
import Evaluators.BioNLP11GeniaTools
import types
import time, datetime

class Detector():
    """
    Detector is the central class of the TEES object oriented interface. Subclasses derived from
    it encapsulate the event and relation detection process used by TEES for the various tasks
    it has been developed for. When extending TEES, a new Detector can be derived from this class.
    
    The Detector is designed for a pipeline where interaction XML is converted to machine learning
    examples, these examples are used to train a classifier and this classifier in turn is used
    to classify unknown text.
    """
    def __init__(self):
        self.structureAnalyzer = StructureAnalyzer()
        self.exampleBuilder = None
        self.exampleWriter = None
        self.Classifier = None
        self.evaluator = None
        self.bioNLPSTParams = None
        self.stEvaluator = Evaluators.BioNLP11GeniaTools
        self.modelPath = None
        self.combinedModelPath = None
        self.tag = "UNKNOWN-"
        self.model = None
        self.combinedModel = None
        self.workDir = ""
        self.workDirIsTempDir = False
        
        self.exampleStyle = None
        self.classifierParameters = None
        self.parse = "split-mccc-preparsed"
        self.tokenization = None
        
        self.state = None # None, TRAIN, CLASSIFY
        self.select = None
        self.STATE_TRAIN = "TRAIN"
        self.STATE_CLASSIFY = "CLASSIFY"
        
        #self.cscConnection = None
        self.connection = None
        self.modelsToClose = []
        self.variablesToRemove = set()
        self.debug=False
    
    def __del__(self):
        self._closeModels()
    
    def _closeModels(self):
        for model in self.modelsToClose:
            model.close()
    
    def checkStep(self, step, verbose=True):
        if self.select == None or self.select.check(step):
            if verbose: print >> sys.stderr, "=== ENTER STEP", self.__class__.__name__ + ":" + self.state + ":" + step, "==="
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
            assert not self.workDirIsTempDir
            self.workDir = ""
        elif not workDir.endswith("/"): # make sure workdir can be combined with other paths using '+'
            assert not self.workDirIsTempDir
            self.workDir = workDir + "/"
    
    def setTempWorkDir(self):
        self.workDir = tempfile.mkdtemp()
        self.workDirIsTempDir = True
    
    def deleteTempWorkDir(self):
        if self.workDirIsTempDir:
            print >> sys.stderr, "Removing temporary work directory", self.workDir
            shutil.rmtree(self.workDir)
            self.workDirIsTempDir = False
            self.setWorkDir("")
    
#    def getSharedStep(self, childDetector, step, direction=1):
#        childDetector.select.getSharedStep(step, self.select.steps, direction)
    
    def setConnection(self, connection):
        self.connection = connection
        self.connection.debug = self.debug
        return connection
    
#    def setCSCConnection(self, options, cscworkdir):
#        if "local" not in options:
#            clear = False
#            if "clear" in options: 
#                clear = True
#            if "louhi" in options:
#                self.cscConnection = CSCConnection(cscworkdir, "jakrbj@louhi.csc.fi", clear)
#            else:
#                self.cscConnection = CSCConnection(cscworkdir, "jakrbj@murska.csc.fi", clear)
#        else:
#            self.cscConnection = None
    
    def getModel(self):
        return self.openModel(model)
    
    def getClassifier(self, parameters):
        #parameters = Parameters.get(parameters, ["TEES.threshold", "TEES.classifier", "c"], valueListKey="c")
        parameters = Parameters.get(parameters, ["TEES.threshold", "TEES.classifier"], allowNew=True, valueListKey="c")
        if parameters["TEES.classifier"] == None:
            return self.Classifier
        else:
            exec "from Classifiers." + parameters["TEES.classifier"] + " import " + parameters["TEES.classifier"] + " as " + parameters["TEES.classifier"]
            return eval(parameters["TEES.classifier"])
    
    def saveStr(self, name, value, model=None, modelMustExist=True):
        if type(model) in types.StringTypes:
            modelObj = self.openModel(model, "a")
        else:
            if modelMustExist:
                assert model != None
            modelObj = model
        if modelObj != None:
            modelObj.addStr(name, value)
            modelObj.save()
    
    def saveStrings(self, dict, model=None, modelMustExist=True):
        if type(model) in types.StringTypes:
            modelObj = self.openModel(model, "a")
        else:
            if modelMustExist:
                assert model != None
            modelObj = model
        if modelObj != None:
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
    
    def addClassifierModel(self, model, classifierModelPath, classifierParameters, threshold=None):
        classifierModel = model.get(self.tag+"classifier-model", True)
        if classifierModelPath != None and os.path.exists(classifierModelPath):
            shutil.copy2(classifierModelPath, classifierModel)
        model.addStr(self.tag+"classifier-parameter", Parameters.toString(Parameters.get(classifierParameters)))
        if threshold != None:
            model.addStr(self.tag+"threshold", str(threshold))
        return classifierModel
    
    def openModel(self, model, mode="r"):
        if type(model) in types.StringTypes:
            model = Model(model, mode)
            self.modelsToClose.append(model)
        return model
    
    def getBioNLPSharedTaskParams(self, parameters=None, model=None):
        if parameters == None:
            if model != None:
                model = self.openModel(model, "r")
                parameters = model.getStr("BioNLPSTParams", defaultIfNotExist=None)
            else:
                parameters = {}
        return Parameters.get(parameters, ["convert", "evaluate", "scores", "a2Tag"])
    
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
        if saveIdsToModel:
            model.save()
    
    def enterState(self, state, steps=None, fromStep=None, toStep=None, omitSteps=None):      
        if self.state == None:
            assert self.select == None
            self.state = state
            if self.select == None or (self.select.currentStep == None and fromStep == steps[0]):
                print >> sys.stderr, "*", self.__class__.__name__ + ":" + state + "(ENTER)", "*"
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
            model.addStr(param[1], Parameters.toString(getattr(self, param[0])))
        model.save()
        return model
    
    def exitState(self):
        if self.select == None or self.select.currentStep == self.select.steps[-1]:
            if self.select != None:
                self.select.printStepTime() # print last step time
            print >> sys.stderr, "*", self.__class__.__name__ + ":" + self.state + "(EXIT)", str(datetime.timedelta(seconds=time.time()-self.enterStateTime)), "*"
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
