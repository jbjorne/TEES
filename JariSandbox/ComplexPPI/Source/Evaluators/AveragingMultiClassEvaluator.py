"""
For multi-class classifications
"""
__version__ = "$Revision: 1.23 $"

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
#        self.classSet = classSet
#        if classSet != None:
#            classNames = sorted(classSet.Ids.keys())
#        else:
#            classNames = []

#        # make an ordered list of class ids
#        self.classes = []
#        for className in classNames:
#            self.classes.append(classSet.getId(className))

#        # create data structures for per-class evaluation
#        self.dataByClass = {}
#        for cls in self.classes:
#            self.dataByClass[cls] = EvaluationData()
#        # hack for unnamed classes
#        if len(self.dataByClass) == 0:
#            self.dataByClass[1] = EvaluationData()
#            self.dataByClass[2] = EvaluationData()
        self.dataByClass = defaultdict(EvaluationData)
        
        #self.untypedUndirected = None
        self.untypedCurrentMajorId = None
        self.untypedPredictionQueue = []
        self.untypedUndirected = EvaluationData()
        #self.AUC = None
        if predictions != None:
            self._calculate(examples, predictions)
    
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
        #self.classifications = []
        #assert(len(examples) == len(predictions))
        #for i in range(len(examples)):
        falsePredictions = []
        truePredictions = []
        classes = set()
        for example, prediction in itertools.izip(examples, predictions):
#            self._queueUntypedUndirected(example, prediction)
            #example = examples[i] # examples and predictions are in matching lists
            #prediction = predictions[i] # examples and predictions are in matching lists
            trueClass = example[1]
            assert(trueClass > 0) # multiclass classification uses non-negative integers
            classes.add(trueClass)
            predictedClass = prediction[0]
            #print predictedClass
            assert(predictedClass > 0) # multiclass classification uses non-negative integers
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
                #for cls in self.classes:
                    # this example was correctly classified for its class, 
                    # so it is also correctly classified for each class, 
                    # i.e. true negative for them
                    #if cls != trueClass:
                    #    self.dataByClass[cls].addTN()
                truePredictions.append(trueClass)
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
                        self.binaryF.addTP()
                falsePredictions.append((trueClass, predictedClass))
#                for cls in self.classes:
#                    if cls == trueClass: # example not found -> false negative
#                        self.dataByClass[cls].addFN()
#                    elif cls != predictedClass:
#                        self.dataByClass[cls].addTN()
        # add negatives for other classes
        classes = sorted(list(classes))
        for falsePrediction in falsePredictions:
            for cls in classes:
                if cls == falsePrediction[0]: # example not found -> false negative
                    self.dataByClass[cls].addFN()
                elif cls != falsePrediction[1]:
                    self.dataByClass[cls].addTN()
        for truePrediction in truePredictions:
            for cls in classes:
                if cls != truePrediction:
                    self.dataByClass[cls].addTN()
        
        # Process remaining untyped undirected examples and calculate untyped undirected f-score
#        self._processUntypedUndirectedQueue()
#        self.untypedUndirected.calculateFScore()
                
        # Then calculate statistics
        for cls in self.dataByClass: #self.classes:
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
        for cls in classes:
            if (self.dataByClass[cls].getNumInstances() > 0 or self.dataByClass[cls].getFP() > 0) and cls != self.getNegativeClassId():
                numClassesWithInstances += 1
                self.macroF.precision += self.dataByClass[cls].precision
                self.macroF.recall += self.dataByClass[cls].recall
                if self.dataByClass[cls].fscore != "N/A":
                    self.macroF.fscore += self.dataByClass[cls].fscore
        if numClassesWithInstances > 0:
            if self.macroF.precision != 0: self.macroF.precision /= float(numClassesWithInstances)
            if self.macroF.recall != 0: self.macroF.recall /= float(numClassesWithInstances)
            if self.macroF.fscore != 0: self.macroF.fscore /= float(numClassesWithInstances)            
    
    def getNegativeClassId(self):
        negativeClassId = None
        if self.classSet != None:
            return self.classSet.getId("neg", False)
        else:
            classIds = sorted(self.dataByClass.keys())
            if -1 in classIds:
                negativeClassId = -1
            elif 1 in classIds:
                assert negativeClassId != -1
                negativeClassId = 1
            return negativeClassId
    
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

        negativeClassId = self.getNegativeClassId()
        if self.classSet != None:
            classNames = sorted(self.classSet.Ids.keys())
            for className in classNames:
                if className != "neg":
                    string += className
                    string += " " + self.dataByClass[self.classSet.getId(className, False)].toStringConcise() + "\n" + indent
        else:
            classIds = sorted(self.dataByClass.keys())
            for classId in classIds:
                if classId != negativeClassId:
                    string += str(classId)
                    string += " " + self.dataByClass[classId].toStringConcise() + "\n" + indent
        
        if negativeClassId != None:
            string += "(neg " + self.dataByClass[negativeClassId].toStringConcise() + ")\n" + indent
        
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
        classes = sorted(self.dataByClass.keys())
        if len(classes) > 0 and self.classSet != None:
            assert(not ("1" in self.classSet.getNames() and "neg" in self.classSet.getNames()))
        negativeClassId = self.getNegativeClassId()
        for cls in classes:
            values = self.dataByClass[cls].toDict()
            dicts.append(values)
            if cls != negativeClassId:
                values["class"] = self.classSet.getName(cls)
            else:
                values["class"] = "neg"
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