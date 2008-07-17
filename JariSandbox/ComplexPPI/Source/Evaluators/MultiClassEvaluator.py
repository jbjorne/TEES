class MultiClassEvaluator:
    def __init__(self, predictions):
        self.predictions = predictions
        self.truePositives = 0
        self.falsePositives = 0
        self.trueNegatives = 0
        self.falseNegatives = 0
        self.precision = None
        self.recall = None
        self.fScore = None
        #self.AUC = None
        self.type = "multiclass"
        self.__calculate(predictions)
    
    def __calculate(self, predictions):
        # First count instances
        self.classifications = []
        for prediction in predictions:
            trueClass = prediction[0][1]
            assert(trueClass > 0)
            predictedClass = prediction[1]
            assert(predictedClass > 0)
            if trueClass != 1:
                if predictedClass == trueClass:
                    self.truePositives += 1
                    self.classifications.append((prediction[0],"tp",self.type))
                elif predictedClass == 1:
                    self.falseNegatives += 1
                    self.classifications.append((prediction[0],"fn",self.type))
                else:
                    self.falsePositives += 1
                    self.classifications.append((prediction[0],"fp",self.type))
            else:
                if predictedClass == 1:
                    self.trueNegatives += 1
                    self.classifications.append((prediction[0],"tn",self.type))
                elif predictedClass != 1:
                    self.falsePositives += 1
                    self.classifications.append((prediction[0],"fp",self.type))
                
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
    
    def toStringConcise(self):
        string = "p/n:" + str(self.truePositives+self.falseNegatives) + "/" + str(self.trueNegatives+self.falsePositives)
        string += " tp/fp|tn/fn:" + str(self.truePositives) + "/" + str(self.falsePositives) + "|" + str(self.trueNegatives) + "/" + str(self.falseNegatives)
        string += " p/r/f:" + str(self.precision)[0:6] + "/" + str(self.recall)[0:6] + "/" + str(self.fScore)[0:6]
        return string