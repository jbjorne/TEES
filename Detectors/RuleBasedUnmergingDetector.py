from SingleStageDetector import SingleStageDetector
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator
thisPath = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(thisPath, "../GeniaChallenge/unflattening")))
from unflatten import unflatten

class RuleBasedUnmergingDetector(SingleStageDetector):
    def __init__(self):
        SingleStageDetector.__init__(self)
        self.tag = "rule-based-unmerging-"
    
    def beginModel(self, step, model, trainExampleFiles, testExampleFile, importIdsFromModel=None):
        pass
    
    def endModel(self, step, model, testExampleFile):
        pass
    
    def train(self, trainData=None, optData=None, model=None, combinedModel=None, exampleStyle=None, 
              classifierParameters=None, parse=None, tokenization=None, fromStep=None, toStep=None):
        pass
    
    def classify(self, data, model, output, parse=None, goldData=None):
        print >> sys.stderr, "--------- Rule based unmerging ---------"
        model = self.openModel(model, "r")
        exampleFileName = output+".examples.gz"
        self.buildExamples(model, [data], [exampleFileName], [goldData])
        if parse == None:
            parse = self.getStr("parse", model)
        unmergedXML = unflatten(xml, parse, parse)
        STFormat.ConvertXML.toSTFormat(unmergedXML, "rulebased-unmerging-geniaformat", getA2FileTag(options.task, subTask))
        # Evaluation of the Shared Task format
        if self.stEvaluator != None:
            # TODO: Store task/subtask in model
            self.stEvaluator.evaluate(output+".tar.gz")