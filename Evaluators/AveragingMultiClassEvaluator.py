"""
For multi-class classifications
"""
__version__ = "$Revision: 1.24 $"

from Evaluator import Evaluator
from Evaluator import EvaluationData
import sys, os, types
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils
import itertools
from collections import defaultdict

class AveragingMultiClassEvaluator(Evaluator):
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
            classNames = sorted(classSet.Ids.keys())
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
        # hack for unnamed classes
        if len(self.dataByClass) == 0:
            self.dataByClass[1] = EvaluationData()
            self.dataByClass[2] = EvaluationData()
        
        #self.untypedUndirected = None
        self.untypedCurrentMajorId = None
        self.untypedPredictionQueue = []
        self.untypedUndirected = EvaluationData()
        #self.AUC = None
        if predictions != None:
            self._calculate(examples, predictions)
    
    @classmethod
    def evaluate(cls, examples, predictions, classSet=None, outputFile=None, verbose=True):
        """
        Enables using this class without having to manually instantiate it
        """
        evaluator = cls(examples, predictions, classSet)
        if verbose:
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
    
    @classmethod
    def threshold(cls, examples, predictions):
        # Make negative confidence score / true class pairs
        if type(examples) in types.StringTypes:
            examples = ExampleUtils.readExamples(examples, False)
        if type(predictions) in types.StringTypes:
            predictions = ExampleUtils.loadPredictions(predictions)
        pairs = []
        realPositives = 0
        for example, prediction in itertools.izip(examples, predictions):
            trueClass = example[1]
            assert(trueClass > 0) # multiclass classification uses non-negative integers
            if trueClass > 1:
                realPositives += 1
            negClassValue = prediction[1]
            pairs.append( (negClassValue, trueClass) )
        pairs.sort(reverse=True)
        realNegatives = len(pairs) - realPositives
        
        # When starting thresholding, all examples are considered positive
        binaryF = EvaluationData()
        binaryF._tp = realPositives
        binaryF._fp = realNegatives
        binaryF._fn = 0
        binaryF.calculateFScore()
        fscore = binaryF.fscore
        threshold = pairs[0][0]-1.
        
        # Turn one example negative at a time
        for pair in pairs:
            if pair[1] == 1: # the real class is negative
                binaryF._fp -= 1 # false positive -> true negative
            else: # the real class is a positive class
                binaryF._tp -= 1 # true positive -> ...
                binaryF._fn += 1 # ... false negative
            binaryF.calculateFScore()
            if binaryF.fscore > fscore:
                fscore = binaryF.fscore
                threshold = pair[0]+0.00000001
        return threshold, fscore        
    
#    def pool(evaluators):
#        predictions = []
#        for evaluator in evaluators:
#            assert(isinstance(evaluator,AveragingMultiClassEvaluator))
#            predictions.extend(evaluator.predictions)
#        return AveragingMultiClassEvaluator(predictions, evaluators[0].classSet)
#    pool = staticmethod(pool) 
#    
#    def average(evaluators):
#        averageEvaluator = AveragingMultiClassEvaluator(None, None)
#        averageEvaluator.microPrecision = 0
#        averageEvaluator.microRecall = 0
#        averageEvaluator.microFScore = 0
#        averageEvaluator.macroPrecision = 0
#        averageEvaluator.macroRecall = 0
#        averageEvaluator.macroFScore = 0
#        averageEvaluator.truePositives = "-"
#        averageEvaluator.falsePositives = "-"
#        averageEvaluator.trueNegatives = "-"
#        averageEvaluator.falseNegatives = "-"
#        sumWeight = 0.0
#        for evaluator in evaluators:
#            assert(isinstance(evaluator,AveragingMultiClassEvaluator))
#            weight = float(len(evaluator.predictions))
#            sumWeight += weight
#            averageEvaluator.macroPrecision += weight * evaluator.macroPrecision
#            averageEvaluator.macroRecall += weight * evaluator.macroRecall
#            averageEvaluator.macroFScore += weight * evaluator.macroFScore
#            averageEvaluator.microPrecision += weight * evaluator.microPrecision
#            averageEvaluator.microRecall += weight * evaluator.microRecall
#            averageEvaluator.microFScore += weight * evaluator.microFScore
#        averageEvaluator.macroPrecision /= sumWeight
#        averageEvaluator.macroRecall /= sumWeight
#        averageEvaluator.macroFScore /= sumWeight
#        averageEvaluator.microPrecision /= sumWeight
#        averageEvaluator.microRecall /= sumWeight
#        averageEvaluator.microFScore /= sumWeight
#        return averageEvaluator
#    average = staticmethod(average)

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
    
#    def _calculateUntypedUndirected(self, examples, predictions):
#        untypedUndirectedPredictions = []
#        predictionsById = {}
#        for i in range(len(examples)):
#            id = examples[i][0]
#            if id != None and id != "":
#                majorId, minorId = id.rsplit(".x", 1)
#                if not predictionsById.has_key(majorId):
#                    predictionsById[majorId] = {}
#                predictionsById[majorId][int(minorId)] = (examples[i], predictions[i])
#        for majorId in sorted(predictionsById.keys()):
#            prevPrediction = None
#            for minorId in sorted(predictionsById[majorId]):
#                prediction = predictionsById[majorId][minorId]
#                if prevPrediction != None and minorId % 2 != 0:
#                    if prediction[0][1] != 1 or prevPrediction[0][1] != 1:
#                        trueClass = 1
#                    else:
#                        trueClass = -1
#                    if prediction[1][0] != 1 or prevPrediction[1][0] != 1:
#                        predictedClass = 1
#                    else:
#                        predictedClass = -1
#                    untypedUndirectedPredictions.append( ((None,trueClass),predictedClass) )
#                prevPrediction = prediction
#        if len(untypedUndirectedPredictions) > 0:
#            self.untypedUndirected = BinaryEvaluator(untypedUndirectedPredictions)

    def _calculate(self, examples, predictions):
        """
        The actual evaluation
        """
        #self._calculateUntypedUndirected(examples, predictions)
        # First count instances
        self.microF = EvaluationData()
        self.binaryF = EvaluationData()
        self.matrix = defaultdict(lambda:defaultdict(int))
        for classId1 in self.classSet.Ids.values():
            for classId2 in self.classSet.Ids.values():
                self.matrix[classId1][classId2] = 0
        #self.classifications = []
        #assert(len(examples) == len(predictions))
        #for i in range(len(examples)):
        for example, prediction in itertools.izip(examples, predictions):
#            self._queueUntypedUndirected(example, prediction)
            #example = examples[i] # examples and predictions are in matching lists
            #prediction = predictions[i] # examples and predictions are in matching lists
            trueClass = example[1]
            assert(trueClass > 0) # multiclass classification uses non-negative integers
            predictedClass = prediction[0]
            #print predictedClass
            assert(predictedClass > 0) # multiclass classification uses non-negative integers
            self.matrix[trueClass][predictedClass] += 1
            if predictedClass == trueClass: # correct classification
                # correctly classified for its class -> true positive for that class
                self.dataByClass[trueClass].addTP()
                if trueClass != 1: # a non-negative example -> correct = true positive
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
                    if cls != trueClass:
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
                    if trueClass == 1:
                        self.binaryF.addFP()
                    else:
                        self.microF.addFN()
                        self.binaryF.addTP()
                for cls in self.classes:
                    if cls == trueClass: # example not found -> false negative
                        self.dataByClass[cls].addFN()
                    elif cls != predictedClass:
                        self.dataByClass[cls].addTN()
        
        # alternative way for calculating the micro-average (the above loop should give the same result)
        # the micro-average is calculated by micro-averaging all classes except 1 (negative). True positives
        # for class 1 are considered true negatives for the micro-F, but this doesn't really matter, as
        # TN does not affect F.
#        self.microF = EvaluationData()
#        for cls in self.classes:
#            if cls != 1:
#                self.microF.addTP(self.dataByClass[cls].getTP())
#                self.microF.addFP(self.dataByClass[cls].getFP())
#                self.microF.addFN(self.dataByClass[cls].getFN())
#        self.microF.addTN(self.dataByClass[1].getTP())
        
        # Process remaining untyped undirected examples and calculate untyped undirected f-score
#        self._processUntypedUndirectedQueue()
#        self.untypedUndirected.calculateFScore()
                
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
                string += self.classSet.getName(cls)
                string += " " + self.dataByClass[cls].toStringConcise() + "\n" + indent
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
    
    def matrixToString(self, usePercentage=False):
        if usePercentage:
            percentages = defaultdict(lambda:defaultdict(int))
            for key1 in self.matrix:
                total = 0
                for key2 in self.matrix[key1]:
                    total += self.matrix[key1][key2]
                if total == 0:
                    total = 1
                total = float(total)
                for key2 in self.matrix[key1]:
                    percentages[key1][key2] = self.matrix[key1][key2] / total
        
        string = "Error Matrix\n"
        maxKey = len(max([self.classSet.getName(x) for x in self.matrix], key=len))
        string += " " * maxKey + "|"
        for key1 in self.matrix:
            string += self.classSet.getName(key1).ljust(maxKey) + "|"
        string += "\n"
        for key1 in self.matrix:
            keyWidth = len(self.classSet.getName(key1))
            string += self.classSet.getName(key1).ljust(maxKey) + "|"
            for key2 in self.matrix[key1]:
                if usePercentage:
                    string += ('%.2f' % (percentages[key1][key2] * 100.0)).ljust(maxKey) + "|"
                else:
                    string += str(self.matrix[key1][key2]).ljust(maxKey) + "|"
            string += "\n"
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
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    from optparse import OptionParser
    optparser = OptionParser(usage="%prog [options]\nCalculate f-score and other statistics.")
    optparser.add_option("-e", "--examples", default=None, dest="examples", help="", metavar="FILE")
    optparser.add_option("-p", "--predictions", default=None, dest="predictions", help="", metavar="FILE")
    optparser.add_option("-c", "--classSet", default=None, dest="classSet", help="", metavar="FILE")
    (options, args) = optparser.parse_args()
    
    ev = AveragingMultiClassEvaluator(options.examples, options.predictions, options.classSet)
    print ev.toStringConcise()

