import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/..")
#sys.path.append("..")
from Utils.ProgressCounter import ProgressCounter
from Utils.Parameters import splitParameters
from optparse import OptionParser
import Core.ExampleUtils as ExampleUtils
from Core.IdSet import IdSet
import Utils.TableUtils as TableUtils
import Evaluator

if __name__=="__main__":
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print >> sys.stderr, "Found Psyco, using"
    except ImportError:
        print >> sys.stderr, "Psyco not installed"

    optparser = OptionParser(usage="%prog [options]\nCalculate f-score and other statistics.")
    optparser.add_option("-i", "--input", default=None, dest="input", help="Input file in csv-format", metavar="FILE")
    optparser.add_option("-p", "--parameters", default=None, dest="parameters", help="Input file in csv-format", metavar="FILE")
    optparser.add_option("-o", "--output", default=None, dest="output", help="Output file for the statistics")
    optparser.add_option("-e", "--evaluator", default="BinaryEvaluator", dest="evaluator", help="Prediction evaluator class")
    optparser.add_option("-c", "--classnames", default=None, dest="classNames", help="class names in Filip's format")
    (options, args) = optparser.parse_args()

    classNameDict = None
    classSet = None
    if options.classNames != None:
        classNameDict = {}
        classNameFile = open(options.classNames, "rt")
        lines = classNameFile.readlines()
        for line in lines:
            className, classId = line.rsplit(":",1)
            className = className.strip()
            classId = classId.strip()
            classNameDict[classId] = className
        classNameFile.close()
        classSet = IdSet(idDict=classNameDict, locked=True)

    if options.output != None:
        print >> sys.stderr, "Outputfile exists, removing", options.output
        if os.path.exists(options.output):
            os.remove(options.output)
    
    print >> sys.stderr, "Importing modules"
    exec "from Evaluators." + options.evaluator + " import " + options.evaluator + " as EvaluatorClass"
    fieldnames = ["class","prediction","id","fold","c"]
    
    # Find best c-parameter from parameter estimation data
    print >> sys.stderr, "Finding optimal c-parameters from", options.parameters    
    rows = TableUtils.readCSV(options.parameters, fieldnames)
    folds = sorted(list(TableUtils.getValueSet(rows, "fold")))
    cParameterByFold = {}
    for fold in folds:
        print >> sys.stderr, "  Processing fold", fold
        foldRows = TableUtils.selectRowsCSV(rows, {"fold":fold})
        cParameters = sorted(list(TableUtils.getValueSet(foldRows, "c")))
        evaluators = []
        cParameterByEvaluator = {}
        for cParameter in cParameters:
            print >> sys.stderr, "    Processing c-parameter", cParameter, 
            paramRows = TableUtils.selectRowsCSV(foldRows, {"c":cParameter})
            evaluator = Evaluator.calculateFromCSV(paramRows, EvaluatorClass, classSet)
            cParameterByEvaluator[evaluator] = cParameter
            evaluators.append(evaluator)
            if evaluator.type == "multiclass":
                print " F-score:", evaluator.microFScore
            else:
                print " F-score:", evaluator.fScore
        evaluators.sort(Evaluator.compare)
        print >> sys.stderr, "  Optimal C-parameter:", cParameterByEvaluator[evaluators[-1]]
        cParameterByFold[fold] = cParameterByEvaluator[evaluators[-1]]
    
    print >> sys.stderr, "Evaluating test data from", options.parameters
    rows = TableUtils.readCSV(options.input, fieldnames)
    selectedRows = []
    for fold in folds:
        foldRows = TableUtils.selectRowsCSV(rows, {"fold":fold})
        selectedRows.extend( TableUtils.selectRowsCSV(foldRows, {"c":cParameterByFold[fold]}) )
    
    if classNameDict != None:
        for row in selectedRows:
            if classNameDict.has_key(row["class"]):
                row["class"] = classNameDict[row["class"]]
            if classNameDict.has_key(row["prediction"]):
                row["prediction"] = classNameDict[row["prediction"]]

    Evaluator.evaluateCSV(selectedRows, options, EvaluatorClass)