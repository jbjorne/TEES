from Core.Classifier import Classifier
import sys, os, shutil
import math

class TestClassifier(Classifier):
    def __init__(self, workDir=None):
        self._makeTempDir(workDir)        
    
    def __del__(self):
        self.debugFile.close()
        if self._workDir == None and os.path.exists(self.tempDir):
            print >> sys.stderr, "Removing temporary classifier work directory", self.tempDir
            shutil.rmtree(self.tempDir)

    def train(self, examples, parameters=None):        
        self.trainExamples = examples
        self.trainingParameters = parameters
        return 0
    
    def classify(self, examples, parameters=None):
        examples, predictions = self.filterClassificationSet(examples, True)
        predictions = self.getDensities(examples, self.trainExamples, float(self.trainingParameters["cutoff"]), float(self.trainingParameters["scale"]))
        return predictions
    
    def getDensities(self, testExamples, trainExamples, cutoff = 0.5, scale = 1.0):
        predictions = []
        maxDensity = 0.0000001
        densities = []
        for testExample in testExamples:
            density = 0.0
            for trainExample in trainExamples:
                lenSum = 0.0
                features = set(trainExample[2].keys() + testExample[2].keys())
                for feature in features:
                    a = 0.0
                    if testExample[2].has_key(feature):
                        a = testExample[2][feature]
                    b = 0.0
                    if testExample[2].has_key(feature):
                        b = testExample[2][feature] 
                    dimensionDistance = a - b
                    lenSum += dimensionDistance * dimensionDistance
#                print "sqrt:", math.sqrt(lenSum)
#                print "scale:", scale
                newDensity = math.sqrt(lenSum) * scale
                if newDensity < density:
                    density = newDensity
            if density > maxDensity:
                maxDensity = newDensity
            densities.append(density)
        for i in range(len(densities)):
            if density / maxDensity > cutoff:
                predictions.append( (testExamples[i], -1) )
            else:
                predictions.append( (testExamples[i], 1) )
        return predictions