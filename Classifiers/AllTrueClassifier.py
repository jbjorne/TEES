from Classifier import Classifier
import Core.ExampleUtils as Example
import sys, os, shutil, types

class AllTrueClassifier(Classifier):
    def __init__(self, workDir=None):
        self._makeTempDir(workDir)        
    
    def __del__(self):
        self.debugFile.close()
        if self._workDir == None and os.path.exists(self.tempDir):
            print >> sys.stderr, "Removing temporary classifier work directory", self.tempDir
            shutil.rmtree(self.tempDir)

    @classmethod
    def train(cls, examples, parameters, outputFile=None, timeout=None):
        return 0
    
    @classmethod
    def test(cls, examples, modelPath, output=None, parameters=None, timeout=None):
        if type(examples) == types.ListType:
            print >> sys.stderr, "Classifying", len(examples), "with All-True Classifier"
            examples, predictions = self.filterClassificationSet(examples, False)
            testPath = self.tempDir+"/test.dat"
            Example.writeExamples(examples, testPath)
        else:
            print >> sys.stderr, "Classifying file", examples, "with All-True Classifier"
            testPath = examples
            examples = Example.readExamples(examples,False)
        print >> sys.stderr, "Note! Classification must be binary"
        #examples, predictions = self.filterClassificationSet(examples, True)
        predictions = []
        for example in examples:
            #predictions.append( (example, example[1]) )
            predictions.append( [2] ) #[example[1]] )
        
        if output == None:
            output = "predictions"
        f = open(output, "wt")
        for p in predictions:
            f.write(str(p[0])+"\n")
        f.close()
            
        return predictions
