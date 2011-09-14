import sys, os
import types
import itertools
import copy
sys.path.append("..")
import Core.ExampleUtils as ExampleUtils
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator
from Evaluators.MultiLabelMultiClassEvaluator import MultiLabelMultiClassEvaluator

# sort by negative class strength
def compare(x,y):
    if x[0] > y[0]:
        return 1
    elif x[0] == y[0]:
        return 0
    else:
        return -1

def threshold(examples, predictions=None, classSet=None):
    if type(classSet) == types.StringType: # class names are in file
        classSet = IdSet(filename=classSet)
    if type(predictions) == types.StringType: # predictions are in file
        predictions = ExampleUtils.loadPredictions(predictions)
    if type(examples) == types.StringType: # examples are in file
        examples = ExampleUtils.readExamples(examples, False)
    
    baseEv = AveragingMultiClassEvaluator(None)
    baseEv._calculate(examples, predictions)
    print baseEv.toStringConcise(title="baseline")
    multilabel = MultiLabelMultiClassEvaluator(None)
    multilabel._calculate(examples, predictions)
    print multilabel.toStringConcise(title="multilabel")
    sys.exit()
    
    pairs = []
    for example, prediction in itertools.izip(examples, predictions):
        if prediction[0] == 1:
            maxNonNegative = -999999
            for val in prediction[2:]:
                if val > maxNonNegative:
                    maxNonNegative = val
            distance = prediction[1] - maxNonNegative
        else:
            distance = prediction[1] - prediction[prediction[0]] 
        pairs.append([distance, example, prediction])
    pairs.sort(compare)
    
    memPredictions = []
    bestEv = baseEv
    bestPair = [None, None, None]
    for p in predictions:
        memPredictions.append(p)
    for pair in pairs:
        modifier = pair[0] + 0.00000001
        changedClass = 0
        for pred in memPredictions:
            negPred = pred[1] - modifier  
            maxVal = negPred
            maxClass = 1
            for i in range(2, len(pred)):
                if pred[i] > maxVal:
                    maxVal = pred[i]
                    maxClass = i
            if pred[0] != maxClass:
                changedClass += 1
            pred[0] = maxClass
        ev = AveragingMultiClassEvaluator(None)
        ev._calculate(examples, memPredictions)
        print pair[0], pair[2], changedClass
        print ev.toStringConcise()
        if ev.compare(bestEv) == 1:
            print "Improved"
            bestPair = pair
            bestEv = ev
    
    print "---------------------------------------------"
    print baseEv.toStringConcise(title="baseline")
    print bestPair[0], bestPair[2] 
    print bestEv.toStringConcise(title="best") 

exampleFilename = "/home/jari/biotext/BioNLP2011/tests/GE/GE-test-110211/edge-test-examples-split-mccc-preparsed_split-mccc-preparsed"
predFilename = "/home/jari/biotext/BioNLP2011/tests/GE/GE-test-110211/edge-models/predictions-c_20000"
threshold(exampleFilename, predFilename)
