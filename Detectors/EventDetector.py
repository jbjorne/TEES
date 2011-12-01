from Detector import Detector
from TriggerDetector import TriggerDetector
from EdgeDetector import EdgeDetector

class EventDetector(Detector):
    def __init__(self):
        Detector.__init__(self)
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
        triggerFromStep = self.getSharedStep(triggerDetector, fromStep)
        edgeFromStep = self.getSharedStep(edgeDetector, fromStep)
        self._enterState(self.STATE_TRAIN, ["EXAMPLES", "BEGIN-MODEL", "END-MODEL", "BEGIN-COMBINED-MODEL", "GRID", "BEGIN-COMBINED-MODEL-FULLGRID", "END-COMBINED-MODEL"], fromStep, toStep)
        self._initVariables(trainData, optData, model, combinedModel, triggerExampleStyle, edgeExampleStyle,
              triggerClassifierParameters, edgeClassifierParameters, recallAdjustParameters, fullGrid, parse, tokenization)
        self.checkStep("EXAMPLES") # mark step
        self.model = self._openModel(model, "a")
        if self.combinedModel != None: 
            self.combinedModel = self._openModel(combinedModel, "a")
        self.triggerDetector.train(self.trainData, self.optData, self.model, self.combinedModel, 
                                   self.triggerExampleStyle, self.triggerClassifierParameters,
                                   self.parse, self.tokenization, 
                                   fromStep=triggerFromStep, toStep="EXAMPLES")
        self.edgeDetector.train(self.trainData, self.optData, self.model, self.combinedModel, 
                                self.edgeExampleStyle, self.edgeClassifierParameters,
                                self.parse, self.tokenization, 
                                fromStep=edgeFromStep, toStep="EXAMPLES")
        self.checkStep("BEGIN-MODEL") # mark step
        self.triggerDetector.train(fromStep=triggerFromStep, toStep="BEGIN-MODEL")
        self.edgeDetector.train(fromStep=edgeFromStep, toStep="BEGIN-MODEL")
        self.checkStep("END-MODEL") # mark step
        self.triggerDetector.train(fromStep=triggerFromStep, toStep="END-MODEL")
        self.edgeDetector.train(fromStep=edgeFromStep, toStep="END-MODEL")
        self.select.check("BEGIN-COMBINED-MODEL", False) # mark step
        if not self.fullGrid:
            self.triggerDetector.train(fromStep=triggerFromStep, toStep="BEGIN-COMBINED-MODEL")
            self.edgeDetector.train(fromStep=edgeFromStep, toStep="BEGIN-COMBINED-MODEL")
        if self.checkStep("GRID"):
            self.doGrid()
        self.select.check("BEGIN-COMBINED-MODEL-FULLGRID", False) # mark step
        if self.fullGrid:
            self.triggerDetector.train(fromStep=triggerFromStep, toStep="BEGIN-COMBINED-MODEL")
            self.edgeDetector.train(fromStep=edgeFromStep, toStep="BEGIN-COMBINED-MODEL")
        self.select.check("END-COMBINED-MODEL", False) # mark step
        self.triggerDetector.train(fromStep=triggerFromStep, toStep="END-COMBINED-MODEL")
        self.edgeDetector.train(fromStep=edgeFromStep, toStep="END-COMBINED-MODEL")
        
        self._exitState()
    
    def doGrid(self):
        BINARY_RECALL_MODE = False # TODO: make a parameter
        print >> sys.stderr, "--------- Booster parameter search ---------"
        # Build trigger examples
        self.triggerDetector.buildExamples([self.optData], ["test-trigger-examples.gz"])
        
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
        EDGE_MODEL_STEM = os.path.join(edgeDetector.workDir, os.path.normpath(self.model.path)+"-edge-models/model-c_")
        TRIGGER_MODEL_STEM = os.path.join(triggerDetector.workDir, os.path.normpath(self.model.path)+"-trigger-models/model-c_")
        for params in paramCombinations:
            print >> sys.stderr, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            print >> sys.stderr, "Processing params", str(count+1) + "/" + str(len(paramCombinations)), params
            print >> sys.stderr, "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            
            # Triggers
            if params["trigger"] != prevTriggerParam:
                print >> sys.stderr, "Classifying trigger examples for parameter", params["trigger"]
                self.triggerDetector.classifyToXML(self, self.optData, self.model, "test-trigger-examples.gz", "grid-", classifierModel=TRIGGER_MODEL_STEM+str(params["trigger"])+".gz", split=False)
            prevTriggerParam = params["trigger"]
            
            # Boost
            xml = RecallAdjust.run("grid-trigger-pred.xml", params["booster"], None, binary=BINARY_RECALL_MODE)
            xml = ix.splitMergedElements(xml, None)
            xml = ix.recalculateIds(xml, None, True)
            
            # Build edge examples
            self.edgeDetector.buildExamples([xml], ["test-edge-examples.gz"])
            if options.classifier == "ACCls":
                self.triggerDetector.edgeDetector([xml], ["test-edge-examples.gz"], [self.optData])
            else:
                self.triggerDetector.edgeDetector([xml], ["test-edge-examples.gz"])
            # Classify with pre-defined model
            if params["edge"] == "BEST":
                edgeClassifierModel=None
            else:
                edgeClassifierModel=EDGE_MODEL_STEM+str(params["trigger"])+".gz"
            xml = self.edgeDetector.classifyToXML(self, self.optData, self.model, "test-edge-examples.gz", "grid-", classifierModel=edgeClassifierModel, split=True)
            if xml != None:                
                # EvaluateInteractionXML differs from the previous evaluations in that it can
                # be used to compare two separate GifXML-files. One of these is the gold file,
                # against which the other is evaluated by heuristically matching triggers and
                # edges. Note that this evaluation will differ somewhat from the previous ones,
                # which evaluate on the level of examples.
                EIXMLResult = EvaluateInteractionXML.run(self.evaluator, xml, self.optData, options.parse, options.tokenization)
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
        # Save grid model
        self.saveStr("recallAdjustParameter", str(bestResults[0]["booster"]), self.model)
        if self.combinedModel != None:
            self.saveStr("recallAdjustParameter", str(bestResults[0]["booster"]), self.combinedModel)
        if fullGrid: # define best models
            self.triggerDetector.addClassifierModel(self.model, TRIGGER_MODEL_STEM+str(bestResults[0]["trigger"])+".gz", bestResults[0]["trigger"])
            self.edgeDetector.addClassifierModel(self.model, EDGE_MODEL_STEM+str(bestResults[0]["edge"])+".gz", bestResults[0]["edge"])
        if options.task in ["OLD", "GE"]:
            print >> sys.stderr, "Best result:", bestResults[1]
        
#        # Final models with full grid
#        if options.classifier != "ACCls" and (not options.noTestSet) and options.fullGrid:
#            print >> sys.stderr, "------------ Submitting final models ------------"
#            print >> sys.stderr, "Everything models for parse", PARSE_TAG
#            c = None
#            if "local" not in options.csc: c = CSCConnection(CSC_WORKDIR+"/everything-trigger-models", CSC_ACCOUNT, True, password=options.password)
#            optimize(CLASSIFIER, Ev, TRIGGER_EVERYTHING_EXAMPLE_FILE, TRIGGER_TEST_EXAMPLE_FILE,\
#                TRIGGER_IDS+".class_names", "c:"+getParameter(bestTriggerModel).split("_")[-1], "everything-trigger-models", None, c, False, steps="SUBMIT")
#            if "local" not in options.csc: c = CSCConnection(CSC_WORKDIR+"/everything-edge-models", CSC_ACCOUNT, True, password=options.password)
#            optimize(CLASSIFIER, Ev, EDGE_EVERYTHING_EXAMPLE_FILE, EDGE_TEST_EXAMPLE_FILE,\
#                EDGE_IDS+".class_names", "c:"+getParameter(bestEdgeModel).split("_")[-1], "everything-edge-models", None, c, False, steps="SUBMIT")
#            print >> sys.stderr, "Everything models submitted"
