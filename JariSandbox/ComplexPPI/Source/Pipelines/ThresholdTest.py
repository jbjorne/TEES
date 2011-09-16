import sys, os
import types
import itertools
import copy
sys.path.append("..")
import Core.ExampleUtils as ExampleUtils
from Core.IdSet import IdSet
from Evaluators.AveragingMultiClassEvaluator import AveragingMultiClassEvaluator
from Evaluators.MultiLabelMultiClassEvaluator import MultiLabelMultiClassEvaluator
from Evaluators.Evaluator import EvaluationData

# sort by negative class strength
def compare(x,y):
    if x[0] > y[0]:
        return 1
    elif x[0] == y[0]:
        return 0
    else:
        return -1
    
def updateF(data, trueClass, predictedClass, count):
    if predictedClass == trueClass: # correct classification
        # correctly classified for its class -> true positive for that class
        if trueClass != 1: # a non-negative example -> correct = true positive
            data._tp += count
        else: # a negative example -> correct = true negative
            data._tn += count
    else: # predictedClass != trueClass:
        if predictedClass == 1: # non-negative example, negative prediction -> incorrect = false negative
            data._fn += count
        else: # non-negative incorrect prediction -> false positive
            data._fp += count

def thresholdClass(examples, predictions, classId, baseLineF):
    ex = []
    for example, prediction in itertools.izip(examples, predictions):
        maxClassValue = -999999
        maxClass = None
        for i in range (1, len(prediction)):
            if i == classId:
                continue
            if prediction[i] > maxClassValue:
                maxClassValue = prediction[i]
                maxClass = i
        distance = prediction[classId] - maxClassValue
        ex.append((distance, (example[1], prediction[0], maxClass)))
    #more.sort(compare, reverse=True)
    ex.sort(compare)
    # Start with all negative
    ev = EvaluationData()
    for example in ex:
        if example[0] < 0.0:
            updateF(ev, example[1][0], example[1][2], 1)
        else:
            updateF(ev, example[1][0], example[1][1], 1)
    count = 0
    bestF = [baseLineF, None, (0.0, None), None]
    for example in ex:
        if example[0] < 0.0:
            # Remove original example
            updateF(ev, example[1][0], example[1][2], -1)
            # Add new example
            updateF(ev, example[1][0], example[1][1], 1)
            # Calculate F for this point
        else:
            # Remove original example
            updateF(ev, example[1][0], example[1][1], -1)
            # Add new example
            updateF(ev, example[1][0], example[1][2], 1)
            # Calculate F for this point
        ev.calculateFScore()
        count += 1
        #print count, example, ev.toStringConcise()
        if ev.fscore > bestF[0]:
            bestF = (ev.fscore, count, example, ev.toStringConcise())
    return bestF

def threshold(examples, predictionsDir=None, classSet=None):
    if type(classSet) == types.StringType: # class names are in file
        classSet = IdSet(filename=classSet)
    classIds = set()
    if type(examples) == types.StringType: # examples are in file
        examplesTemp = ExampleUtils.readExamples(examples, False)
        examples = []
        for example in examplesTemp:
            examples.append(example)
            classIds.add(example[1])
    classIds = list(classIds)
    classIds.sort()
    
    #multilabel = MultiLabelMultiClassEvaluator(None, None, classSet)
    #multilabel._calculate(examples, predictions)
    #print multilabel.toStringConcise(title="multilabel")
    
    bestThrF = [0]
    bestBaseF = [0]
    predFileNames = []
    for filename in os.listdir(predictionsDir):
        if "predictions" in filename:
            predFileNames.append( (int(filename.rsplit("_")[-1]), filename) )
    predFileNames.sort()
    for predFileName in predFileNames:
        predictionsTemp = ExampleUtils.loadPredictions(os.path.join(predictionsDir, predFileName[1]))
        predictions = []
        for prediction in predictionsTemp:
            predictions.append(prediction)
    
        baseEv = AveragingMultiClassEvaluator(None, None, classSet)
        baseEv._calculate(examples, predictions)
        print "============================"
        print predFileName[1]
        print "============================"
        #print baseEv.toStringConcise(title="baseline")
        
        baseLineF = baseEv.microF.fscore
        for step in [0]:
            for classId in classIds:
                cls = None
                if classSet != None:
                    cls = classSet.getName(classId)
                else:
                    cls = str(classId)
                bestF = thresholdClass(examples, predictions, classId, baseLineF)
                for prediction in predictions:
                    prediction[classId] += bestF[2][0] + 0.00000001
                changed = 0
                for prediction in predictions:
                    maxVal = -999999
                    maxClass = None
                    for i in range(1, len(prediction)):
                        if prediction[i] > maxVal:
                            maxVal = prediction[i]
                            maxClass = i
                    if maxClass != prediction[0]:
                        prediction[0] = maxClass
                        changed += 1
                print step, cls, "changed", changed, bestF[0]
                baseLineF = bestF[0]
        
        if bestF[0] > bestThrF[0]:
            bestThrF = (bestF[0], predFileName[1], bestF[1], bestF[2], bestF[3])
        if baseEv.microF.fscore > bestBaseF[0]:
            bestBaseF = (baseEv.microF.fscore, predFileName[1], baseEv.microF.toStringConcise())
    
        print "-------- Baseline ------------"
        print baseEv.toStringConcise()
        print "-------- Best ------------"
        print bestF[0], bestF[1], bestF[2]
        print bestF[3]
        thEv = AveragingMultiClassEvaluator(None, None, classSet)
        thEv._calculate(examples, predictions)
        print thEv.toStringConcise()
    
    print "=============== All Best ==============="
    print "Threshold", bestThrF
    print "Base", bestBaseF
    sys.exit()
    
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

if __name__=="__main__":
    import sys, os
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    exampleFilename = "/home/jari/biotext/BioNLP2011/tests/main-tasks/GE/full/fulltest110307/edge-test-examples-split-mccc-preparsed"
    predFilename = "/home/jari/biotext/BioNLP2011/tests/main-tasks/GE/full/fulltest110307/edge-models/"
    classSetFilename = "/home/jari/biotext/BioNLP2011/tests/main-tasks/GE/full/fulltest110307/edge-ids.class_names"

    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\n")
    optparser.add_option("-e", "--examples", default=exampleFilename, dest="examples", help="Input file in csv-format", metavar="FILE")
    optparser.add_option("-p", "--predictions", default=predFilename, dest="predictions", help="Input file in csv-format", metavar="FILE")
    optparser.add_option("-c", "--classes", default=None, dest="classes", help="Input file in csv-format", metavar="FILE")
    (options, args) = optparser.parse_args()
    
    threshold(options.examples, options.predictions, options.classes)
