"""
Base class for classifiers
"""
import sys, os, copy, types, subprocess, atexit, shutil
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
import Utils.Parameters as Parameters

def removeTempUnzipped(filename):
    if os.path.exists(filename):
        count = Classifier.getFileCounter(filename, removeIfZero=True)
        if count == 0:
            os.remove(filename)

class Classifier:
    # Public interface ##########################################################################
    def __init__(self, connection=None):
        pass

    def train(self, examples, outDir, parameters, classifyExamples=None):        
        return copy.copy(self)
    
    def classify(self, examples, output, model=None, finishBeforeReturn=False, replaceRemoteFiles=True):
        raise NotImplementedError
    
    def optimize(self, examples, outDir, parameters, classifyExamples, classIds, step="BOTH", evaluator=None, determineThreshold=False, timeout=None, downloadAllModels=False):
        classifier = copy.copy(self)
        classifier.parameters = parameters
        return classifier
    
    def saveModel(self, teesModel, tag=""):
        if hasattr(self, "model") and self.model != None:
            teesModelPath = teesModel.get(tag+"classifier-model", True)
            shutil.copy2(self.model, teesModelPath)
        if hasattr(self, "parameters") and self.parameters != None:
            teesModel.addStr(tag+"classifier-parameter", Parameters.toString(Parameters.get(self.parameters)))
        if hasattr(self, "threshold") and self.threshold != None:
            teesModel.addStr(tag+"threshold", str(self.threshold))
    
    
    # Utility methods ##########################################################################
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
            examplesPath = Classifier.getUnzipped(examplesPath) # uncompress if not yet uncompressed
            Classifier.getFileCounter(examplesPath, 1, createIfNotExist=True) # increase user counter in any case
            print >> sys.stderr, self.__class__.__name__, "using example file", examples, "as", examplesPath
        return examplesPath