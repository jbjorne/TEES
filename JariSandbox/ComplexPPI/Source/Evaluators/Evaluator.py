g_evaluatorFieldnames = ["fold","class","positives","negatives","true positives","false positives","true negatives","false negatives","precision","recall","f-score","AUC"]

def compare(e1, e2):
    return e1.compare(e2)

class Evaluator:
    def compare(self, evaluator):
        raise NotImplementedError
    
    def average(evaluators):
        raise NotImplementedError
    average = staticmethod(average)
    
    def pool(evaluators):
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

def calculateFromCSV(rows, EvaluatorClass, classSet=None):
    predictions = []
    for row in rows:
        if classSet != None:
            predictions.append( ((row["id"],classSet.getId(row["prediction"])),classSet.getId(row["class"])) )
        else:
            predictions.append( ((row["id"],float(row["prediction"])),int(row["class"])) )
    # Calculate statistics
    return EvaluatorClass(predictions, classSet)

def evaluateCSV(rows, options, EvaluatorClass = None):
    import sys, os
    sys.path.append("..")
    from Core.IdSet import IdSet
    import Utils.TableUtils as TableUtils
    
    if EvaluatorClass == None:
        print >> sys.stderr, "Importing modules"
        exec "from Evaluators." + options.evaluator + " import " + options.evaluator + " as EvaluatorClass"

    foldDict = {}
    classNames = set()
    for row in rows:
        classNames.add(row["class"])
        classNames.add(row["prediction"])
        if row["fold"] != None and row["fold"] != "":
            if not foldDict.has_key(row["fold"]):
                foldDict[row["fold"]] = []
            foldDict[row["fold"]].append(row)
    
    # In the case of multiclass, give integer id:s for the classes
    classSet = None
    if EvaluatorClass().type == "multiclass":
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