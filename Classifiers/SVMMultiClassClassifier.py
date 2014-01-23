import sys,os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import subprocess
import copy
import tempfile
import types, copy
from ExternalClassifier import ExternalClassifier
import Utils.Settings as Settings
import Utils.Download as Download
import Utils.Connection.Connection as Connection
import Utils.Parameters as Parameters
import Tools.Tool
#import SVMMultiClassModelUtils
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator

def install(destDir=None, downloadDir=None, redownload=False, compile=True, updateLocalSettings=False):
    print >> sys.stderr, "Installing SVM-Multiclass"
    if compile:
        url = Settings.URL["SVM_MULTICLASS_SOURCE"]
    else:
        url = Settings.URL["SVM_MULTICLASS_LINUX"]
    if downloadDir == None:
        downloadDir = os.path.join(Settings.DATAPATH, "tools/download/")
    if destDir == None:
        destDir = Settings.DATAPATH
    destDir += "/tools/SVMMultiClass"
    
    Download.downloadAndExtract(url, destDir, downloadDir, redownload=redownload)
    if compile:
        print >> sys.stderr, "Compiling SVM-Multiclass"
        Tools.Tool.testPrograms("SVM-Multiclass", ["make"])
        subprocess.call("cd " + destDir + "; make", shell=True)
    
    Tools.Tool.finalizeInstall(["svm_multiclass_learn", "svm_multiclass_classify"], 
        {"svm_multiclass_learn":"echo | ./svm_multiclass_learn -? > /dev/null", 
         "svm_multiclass_classify":"echo | ./svm_multiclass_classify -? > /dev/null"},
        destDir, {"SVM_MULTICLASS_DIR":destDir}, updateLocalSettings)

class SVMMultiClassClassifier(ExternalClassifier):
    """
    A wrapper for the Joachims SVM Multiclass classifier.
    """
    
    def __init__(self, connection=None):
        ExternalClassifier.__init__(self, connection=connection)
        self.defaultEvaluator = AveragingMultiClassEvaluator
        self.parameterFormat = "-%k %v"
        self.parameterValueListKey["train"] = "c"
        self.parameterValueTypes["train"] = {"c":[int,float]}
        self.trainDirSetting = "SVM_MULTICLASS_DIR"
        self.trainCommand = "%dsvm_multiclass_learn %p %e %m"
        self.classifyDirSetting = "SVM_MULTICLASS_DIR"
        self.classifyCommand = "%dsvm_multiclass_classify %e %m %c"
    
#    def filterIds(self, ids, model, verbose=False):
#        # Get feature ids
#        if type(ids) in types.StringTypes:
#            from Core.IdSet import IdSet
#            ids = IdSet(filename=ids)
#        # Get SVM model file feature ids
#        if verbose:
#            print >> sys.stderr, "Reading SVM model"
#        if model.endswith(".gz"):
#            f = gzip.open(model, "rt")
#        else:
#            f = open(model, "rt")
#        supportVectorLine = f.readlines()[-1]
#        f.close()
#        modelIdNumbers = set()
#        for split in supportVectorLine.split():
#            if ":" in split:
#                idPart = split.split(":")[0]
#                if idPart.isdigit():
#                    #print idPart
#                    modelIdNumbers.add(int(idPart))
#        modelIdNumbers = list(modelIdNumbers)
#        modelIdNumbers.sort()
#        # Make a new feature set with only features that are in the model file
#        if verbose:
#            print >> sys.stderr, "Feature set has", len(ids.Ids), "features, highest id is", max(ids._namesById.keys())
#            print >> sys.stderr, "Model has", len(modelIdNumbers), "features"
#            print >> sys.stderr, "Filtering ids"
#        newIds = IdSet()
#        newIds.nextFreeId = 999999999
#        for featureId in modelIdNumbers:
#            featureName = ids.getName(featureId)
#            assert featureName != None, featureId
#            newIds.defineId(featureName, featureId)
#        newIds.nextFreeId = max(newIds.Ids.values())+1
#        # Print statistics
#        if verbose:
#            print >> sys.stderr, "Filtered ids:", len(newIds.Ids), "(original", str(len(ids.Ids)) + ")"
#        return newIds
    
if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    from optparse import OptionParser
    import os
    from Utils.Parameters import *
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
    
    if options.install != None:
        downloadDir = None
        destDir = None
        if options.install != "DEFAULT":
            if "," in options.install:
                destDir, downloadDir = options.install.split(",")
            else:
                destDir = options.install
        install(destDir, downloadDir, False, options.installFromSource)
        sys.exit()
#    elif options.filterIds != None:
#        assert options.model != None
#        classifier = SVMMultiClassClassifier()
#        filteredIds = classifier.filterIds(options.filterIds, options.model, verbose=True)
#        if options.output != None:
#            filteredIds.write(options.output)
    else:
        assert options.action in ["TRAIN", "CLASSIFY", "OPTIMIZE"]
        classifier = SVMMultiClassClassifier(Connection.getConnection(options.remote))
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