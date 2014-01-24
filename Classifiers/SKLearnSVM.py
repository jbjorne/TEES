import sys,os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from ExternalClassifier import ExternalClassifier
import Utils.Connection.Connection as Connection
import Utils.Parameters as Parameters
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator

class SKLearnSVM(ExternalClassifier):
    
    def __init__(self, connection=None):
        ExternalClassifier.__init__(self, connection=connection)
        self.defaultEvaluator = AveragingMultiClassEvaluator
        self.parameterFormat = "-%k %v"
        self.parameterValueListKey["train"] = "c"
        self.parameterValueTypes["train"] = {"c":[int,float]}
        self.trainDirSetting = "SCIKIT_WRAPPER_DIR"
        self.trainCommand = "python %dSKLearnSVMWrapper.py --train %p --examples %e --model %m"
        self.classifyDirSetting = "SCIKIT_WRAPPER_DIR"
        self.classifyCommand = "python %dSKLearnSVMWrapper.py --classify --examples %e --model %m --predictions %c"
    
if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    from optparse import OptionParser
    optparser = OptionParser(description="Joachims SVM Multiclass classifier wrapper")
    optparser.add_option("-e", "--examples", default=None, dest="examples", help="Example File", metavar="FILE")
    optparser.add_option("-a", "--action", default=None, dest="action", help="TRAIN, CLASSIFY or OPTIMIZE")
    optparser.add_option("--optimizeStep", default="BOTH", dest="optimizeStep", help="BOTH, SUBMIT or RESULTS")
    optparser.add_option("-c", "--classifyExamples", default=None, dest="classifyExamples", help="Example File", metavar="FILE")
    optparser.add_option("--classIds", default=None, dest="classIds", help="Class ids", metavar="FILE")
    optparser.add_option("-m", "--model", default=None, dest="model", help="path to model file")
    #optparser.add_option("-w", "--work", default=None, dest="work", help="Working directory for intermediate and debug files")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output directory or file")
    optparser.add_option("-r", "--remote", default=None, dest="remote", help="Remote connection")
    #optparser.add_option("-c", "--classifier", default="SVMMultiClassClassifier", dest="classifier", help="Classifier Class")
    optparser.add_option("-p", "--parameters", default=None, dest="parameters", help="Parameters for the classifier")
    #optparser.add_option("-d", "--ids", default=None, dest="ids", help="")
    #optparser.add_option("--filterIds", default=None, dest="filterIds", help="")
    optparser.add_option("--install", default=None, dest="install", help="Install directory (or DEFAULT)")
    optparser.add_option("--installFromSource", default=False, action="store_true", dest="installFromSource", help="")
    (options, args) = optparser.parse_args()

    assert options.action in ["TRAIN", "CLASSIFY", "OPTIMIZE"]
    classifier = SKLearnSVM(Connection.getConnection(options.remote))
    if options.action == "TRAIN":
        import time
        trained = classifier.train(options.examples, options.output, options.parameters, options.classifyExamples)
        status = trained.getStatus()
        while status not in ["FINISHED", "FAILED"]:
            print >> sys.stderr, "Training classifier, status =", status
            time.sleep(10)
            status = trained.getStatus()
        print >> sys.stderr, "Training finished, status =", status
        if trained.getStatus() == "FINISHED":
            trained.downloadPredictions()
            trained.downloadModel()
    elif options.action == "CLASSIFY":
        classified = classifier.classify(options.examples, options.output, options.model, True)
        if classified.getStatus() == "FINISHED":
            classified.downloadPredictions()
    else: # OPTIMIZE
        options.parameters = Parameters.get(options.parameters)
        optimized = classifier.optimize(options.examples, options.output, options.parameters, options.classifyExamples, options.classIds, step=options.optimizeStep)