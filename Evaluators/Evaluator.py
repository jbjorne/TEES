"""
Base class for Evaluators
"""
__version__ = "$Revision: 1.17 $"

g_evaluatorFieldnames = ["fold","class","positives","negatives","true positives","false positives","true negatives","false negatives","precision","recall","f-score","AUC"]

def compare(e1, e2):
    return e1.compare(e2)

class Evaluator:
    """
    An abstract base class for classes used to evaluate the performance of different classifiers.
    """
    def compare(self, evaluator):
        """
        Compare overall performance between two sets of classified examples.
        """
        raise NotImplementedError
    
    def getData(self):
        """
        Return the EvaluationData corresponding to the main evaluation criterion for this Evaluator.
        """
        raise NotImplementedError
    
    def average(evaluators):
        """
        Return the average of the main evaluation criteria for this Evaluator type.
        """
        raise NotImplementedError
    average = staticmethod(average)
    
    def pool(evaluators):
        """
        Return the average of the main evaluation criteria for this Evaluator type calculated
        by pooling all individual classifications.
        """
        raise NotImplementedError
    pool = staticmethod(pool)
    
    def _calculate(self, predictions):
        raise NotImplementedError
    
    def toStringConcise(self, indent="", title=None):
        raise NotImplementedError
    
    def toDict(self):
        raise NotImplementedError
    
    def saveCSV(self, filename, fold=None):
        import sys
        sys.path.append("..")
        import Utils.TableUtils as TableUtils
        dicts = self.toDict()
        if fold != None:
            for d in dicts:
                d["fold"] = fold
        TableUtils.addToCSV(dicts, filename, g_evaluatorFieldnames)

class EvaluationData:
    """
    Calculates F-score for data that can be divided into true/false positives and
    true/false negatives.
    """
    def __init__(self):
        self._tp = 0
        self._fp = 0
        self._tn = 0
        self._fn = 0
        self.resetStats()
    
    def resetStats(self):
        self.fscore = None
        self.precision = None
        self.recall = None
    
    def addInstance(self, trueClassIsPositive, predictedClassIsPositive):
        if trueClassIsPositive and predictedClassIsPositive:
            self.addTP()
        elif trueClassIsPositive and not predictedClassIsPositive:
            self.addFN()
        elif (not trueClassIsPositive) and predictedClassIsPositive:
            self.addFP()
        else: # (not trueClassIsPositive) and (not predictedClassIsPositive)
            self.addTN()
    
    def removeInstance(self, trueClassIsPositive, predictedClassIsPositive):
        self.resetStats()
        if trueClassIsPositive and predictedClassIsPositive:
            self._tp -= 1
        elif trueClassIsPositive and not predictedClassIsPositive:
            self._fn -= 1
        elif (not trueClassIsPositive) and predictedClassIsPositive:
            self._fp -= 1
        else: # (not trueClassIsPositive) and (not predictedClassIsPositive)
            self._tn -= 1
        
    def addTP(self, amount=1):
        self.resetStats()
        self._tp += amount

    def addFP(self, amount=1):
        self.resetStats()
        self._fp += amount
    
    def addTN(self, amount=1):
        self.resetStats()
        self._tn += amount
    
    def addFN(self, amount=1):
        self.resetStats()
        self._fn += amount
    
    def getTP(self): return self._tp
    def getFP(self): return self._fp
    def getTN(self): return self._tn
    def getFN(self): return self._fn
    
    def getNumInstances(self):
        return self._tp + self._fp + self._tn + self._fn
    
    def calculateFScore(self):
        assert self._tp >= 0 and self._fp >= 0 and self._tn >= 0 and self._fn >= 0, (self._tp, self._fp, self._tn, self._fn)
        if self._tp + self._fp > 0:
            self.precision = float(self._tp) / float(self._tp + self._fp)
        else:
            self.precision = 0.0
        if self._tp + self._fn > 0:
            self.recall = float(self._tp) / float(self._tp + self._fn)
        else:
            self.recall = 0.0
        if self.precision + self.recall > 0.0:
            self.fscore = (2*self.precision*self.recall) / (self.precision + self.recall)
        else:
            self.fscore = 0
    
    def prfToString(self):
        if self.fscore != "N/A":
            return "p/r/f:" + str(self.precision)[0:6] + "/" + str(self.recall)[0:6] + "/" + str(self.fscore)[0:6]
        else:
            return "p/r/f:N/A"
    
    def pnToString(self):
        return "p/n:" + str(self._tp+self._fn) + "/" + str(self._tn+self._fp)
    
    def instanceCountsToString(self):
        return "tp/fp|tn/fn:" + str(self._tp) + "/" + str(self._fp) + "|" + str(self._tn) + "/" + str(self._fn)
    
    def toStringConcise(self):
        return self.pnToString() + " " + self.instanceCountsToString() + " " + self.prfToString()

    def toDict(self):
        values = {}        
        values["positives"] = self._tp+self._fn
        values["negatives"] = self._tn+self._fp
        values["true positives"] = self._tp
        values["false positives"] = self._fp
        values["true negatives"] = self._tn
        values["false negatives"] = self._fn
        values["precision"] = self.precision
        values["recall"] = self.recall
        values["f-score"] = self.fscore
        values["AUC"] = "N/A"
        return values
    
    def saveCSV(self, filename, fold=None):
        global g_evaluatorFieldnames
        import sys
        sys.path.append("..")
        import Utils.TableUtils as TableUtils
        dicts = self.toDict()
        if fold != None:
            for d in dicts:
                d["fold"] = fold
        #TableUtils.addToCSV(dicts, filename, g_evaluatorFieldnames)
        TableUtils.writeCSV(dicts, filename, g_evaluatorFieldnames, writeTitles=True)

def calculateFromCSV(rows, EvaluatorClass, classSet=None):
    if EvaluatorClass().type == "multiclass" and classSet == None:
        classSet = getClassSet(rows)
        
    predictions = []
    for row in rows:
        if classSet != None:
            predictions.append( ((row["id"],classSet.getId(row["class"])),classSet.getId(row["prediction"]),None,None) )
        else:
            predictions.append( ((row["id"],int(row["class"])),float(row["prediction"]),None,None) )
    # Calculate statistics
    return EvaluatorClass(predictions, classSet)

def getClassSet(rows, classSet=None):
    from Core.IdSet import IdSet
    classNames = set()
    for row in rows:
        classNames.add(row["class"])
        classNames.add(row["prediction"])
    
    # In the case of multiclass, give integer id:s for the classes
    if classSet == None:
        classSet = IdSet()
        assert(not ("1" in classNames and "neg" in classNames))
        assert("1" in classNames or "neg" in classNames)
        if "1" in classNames:
            classSet.defineId("1",1)
        else:
            classSet.defineId("neg",1)
    for i in sorted(list(classNames)):
        if i != "1" and i != "neg":
            classSet.getId(i)
    return classSet
                
def evaluateCSV(rows, options, EvaluatorClass = None):
    import sys, os
    sys.path.append("..")
    from Core.IdSet import IdSet
    import Utils.TableUtils as TableUtils
    
    if EvaluatorClass == None:
        print >> sys.stderr, "Importing modules"
        exec "from Evaluators." + options.evaluator + " import " + options.evaluator + " as EvaluatorClass"
    
    foldDict = {}
    for row in rows:
        if row["fold"] != None and row["fold"] != "":
            if not foldDict.has_key(row["fold"]):
                foldDict[row["fold"]] = []
            foldDict[row["fold"]].append(row)
    
    classSet = None
    if EvaluatorClass().type == "multiclass":
        classSet = getClassSet(rows)
    
    # Calculate performance per fold and the averages
    if len(foldDict) == 0:
        evaluator = calculateFromCSV(rows, EvaluatorClass, classSet)
        print >> sys.stderr, evaluator.toStringConcise("  ")
        if options.output != None:
            evaluator.saveCSV(options.output)
    else:
        evaluators = []
        for key in sorted(foldDict.keys()):
            print >> sys.stderr, "Fold", key
            evaluator = calculateFromCSV(foldDict[key], EvaluatorClass, classSet)
            print >> sys.stderr, evaluator.toStringConcise("  ")
            if options.output != None:
                evaluator.saveCSV(options.output, key)
            evaluators.append(evaluator)

        print >> sys.stderr, "Averages:"
        print >> sys.stderr, "Avg"
        averageResult = EvaluatorClass.average(evaluators)
        print >> sys.stderr, averageResult.toStringConcise("  ")
        pooledResult = EvaluatorClass.pool(evaluators)
        print >> sys.stderr, "Pool"
        print >> sys.stderr, pooledResult.toStringConcise("  ")
        if options.output != None:
            averageResult.saveCSV(options.output, "Avg")
            pooledResult.saveCSV(options.output, "Pool")

if __name__=="__main__":
    import sys, os
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"
    sys.path.append("..")
    from Utils.ProgressCounter import ProgressCounter
    from Utils.Parameters import splitParameters
    from optparse import OptionParser
    import Core.ExampleUtils as ExampleUtils
    from Core.IdSet import IdSet
    import Utils.TableUtils as TableUtils
    optparser = OptionParser(usage="%prog [options]\nCalculate f-score and other statistics.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Input file in csv-format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file for the statistics")
    optparser.add_option("-e", "--evaluator", default="BinaryEvaluator", dest="evaluator", help="Prediction evaluator class")
    (options, args) = optparser.parse_args()

    print >> sys.stderr, "Importing modules"
    exec "from Evaluators." + options.evaluator + " import " + options.evaluator + " as EvaluatorClass"
    
    if options.output != None:
        print >> sys.stderr, "Outputfile exists, removing", options.output
        if os.path.exists(options.output):
            os.remove(options.output)

    # Read input data
    fieldnames = ["class","prediction","id","fold"]
    rows = TableUtils.readCSV(options.input, fieldnames)
    evaluateCSV(rows, options, EvaluatorClass)