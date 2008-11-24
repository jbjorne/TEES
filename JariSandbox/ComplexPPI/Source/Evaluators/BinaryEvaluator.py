import Evaluator

class BinaryEvaluator(Evaluator.Evaluator):
    def __init__(self, predictions=None, classSet=None):
        self.predictions = predictions
        self.truePositives = 0
        self.falsePositives = 0
        self.trueNegatives = 0
        self.falseNegatives = 0
        self.precision = None
        self.recall = None
        self.fScore = None
        self.AUC = None
        self.type = "binary"
        if predictions != None:
            self._calculate(predictions)
    
    def compare(self, evaluation):
        if self.fScore > evaluation.fScore:
            return 1
        elif self.fScore == evaluation.fScore:
            return 0
        else:
            return -1
    
    def average(evaluators):
        averageEvaluator = BinaryEvaluator(None)
        averageEvaluator.precision = 0
        averageEvaluator.recall = 0
        averageEvaluator.fScore = 0
        averageEvaluator.AUC = 0
        averageEvaluator.truePositives = "-"
        averageEvaluator.falsePositives = "-"
        averageEvaluator.trueNegatives = "-"
        averageEvaluator.falseNegatives = "-"
        sumWeight = 0.0
        for evaluator in evaluators:
            assert(isinstance(evaluator,BinaryEvaluator))
            weight = float(len(evaluator.predictions))
            sumWeight += weight
            averageEvaluator.precision += weight * evaluator.precision
            averageEvaluator.recall += weight * evaluator.recall
            averageEvaluator.fScore += weight * evaluator.fScore
            if evaluator.AUC != None:
                averageEvaluator.AUC += weight * evaluator.AUC
        if averageEvaluator.AUC > 0:
            averageEvaluator.AUC /= sumWeight
        else:
            averageEvaluator.AUC = None
        if sumWeight > 0:
            averageEvaluator.precision /= sumWeight
            averageEvaluator.recall /= sumWeight
            averageEvaluator.fScore /= sumWeight
        return averageEvaluator
    average = staticmethod(average)
    
    def pool(evaluators):
        predictions = []
        for evaluator in evaluators:
            assert(isinstance(evaluator,BinaryEvaluator))
            predictions.extend(evaluator.predictions)
        return BinaryEvaluator(predictions)
    pool = staticmethod(pool)      
    
    def __calculateAUC(self, predictions):
        numPositiveExamples = 0
        numNegativeExamples = 0
        predictionsForPositives = []
        predictionsForNegatives = []
        for prediction in predictions:
            trueClass = prediction[0][1]
            predictedClass = prediction[1]
            if trueClass > 0:
                numPositiveExamples += 1
                if predictedClass > 0:
                    predictionsForPositives.append(1)
                else:
                    predictionsForPositives.append(0)
            else:
                numNegativeExamples += 1
                if predictedClass > 0:
                    predictionsForNegatives.append(1)
                else:
                    predictionsForNegatives.append(0)
        auc = 0
        for i in predictionsForPositives:
           for j in predictionsForNegatives:
               if i > j:
                   auc += 1.
               elif i == j:
                   auc += 0.5
        if numPositiveExamples * numNegativeExamples > 0:
            auc /= float(numPositiveExamples * numNegativeExamples)
        else:
            auc = 0
        return auc
    
    def _calculate(self, predictions):
        # First count instances
        self.classifications = []
        for prediction in predictions:
            trueClass = prediction[0][1]
            predictedClass = prediction[1]
            if trueClass > 0:
                if predictedClass > 0:
                    self.truePositives += 1
                    self.classifications.append((prediction[0],"tp",self.type))
                else:
                    self.falseNegatives += 1
                    self.classifications.append((prediction[0],"fn",self.type))
            else:
                if predictedClass > 0:
                    self.falsePositives += 1
                    self.classifications.append((prediction[0],"fp",self.type))
                else:
                    self.trueNegatives += 1
                    self.classifications.append((prediction[0],"tn",self.type))
        # Then calculate statistics
        totalPositives = float(self.truePositives + self.falsePositives)
        if totalPositives > 0.0:
            self.precision = float(self.truePositives) / totalPositives
        else:
            self.precision = 0.0
        realPositives = float(self.truePositives + self.falseNegatives)
        if realPositives > 0.0:
            self.recall = float(self.truePositives) / realPositives
        else:
            self.recall = 0.0
        if self.precision + self.recall > 0.0:
            self.fScore = (2*self.precision*self.recall) / (self.precision + self.recall)
        else:
            self.fScore = 0.0
        
        self.AUC = self.__calculateAUC(predictions)
    
    def toStringConcise(self, indent="", title=None):
        if title != None:
            string = indent + title + ": "
        else:
            string = indent
        string += "p/n:" + str(self.truePositives+self.falseNegatives) + "/" + str(self.trueNegatives+self.falsePositives)
        string += " tp/fp|tn/fn:" + str(self.truePositives) + "/" + str(self.falsePositives) + "|" + str(self.trueNegatives) + "/" + str(self.falseNegatives)
        string += " p/r/f:" + str(self.precision)[0:6] + "/" + str(self.recall)[0:6] + "/" + str(self.fScore)[0:6]            
        if self.AUC != None:
            string += " a:" + str(self.AUC)[0:6]
        else:
            string += " a:N/A"
        return string
    
#    def saveCSV(self, filename, fold=None):
##        import csv
##        csvFile = open(filename, "wb")        
##        writer = csv.writer(csvFile)
##        writer.writerow(["positives","negatives","true positives","false positives","true negatives","false negatives","precision","recall","f-score","AUC"])
##        values = [self.truePositives+self.falseNegatives,self.trueNegatives+self.falsePositives,self.truePositives,self.falsePositives,self.trueNegatives,self.falseNegatives,self.precision,self.recall,self.fScore]
##        if self.AUC != None:
##            values.append(self.AUC)
##        else:
##            values.append("N/A")
##        writer.writerow(values)
##        csvFile.close()
#        import sys
#        sys.path.append("..")
#        import Utils.TableUtils as TableUtils
#        dicts = self.toDict()
#        if fold != None:
#            dicts[0]["fold"] = fold
#        TableUtils.addToCSV(dicts, filename, Evaluator.g_evaluatorFieldnames)
    
    def toDict(self):
        dict = {}
        dict["positives"] = self.truePositives+self.falseNegatives
        dict["negatives"] = self.trueNegatives+self.falsePositives
        dict["true positives"] = self.truePositives
        dict["false positives"] = self.falsePositives
        dict["true negatives"] = self.trueNegatives
        dict["false negatives"] = self.falseNegatives 
        dict["precision"] = self.precision
        dict["recall"] = self.recall
        dict["f-score"] = self.fScore
        if self.AUC != None:
            dict["AUC"] = self.AUC
        else:
            dict["AUC"] = "N/A"
        return [dict]
    