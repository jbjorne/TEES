import sys, os
import shutil
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Core.Model import Model

def SingleStageDetector():
    def __init__(self):
        self.exampleBuilder = None
        self.classifier = None
        self.evaluator = None
        self.stEvaluator = None
        self.modelPath = None
        self.tag = "ssd-"
        self._model = None
        self.workDir = None
        
        self.exampleStyle = None
        self.classifierParameters = None
        self.parse = "split-mccc-preparsed"
        self.tokenization = None
        
        self.state = None # None, TRAIN, OPTIMIZE, CLASSIFY
        self.step = None # TRAIN/OPTIMIZE: EXAMPLES, TRAIN, MODELS, CLASSIFY: EXAMPLES, CLASSIFY
        self.STATE_TRAIN = "STATE_TRAIN"
        self.STATE_OPTIMIZE = "STATE_OPTIMIZE"
        self.STATE_TEST = "STATE_TEST"
        
        self.TARGET_TRAIN = "TARGET_TRAIN"
        self.TARGET_OPT = "TARGET_OPT"
        self.TARGET_TEST = "TARGET_TEST"
        self.input = {self.TARGET_TRAIN:None, self.TARGET_OPT:None, self.TARGET_TEST:None}
        self.gold = {self.TARGET_TRAIN:None, self.TARGET_OPT:None, self.TARGET_TEST:None}
        self.examples = {self.TARGET_TRAIN:None, self.TARGET_OPT:None, self.TARGET_TEST:None}
        
        self.cscConnection = None
    
    def importIds(filename):
        pass
    
    def setCSCConnection(options):
        if "local" not in options:
            clear = False
            if "clear" in options: 
                clear = True
            if "louhi" in options:
                self.cscConnection = CSCConnection(CSC_WORKDIR+"/edge-models", "jakrbj@louhi.csc.fi", clear)
            else:
                self.cscConnection = CSCConnection(CSC_WORKDIR+"/edge-models", "jakrbj@murska.csc.fi", clear)
        else:
            self.cscConnection = None
        
    def train(self, trainData, optData=None, fromStep=None, toStep=None):
        assert self.state == None
        self.state = self.STATE_OPTIMIZE
        self.fromStep = fromStep
        self.toStep = toStep
        self.steps = ["INIT", "EXAMPLES", "TRAIN", "MODELS"]
        self.input[self.TARGET_OPT] = optData
        self.input[self.TARGET_TRAIN] = trainData
        self.input[self.TARGET_TEST] = None
        if self.check("INIT"):
            print >> sys.stderr, "Clearing model if it exists"
            self._model = Model(self.modelPath, "w")
        else:
            print >> sys.stderr, "Using previous model if it exists"
            self._model = Model(self.modelPath, "a")
        # Build examples
        if self.check("EXAMPLES"):
            print >> sys.stderr, "Building examples"
            if self.TARGET_OPT != None:
                self.buildExamples(self.TARGET_OPT)
                self._model.save()
            self.buildExamples(self.TARGET_TRAIN)
            self._model.save()
        # Upload models
        if self.check("TRAIN"):
            print >> sys.stderr, "Training models"
            optimize(self.classifier, self.evaluator, self.examples[self.TARGET_TRAIN], self.examples[self.TARGET_OPT],\
                     self._model.get(self.tag+"ids.classes"), self.classifierParameters, self.tag+"models", None, c, False, "SUBMIT")
        # Download models
        if self.check("MODELS"):
            print >> sys.stderr, "Selecting optimal model"
            bestResult = optimize(self.classifier, self.evaluator, self.examples[self.TARGET_TRAIN], self.examples[self.TARGET_OPT],\
                                  self._model.get(self.tag+"ids.classes"), self.classifierParameters, self.tag+"models", None, c, False, "RESULTS")
            classifierModel = self._model.get(self.tag+"classifier-model", True)
            shutil.copy2(bestResult[1], classifierModel)
            self._model.save()
            
        self._model.close()
        self._model = None
        self.state = None
        
    def check(step):
        if self.fromStep == None:
            return True
        assert step in self.steps
        assert self.fromStep in self.steps
        if steps.index(self.fromStep) <= steps.index(step):
            if self.toStep == None:
                return True
            assert self.toStep in self.steps
            if steps.index(self.toStep) >= steps.index(step):
                return True
            else:
                return False
        
    def classify(self, target, output):
        assert self.state == None
        self._model = Model(self.modelPath, "r")
        if target in self.examples:
            examples = self.examples[target]
        else:
            examples = self.buildExamples(target, output + ".examples")
        self.classifier.test(examples, self.model.get(self.tag+"classifier-model"), "test-classifications")
        xml = BioTextExampleWriter.write(self.examples[target], output + ".classifications", self.input[target], None, self._model.get(self.tag+"ids.classes"), self.parse, self.tokenization)
        xml = ix.splitMergedElements(xml, None)
        xml = ix.recalculateIds(xml, output + ".xml", True)
        EvaluateInteractionXML.run(Ev, xml, self.input[target], self.parse, self.tokenization)
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
    
    def buildExamples(self, target, append=False):
        self.exampleBuilder.run(self.input[target], self.examples[target], self.parse, self.tokenization, self.exampleStyle, self._model.get(self.tag+"ids.classes"), self._model.get(self.tag+"ids.features"), self.gold[target], append)