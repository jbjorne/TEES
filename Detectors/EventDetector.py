from Detector import Detector
from TriggerDetector import TriggerDetector
from EdgeDetector import EdgeDetector

class EventDetector(Detector):
    def __init__(self):
        self.triggerDetector = TriggerDetector()
        self.edgeDetector = EdgeDetector()
    
    def setCSCConnection(self, options, cscworkdir):
        self.triggerDetector.setCSCConnection(options, os.path.join(cscworkdir, "trigger"))
        self.edgeDetector.setCSCConnection(options, os.path.join(cscworkdir, "edge"))
    
    def train(self, trainData=None, optData=None, 
              model=None, combinedModel=None,
              triggerExampleStyle=None, edgeExampleStyle=None,
              triggerClassifierParameters=None, edgeClassifierParameters=None,
              recallAdjustParameters=None, fullGrid=False,
              parse=None, tokenization=None,
              fromStep=None, toStep=None):
        self._enterState(self.STATE_TRAIN, ["EXAMPLES", "OPTIMIZE", "MODELS", "GRID", "TRAIN-COMBINED", "MODEL-COMBINED"], fromStep, toStep)
        self._initVariables(trainData, optData, model, combinedModel, triggerExampleStyle, edgeExampleStyle,
              triggerClassifierParameters, edgeClassifierParameters, recallAdjustParameters, fullGrid, parse, tokenization)
        self.checkStep("EXAMPLES") # mark step
        self.triggerDetector.train(self.trainData, self.optData, self.model, self.combinedModel, 
                                   self.triggerExampleStyle, self.triggerClassifierParameters,
                                   self.parse, self.tokenization, fromStep=fromStep, toStep="EXAMPLES")
        self.edgeDetector.train(self.trainData, self.optData, self.model, self.combinedModel, 
                                self.edgeExampleStyle, self.edgeClassifierParameters,
                                self.parse, self.tokenization, fromStep=fromStep, toStep="EXAMPLES")
        self.checkStep("OPTIMIZE") # mark step
        self.triggerDetector.train(fromStep=fromStep, toStep="OPTIMIZE")
        self.edgeDetector.train(fromStep=fromStep, toStep="OPTIMIZE")
        self.checkStep("MODELS") # mark step
        self.triggerDetector.train(fromStep=fromStep, toStep="MODELS")
        self.edgeDetector.train(fromStep=fromStep, toStep="MODELS")
        if self.checkStep("GRID"):
            self.doGrid(self.edgeDetector, self.triggerDetector, self.recallAdjustParameters)
        self.select.check("TRAIN-COMBINED", False) # mark step
        self.triggerDetector.train(fromStep=fromStep, toStep="TRAIN-COMBINED")
        self.edgeDetector.train(fromStep=fromStep, toStep="TRAIN-COMBINED")
        
        self._exitState()
    
    def doGrid(self):
        BINARY_RECALL_MODE = False # TODO: make a parameter
        print >> sys.stderr, "--------- Booster parameter search ---------"
        # Build trigger examples
        self.triggerDetector.buildExamples([self.optData], ["test-trigger-examples.gz"])
        if not options.fullGrid:
            self.classifier.test("test-trigger-examples.gz", self.model.get("trigger-classifier-model.gz"), "test-trigger-classifications")
            evaluator = self.evaluator.evaluate("test-trigger-examples.gz", "test-trigger-classifications", self.model.get("trigger-ids.classes"))
            BioTextExampleWriter.write("test-trigger-examples.gz", "test-trigger-classifications", self.optData, "trigger-pred-best.xml", self.model.get("trigger-ids.classes"), self.parse, self.tokenization)
        
        count = 0
        bestResults = None
        if self.fullGrid:
            # Parameters to optimize
            ALL_PARAMS={
                "trigger":[int(i) for i in splitParameters(self.triggerClassifierParameters)["c"]], 
                "booster":[float(i) for i in recallAdjustParameters], 
                "edge":[int(i) for i in splitParameters(self.edgeClassifierParameters)["c"]] }
        else:
            ALL_PARAMS={"trigger":["BEST"],
                        "booster":[float(i) for i in recallAdjustParameters],
                        "edge":["BEST"]}
        paramCombinations = getParameterCombinations(ALL_PARAMS)
        #for boost in boosterParams:
        prevTriggerParam = None
        EDGE_MODEL_STEM = os.path.join(edgeDetector.workDir, "edge-models/model-c_")
        TRIGGER_MODEL_STEM = os.path.join(triggerDetector.workDir, "trigger-models/model-c_")
        for params in paramCombinations:
            print >> sys.stderr, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            print >> sys.stderr, "Processing params", str(count+1) + "/" + str(len(paramCombinations)), params
            print >> sys.stderr, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            
            # Triggers
            if params["trigger"] != prevTriggerParam:
                print >> sys.stderr, "Reclassifying trigger examples for parameter", params["trigger"]
                self.triggerDetector.classifier.test("test-trigger-examples.gz", TRIGGER_MODEL_STEM+str(params["trigger"])+".gz", "test-trigger-classifications")
                evaluator = self.evaluator.evaluate("test-trigger-examples.gz", "test-trigger-classifications", self.model.get("trigger-ids.classes"))
                BioTextExampleWriter.write("test-trigger-examples.gz", "test-trigger-classifications", self.optData, "trigger-pred-best.xml", self.model.get("trigger-ids.classes"), options.parse, options.tokenization)
            prevTriggerParam = params["trigger"]
            
            # Boost
            xml = RecallAdjust.run("trigger-pred-best.xml", params["booster"], None, binary=BINARY_RECALL_MODE)
            xml = ix.splitMergedElements(xml, None)
            xml = ix.recalculateIds(xml, None, True)
            
            # Build edge examples
            self.triggerDetector.buildExamples([xml], ["test-edge-examples.gz"])
            if options.classifier == "ACCls":
                self.triggerDetector.buildExamples([xml], ["test-edge-examples.gz"], [self.optData])
            else:
                self.triggerDetector.buildExamples([xml], ["test-edge-examples.gz"])
            # Classify with pre-defined model
            if params["edge"] == "BEST":
                if bestEdgeModel != None:
                    print >> sys.stderr, "best-edge-model=", os.path.realpath("best-edge-model.gz")
                self.edgeDetector.classifier.test("test-edge-examples.gz", bestEdgeModel, "test-edge-classifications")
            else:
                self.edgeDetector.classifier.test("test-edge-examples.gz", EDGE_MODEL_STEM+str(params["edge"])+".gz", "test-edge-classifications")
            # Write to interaction xml
            evaluator = self.evaluator.evaluate("test-edge-examples.gz", "test-edge-classifications", self.model.get("edge-ids.classes"))
            if evaluator.getData().getTP() + evaluator.getData().getFP() > 0:
                #xml = ExampleUtils.writeToInteractionXML("test-edge-examples", "test-edge-classifications", xml, None, EDGE_IDS+".class_names", PARSE, TOK)
                xml = BioTextExampleWriter.write("test-edge-examples", "test-edge-classifications", xml, None, self.model.get("edge-ids.classes"), options.parse, options.tokenization)
                xml = ix.splitMergedElements(xml, None)
                #xml = ix.recalculateIds(xml, "flat-" + str(boost) + ".xml.gz", True)
                xml = ix.recalculateIds(xml, "flat-devel.xml.gz", True)
                
                # EvaluateInteractionXML differs from the previous evaluations in that it can
                # be used to compare two separate GifXML-files. One of these is the gold file,
                # against which the other is evaluated by heuristically matching triggers and
                # edges. Note that this evaluation will differ somewhat from the previous ones,
                # which evaluate on the level of examples.
                EIXMLResult = EvaluateInteractionXML.run(evaluator, xml, self.optData, options.parse, options.tokenization)
                # Convert to ST-format
                if os.path.exists("flat-devel-geniaformat"):
                    shutil.rmtree("flat-devel-geniaformat")
                STFormat.ConvertXML.toSTFormat(xml, "flat-devel-geniaformat", getA2FileTag(options.task, subTask))
                
#                if options.task in ["OLD", "GE", "EPI", "ID"]:
#                    assert options.unmerging
#                    if options.unmerging:
#                        if os.path.exists("unmerged-devel-geniaformat"):
#                            shutil.rmtree("unmerged-devel-geniaformat")
#                        print >> sys.stderr, "--------- ML Unmerging ---------"
#                        GOLD_TEST_FILE = TEST_FILE.replace("-nodup", "")
#                        UnmergingExampleBuilder.run("flat-devel.xml.gz", "unmerging-grid-examples", PARSE, TOK, UNMERGING_FEATURE_PARAMS, UNMERGING_IDS, GOLD_TEST_FILE)
#                        CLASSIFIER.test("unmerging-grid-examples", bestUnmergingModel, "unmerging-grid-classifications")
#                        unmergedXML = BioTextExampleWriter.write("unmerging-grid-examples", "unmerging-grid-classifications", "flat-devel.xml.gz", "unmerged-devel.xml.gz", UNMERGING_IDS+".class_names", PARSE, TOK)
#                        STFormat.ConvertXML.toSTFormat(unmergedXML, "unmerged-devel-geniaformat", getA2FileTag(options.task, subTask))
#                        if options.task == "OLD":
#                            results = evaluateSharedTask("unmerged-devel-geniaformat", subTask)
#                        elif options.task == "GE":
#                            results = evaluateBioNLP11Genia("unmerged-devel-geniaformat", subTask)
#                        elif options.task in ["EPI", "ID"]:
#                            results = evaluateEPIorID("unmerged-devel-geniaformat", options.task)
#                        else:
#                            assert False
#                        shutil.rmtree("unmerged-devel-geniaformat")
#                        if options.task in ["OLD", "GE"]:
#                            if bestResults == None or bestResults[1]["approximate"]["ALL-TOTAL"]["fscore"] < results["approximate"]["ALL-TOTAL"]["fscore"]:
#                                bestResults = (params, results)
#                        else:
#                            if bestResults == None or bestResults[1]["TOTAL"]["fscore"] < results["TOTAL"]["fscore"]:
#                                bestResults = (params, results)
#                    if options.task in ["OLD"]: # rule-based unmerging
#                        print >> sys.stderr, "--------- Rule based unmerging ---------"
#                        # Post-processing
#                        unmergedXML = unflatten(xml, PARSE, TOK)
#                        # Output will be stored to the geniaformat-subdirectory, where will also be a
#                        # tar.gz-file which can be sent to the Shared Task evaluation server.
#                        #gifxmlToGenia(unmergedXML, "rulebased-unmerging-geniaformat", subTask)
#                        if os.path.exists("rulebased-unmerging-geniaformat"):
#                            shutil.rmtree("rulebased-unmerging-geniaformat")
#                        STFormat.ConvertXML.toSTFormat(unmergedXML, "rulebased-unmerging-geniaformat", getA2FileTag(options.task, subTask))
#                        # Evaluation of the Shared Task format
#                        results = evaluateSharedTask("rulebased-unmerging-geniaformat", subTask)
#                        #if bestResults == None or bestResults[1]["approximate"]["ALL-TOTAL"]["fscore"] < results["approximate"]["ALL-TOTAL"]["fscore"]:
#                        #    bestResults = (boost, results)
#                elif options.task == "BB":
#                    results = evaluateBX("flat-devel-geniaformat", "BB")
#                    if bestResults == None or results["fscore"]  > bestResults[1]["fscore"]:
#                        bestResults = (params, results)
#                else:
                if bestResults == None or EIXMLResult.getData().fscore > bestResults[1].getData().fscore:
                    bestResults = (params, EIXMLResult)
                shutil.rmtree("flat-devel-geniaformat")
            else:
                print >> sys.stderr, "No predicted edges"
            count += 1
        print >> sys.stderr, "Booster search complete"
        print >> sys.stderr, "Tested", count, "out of", count, "combinations"
        print >> sys.stderr, "Best parameters:", bestResults[0]
        self.saveStr("recallAdjustParameter", str(bestResults[0]["booster"]))
        if options.fullGrid: # define best models
            bestTriggerModel = updateModel((None, TRIGGER_MODEL_STEM+str(bestResults[0]["trigger"])+".gz", str(bestResults[0]["trigger"])), "best-trigger-model.gz")
            bestEdgeModel = updateModel((None, EDGE_MODEL_STEM+str(bestResults[0]["edge"])+".gz", str(bestResults[0]["edge"])), "best-edge-model.gz")
        if options.task in ["OLD", "GE"]:
            print >> sys.stderr, "Best result:", bestResults[1]
        # Final models with full grid
        if options.classifier != "ACCls" and (not options.noTestSet) and options.fullGrid:
            print >> sys.stderr, "------------ Submitting final models ------------"
            print >> sys.stderr, "Everything models for parse", PARSE_TAG
            c = None
            if "local" not in options.csc: c = CSCConnection(CSC_WORKDIR+"/everything-trigger-models", CSC_ACCOUNT, True, password=options.password)
            optimize(CLASSIFIER, Ev, TRIGGER_EVERYTHING_EXAMPLE_FILE, TRIGGER_TEST_EXAMPLE_FILE,\
                TRIGGER_IDS+".class_names", "c:"+getParameter(bestTriggerModel).split("_")[-1], "everything-trigger-models", None, c, False, steps="SUBMIT")
            if "local" not in options.csc: c = CSCConnection(CSC_WORKDIR+"/everything-edge-models", CSC_ACCOUNT, True, password=options.password)
            optimize(CLASSIFIER, Ev, EDGE_EVERYTHING_EXAMPLE_FILE, EDGE_TEST_EXAMPLE_FILE,\
                EDGE_IDS+".class_names", "c:"+getParameter(bestEdgeModel).split("_")[-1], "everything-edge-models", None, c, False, steps="SUBMIT")
            print >> sys.stderr, "Everything models submitted"
