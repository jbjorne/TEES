class AveragingMultiClassEvaluator:
    def __init__(self, predictions, classSet=None):
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
        classNames = classSet.Ids.keys()
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

        self.precision = 0
        self.recall = 0
        self.fScore = 0
        
        self.microPrecision = 0
        self.microRecall = 0
        self.microFScore = 0

        #self.AUC = None
        self.type = "multiclass"
        self.__calculate(predictions)
    
    def __calculate(self, predictions):
        # First count instances
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
                    self.classifications.append((prediction[0],"tp",self.type,prediction[1]))
                else:
                    self.classifications.append((prediction[0],"tn",self.type,prediction[1]))
                for cls in self.classes:
                    if cls != trueClass:
                        self.trueNegativesByClass[cls] += 1
            elif predictedClass != trueClass:
                self.falsePositivesByClass[predictedClass] += 1
                if predictedClass == 1:
                    self.classifications.append((prediction[0],"fn",self.type,prediction[1]))
                else:
                    self.classifications.append((prediction[0],"fp",self.type,prediction[1]))
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
        totalWeight = 0.0
        for cls in self.classes:
            weigth = self.instancesByClass[cls]
            self.microPrecision += weigth * self.precisionByClass[cls]
            self.microRecall += weigth * self.recallByClass[cls]
            self.microFScore += weigth * self.fScoreByClass[cls]
            totalWeight += float(weigth)
        if totalWeight != 0.0:
            if self.microPrecision != 0: self.microPrecision /= totalWeight
            if self.microRecall != 0: self.microRecall /= totalWeight
            if self.microFScore != 0: self.microFScore /= totalWeight 
        
        # Finally calculate macro-f-score
        for cls in self.classes:
            self.precision += self.precisionByClass[cls]
            self.recall += self.recallByClass[cls]
            self.fScore += self.fScoreByClass[cls]
        if self.precision != 0: self.precision /= float(len(self.classes))
        if self.recall != 0: self.recall /= float(len(self.classes))
        if self.fScore != 0: self.fScore /= float(len(self.classes))            
    
    def toStringConcise(self, indent=""):
        string = indent
        for cls in self.classes:
            string += self.classSet.getName(cls)
            string += " p/n:" + str(self.truePositivesByClass[cls]+self.falseNegativesByClass[cls]) + "/" + str(self.trueNegativesByClass[cls]+self.falsePositivesByClass[cls])
            string += " tp/fp|tn/fn:" + str(self.truePositivesByClass[cls]) + "/" + str(self.falsePositivesByClass[cls]) + "|" + str(self.trueNegativesByClass[cls]) + "/" + str(self.falseNegativesByClass[cls])
            string += " p/r/f:" + str(self.precisionByClass[cls])[0:6] + "/" + str(self.recallByClass[cls])[0:6] + "/" + str(self.fScoreByClass[cls])[0:6]
            string += "\n" + indent
        string += "averages:\n" + indent
        string += "micro p/r/f:" + str(self.microPrecision)[0:6] + "/" + str(self.microRecall)[0:6] + "/" + str(self.microFScore)[0:6]
        string += "\n" + indent
        string += "macro p/r/f:" + str(self.precision)[0:6] + "/" + str(self.recall)[0:6] + "/" + str(self.fScore)[0:6]
        return string