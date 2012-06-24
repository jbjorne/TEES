import sys, os
import shutil
import types
from Detector import Detector
from TriggerDetector import TriggerDetector
from EdgeDetector import EdgeDetector
from UnmergingDetector import UnmergingDetector
from ModifierDetector import ModifierDetector
#from Core.RecallAdjust import RecallAdjust
import Utils.Parameters as Parameters
import InteractionXML
import Evaluators.EvaluateInteractionXML as EvaluateInteractionXML
import STFormat.ConvertXML
import STFormat.Compare
import Evaluators.BioNLP11GeniaTools

class EventDetector(Detector):
    def __init__(self):
        Detector.__init__(self)
        self.triggerDetector = TriggerDetector()
        self.edgeDetector = EdgeDetector()
        self.unmergingDetector = UnmergingDetector()
        self.doUnmergingSelfTraining = True #False
        self.modifierDetector = ModifierDetector()
        self.stEvaluator = Evaluators.BioNLP11GeniaTools
        self.stWriteScores = False
        self.STATE_COMPONENT_TRAIN = "COMPONENT_TRAIN"
        self.tag = "event-"
    
    def setConnection(self, connection):
        self.triggerDetector.setConnection(connection)
        self.edgeDetector.setConnection(connection)
        self.unmergingDetector.setConnection(connection)
        self.modifierDetector.setConnection(connection)
        return connection
    
    def setWorkDir(self, workDir):
        Detector.setWorkDir(self, workDir) # for EventDetector
        # setup components
        for detector in [self.triggerDetector, self.edgeDetector, self.unmergingDetector, self.modifierDetector]:
            if detector != None:
                detector.setWorkDir(workDir)
    
    def train(self, trainData=None, optData=None, 
              model=None, combinedModel=None,
              triggerExampleStyle=None, edgeExampleStyle=None, unmergingExampleStyle=None, modifierExampleStyle=None,
              triggerClassifierParameters=None, edgeClassifierParameters=None, 
              unmergingClassifierParameters=None, modifierClassifierParameters=None, 
              recallAdjustParameters=None, unmerging=False, trainModifiers=False, 
              fullGrid=False, task=None,
              parse=None, tokenization=None,
              fromStep=None, toStep=None,
              workDir=None):
        # Initialize the training process ##############################
        self.initVariables(trainData=trainData, optData=optData, model=model, combinedModel=combinedModel,
                           triggerExampleStyle=triggerExampleStyle, edgeExampleStyle=edgeExampleStyle, 
                           unmergingExampleStyle=unmergingExampleStyle, modifierExampleStyle=modifierExampleStyle,
                           triggerClassifierParameters=triggerClassifierParameters, 
                           edgeClassifierParameters=edgeClassifierParameters,
                           unmergingClassifierParameters=unmergingClassifierParameters,
                           modifierClassifierParameters=modifierClassifierParameters, 
                           recallAdjustParameters=recallAdjustParameters, unmerging=unmerging, trainModifiers=trainModifiers, 
                           fullGrid=fullGrid, task=task, parse=parse, tokenization=tokenization)
        self.setWorkDir(workDir)
        # Begin the training process ####################################
        self.enterState(self.STATE_TRAIN, ["EXAMPLES", "BEGIN-MODEL", "END-MODEL", "BEGIN-COMBINED-MODEL", 
                                           "SELF-TRAIN-EXAMPLES-FOR-UNMERGING", "UNMERGING-EXAMPLES", "BEGIN-UNMERGING-MODEL", "END-UNMERGING-MODEL", 
                                           "GRID", "BEGIN-COMBINED-MODEL-FULLGRID", "END-COMBINED-MODEL"], fromStep, toStep)
        self.triggerDetector.enterState(self.STATE_COMPONENT_TRAIN)
        self.edgeDetector.enterState(self.STATE_COMPONENT_TRAIN)
        self.unmergingDetector.enterState(self.STATE_COMPONENT_TRAIN)
        self.modifierDetector.enterState(self.STATE_COMPONENT_TRAIN)
        if self.checkStep("EXAMPLES"):
            self.model = self.initModel(self.model, 
                                         [("triggerExampleStyle", self.triggerDetector.tag+"example-style"), 
                                          ("triggerClassifierParameters", self.triggerDetector.tag+"classifier-parameters-train"),
                                          ("edgeExampleStyle", self.edgeDetector.tag+"example-style"), 
                                          ("edgeClassifierParameters", self.edgeDetector.tag+"classifier-parameters-train"),
                                          ("unmergingExampleStyle", self.unmergingDetector.tag+"example-style"), 
                                          ("unmergingClassifierParameters", self.unmergingDetector.tag+"classifier-parameters-train"),
                                          ("modifierExampleStyle", self.modifierDetector.tag+"example-style"), 
                                          ("modifierClassifierParameters", self.modifierDetector.tag+"classifier-parameters-train")])
            self.combinedModel = self.initModel(self.combinedModel)
            tags = [self.triggerDetector.tag, self.edgeDetector.tag, self.unmergingDetector.tag]
            if trainModifiers: tags += [self.modifierDetector.tag]
            stringDict = {}
            for tag in tags:
                stringDict[tag+"parse"] = parse
                stringDict[tag+"task"] = task
            self.saveStrings(stringDict, self.model)
            self.saveStrings(stringDict, self.combinedModel, False)
            self.triggerDetector.buildExamples(self.model, [optData.replace("-nodup", ""), trainData.replace("-nodup", "")], [self.workDir+self.triggerDetector.tag+"opt-examples.gz", self.workDir+self.triggerDetector.tag+"train-examples.gz"], saveIdsToModel=True)
            self.edgeDetector.buildExamples(self.model, [optData.replace("-nodup", ""), trainData.replace("-nodup", "")], [self.workDir+self.edgeDetector.tag+"opt-examples.gz", self.workDir+self.edgeDetector.tag+"train-examples.gz"], saveIdsToModel=True)
            if trainModifiers:
                self.modifierDetector.buildExamples(self.model, [optData, trainData], [self.workDir+self.modifierDetector.tag+"opt-examples.gz", self.workDir+self.modifierDetector.tag+"train-examples.gz"], saveIdsToModel=True)             
        # (Re-)open models in case we start after the "EXAMPLES" step
        self.model = self.openModel(model, "a")
        self.combinedModel = self.openModel(combinedModel, "a")
        if self.checkStep("BEGIN-MODEL"):
            self.triggerDetector.beginModel(None, self.model, [self.workDir+self.triggerDetector.tag+"train-examples.gz"], self.workDir+self.triggerDetector.tag+"opt-examples.gz")
            self.edgeDetector.beginModel(None, self.model, [self.workDir+self.edgeDetector.tag+"train-examples.gz"], self.workDir+self.edgeDetector.tag+"opt-examples.gz")
            if trainModifiers:
                self.modifierDetector.beginModel(None, self.model, [self.workDir+self.modifierDetector.tag+"train-examples.gz"], self.workDir+self.modifierDetector.tag+"opt-examples.gz")
        if self.checkStep("END-MODEL"):
            self.triggerDetector.endModel(None, self.model, self.workDir+self.triggerDetector.tag+"opt-examples.gz")
            self.edgeDetector.endModel(None, self.model, self.workDir+self.edgeDetector.tag+"opt-examples.gz")
            if trainModifiers:
                self.modifierDetector.endModel(None, self.model, self.workDir+self.modifierDetector.tag+"opt-examples.gz")
        if self.checkStep("BEGIN-COMBINED-MODEL"):
            if not self.fullGrid:
                print >> sys.stderr, "Training combined model before grid search"
                self.triggerDetector.beginModel(None, self.combinedModel, [self.workDir+self.triggerDetector.tag+"train-examples.gz", self.workDir+self.triggerDetector.tag+"opt-examples.gz"], self.workDir+self.triggerDetector.tag+"opt-examples.gz", self.model)
                self.edgeDetector.beginModel(None, self.combinedModel, [self.workDir+self.edgeDetector.tag+"train-examples.gz", self.workDir+self.edgeDetector.tag+"opt-examples.gz"], self.workDir+self.edgeDetector.tag+"opt-examples.gz", self.model)
            else:
                print >> sys.stderr, "Combined model will be trained after grid search"
            if trainModifiers:
                print >> sys.stderr, "Training combined model for modifier detection"
                self.modifierDetector.beginModel(None, self.combinedModel, [self.workDir+self.modifierDetector.tag+"train-examples.gz", self.workDir+self.modifierDetector.tag+"opt-examples.gz"], self.workDir+self.modifierDetector.tag+"opt-examples.gz", self.model)
        self.trainUnmergingDetector()
        if self.checkStep("GRID"):
            self.doGrid()
        if self.checkStep("BEGIN-COMBINED-MODEL-FULLGRID"):
            if self.fullGrid:
                print >> sys.stderr, "Training combined model after grid search"
                self.triggerDetector.beginModel(None, self.combinedModel, [self.workDir+self.triggerDetector.tag+"train-examples.gz", self.workDir+self.triggerDetector.tag+"opt-examples.gz"], self.workDir+self.triggerDetector.tag+"opt-examples.gz", self.model)
                self.edgeDetector.beginModel(None, self.combinedModel, [self.workDir+self.edgeDetector.tag+"train-examples.gz", self.workDir+self.edgeDetector.tag+"opt-examples.gz"], self.workDir+self.edgeDetector.tag+"opt-examples.gz", self.model)
                if trainModifiers:
                    print >> sys.stderr, "Training combined model for modifier detection"
                    self.modifierDetector.beginModel(None, self.combinedModel, [self.workDir+self.modifierDetector.tag+"train-examples.gz", self.workDir+self.modifierDetector.tag+"opt-examples.gz"], self.workDir+self.modifierDetector.tag+"opt-examples.gz", self.model)
            else:
                print >> sys.stderr, "Combined model has been trained before grid search"
        if self.checkStep("END-COMBINED-MODEL"):
            self.triggerDetector.endModel(None, self.combinedModel, self.workDir+self.triggerDetector.tag+"opt-examples.gz")
            self.edgeDetector.endModel(None, self.combinedModel, self.workDir+self.edgeDetector.tag+"opt-examples.gz")
            if trainModifiers:
                self.modifierDetector.endModel(None, self.combinedModel, self.workDir+self.modifierDetector.tag+"opt-examples.gz")
        # End the training process ####################################
        if workDir != None:
            self.setWorkDir("")
        self.exitState()
        self.triggerDetector.exitState()
        self.edgeDetector.exitState()
        self.unmergingDetector.exitState()
        self.modifierDetector.exitState()
    
    def doGrid(self):
        print >> sys.stderr, "--------- Booster parameter search ---------"
        # Build trigger examples
        self.triggerDetector.buildExamples(self.model, [self.optData], [self.workDir+"grid-trigger-examples.gz"])

        if self.fullGrid:
            # Parameters to optimize
            ALL_PARAMS={
                "trigger":[int(i) for i in Parameters.get(self.triggerClassifierParameters, valueListKey="c")["c"]], 
                "booster":[float(i) for i in self.recallAdjustParameters.split(",")], 
                "edge":[int(i) for i in Parameters.get(self.edgeClassifierParameters, valueListKey="c")["c"]] }
        else:
            ALL_PARAMS={"trigger":Parameters.get(self.model.getStr(self.triggerDetector.tag+"classifier-parameter"), valueListKey="c")["c"],
                        "booster":[float(i) for i in self.recallAdjustParameters.split(",")],
                        "edge":Parameters.get(self.model.getStr(self.edgeDetector.tag+"classifier-parameter"), valueListKey="c")["c"]}
        
        paramCombinations = Parameters.getCombinations(ALL_PARAMS, ["trigger", "booster", "edge"])
        prevParams = None
        EDGE_MODEL_STEM = os.path.join(self.edgeDetector.workDir, os.path.normpath(self.model.path)+"-edge-models/model-c_")
        TRIGGER_MODEL_STEM = os.path.join(self.triggerDetector.workDir, os.path.normpath(self.model.path)+"-trigger-models/model-c_")
        bestResults = None
        for i in range(len(paramCombinations)):
            params = paramCombinations[i]
            print >> sys.stderr, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            print >> sys.stderr, "Processing params", str(i+1) + "/" + str(len(paramCombinations)), params
            print >> sys.stderr, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            # Triggers and Boost
            if prevParams == None or prevParams["trigger"] != params["trigger"] or prevParams["booster"] != params["booster"]:
                print >> sys.stderr, "Classifying trigger examples for parameters", "trigger:" + str(params["trigger"]), "booster:" + str(params["booster"])
                xml = self.triggerDetector.classifyToXML(self.optData, self.model, self.workDir+"grid-trigger-examples.gz", self.workDir+"grid-", classifierModel=TRIGGER_MODEL_STEM+str(params["trigger"]), recallAdjust=params["booster"])
            prevParams = params
            # Build edge examples
            self.edgeDetector.buildExamples(self.model, [xml], [self.workDir+"grid-edge-examples.gz"], [self.optData])
            # Classify with pre-defined model
            edgeClassifierModel=EDGE_MODEL_STEM+str(params["edge"])
            xml = self.edgeDetector.classifyToXML(xml, self.model, self.workDir+"grid-edge-examples.gz", self.workDir+"grid-", classifierModel=edgeClassifierModel)
            bestResults = self.evaluateGrid(xml, params, bestResults)
        print >> sys.stderr, "Booster search complete"
        print >> sys.stderr, "Tested", len(paramCombinations), "combinations"
        print >> sys.stderr, "Best parameters:", bestResults[0]
        print >> sys.stderr, "Best result:", bestResults[2] # f-score
        # Save grid model
        self.saveStr("recallAdjustParameter", str(bestResults[0]["booster"]), self.model)
        self.saveStr("recallAdjustParameter", str(bestResults[0]["booster"]), self.combinedModel, False)
        if self.fullGrid: # define best models
            self.triggerDetector.addClassifierModel(self.model, TRIGGER_MODEL_STEM+str(bestResults[0]["trigger"]), bestResults[0]["trigger"])
            self.edgeDetector.addClassifierModel(self.model, EDGE_MODEL_STEM+str(bestResults[0]["edge"]), bestResults[0]["edge"])
        # Remove work files
        for stepTag in [self.workDir+"grid-trigger", self.workDir+"grid-edge", self.workDir+"grid-unmerging"]:
            for fileStem in ["-classifications", "-classifications.log", "examples.gz", "pred.xml.gz"]:
                if os.path.exists(stepTag+fileStem):
                    os.remove(stepTag+fileStem)
    
    def evaluateGrid(self, xml, params, bestResults):
        if xml != None:                
            # TODO: Where should the EvaluateInteractionXML evaluator come from?
            EIXMLResult = EvaluateInteractionXML.run(self.edgeDetector.evaluator, xml, self.optData, self.parse)
            # Convert to ST-format
            STFormat.ConvertXML.toSTFormat(xml, self.workDir+"grid-flat-geniaformat", "a2") #getA2FileTag(options.task, subTask))
            stFormatDir = self.workDir+"grid-flat-geniaformat"
            
            if self.unmerging:
                xml = self.unmergingDetector.classifyToXML(xml, self.model, None, self.workDir+"grid-", goldData=self.optData.replace("-nodup", ""))
                STFormat.ConvertXML.toSTFormat(xml, self.workDir+"grid-unmerging-geniaformat", "a2")
                stFormatDir = self.workDir+"grid-unmerging-geniaformat"
            stEvaluation = self.stEvaluator.evaluate(stFormatDir, self.task)
            if stEvaluation != None:
                if bestResults == None or stEvaluation[0] > bestResults[1][0]:
                    bestResults = (params, stEvaluation, stEvaluation[0])
            else:
                if bestResults == None or EIXMLResult.getData().fscore > bestResults[1].getData().fscore:
                    bestResults = (params, EIXMLResult, EIXMLResult.getData().fscore)
            shutil.rmtree(self.workDir+"grid-flat-geniaformat")
            if os.path.exists(self.workDir+"grid-unmerging-geniaformat"):
                shutil.rmtree(self.workDir+"grid-unmerging-geniaformat")
        else:
            print >> sys.stderr, "No predicted edges"
        return bestResults

    def trainUnmergingDetector(self):
        xml = None
        if not self.unmerging:
            print >> sys.stderr, "No unmerging"
        if self.checkStep("SELF-TRAIN-EXAMPLES-FOR-UNMERGING", self.unmerging) and self.unmerging:
            # Self-classified train data for unmerging
            if self.doUnmergingSelfTraining:
                xml = self.triggerDetector.classifyToXML(self.trainData, self.model, None, self.workDir+"unmerging-extra-")#, recallAdjust=0.5)
                xml = self.edgeDetector.classifyToXML(xml, self.model, None, self.workDir+"unmerging-extra-")#, recallAdjust=0.5)
                assert xml != None
                EvaluateInteractionXML.run(self.edgeDetector.evaluator, xml, self.trainData, self.parse)
            else:
                print >> sys.stderr, "No self-training for unmerging"
        if self.checkStep("UNMERGING-EXAMPLES", self.unmerging) and self.unmerging:
            # Unmerging example generation
            GOLD_TEST_FILE = self.optData.replace("-nodup", "")
            GOLD_TRAIN_FILE = self.trainData.replace("-nodup", "")
            if self.doUnmergingSelfTraining:
                if xml == None: 
                    xml = self.workDir+"unmerging-extra-edge-pred.xml"
                self.unmergingDetector.buildExamples(self.model, [self.optData.replace("-nodup", ""), [self.trainData.replace("-nodup", ""), xml]], 
                                                     [self.workDir+"unmerging-opt-examples.gz", self.workDir+"unmerging-train-examples.gz"], 
                                                     [GOLD_TEST_FILE, [GOLD_TRAIN_FILE, GOLD_TRAIN_FILE]], 
                                                     exampleStyle=self.unmergingExampleStyle, saveIdsToModel=True)
                xml = None
            else:
                self.unmergingDetector.buildExamples(self.model, [self.optData.replace("-nodup", ""), self.trainData.replace("-nodup", "")], 
                                                     [self.workDir+"unmerging-opt-examples.gz", self.workDir+"unmerging-train-examples.gz"], 
                                                     [GOLD_TEST_FILE, GOLD_TRAIN_FILE], 
                                                     exampleStyle=self.unmergingExampleStyle, saveIdsToModel=True)
                xml = None
            #UnmergingExampleBuilder.run("/home/jari/biotext/EventExtension/TrainSelfClassify/test-predicted-edges.xml", GOLD_TRAIN_FILE, UNMERGING_TRAIN_EXAMPLE_FILE, PARSE, TOK, UNMERGING_FEATURE_PARAMS, UNMERGING_IDS, append=True)
        if self.checkStep("BEGIN-UNMERGING-MODEL", self.unmerging) and self.unmerging:
            self.unmergingDetector.beginModel(None, self.model, self.workDir+"unmerging-train-examples.gz", self.workDir+"unmerging-opt-examples.gz")
        if self.checkStep("END-UNMERGING-MODEL", self.unmerging) and self.unmerging:
            self.unmergingDetector.endModel(None, self.model, self.workDir+"unmerging-opt-examples.gz")
            print >> sys.stderr, "Adding unmerging classifier model to test-set event model"
            if self.combinedModel != None:
                self.combinedModel.addStr("unmerging-example-style", self.model.getStr("unmerging-example-style"))
                self.combinedModel.insert(self.model.get("unmerging-ids.classes"), "unmerging-ids.classes")
                self.combinedModel.insert(self.model.get("unmerging-ids.features"), "unmerging-ids.features")
                self.unmergingDetector.addClassifierModel(self.combinedModel, self.model.get("unmerging-classifier-model"), 
                                                          self.model.getStr("unmerging-classifier-parameter"))
                self.combinedModel.save()

    def classify(self, data, model, output, parse=None, task=None, fromStep=None, toStep=None, saveChangedModelPath=None):
        BINARY_RECALL_MODE = False # TODO: make a parameter
        xml = None
        self.initVariables(classifyData=data, model=model, xml=None, task=task, parse=parse)
        self.enterState(self.STATE_CLASSIFY, ["TRIGGERS", "EDGES", "UNMERGING", "MODIFIERS", "ST-CONVERT"], fromStep, toStep)
        #self.enterState(self.STATE_CLASSIFY, ["TRIGGERS", "RECALL-ADJUST", "EDGES", "UNMERGING", "MODIFIERS", "ST-CONVERT"], fromStep, toStep)
        self.model = self.openModel(self.model, "r")
        if self.checkStep("TRIGGERS"):
            xml = self.triggerDetector.classifyToXML(self.classifyData, self.model, None, output + "-", parse=self.parse, recallAdjust=float(self.getStr("recallAdjustParameter", self.model)))
        if self.checkStep("EDGES"):
            xml = self.getWorkFile(xml, output + "-recall-adjusted.xml.gz")
            xml = self.edgeDetector.classifyToXML(xml, self.model, None, output + "-", parse=self.parse)
            assert xml != None
            if self.parse == None:
                edgeParse = self.getStr(self.edgeDetector.tag+"parse", self.model)
            else:
                edgeParse = self.parse
            #EvaluateInteractionXML.run(self.edgeDetector.evaluator, xml, self.classifyData, edgeParse)
            EvaluateInteractionXML.run(self.edgeDetector.evaluator, xml, None, edgeParse)
        if self.checkStep("UNMERGING"):
            if self.model.hasMember("unmerging-classifier-model"):
                #xml = self.getWorkFile(xml, output + "-edge-pred.xml.gz")
                # To avoid running out of memory, always use file on disk
                xml = self.getWorkFile(None, output + "-edge-pred.xml.gz")
                goldData = None
                if type(self.classifyData) in types.StringTypes:
                    if os.path.exists(self.classifyData.replace("-nodup", "")):
                        goldData = self.classifyData.replace("-nodup", "")
                xml = self.unmergingDetector.classifyToXML(xml, self.model, None, output + "-", goldData=goldData, parse=self.parse)
            else:
                print >> sys.stderr, "No model for unmerging"
        if self.checkStep("MODIFIERS"):
            if self.model.hasMember("modifier-classifier-model"):
                xml = self.getWorkFile(xml, [output + "-unmerging-pred.xml.gz", output + "-edge-pred.xml.gz"])
                xml = self.modifierDetector.classifyToXML(xml, self.model, None, output + "-", parse=self.parse)
            else:
                print >> sys.stderr, "No model for modifier detection"
        if self.checkStep("ST-CONVERT"):
            xml = self.getWorkFile(xml, [output + "-modifier-pred.xml.gz", output + "-unmerging-pred.xml.gz", output + "-edge-pred.xml.gz"])
            STFormat.ConvertXML.toSTFormat(xml, output+"-events.tar.gz", outputTag="a2", writeScores=self.stWriteScores)
            if self.stEvaluator != None:
                task = self.task
                if task == None:
                    task = self.getStr(self.edgeDetector.tag+"task", self.model)
                self.stEvaluator.evaluate(output + "-events.tar.gz", task)
            if saveChangedModelPath != None:
                self.model.saveAs(saveChangedModelPath)
        self.exitState()
    
    def getWorkFile(self, fileObject, serializedPath=None):
        """
        Returns fileObject if it is not None, otherwise tries all paths in serializedPath
        and returns the first one that exists. Use this to get an intermediate file in a
        stepwise process.
        """
        if fileObject != None:
            return fileObject
        elif type(serializedPath) not in types.StringTypes: # multiple files to try
            for sPath in serializedPath:
                if os.path.exists(sPath):
                    return sPath
            assert False
        else:
            assert os.path.exists(serializedPath)
            return serializedPath
