import sys,os
sys.path.append("..")
import shutil
import subprocess
import Core.ExampleUtils as Example
import combine
import copy
#from Core.Evaluation import Evaluation
from Core.Classifier import Classifier

defaultOptimizationParameters = {"c":[0.0001,0.001,0.01,0.1,1,10,100]}

class CompositeClassifier(Classifier):
    def __init__(self, workDir=None):
        self._makeTempDir(workDir)
        self.internalClassifierClass = None
        self.classifiers = {}
#        self.notOptimizedParameters = ["classifier", "length"]   
    
    def __del__(self):
        self.debugFile.close()
        if self._workDir == None and os.path.exists(self.tempDir):
            print >> sys.stderr, "Removing temporary CompositeClassifier work directory", self.tempDir
            shutil.rmtree(self.tempDir)
    
    def _createInternalClassifier(self, tag):
        if self.tempDir != None:
            classifier = self.internalClassifierClass(workDir = self.tempDir + "/classifierLen_"+str(tag))
        else:
            classifier = self.internalClassifierClass()
        classifier.featureSet = self.featureSet
        classifier.classSet = self.classSet
        return classifier
    
    def _divideExamplesByLength(self, examples, separate):
        separated = {}
        for example in examples:
            exampleWasSeparated = False
            for tag in separate:
                featureName = "len_tokens_"+str(tag)
                if example[2].has_key(self.featureSet.getId(featureName)):
                    if not separated.has_key(tag):
                        separated[tag] = []
                    separated[tag].append(example)
                    exampleWasSeparated = True
            if not exampleWasSeparated:
                if not separated.has_key("rest"):
                    separated["rest"] = []
                separated["rest"].append(example)
        return separated

    def _dummyDivideExamplesByLength(self, examples, separate):
        separated = {}
        for example in examples:
            exampleWasSeparated = False
            for tag in separate:
                featureName = "len_tokens_"+str(tag)
                if example[2].has_key(self.featureSet.getId(featureName)):
                    if not separated.has_key(tag):
                        separated[tag] = []
                    separated[tag].append(example)
                    exampleWasSeparated = True
            if not exampleWasSeparated:
                if not separated.has_key("rest"):
                    separated["rest"] = []
                separated["rest"].append(example)
        for key in separated.keys():
            separated[key] = examples
        return separated
    
#    def _getExamplesByLength(self, examples, length):
#        selected = []
#        for example in examples:
#            if example[2].has_key(self.featureSet.getId("len")):
#                if example[2][self.featureSet.getId("len")] == length:
#                    selected.append(example)
#        return selected
    
    def _getInternalClassifierParameters(self, parameters):
        internalClassifierParameters = copy.deepcopy(parameters)
        del internalClassifierParameters["classifier"]
        del internalClassifierParameters["lengths"]
        return internalClassifierParameters
    
    def _selectInternalClassifierParameters(self, parameters, tag):
        parameters = self._getInternalClassifierParameters(parameters)
        selectedParameters = {}
        for k, v in parameters.iteritems():
            if "optimal_internal_" in k:
                paramName = k[len("optimal_internal_"):]
                nameParts = paramName.split("_",1)
                if nameParts[0] == tag:
                    assert(not selectedParameters.has_key(nameParts[1]))
                    selectedParameters[nameParts[1]] = v
            else:
                assert(not selectedParameters.has_key(k))
                selectedParameters[k] = v
        return selectedParameters
    
    def train(self, examples, parameters=None):
        exec "from Classifiers." + parameters["classifier"][0]+ " import " + parameters["classifier"][0] + " as InternalClassifier"
        self.internalClassifierClass = InternalClassifier
        examples = self.filterTrainingSet(examples)
        examplesByLength = self._divideExamplesByLength(examples, parameters["lengths"])
        for k,v in examplesByLength.iteritems():
            internalClassifierParameters = self._selectInternalClassifierParameters(parameters, str(k))
            self.classifiers[k] = self._createInternalClassifier(str(k))
            print >> sys.stderr, "Training internal classifier \""+str(k)+"\" with parameters: " + str(internalClassifierParameters)
            self.classifiers[k].train(examples, internalClassifierParameters)
        
    def classify(self, examples, parameters=None):
        examples, predictions = self.filterClassificationSet(examples, True)
        examplesByLength = self._divideExamplesByLength(examples, self.classifiers.keys())
        for k,v in examplesByLength.iteritems():
            #internalClassifierParameters = self._selectInternalClassifierParameters(parameters, str(k))
            if self.classifiers.has_key(k):
                print >> sys.stderr, "Internal classifier \""+str(k)+"\" classifying"
                #print "Examples:", len(v)
                newPredictions = self.classifiers[k].classify(v)
                newEvaluation = self.evaluationClass(newPredictions, self.classSet)
                print >> sys.stderr, newEvaluation.toStringConcise(title=str(k))
                predictions.extend( newPredictions )
        return predictions
    
    def optimize(self, trainSets, classifySets, parameters=defaultOptimizationParameters, evaluationClass=None, evaluationArgs={}):
        self.evaluationClass = evaluationClass
        
        print >> sys.stderr, "Optimizing composite classifier parameters" 
        exec "from Classifiers." + parameters["classifier"][0] + " import " + parameters["classifier"][0] + " as InternalClassifier"
        self.internalClassifierClass = InternalClassifier
        for i in range(len(trainSets)):
            trainSets[i] = self._divideExamplesByLength(trainSets[i], parameters["lengths"])
        for i in range(len(classifySets)):
            classifySets[i] = self._divideExamplesByLength(classifySets[i], parameters["lengths"])
        bestResult = (None, None, {})
        for length in parameters["lengths"]+["rest"]:
            print >> sys.stderr, "Optimizing parameters for group", length 
            lengthTrainSets = []
            for s in trainSets:
                if s.has_key(length):
                    lengthTrainSets.append(s[length])
                else:
                    lengthTrainSets.append([])
            lengthClassifySets = []
            for s in classifySets:
                if s.has_key(length):
                    lengthClassifySets.append(s[length])
                else:
                    lengthClassifySets.append([])
            internalClassifierParameters = self._getInternalClassifierParameters(parameters)
            lengthClassifier = self._createInternalClassifier(str(length))
            result = lengthClassifier.optimize(lengthTrainSets, lengthClassifySets, internalClassifierParameters, evaluationClass, evaluationArgs)
            for k,v in result[2].iteritems():
                bestResult[2]["optimal_internal_"+str(length)+"_"+str(k)] = v
        bestResult[2]["lengths"] = parameters["lengths"]
        bestResult[2]["classifier"] = parameters["classifier"]
        return bestResult