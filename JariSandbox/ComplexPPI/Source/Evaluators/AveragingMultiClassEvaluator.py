from Evaluator import Evaluator
from BinaryEvaluator import BinaryEvaluator
import sys, os, types
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
from Core.IdSet import IdSet
import Core.ExampleUtils as ExampleUtils

def run(examples, predictions, classSet=None, outputFile=None):
    if type(classSet) == types.StringType: # class names are in file
        classSet = IdSet(filename=classSet)
    if type(predictions) == types.StringType: # predictions are in file
        predictions = ExampleUtils.loadPredictions(predictions, examples)
    evaluator = AveragingMultiClassEvaluator(predictions, classSet)
    print >> sys.stderr, evaluator.toStringConcise()
    if outputFile != None:
        evaluator.saveCSV(outputFile)
    return evaluator

class AveragingMultiClassEvaluator(Evaluator):
    def __init__(self, predictions=None, classSet=None):
        self.predictions = predictions
        self.truePositivesByClass = {}
        self.falsePositivesByClass = {}
        self.trueNegativesByClass = {}
        self.falseNegativesByClass = {}
        self.precisionByClass = {}
        self.recallByClass = {}
        self.fScoreByClass = {}
        self.classSet = classSet
        # define class ids in alphabetical order
        self.classSet = classSet
        if classSet != None:
            classNames = classSet.Ids.keys()
        else:
            classNames = []
        classNames.sort()
        self.classes = []
        for className in classNames:
            self.classes.append(classSet.getId(className))
        self.instancesByClass = {}
        #print self.classes
        for cls in self.classes:
            self.truePositivesByClass[cls] = 0
            self.falsePositivesByClass[cls] = 0
            self.trueNegativesByClass[cls] = 0
            self.falseNegativesByClass[cls] = 0
            self.precisionByClass[cls] = 0
            self.recallByClass[cls] = 0
            self.fScoreByClass[cls] = 0
            self.instancesByClass[cls] = 0

        self.macroPrecision = 0
        self.macroRecall = 0
        self.macroFScore = 0
        
        self.microTP = 0
        self.microFP = 0
        self.microTN = 0
        self.microFN = 0
        self.microPrecision = 0
        self.microRecall = 0
        self.microFScore = 0
        
        self.binaryTP = 0
        self.binaryFP = 0
        self.binaryTN = 0
        self.binaryFN = 0
        self.binaryPrecision = 0
        self.binaryRecall = 0
        self.binaryFScore = 0
        
        self.untypedUndirected = None

        #self.AUC = None
        self.type = "multiclass"
        if predictions != None:
            self._calculate(predictions)

    def compare(self, evaluation):
        if self.microFScore > evaluation.microFScore:
            return 1
        elif self.microFScore == evaluation.microFScore:
            return 0
        else:
            return -1
    
    def pool(evaluators):
        predictions = []
        for evaluator in evaluators:
            assert(isinstance(evaluator,AveragingMultiClassEvaluator))
            predictions.extend(evaluator.predictions)
        return AveragingMultiClassEvaluator(predictions, evaluators[0].classSet)
    pool = staticmethod(pool) 
    
    def average(evaluators):
        averageEvaluator = AveragingMultiClassEvaluator(None, None)
        averageEvaluator.microPrecision = 0
        averageEvaluator.microRecall = 0
        averageEvaluator.microFScore = 0
        averageEvaluator.macroPrecision = 0
        averageEvaluator.macroRecall = 0
        averageEvaluator.macroFScore = 0
        averageEvaluator.truePositives = "-"
        averageEvaluator.falsePositives = "-"
        averageEvaluator.trueNegatives = "-"
        averageEvaluator.falseNegatives = "-"
        sumWeight = 0.0
        for evaluator in evaluators:
            assert(isinstance(evaluator,AveragingMultiClassEvaluator))
            weight = float(len(evaluator.predictions))
            sumWeight += weight
            averageEvaluator.macroPrecision += weight * evaluator.macroPrecision
            averageEvaluator.macroRecall += weight * evaluator.macroRecall
            averageEvaluator.macroFScore += weight * evaluator.macroFScore
            averageEvaluator.microPrecision += weight * evaluator.microPrecision
            averageEvaluator.microRecall += weight * evaluator.microRecall
            averageEvaluator.microFScore += weight * evaluator.microFScore
        averageEvaluator.macroPrecision /= sumWeight
        averageEvaluator.macroRecall /= sumWeight
        averageEvaluator.macroFScore /= sumWeight
        averageEvaluator.microPrecision /= sumWeight
        averageEvaluator.microRecall /= sumWeight
        averageEvaluator.microFScore /= sumWeight
        return averageEvaluator
    average = staticmethod(average)
    
    def _calculateUntypedUndirected(self, predictions):
        untypedUndirectedPredictions = []
        predictionsById = {}
        for prediction in predictions:
            id = prediction[0][0]
            if id != None and id != "":
                majorId, minorId = id.rsplit(".x", 1)
                if not predictionsById.has_key(majorId):
                    predictionsById[majorId] = {}
                predictionsById[majorId][int(minorId)] = prediction
        for majorId in sorted(predictionsById.keys()):
            prevPrediction = None
            for minorId in sorted(predictionsById[majorId]):
                prediction = predictionsById[majorId][minorId]
                if prevPrediction != None and minorId % 2 != 0:
                    if prediction[0][1] != 1 or prevPrediction[0][1] != 1:
                        trueClass = 1
                    else:
                        trueClass = -1
                    if prediction[1] != 1 or prevPrediction[1] != 1:
                        predictedClass = 1
                    else:
                        predictedClass = -1
                    untypedUndirectedPredictions.append( ((None,trueClass),predictedClass) )
                prevPrediction = prediction
        if len(untypedUndirectedPredictions) > 0:
            self.untypedUndirected = BinaryEvaluator(untypedUndirectedPredictions)
        
    def _calculate(self, predictions):
        self._calculateUntypedUndirected(predictions)
        # First count instances
        self.microTP = 0
        self.microFP = 0
        self.microTN = 0
        self.microFN = 0
        self.classifications = []
        for prediction in predictions:
            trueClass = prediction[0][1]
            self.instancesByClass[trueClass] += 1
            assert(trueClass > 0)
            predictedClass = prediction[1]
            #print predictedClass
            assert(predictedClass > 0)
            if predictedClass == trueClass:
                self.truePositivesByClass[trueClass] += 1
                if trueClass != 1:
                    self.classifications.append((prediction[0],"tp",self.type,prediction[1],prediction[3]))
                    self.microTP += 1
                    self.binaryTP += 1
                else:
                    self.classifications.append((prediction[0],"tn",self.type,prediction[1],prediction[3]))
                    self.microTN += 1
                    self.binaryTN += 1
                for cls in self.classes:
                    if cls != trueClass:
                        self.trueNegativesByClass[cls] += 1
            elif predictedClass != trueClass:
                self.falsePositivesByClass[predictedClass] += 1
                if predictedClass == 1:
                    self.classifications.append((prediction[0],"fn",self.type,prediction[1],prediction[3]))
                    self.microFN += 1
                    self.binaryFN += 1
                else:
                    self.classifications.append((prediction[0],"fp",self.type,prediction[1],prediction[3]))
                    self.microFP += 1
                    if trueClass == 1:
                        self.binaryFP += 1
                    else:
                        self.binaryTP += 1
                for cls in self.classes:
                    if cls == trueClass:
                        self.falseNegativesByClass[cls] += 1
                    elif cls != predictedClass:
                        self.trueNegativesByClass[cls] += 1
                
        # Then calculate statistics
        for cls in self.classes:
            totalPositives = float(self.truePositivesByClass[cls] + self.falsePositivesByClass[cls])
            if totalPositives > 0.0:
                self.precisionByClass[cls] = float(self.truePositivesByClass[cls]) / totalPositives
            else:
                self.precisionByClass[cls] = 0.0
            realPositives = float(self.truePositivesByClass[cls] + self.falseNegativesByClass[cls])
            if realPositives > 0.0:
                self.recallByClass[cls] = float(self.truePositivesByClass[cls]) / realPositives
            else:
                self.recallByClass[cls] = 0.0
            if self.precisionByClass[cls] + self.recallByClass[cls] > 0.0:
                self.fScoreByClass[cls] = (2*self.precisionByClass[cls]*self.recallByClass[cls]) / (self.precisionByClass[cls] + self.recallByClass[cls])
            else:
                self.fScoreByClass[cls] = 0.0
        
        # Calculate micro-f-score
#        totalWeight = 0.0
#        for cls in self.classes:
#            if cls != self.classSet.getId("neg", False):
#                if self.instancesByClass[cls] > 0 or self.falsePositivesByClass[cls] > 0:
#                    self.microTP += self.truePositivesByClass[cls]
#                    self.microTN += self.trueNegativesByClass[cls]
#                    self.microFP += self.falsePositivesByClass[cls]
#                    self.microFN += self.falseNegativesByClass[cls]
#                weigth = self.instancesByClass[cls]
#                self.microPrecision += weigth * self.precisionByClass[cls]
#                self.microRecall += weigth * self.recallByClass[cls]
#                self.microFScore += weigth * self.fScoreByClass[cls]
#                totalWeight += float(weigth)
#        if totalWeight != 0.0:
#            if self.microPrecision != 0: self.microPrecision /= totalWeight
#            if self.microRecall != 0: self.microRecall /= totalWeight
#            if self.microFScore != 0: self.microFScore /= totalWeight
        if self.microTP + self.microFP > 0:
            self.microPrecision = float(self.microTP) / float(self.microTP + self.microFP)
        if self.microTP + self.microFN > 0:
            self.microRecall = float(self.microTP) / float(self.microTP + self.microFN)
        if self.microPrecision + self.microRecall > 0.0:
            self.microFScore = (2*self.microPrecision*self.microRecall) / (self.microPrecision + self.microRecall)

        if self.binaryTP + self.binaryFP > 0:
            self.binaryPrecision = float(self.binaryTP) / float(self.binaryTP + self.binaryFP)
        if self.binaryTP + self.binaryFN > 0:
            self.binaryRecall = float(self.binaryTP) / float(self.binaryTP + self.binaryFN)
        if self.binaryPrecision + self.binaryRecall > 0.0:
            self.binaryFScore = (2*self.binaryPrecision*self.binaryRecall) / (self.binaryPrecision + self.binaryRecall)
        
        # Finally calculate macro-f-score
        numClassesWithInstances = 0
        for cls in self.classes:
            if (self.instancesByClass[cls] > 0 or self.falsePositivesByClass[cls] > 0) and cls != self.classSet.getId("neg", False):
                numClassesWithInstances += 1
                self.macroPrecision += self.precisionByClass[cls]
                self.macroRecall += self.recallByClass[cls]
                self.macroFScore += self.fScoreByClass[cls]
        if numClassesWithInstances > 0:
            if self.macroPrecision != 0: self.macroPrecision /= float(numClassesWithInstances)
            if self.macroRecall != 0: self.macroRecall /= float(numClassesWithInstances)
            if self.macroFScore != 0: self.macroFScore /= float(numClassesWithInstances)            
    
    def toStringConcise(self, indent="", title=None):
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
                string += " p/n:" + str(self.truePositivesByClass[cls]+self.falseNegativesByClass[cls]) + "/" + str(self.trueNegativesByClass[cls]+self.falsePositivesByClass[cls])
                string += " tp/fp|tn/fn:" + str(self.truePositivesByClass[cls]) + "/" + str(self.falsePositivesByClass[cls]) + "|" + str(self.trueNegativesByClass[cls]) + "/" + str(self.falseNegativesByClass[cls])
                if self.instancesByClass[cls] > 0 or self.falsePositivesByClass[cls] > 0:
                    string += " p/r/f:" + str(self.precisionByClass[cls])[0:6] + "/" + str(self.recallByClass[cls])[0:6] + "/" + str(self.fScoreByClass[cls])[0:6]
                else:
                    string += " p/r/f:N/A"
                string += "\n" + indent
            else:
                negativeClassId = cls
        if negativeClassId != None:
            cls = negativeClassId
            string += "(neg"
            string += " p/n:" + str(self.truePositivesByClass[cls]+self.falseNegativesByClass[cls]) + "/" + str(self.trueNegativesByClass[cls]+self.falsePositivesByClass[cls])
            string += " tp/fp|tn/fn:" + str(self.truePositivesByClass[cls]) + "/" + str(self.falsePositivesByClass[cls]) + "|" + str(self.trueNegativesByClass[cls]) + "/" + str(self.falseNegativesByClass[cls])
            string += " p/r/f:" + str(self.precisionByClass[cls])[0:6] + "/" + str(self.recallByClass[cls])[0:6] + "/" + str(self.fScoreByClass[cls])[0:6]
            string += ")\n" + indent
        
        string += "averages:\n" + indent
        # Micro results
        string += "micro p/n:" + str(self.microTP+self.microFN) + "/" + str(self.microTN+self.microFP)
        string += " tp/fp|tn/fn:" + str(self.microTP) + "/" + str(self.microFP) + "|" + str(self.microTN) + "/" + str(self.microFN)
        string += " p/r/f:" + str(self.microPrecision)[0:6] + "/" + str(self.microRecall)[0:6] + "/" + str(self.microFScore)[0:6]
        string += "\n" + indent
        # Macro results
        string += "macro p/r/f:" + str(self.macroPrecision)[0:6] + "/" + str(self.macroRecall)[0:6] + "/" + str(self.macroFScore)[0:6]
        string += "\n" + indent
        # Binary results
        string += "untyped p/n:" + str(self.binaryTP+self.binaryFN) + "/" + str(self.binaryTN+self.binaryFP)
        string += " tp/fp|tn/fn:" + str(self.binaryTP) + "/" + str(self.binaryFP) + "|" + str(self.binaryTN) + "/" + str(self.binaryFN)
        string += " p/r/f:" + str(self.binaryPrecision)[0:6] + "/" + str(self.binaryRecall)[0:6] + "/" + str(self.binaryFScore)[0:6]
        string += "\n" + indent
        if self.untypedUndirected != None:
            string += self.untypedUndirected.toStringConcise("untyped undirected ") + "\n"
        return string
    
    def __addClassToCSV(self, csvWriter, cls):
        values = []        
        values.append( self.classSet.getName(cls) )
        values.append( self.truePositivesByClass[cls]+self.falseNegativesByClass[cls] )
        values.append( self.trueNegativesByClass[cls]+self.falsePositivesByClass[cls] )
        values.append(self.truePositivesByClass[cls])
        values.append(self.falsePositivesByClass[cls])
        values.append(self.trueNegativesByClass[cls])
        values.append(self.falseNegativesByClass[cls])
        if self.instancesByClass[cls] > 0 or self.falsePositivesByClass[cls] > 0:
            values.append(self.precisionByClass[cls])
            values.append(self.recallByClass[cls])
            values.append(self.fScoreByClass[cls])
        else:
            values.extend(["N/A","N/A","N/A"])
        csvWriter.writerow(values)       

    def __getClassDict(self, cls):
        values = {}        
        values["class"] = self.classSet.getName(cls)
        values["positives"] = self.truePositivesByClass[cls]+self.falseNegativesByClass[cls]
        values["negatives"] = self.trueNegativesByClass[cls]+self.falsePositivesByClass[cls]
        values["true positives"] = self.truePositivesByClass[cls]
        values["false positives"] = self.falsePositivesByClass[cls]
        values["true negatives"] = self.trueNegativesByClass[cls]
        values["false negatives"] = self.falseNegativesByClass[cls]
        if self.instancesByClass[cls] > 0 or self.falsePositivesByClass[cls] > 0:
            values["precision"] = self.precisionByClass[cls]
            values["recall"] = self.recallByClass[cls]
            values["f-score"] = self.fScoreByClass[cls]
        else:
            values["precision"] = "N/A"
            values["recall"] = "N/A"
            values["f-score"] = "N/A"
        values["AUC"] = "N/A"
        return values
    
#    def saveCSV(self, filename):
#        import csv
#        csvFile = open(filename, "wb")        
#        writer = csv.writer(csvFile)
#        writer.writerow(["class","positives","negatives","true positives","false positives","true negatives","false negatives","precision","recall","f-score"])
#        negativeClassId = None
#        for cls in self.classes:
#            if cls != self.classSet.getId("neg", False):
#                self.__addClassToCSV(writer, cls)
#            else:
#                negativeClassId = cls
#        if negativeClassId != None:
#            self.__addClassToCSV(writer, negativeClassId)
#        # add averages
#        writer.writerow(["micro",self.microTP+self.microFN,self.microTN+self.microFP,self.microTP,self.microFP,self.microTN,self.microFN,self.microPrecision,self.microRecall,self.microFScore])
#        writer.writerow(["macro","N/A","N/A","N/A","N/A","N/A","N/A",self.macroPrecision,self.macroRecall,self.macroFScore])
#        writer.writerow(["binary",self.binaryTP+self.binaryFN,self.binaryTN+self.binaryFP,self.binaryTP,self.binaryFP,self.binaryTN,self.binaryFN,self.binaryPrecision,self.binaryRecall,self.binaryFScore])
#        csvFile.close()
    
    def toDict(self):
        dicts = []
        if len(self.classes) > 0:
            assert(not ("1" in self.classSet.getNames() and "neg" in self.classSet.getNames()))
        negativeClassId = None
        for cls in self.classes:
            if cls != self.classSet.getId("neg", False) and cls != self.classSet.getId("1", False):
                dicts.append(self.__getClassDict(cls))
            else:
                assert(negativeClassId == None)
                negativeClassId = cls
        if negativeClassId != None:
            dicts.append(self.__getClassDict(negativeClassId))
        dicts.append({"class":"micro","positives":self.microTP+self.microFN,"negatives":self.microTN+self.microFP,"true positives":self.microTP,"false positives":self.microFP,"true negatives":self.microTN,"false negatives":self.microFN,"precision":self.microPrecision,"recall":self.microRecall,"f-score":self.microFScore,"AUC":"N/A"})
        dicts.append({"class":"macro","positives":"N/A","negatives":"N/A","true positives":"N/A","false positives":"N/A","true negatives":"N/A","false negatives":"N/A","precision":self.macroPrecision,"recall":self.macroRecall,"f-score":self.macroFScore,"AUC":"N/A"})
        dicts.append({"class":"untyped","positives":self.binaryTP+self.binaryFN,"negatives":self.binaryTN+self.binaryFP,"true positives":self.binaryTP,"false positives":self.binaryFP,"true negatives":self.binaryTN,"false negatives":self.binaryFN,"precision":self.binaryPrecision,"recall":self.binaryRecall,"f-score":self.binaryFScore,"AUC":"N/A"})
        if self.untypedUndirected != None:
            dicts.extend(self.untypedUndirected.toDict())
            dicts[-1]["class"] = "untyped undirected"
        return dicts