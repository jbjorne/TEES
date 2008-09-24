def averageEvaluations(evaluations):
    average = Evaluation(None)
    average.precision = 0
    average.recall = 0
    average.fScore = 0
    average.truePositives = "-"
    average.falsePositives = "-"
    average.trueNegatives = "-"
    average.falseNegatives = "-"
    sumWeight = 0.0
    precisions = []
    recalls = []
    fScores = []
    for evaluation in evaluations:
        weight = float(len(evaluation.predictions))
        sumWeight += weight
        average.precision += weight * evaluation.precision
        average.recall += weight * evaluation.recall
        average.fScore += weight * evaluation.fScore
        precisions.append(evaluation.precision)
        recalls.append(evaluation.recall)
        fScores.append(evaluation.fScore)
    average.precision /= sumWeight
    average.recall /= sumWeight
    average.fScore /= sumWeight
    return average

class Evaluation:
    def __init__(self, predictions, classSet=None):
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
            self.__calculate(predictions)
    
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
        auc /= float(numPositiveExamples * numNegativeExamples)
        return auc
    
    def __calculate(self, predictions):
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
            string = indent + Title + ": "
        else:
            string = indent
        string += "p/n:" + str(self.truePositives+self.falseNegatives) + "/" + str(self.trueNegatives+self.falsePositives)
        string += " tp/fp|tn/fn:" + str(self.truePositives) + "/" + str(self.falsePositives) + "|" + str(self.trueNegatives) + "/" + str(self.falseNegatives)
        if self.AUC != None:
            string += " p/r/f/a:" + str(self.precision)[0:6] + "/" + str(self.recall)[0:6] + "/" + str(self.fScore)[0:6] + "/" + str(self.AUC)[0:6]
        else:
            string += " p/r/f:" + str(self.precision)[0:6] + "/" + str(self.recall)[0:6] + "/" + str(self.fScore)[0:6]            
        return string