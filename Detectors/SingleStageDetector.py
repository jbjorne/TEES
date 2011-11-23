import sys, os
import shutil
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Core.Model import Model
import STFormat.ConvertXML
import STFormat.Compare
from Murska.CSCConnection import CSCConnection
from Core.OptimizeParameters import optimize

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
        
        self.state = None # None, TRAIN, OPTIMIZE, CLASSIFY
        self.currentStep = None # TRAIN/OPTIMIZE: EXAMPLES, TRAIN, MODELS, CLASSIFY: EXAMPLES, CLASSIFY
        self.STATE_TRAIN = "STATE_TRAIN"
        self.STATE_OPTIMIZE = "STATE_OPTIMIZE"
        self.STATE_TEST = "STATE_TEST"
        
        #self.TARGET_TRAIN = "TARGET_TRAIN"
        #self.TARGET_OPT = "TARGET_OPT"
        #self.TARGET_TEST = "TARGET_TEST"
        #self.input = {self.TARGET_TRAIN:None, self.TARGET_OPT:None, self.TARGET_TEST:None}
        #self.gold = {self.TARGET_TRAIN:None, self.TARGET_OPT:None, self.TARGET_TEST:None}
        #self.examples = {self.TARGET_TRAIN:None, self.TARGET_OPT:None, self.TARGET_TEST:None}
        
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
        
    def train(self, trainData, optData=None, fromStep=None, toStep=None):
        assert self.state == None
        self.state = self.STATE_OPTIMIZE
        self.fromStep = fromStep
        self.toStep = toStep
        self.steps = ["INIT", "EXAMPLES", "TRAIN", "MODELS"]
        self.currentStep = None
        #self.input[self.TARGET_OPT] = optData
        #self.input[self.TARGET_TRAIN] = trainData
        #self.input[self.TARGET_TEST] = None
        if self.check("INIT"):
            print >> sys.stderr, "Clearing model if it exists"
            self._model = Model(self.modelPath, "w")
        else:
            print >> sys.stderr, "Using previous model if it exists"
            self._model = Model(self.modelPath, "a")
        # Build examples
        if self.check("EXAMPLES"):
            print >> sys.stderr, "Building examples"
            if optData != None:
                self.buildExamples(optData, self.tag+"opt-examples.gz")
                self._model.save()
            self.buildExamples(trainData, self.tag+"train-examples.gz")
            self._model.save()
        # Upload models
        if self.check("TRAIN"):
            print >> sys.stderr, "Training models"
            optimize(self.classifier, self.evaluator, self.tag+"train-examples.gz", self.tag+"opt-examples.gz",\
                     self._model.get(self.tag+"ids.classes"), self.classifierParameters, self.tag+"models", None, self.cscConnection, False, "SUBMIT")
        # Download models
        if self.check("MODELS"):
            print >> sys.stderr, "Selecting optimal model"
            bestResult = optimize(self.classifier, self.evaluator, self.tag+"train-examples", self.tag+"opt-examples",\
                                  self._model.get(self.tag+"ids.classes"), self.classifierParameters, self.tag+"models", None, self.cscConnection, False, "RESULTS")
            classifierModel = self._model.get(self.tag+"classifier-model", True)
            shutil.copy2(bestResult[1], classifierModel)
            self._model.save()
            
        self._model.close()
        self._model = None
        self.state = None
        self.fromStep = None
        self.toStep = None
        self.steps = None
        self.currentStep = None
        
    def check(self, step):
        assert step in self.steps
        # Remember step
        if self.currentStep == None:
            self.currentStep = step
        elif self.steps.index(step) < self.steps.index(self.currentStep):
            print >> sys.stderr, "Step", step, "already done, skipping."
            return False
        else:
            self.currentStep = step
        
        # User control
        if self.fromStep == None:
            return True
        assert self.fromStep in self.steps
        if self.steps.index(self.fromStep) <= self.steps.index(step):
            if self.toStep == None:
                return True
            assert self.toStep in self.steps
            if self.steps.index(self.toStep) >= self.steps.index(step):
                return True
            else:
                print >> sys.stderr, "Step", step, "out of range"
                return False
        else:
            print >> sys.stderr, "Skipping step", step, "by user request"
            return False
        
    def classify(self, data, output):
        assert self.state == None
        self._model = Model(self.modelPath, "r")
        examples = self.buildExamples(data, output + ".examples.gz")
        self.classifier.test(examples, self.model.get(self.tag+"classifier-model"), output + ".classifications")
        xml = BioTextExampleWriter.write(output+".examples", output+".classifications", data, None, self._model.get(self.tag+"ids.classes"), self.parse, self.tokenization)
        xml = ix.splitMergedElements(xml, None)
        xml = ix.recalculateIds(xml, output + ".xml", True)
        EvaluateInteractionXML.run(Ev, xml, data, self.parse, self.tokenization)
        STFormat.ConvertXML.toSTFormat(xml, output + ".tar.gz", outputTag="a2")
        if self.stEvaluator != None:
            self.stEvaluator.evaluate(output + ".tar.gz")
        #if options.task == "BI":
        #    evaluateBX("devel-geniaformat", "BI")
        #else:
        #    evaluateREN("devel-geniaformat")
        self._model.close()
        self._model = None
        self.state = None
    
    def buildExamples(self, input, output, gold=None, append=False):
        self.exampleBuilder.run(input, output, self.parse, self.tokenization, self.exampleStyle, self._model.get(self.tag+"ids.classes"), self._model.get(self.tag+"ids.features"), gold, append)
        return output