"""
For multi-class classifications
"""
__version__ = "$Revision: 1.3 $"

from Evaluator import Evaluator
from Evaluator import EvaluationData
import sys, os, types
import copy
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
import itertools
import types

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

class MultiLabelEvaluator(Evaluator):
    """
    An evaluator for multiclass classification results, where an example can belong to one
    of several classes. For calculating averages over multiple classes, one of the classes, 
    "neg"/1 is considered to be negative while the others are considered to be different 
    types of positive instances.
    """
    type = "multiclass"
    
    def __init__(self, examples, predictions=None, classSet=None):
        if type(classSet) == types.StringType: # class names are in file
            classSet = IdSet(filename=classSet)
        if type(predictions) == types.StringType: # predictions are in file
            predictions = ExampleUtils.loadPredictions(predictions)
        if type(examples) == types.StringType: # examples are in file
            examples = ExampleUtils.readExamples(examples, False)

        self.classSet = classSet
        # define class ids in alphabetical order
        self.classSet = classSet
        if classSet != None:
            classNames = []
            for className in sorted(classSet.Ids.keys()):
                if "---" not in className:
                    classNames.append(className)
        else:
            classNames = []
        # make an ordered list of class ids
        self.classes = []
        for className in classNames:
            self.classes.append(classSet.getId(className))
        # create data structures for per-class evaluation
        self.dataByClass = {}
        for cls in self.classes:
            self.dataByClass[cls] = EvaluationData()
        
        #self.untypedUndirected = None
        self.untypedCurrentMajorId = None
        self.untypedPredictionQueue = []
        self.untypedUndirected = None # EvaluationData()
        #self.AUC = None
        if predictions != None:
            self._calculate(examples, predictions)
            
        self.thresholds = None
    
    @classmethod
    def evaluate(cls, examples, predictions, classSet=None, outputFile=None):
        """
        Enables using this class without having to manually instantiate it
        """
        evaluator = cls(examples, predictions, classSet)
        print >> sys.stderr, evaluator.toStringConcise()
        if outputFile != None:
            evaluator.saveCSV(outputFile)
        return evaluator

    def compare(self, evaluation):
        if self.microF.fscore > evaluation.microF.fscore:
            return 1
        elif self.microF.fscore == evaluation.microF.fscore:
            return 0
        else:
            return -1
    
    def getData(self):
        return self.microF

    def _queueUntypedUndirected(self, example, prediction):
        """
        All examples within the same majorId (same sentence) are
        put in queue. Once major id (sentence) changes, these
        examples are processed.
        """
        majorId, minorId = example[0].rsplit(".x", 1)
        if majorId != self.untypedCurrentMajorId: # new sentence
            self._processUntypedUndirectedQueue() # process queue
            self.untypedCurrentMajorId = majorId 
        self.untypedPredictionQueue.append( (example, prediction) ) # queue example
    
    def _processUntypedUndirectedQueue(self):
        """
        Determines the untyped undirected performance by merging example
        pairs. This statistic is only meaningful for examples representing
        directed edges where two consecutive examples are the two directed
        edges between a pair of nodes.
        """
        prevExample = None
        prevPrediction = None
        for example, prediction in self.untypedPredictionQueue:
            majorId, minorId = example[0].rsplit(".x", 1)
            if prevExample != None and prevPrediction != None and int(minorId) % 2 != 0:
                # A positive example in either direction counts as a positive
                if example[1] != 1 or prevExample[1] != 1: # 1 is the multiclass "neg" class id
                    trueClass = 1 # binary positive class
                else:
                    trueClass = -1 # binary negative class
                # A positive prediction in either direction counts as a positive
                if prediction[0] != 1 or prevPrediction[0] != 1:
                    predictedClass = 1
                else:
                    predictedClass = -1
                self.untypedUndirected.addInstance(trueClass == 1, predictedClass == 1)
            prevExample = example
            prevPrediction = prediction
        self.untypedPredictionQueue = [] # clear the queue
    
    def determineThreshold(self, examples, predictions):
        if type(predictions) == types.StringType: # predictions are in file
            predictions = ExampleUtils.loadPredictions(predictions)
        if type(examples) == types.StringType: # examples are in file
            examples = ExampleUtils.readExamples(examples, False)
            
        examplesByClass = {}
        for cls in self.classes:
            examplesByClass[cls] = []
        # prepare examples
        for example, prediction in itertools.izip(examples, predictions):
            # Check true class for multilabel
            trueClass = example[1]
            trueClassName = self.classSet.getName(trueClass)
            assert(trueClass > 0) # multiclass classification uses non-negative integers
            if "---" in trueClassName:
                trueClass = set()
                for name in trueClassName.split("---"):
                    trueClass.add(self.classSet.getId(name))
            else:
                trueClass = [trueClass]
            # Check prediction for multilabel
            predictedClasses = prediction[0]
            if type(predictedClasses) == types.IntType:
                predictedClasses = [predictedClasses]
            
            for predType in predictedClasses:
                if predType != 1:
                    exTrueClass = 1
                    if predType in trueClass:
                        exTrueClass = 2
                    examplesByClass[predType].append( (prediction[predType], exTrueClass, 2) )
            # positives are negatives for other classes
            for cls in self.classes:
                if cls not in predictedClasses:
                    exTrueClass = 1
                    if cls in trueClass:
                        exTrueClass = 2
                    examplesByClass[cls].append( (prediction[cls], exTrueClass, 1) )
        # do the thresholding
        thresholdByClass = {}
        for cls in self.classes:
            if cls == 1:
                continue
            thresholdByClass[cls] = 0.0
            examplesByClass[cls].sort()
            # Start with all below zero being negative, and all above it being what is predicted
            ev = EvaluationData()
            for example in examplesByClass[cls]:
                #print example
                if example[0] < 0.0:
                    updateF(ev, example[1], 2, 1) # always negative
                else:
                    updateF(ev, example[1], example[2], 1) # what is predicted
            count = 0
            bestF = [self.dataByClass[cls].fscore, None, (0.0, None), None]
            for example in examplesByClass[cls]:
                if example[0] < 0.0:
                    # Remove original example
                    updateF(ev, example[1], 2, -1)
                    # Add new example
                    updateF(ev, example[1], example[2], 1)
                    # Calculate F for this point
                else:
                    # Remove original example
                    updateF(ev, example[1], example[2], -1)
                    # Add new example
                    updateF(ev, example[1], 1, 1)
                    # Calculate F for this point
                ev.calculateFScore()
                #print example, ev.toStringConcise()
                count += 1
                #if self.classSet.getName(cls) == "Binding":
                #    print count, example, ev.toStringConcise()
                if ev.fscore > bestF[0]:
                    bestF = (ev.fscore, count, example, ev.toStringConcise())
                    self.dataByClass[cls] = copy.copy(ev)
            print >> sys.stderr, "Threshold", self.classSet.getName(cls), bestF
            if bestF[2][0] != 0.0:
                thresholdByClass[cls] = bestF[2][0] + 0.00000001
            else:
                thresholdByClass[cls] = 0.0
        #print thresholdByClass
        self.thresholds = thresholdByClass
        #self._calculate(examples, predictions, thresholdByClass)
        #print >> sys.stderr, "Optimal", self.toStringConcise()
        return thresholdByClass

    def _calculate(self, examples, predictions, thresholds=None):
        """
        The actual evaluation
        """
        for cls in self.classes:
            self.dataByClass[cls] = EvaluationData()
        #self._calculateUntypedUndirected(examples, predictions)
        # First count instances
        self.microF = EvaluationData()
        self.binaryF = EvaluationData()
        #self.classifications = []
        #assert(len(examples) == len(predictions))
        #for i in range(len(examples)):
        
        # Prepare offsets for thresholding
        self.thresholds = thresholds
        offsets = [None] + len(self.classSet.Ids) * [0.0]
        for cls in self.classSet.Ids.keys():
            if thresholds != None and cls in thresholds:
                offsets[cls] = thresholds[cls]
        #print self.classes, offsets
        
        # Calculate results
        for example, prediction in itertools.izip(examples, predictions):
            #self._queueUntypedUndirected(example, prediction)
            # Check true class for multilabel
            trueClass = example[1]
            trueClassName = self.classSet.getName(trueClass)
            assert(trueClass > 0) # multiclass classification uses non-negative integers
            if "---" in trueClassName:
                trueClass = set()
                for name in trueClassName.split("---"):
                    trueClass.add(self.classSet.getId(name))
            else:
                trueClass = [trueClass]
            # Check prediction for multilabel
            predictedClasses = prediction[0]
            if type(predictedClasses) == types.IntType:
                predictedClasses = [predictedClasses]
            # Thresholding
            if thresholds != None:
                for i in range(2, len(prediction)):
                    if prediction[i] != "N/A":
                        if prediction[i] < 0.0 and prediction[i] - offsets[i] > 0.0:
                            if predictedClasses == [1]:
                                predictedClasses = []
                            predictedClasses.append(i)
                        elif prediction[i] > 0.0 and prediction[i] - offsets[i] < 0.0:
                            predictedClasses.remove(i)
                            if len(predictedClasses) == 0:
                                predictedClasses = [1]
                          
            for predictedClass in predictedClasses:
                #print predictedClass
                assert(predictedClass > 0) # multiclass classification uses non-negative integers
                if predictedClass in trueClass: # correct classification
                    # correctly classified for its class -> true positive for that class
                    self.dataByClass[predictedClass].addTP()
                    if predictedClass != 1: # a non-negative example -> correct = true positive
                        #self.classifications.append("tp")
                        #self.classifications.append((prediction[0],"tp",self.type,prediction[1],prediction[3]))
                        self.microF.addTP()
                        self.binaryF.addTP()
                    else: # a negative example -> correct = true negative
                        #self.classifications.append((prediction[0],"tn",self.type,prediction[1],prediction[3]))
                        #self.classifications.append("tn")
                        self.microF.addTN()
                        self.binaryF.addTN()
                    for cls in self.classes:
                        # this example was correctly classified for its class, 
                        # so it is also correctly classified for each class, 
                        # i.e. true negative for them
                        if cls != predictedClass:
                            if cls not in predictedClasses:
                                self.dataByClass[cls].addTN()
                else: # predictedClass != trueClass:
                    # prediction was incorrect -> false positive for the predicted class
                    self.dataByClass[predictedClass].addFP()
                    if predictedClass == 1: # non-negative example, negative prediction -> incorrect = false negative
                        #self.classifications.append("fn")
                        #self.classifications.append((prediction[0],"fn",self.type,prediction[1],prediction[3]))
                        self.microF.addFN()
                        self.binaryF.addFN()
                    else: # non-negative incorrect prediction -> false positive
                        #self.classifications.append("fp")
                        #self.classifications.append((prediction[0],"fp",self.type,prediction[1],prediction[3]))
                        self.microF.addFP()
                        if 1 in trueClass:
                            self.binaryF.addFP()
                        else:
                            self.binaryF.addTP()
                    for cls in self.classes:
                        if cls in trueClass: # example not found -> false negative
                            if cls not in predictedClasses:
                                self.dataByClass[cls].addFN()
                        elif cls != predictedClass:
                            self.dataByClass[cls].addTN()
        
        # Process remaining untyped undirected examples and calculate untyped undirected f-score
        #self._processUntypedUndirectedQueue()
        #self.untypedUndirected.calculateFScore()
                
        # Then calculate statistics
        for cls in self.classes:
            self.dataByClass[cls].calculateFScore()
        self.microF.calculateFScore()
        self.binaryF.calculateFScore()
        
        # Finally calculate macro-f-score
        # macro-average is simply the unweighted average of per-class f-scores
        numClassesWithInstances = 0
        self.macroF = EvaluationData()
        self.macroF.precision = 0.0
        self.macroF.recall = 0.0
        self.macroF.fscore = 0.0
        for cls in self.classes:
            if (self.dataByClass[cls].getNumInstances() > 0 or self.dataByClass[cls].getFP() > 0) and cls != self.classSet.getId("neg", False):
                numClassesWithInstances += 1
                self.macroF.precision += self.dataByClass[cls].precision
                self.macroF.recall += self.dataByClass[cls].recall
                if self.dataByClass[cls].fscore != "N/A":
                    self.macroF.fscore += self.dataByClass[cls].fscore
        if numClassesWithInstances > 0:
            if self.macroF.precision != 0: self.macroF.precision /= float(numClassesWithInstances)
            if self.macroF.recall != 0: self.macroF.recall /= float(numClassesWithInstances)
            if self.macroF.fscore != 0: self.macroF.fscore /= float(numClassesWithInstances)            
    
    def toStringConcise(self, indent="", title=None):
        """
        Evaluation results in a human readable string format
        """
        if title != None:
            string = indent + title + "\n"
            indent += " "
            string += indent
        else:
            string = indent
        negativeClassId = None
        for cls in self.classes:
            if cls != self.classSet.getId("neg", False):
                tString = ""
                if self.thresholds != None and cls in self.thresholds:
                    tString = " t:" + str(self.thresholds[cls])
                string += self.classSet.getName(cls)
                string += " " + self.dataByClass[cls].toStringConcise() + tString + "\n" + indent
            else:
                negativeClassId = cls
        if negativeClassId != None:
            cls = negativeClassId
            string += "(neg " + self.dataByClass[cls].toStringConcise() + ")\n" + indent
        
        string += "averages:\n" + indent
        # Micro results
        string += "micro " + self.microF.toStringConcise() + "\n" + indent
        # Macro results
        string += "macro " + self.macroF.prfToString() + "\n" + indent
        # Binary results
        string += "untyped " + self.binaryF.toStringConcise()
        # Untyped undirected results
        if self.untypedUndirected != None:
            string += "\n" + indent
            string += "untyped undirected " + self.untypedUndirected.toStringConcise()
        return string
    
#    def __addClassToCSV(self, csvWriter, cls):
#        values = []        
#        values.append( self.classSet.getName(cls) )
#        values.append( self.truePositivesByClass[cls]+self.falseNegativesByClass[cls] )
#        values.append( self.trueNegativesByClass[cls]+self.falsePositivesByClass[cls] )
#        values.append(self.truePositivesByClass[cls])
#        values.append(self.falsePositivesByClass[cls])
#        values.append(self.trueNegativesByClass[cls])
#        values.append(self.falseNegativesByClass[cls])
#        if self.instancesByClass[cls] > 0 or self.falsePositivesByClass[cls] > 0:
#            values.append(self.precisionByClass[cls])
#            values.append(self.recallByClass[cls])
#            values.append(self.fScoreByClass[cls])
#        else:
#            values.extend(["N/A","N/A","N/A"])
#        csvWriter.writerow(values)       
#

    def toDict(self):
        """
        Evaluation results in a computationally easy to process dictionary format
        """
        dicts = []
        if len(self.classes) > 0:
            assert(not ("1" in self.classSet.getNames() and "neg" in self.classSet.getNames()))
        negativeClassId = None
        for cls in self.classes:
            if cls != self.classSet.getId("neg", False) and cls != self.classSet.getId("1", False):
                values = self.dataByClass[cls].toDict()
                values["class"] = self.classSet.getName(cls)
                dicts.append(values)
            else:
                assert(negativeClassId == None)
                negativeClassId = cls
        if negativeClassId != None:
            values = self.dataByClass[negativeClassId].toDict()
            values["class"] = "neg"
            dicts.append(values)
        dicts.append( self.microF.toDict() )
        dicts[-1]["class"] = "micro"
        dicts.append( self.macroF.toDict() )
        dicts[-1]["class"] = "macro"
        dicts.append( self.binaryF.toDict() )
        dicts[-1]["class"] = "untyped"
        if self.untypedUndirected != None:
            dicts.append(self.untypedUndirected.toDict())
            dicts[-1]["class"] = "untyped undirected"
        return dicts
    
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
    
    ev = MultiLabelEvaluator(options.examples, options.predictions, classSet=options.classes)
    #ev.determineThreshold(exampleFilename, predFilename)
    #ev._calculate()
    print ev.toStringConcise()
    print ev.determineThreshold(options.examples, options.predictions)