from Core.Classifier import Classifier

class AllTrueClassifier(Classifier):
    def __init__(self, workDir=None):
        self._makeTempDir(workDir)        
    
    def __del__(self):
        self.debugFile.close()
        if self._workDir == None and os.path.exists(self.tempDir):
            print >> sys.stderr, "Removing temporary classifier work directory", self.tempDir
            shutil.rmtree(self.tempDir)

    def train(self, examples, parameters=None):        
        pass
    
    def classify(self, examples, parameters=None):
        examples, predictions = self.filterClassificationSet(examples, True)
        #predictions = []
        for example in examples:
            predictions.append( (example, 1.0) )
        return predictions
