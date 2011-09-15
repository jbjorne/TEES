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

def threshold(examples, predictionsDir=None, classSet=None):
    if type(classSet) == types.StringType: # class names are in file
        classSet = IdSet(filename=classSet)
    if type(examples) == types.StringType: # examples are in file
        examples = ExampleUtils.readExamples(examples, False)
    
    #multilabel = MultiLabelMultiClassEvaluator(None, None, classSet)
    #multilabel._calculate(examples, predictions)
    #print multilabel.toStringConcise(title="multilabel")
    
    bestThrF = [0]
    bestBaseF = [0]
    for filename in os.listdir(predictionsDir):
        if "predictions" in filename:
            predictions = ExampleUtils.loadPredictions(os.path.join(predictionsDir, filename))
        
            baseEv = AveragingMultiClassEvaluator(None, None, classSet)
            baseEv._calculate(examples, predictions)
            print "============================"
            print filename
            print "============================"
            #print baseEv.toStringConcise(title="baseline")
            
            ex = []
            for example, prediction in itertools.izip(examples, predictions):
                if prediction[0] == 1:
                    maxNonNegative = -999999
                    maxClass = None
                    cls = 2
                    for val in prediction[2:]:
                        if val > maxNonNegative:
                            maxNonNegative = val
                            maxClass = cls
                        cls += 1
                    distance = prediction[1] - maxNonNegative
                    ex.append((distance, (example[1], prediction[0], maxClass)))
                else:
                    distance = prediction[1] - prediction[prediction[0]] 
                    ex.append((distance, (example[1], prediction[0], 1)))
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
            bestF = [0]
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
            
            if bestF[0] > bestThrF[0]:
                bestThrF = (bestF[0], filename, bestF[1], bestF[2], bestF[3])
            if baseEv.microF.fscore > bestBaseF[0]:
                bestBaseF = (baseEv.microF.fscore, filename, baseEv.microF.toStringConcise())
        
            print "-------- Baseline ------------"
            print baseEv.toStringConcise()
            print "-------- Best ------------"
            print bestF[0], bestF[1], bestF[2]
            print bestF[3]
    
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
    optparser.add_option("-c", "--classes", default=classSetFilename, dest="classes", help="Input file in csv-format", metavar="FILE")
    (options, args) = optparser.parse_args()
    
    threshold(options.examples, options.predictions, options.classes)
