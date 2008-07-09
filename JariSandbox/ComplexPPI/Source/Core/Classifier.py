import sys
import combine
from Evaluation import Evaluation

defaultOptimizationParameters = {"c":[0.0001,0.001,0.01,0.1,1,10,100]}

class Classifier:
    def train(self, examples, parameters=None):        
        pass
    
    def classify(self, examples, parameters=None):
        pass
    
    def optimize(self, trainExamples, classifyExamples, parameters=defaultOptimizationParameters, evaluationClass=Evaluation, evaluationArgs=None):
        print >> sys.stderr, "Optimizing parameters"        
        parameterNames = parameters.keys()
        parameterNames.sort()
        parameterValues = []
        for parameterName in parameterNames:
            parameterValues.append([])
            for value in parameters[parameterName]:
                parameterValues[-1].append( (parameterName,value) )
        combinationLists = combine.combine(*parameterValues)
        combinations = []
        for combinationList in combinationLists:
            combinations.append({})
            for value in combinationList:
                combinations[-1][value[0]] = value[1]
        bestResult = None
        count = 1
        for combination in combinations:
            print >> sys.stderr, "Parameters "+str(count)+"/"+str(len(combinations))+":", str(combination)
            self.train(trainExamples, combination)
            predictions = self.classify(classifyExamples)        
            evaluation = evaluationClass(predictions)
            print >> sys.stderr, " " + evaluation.toStringConcise()
            if bestResult == None or evaluation.fScore > bestResult[1].fScore:
                bestResult = (predictions, evaluation, combination)
            count += 1
        return bestResult