__version__ = "$Revision: 1.51 $"

import sys,os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import shutil, tempfile
import subprocess
import Core.ExampleUtils as ExampleUtils
#import Core.OptimizeParameters
import Utils.Libraries.combine as combine
import copy
import tempfile
import subprocess
import atexit
import gzip
"""
A wrapper for the Joachims SVM Multiclass classifier.
"""
    
import types, copy
from Core.Classifier import Classifier
import Core.Split as Split
from Utils.Timer import Timer
import Utils.Parameters as Parameters
from Utils.ProgressCounter import ProgressCounter
import Utils.Settings as Settings
import Utils.Download as Download
import Tools.Tool
import SVMMultiClassModelUtils
import Utils.Connection.Connection as Connection
from Utils.Connection.UnixConnection import UnixConnection
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

def removeTempUnzipped(filename):
    if os.path.exists(filename):
        count = SVMMultiClassClassifier.getFileCounter(filename, removeIfZero=True)
        if count == 0:
            os.remove(filename)

class SVMMultiClassClassifier(Classifier):
    """
    A wrapper for the Joachims SVM Multiclass classifier.
    """
    
    def __init__(self, connection=None):
        self.defaultEvaluator = AveragingMultiClassEvaluator
        if connection == None:
            self.connection = UnixConnection() # A local connection
        else:
            self.connection = connection
        self.parameterGrid = None
        self.state = None
        self._job = None
        self._prevJobStatus = None
        self._filesToRelease = []
        
        self.parameters = None
        self.model = None
        self.predictions = None
        #self.parameterFormat = "-%k %v"
        #self.trainDir = "SVM_MULTICLASS_DIR"
        #self.trainCommand = "svm_multiclass_learn %a %m"
        #self.classifyDir = "SVM_MULTICLASS_DIR"
        #self.classifyCommand = "svm_multiclass_classify %m %e %p"
    
    def getJob(self):
        return self._job
    
    def getStatus(self):
        if self._job != None:
            self._prevJobStatus = self.connection.getJobStatus(self._job)
        if self._prevJobStatus in ["FINISHED", "FAILED"]:
            self.state = None
            self._job = None
            for filename in self._filesToRelease:
                SVMMultiClassClassifier.getFileCounter(filename, add=-1, createIfNotExist=False)
            self._filesToRelease = []
        if self._prevJobStatus == None:
            return "FINISHED"
        else:
            return self._prevJobStatus
    
    def setState(self, stateName):
        assert self.getStatus() in ["FINISHED", "FAILED"]
        self.state = stateName
        self._job = None
        self._prevJobStatus = None
        if stateName == "TRAIN" or stateName == "OPTIMIZE":
            self.model = None
            self.parameters = None
        # for all states
        self.predictions = None
        #self.optimizeJobs = []
    
    @classmethod
    def getUnzipped(cls, filename):
        """
        Temporarily uncompress a file, usually a compressed example file. The uncompressed
        file appears in the same location as the original file. The /tmp directory is
        as these examples are usually used by a classifier that is run in separate process,
        which on clusters might end up on a different node, where the local /tmp is no
        longer accessible.
        """
        if not filename.endswith(".gz"):
            return filename
        tempfilename = filename[:-3] + "-unzipped-temp"
        # Determine if the uncompressed file does not exist, or needs to be updated
        uncompress = False
        if os.path.exists(tempfilename):
            if os.path.getmtime(filename) > os.path.getmtime(tempfilename): # compressed file has changed
                uncompress = True
        else:
            uncompress = True
        # Uncompress if needed
        if uncompress:
            print >> sys.stderr, "Uncompressing example file", filename
            subprocess.call("gunzip -cfv " + filename + " > " + tempfilename, shell=True)
            assert os.path.exists(filename)
            assert os.path.exists(tempfilename)
            atexit.register(removeTempUnzipped, tempfilename) # mark for deletion
        return tempfilename
    
    @classmethod
    def getFileCounter(cls, filename, add=0, createIfNotExist=False, removeIfZero=False):
        """
        Keep track of the number of users on a temporary file
        """
        filename += "-counter"
        count = 0
        if os.path.exists(filename):
            f = open(filename, "rt")
            lines = f.readlines()
            f.close()
            assert len(lines) == 1, filename
            count = int(lines[0])
        elif not createIfNotExist:
            return None
        count += add
        if count < 0:
            count = 0
        if removeIfZero and count == 0 and os.path.exists(filename):
            os.remove(filename)
        else:
            f = open(filename, "wt")
            f.write(str(count))
            f.close()
        return count

    def getExampleFile(self, examples, upload=True, replaceRemote=True, dummy=False):
        # If examples are in a list, they will be written to a file for SVM-multiclass
        if examples == None:
            return None
        if dummy:
            return "DUMMY"
        elif type(examples) == types.ListType:
            assert False
            #ExampleUtils.writeExamples(examples, trainPath + "/")
        else:
            examplesPath = os.path.normpath(os.path.abspath(examples))
       
        localPath = examplesPath
        if upload:
            examplesPath = self.connection.upload(examplesPath, uncompress=True, replace=replaceRemote)
        if examplesPath == localPath and examplesPath.endswith(".gz"): # no upload happened
            examplesPath = SVMMultiClassClassifier.getUnzipped(examplesPath) # uncompress if not yet uncompressed
            SVMMultiClassClassifier.getFileCounter(examplesPath, 1, createIfNotExist=True) # increase user counter in any case
            print >> sys.stderr, self.__class__.__name__, "using example file", examples, "as", examplesPath
        return examplesPath
    
    def train(self, examples, outDir, parameters, classifyExamples=None, finishBeforeReturn=False, replaceRemoteExamples=True, dummy=False):
        outDir = os.path.abspath(outDir)
        
        examples = self.getExampleFile(examples, replaceRemote=replaceRemoteExamples, dummy=dummy)
        classifyExamples = self.getExampleFile(classifyExamples, replaceRemote=replaceRemoteExamples, dummy=dummy)
        parameters = Parameters.get(parameters, valueListKey="c")
        svmMulticlassDir = self.connection.getSetting("SVM_MULTICLASS_DIR")
        
        # Return a new classifier instance for following the training process and using the model
        classifier = copy.copy(self)
        classifier.setState("TRAIN")
        classifier.parameters = parameters
        classifier._filesToRelease = [examples, classifyExamples]
        # Train
        if not os.path.exists(outDir):
            os.makedirs(outDir)
        trainCommand = svmMulticlassDir + "/svm_multiclass_learn "
        paramKeys = sorted(parameters.keys())
        idStr = ""
        for key in paramKeys:
            if key.startswith("TEES."):
                continue
            trainCommand += "-" + str(key) + " "
            idStr += "-" + str(key)
            if parameters[key] != None:
                trainCommand += str(parameters[key]) + " "
                idStr += "_" + str(parameters[key])
        classifier.parameterIdStr = idStr
        classifier.model = self.connection.getRemotePath(outDir + "/model" + idStr, True)
        modelPath = self.connection.getRemotePath(outDir + "/model" + idStr, False)
        trainCommand += examples + " " + modelPath
        self.connection.addCommand(trainCommand)
        # Classify with the trained model (optional)
        if classifyExamples != None:
            classifier.predictions = self.connection.getRemotePath(outDir + "/predictions" + idStr, True)
            predictionsPath = self.connection.getRemotePath(outDir + "/predictions" + idStr, False)
            classifyCommand = svmMulticlassDir + "/svm_multiclass_classify " + classifyExamples + " " + modelPath + " " + predictionsPath
            self.connection.addCommand(classifyCommand)
        # Run the process
        jobName = "svm_multiclass_learn" + idStr
        logPath = outDir + "/" + jobName
        if dummy: # return a classifier that connects to an existing job
            self.connection.clearCommands()
            classifier._job = self.connection.getJob(jobDir=outDir, jobName=jobName)
        else: # submit the job
            classifier._job = self.connection.submit(jobDir=outDir, jobName=jobName, stdout=logPath+".stdout")
            if finishBeforeReturn:
                self.connection.waitForJob(classifier._job)
                self.getStatus()
        return classifier
    
    def downloadModel(self, outPath=None, breakConnection=True):
        assert self.getStatus() == "FINISHED" and self.model != None
        self.model = self.connection.download(self.model, outPath)
        if breakConnection:
            self.connection = UnixConnection() # A local connection
        return self.model
    
    def downloadPredictions(self, outPath=None):
        assert self.getStatus() == "FINISHED" and self.predictions != None
        self.predictions = self.connection.download(self.predictions, outPath)
        return self.predictions
    
    def classify(self, examples, output, model=None, finishBeforeReturn=False, replaceRemoteFiles=True):
        output = os.path.abspath(output)
        # Return a new classifier instance for following the training process and using the model
        classifier = copy.copy(self)
        classifier.setState("CLASSIFY")
        # Classify
        if model == None:
            classifier.model = model = self.model
        model = os.path.abspath(model)
        model = self.connection.upload(model, uncompress=True, replace=replaceRemoteFiles)
        classifier.predictions = self.connection.getRemotePath(output, True)
        predictionsPath = self.connection.getRemotePath(output, False)
        examples = self.getExampleFile(examples, replaceRemote=replaceRemoteFiles)
        classifier._filesToRelease = [examples]
        self.connection.clearCommands()
        self.connection.addCommand( self.connection.getSetting("SVM_MULTICLASS_DIR") + "/svm_multiclass_classify " + examples + " " + model + " " + predictionsPath )
        classifier._job = self.connection.submit(jobDir=os.path.abspath(os.path.dirname(output)), 
                                                 jobName="svm_multiclass_classify-"+os.path.basename(model))
        if finishBeforeReturn:
            self.connection.waitForJob(classifier._job)
            classifier.downloadPredictions()
        return classifier
    
    def optimize(self, examples, outDir, parameters, classifyExamples, classIds, step="BOTH", evaluator=None, determineThreshold=False, timeout=None, downloadAllModels=False):
        assert step in ["BOTH", "SUBMIT", "RESULTS"], step
        outDir = os.path.abspath(outDir)
        # Initialize training (or reconnect to existing jobs)
        combinations = Parameters.getCombinations(Parameters.get(parameters, valueListKey="c")) #Core.OptimizeParameters.getParameterCombinations(parameters)
        trained = []
        for combination in combinations:
            trained.append( self.train(examples, outDir, combination, classifyExamples, replaceRemoteExamples=(len(trained) == 0), dummy=(step == "RESULTS")) )
        if step == "SUBMIT": # Return already
            classifier = copy.copy(self)
            classifier.setState("OPTIMIZE")
            return classifier
        
        # Wait for the training to finish
        finalJobStatus = self.connection.waitForJobs([x.getJob() for x in trained])
        # Evaluate the results
        print >> sys.stderr, "Evaluating results"
        #Stream.setIndent(" ")
        bestResult = None
        if evaluator == None:
            evaluator = self.defaultEvaluator
        for i in range(len(combinations)):
            id = trained[i].parameterIdStr
            #Stream.setIndent(" ")
            # Get predictions
            predictions = None
            if trained[i].getStatus() == "FINISHED":
                predictions = trained[i].downloadPredictions()
            else:
                print >> sys.stderr, "No results for combination" + id
                continue
            if downloadAllModels:
                trained[i].downloadModel()
            # Compare to other results
            print >> sys.stderr, "*** Evaluating results for combination" + id + " ***"
            threshold = None
            if determineThreshold:
                print >> sys.stderr, "Thresholding, original micro =",
                evaluation = evaluator.evaluate(classifyExamples, predictions, classIds, os.path.join(outDir, "evaluation-before-threshold" + id + ".csv"), verbose=False)
                print >> sys.stderr, evaluation.microF.toStringConcise()
                threshold, bestF = evaluator.threshold(classifyExamples, predictions)
                print >> sys.stderr, "threshold =", threshold, "at binary fscore", str(bestF)[0:6]
            evaluation = evaluator.evaluate(classifyExamples, ExampleUtils.loadPredictions(predictions, threshold=threshold), classIds, os.path.join(outDir, "evaluation" + id + ".csv"))
            if bestResult == None or evaluation.compare(bestResult[0]) > 0: #: averageResult.fScore > bestResult[1].fScore:
                bestResult = [evaluation, trained[i], combinations[i], threshold]
            if not self.connection.isLocal():
                os.remove(predictions) # remove predictions to save space
        #Stream.setIndent()
        print >> sys.stderr, "*** Evaluation complete", finalJobStatus, "***"
        print >> sys.stderr, "Selected parameters", bestResult[2]
        classifier = copy.copy(bestResult[1])
        classifier.threshold = bestResult[3]
        classifier.downloadModel()
        return classifier
    
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
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-e", "--examples", default=None, dest="examples", help="Example File", metavar="FILE")
    optparser.add_option("-a", "--action", default=None, dest="action", help="TRAIN, CLASSIFY or OPTIMIZE")
    optparser.add_option("--optimizeStep", default="BOTH", dest="optimizeStep", help="BOTH, SUBMIT or RESULTS")
    optparser.add_option("--classifyExamples", default=None, dest="classifyExamples", help="Example File", metavar="FILE")
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
            options.parameters = splitParameters(options.parameters)
            optimized = classifier.optimize(options.examples, options.output, options.parameters, options.classifyExamples, options.classIds, step=options.optimizeStep)